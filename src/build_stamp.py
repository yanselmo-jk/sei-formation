#!/usr/bin/env python3
"""빌드 신선도 원장 — **"tarball이 소스보다 낡았다"를 자동으로 잡는다.**

🔴 왜 생겼나: lead가 `dist/*.tar.gz`(16:49)와 `payload/qc_adapter.sh`(17:01)의 mtime을
**우연히 눈으로 비교해서** 낡은 패키지를 잡았다. 그 방식은 다음에 반복되지 않는다.
인도 직전에 "내 수정이 안 들어간 패키지"를 보내는 것은 왕복 1회(3.5일)를 통째로 버린다.

방식: 빌드 시 소스 트리의 **내용 해시**와 시각을 `dist/BUILD_STAMP.json` 에 남기고,
`check` 가 현재 소스와 비교한다. mtime이 아니라 **내용 해시**가 기준이다
(touch/포맷 변경으로 거짓 경고가 나면 사람이 경고를 무시하게 된다).

    python3 src/build_stamp.py write   # make_package.sh 가 호출
    python3 src/build_stamp.py check   # 종료코드 1 = tarball이 낡았다
"""

import argparse
import hashlib
import json
import os
import sys
import time

SRC_SUBDIR = os.path.join("src", "pilot_package")
STAMP = "BUILD_STAMP.json"
EXCLUDE_DIRS = ("__pycache__", "sei_pilot_work", "dist", ".session_state")
INCLUDE_EXT = (".py", ".sh", ".tmpl", ".inp", ".xyz", ".json", ".md")
#: 빌드가 스스로 바꾸는 파일 — 비교에서 뺀다(넣으면 매번 거짓 경고가 난다)
EXCLUDE_NAMES = ("PROFILE",)


def source_files(root):
    base = os.path.join(root, SRC_SUBDIR)
    out = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS)
        for fn in sorted(filenames):
            if fn in EXCLUDE_NAMES or not fn.endswith(INCLUDE_EXT):
                continue
            out.append(os.path.join(dirpath, fn))
    return sorted(out)


def source_digest(root):
    """소스 트리 내용 해시 + 파일별 해시(무엇이 바뀌었는지 지목하기 위해)."""
    h = hashlib.sha256()
    per_file = {}
    base = os.path.join(root, SRC_SUBDIR)
    for path in source_files(root):
        rel = os.path.relpath(path, base)
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            data = b"<unreadable>"
        fh_hash = hashlib.sha256(data).hexdigest()[:16]
        per_file[rel] = fh_hash
        h.update(rel.encode("utf-8"))
        h.update(fh_hash.encode("ascii"))
    return h.hexdigest()[:16], per_file


def cmd_write(args):
    digest, per_file = source_digest(args.root)
    stamp = {
        "_doc": "이 dist/ 가 어느 소스에서 나왔는지. check 가 이것과 현재 소스를 비교한다.",
        "built_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "built_at_epoch": int(time.time()),
        "source_digest": digest,
        "n_files": len(per_file),
        "per_file": per_file,
        "tarballs": {},
    }
    for fn in sorted(os.listdir(args.dist)):
        if fn.endswith(".tar.gz"):
            path = os.path.join(args.dist, fn)
            stat = os.stat(path)
            # 🔴 sha256 을 기록한다. 크기만으로는 **같은 트리임을 증명하지 못한다** —
            #    소스가 바뀌어도 tarball 크기는 같을 수 있다. lead 가 critic 이 리뷰한
            #    트리와 사용자에게 가는 트리의 동일성을 해시로 못박겠다고 요구했고,
            #    그 요구가 이 구멍을 드러냈다(기록이 size/mtime 뿐이었다).
            with open(path, "rb") as fh:
                digest_hex = hashlib.sha256(fh.read()).hexdigest()
            stamp["tarballs"][fn] = {"size": stat.st_size,
                                     "sha256": digest_hex,
                                     "mtime_epoch": int(stat.st_mtime)}
    with open(os.path.join(args.dist, STAMP), "w") as fh:
        json.dump(stamp, fh, ensure_ascii=False, indent=1)
    print("[stamp] source_digest=%s  files=%d  tarballs=%d"
          % (digest, len(per_file), len(stamp["tarballs"])))
    return 0


#: 🔒 빌드 후 산출물 검증(`make_package.sh` [6단계])이 실패하면 여기에 남는다.
#: 🔴 lead 요구: **"검증 실패는 사람들이 이미 돌리는 게이트를 통해 드러나야 한다."**
#:  표시 파일만 두면 *"다음 사람이 그 파일을 본다"* 는 **습관**에 기대게 되고,
#:  이번 사건의 교훈이 정확히 *"구조가 아니라 습관으로 막혔다"* 였다.
#:  ⟹ 이 표시가 있는 동안 `check` 는 **절대 ✅ 를 내지 않는다.**
VERIFICATION_FAILED = "VERIFICATION_FAILED.json"


def check(root, dist):
    """반환 (ok, 문제 목록). 조용히 통과시키지 않는다."""
    path = os.path.join(dist, STAMP)
    problems = []
    # 🔴 **가장 먼저 본다.** 산출물 검증이 실패한 채 남아 있으면 그 사실이 다른 무엇보다 먼저다.
    #    (tarball 은 일부러 지우지 않는다 — 지우면 "아직 안 만들었나 보다"로 오독된다.
    #     남기되 **건강해 보이지 않게** 하는 것이 이 표시의 목적이다.)
    marker = os.path.join(dist, VERIFICATION_FAILED)
    if os.path.exists(marker):
        detail = ""
        try:
            with open(marker) as fh:
                detail = json.load(fh).get("reason", "")
        except (OSError, ValueError):
            detail = "(표시 파일을 읽지 못했다)"
        problems.append(
            "🔴 이 dist/ 는 **산출물 검증에 실패한 상태**다 — 인도하지 마라.\n"
            "    사유: %s\n"
            "    tarball 은 조사할 수 있게 일부러 남겨 뒀다.\n"
            "    → 고친 뒤 src/make_package.sh 를 다시 실행하면 이 표시가 사라진다."
            % (detail or "(사유 없음)"))
    try:
        with open(path) as fh:
            stamp = json.load(fh)
    except (OSError, ValueError):
        # 🔴 marker 메시지를 버리지 않는다 — 이른 return 이 그것을 삼키면
        #    "검증 실패"가 "스탬프 없음"으로 바뀌어 보고된다(사유가 바뀌는 것은 위험하다).
        return False, problems + [
            "빌드 스탬프가 없다(%s) — 이 dist/ 가 어느 소스에서 나왔는지 "
            "알 수 없다. make_package.sh 를 다시 돌려라." % path]
    digest, per_file = source_digest(root)
    if digest != stamp.get("source_digest"):
        changed = [f for f, h in sorted(per_file.items())
                   if stamp.get("per_file", {}).get(f) != h]
        gone = [f for f in sorted(stamp.get("per_file") or {}) if f not in per_file]
        # 🔴 잘못된 --root 를 "소스가 통째로 삭제됐다"로 보고하면 안 된다.
        #    (실제로 `--root src` 로 잘못 호출해 68개 파일이 사라졌다는 오경보가 났다.)
        #    오경보는 진짜 경보를 믿지 않게 만들어서, 낡은 tarball 보다 더 위험하다.
        n_stamped = len(stamp.get("per_file") or {})
        if n_stamped and len(gone) > n_stamped * 0.5:
            return False, problems + [
                "🔴 스탬프에 기록된 파일의 %d/%d 가 이 root 아래에 없다."
                % (len(gone), n_stamped),
                "    이건 '소스가 낡았다'가 아니라 **--root 가 잘못됐을 가능성이 크다.**",
                "    지금 root : %s" % os.path.abspath(root),
                "    기대하는 것: pilot_package 를 담고 있는 **저장소 루트**",
                "    예: python3 src/build_stamp.py check --root . --dist src/dist",
            ]
        problems.append("🔴 tarball 이 현재 소스보다 낡았다 — 지금 인도하면 "
                        "아래 수정이 **패키지에 들어가지 않는다.**")
        for f in (changed + ["(삭제됨) " + g for g in gone])[:12]:
            problems.append("    변경: %s" % f)
        if len(changed) + len(gone) > 12:
            problems.append("    … 외 %d개" % (len(changed) + len(gone) - 12))
        problems.append("    → 고치는 법: src/make_package.sh 를 다시 실행하라.")
    for fn, meta in sorted((stamp.get("tarballs") or {}).items()):
        p = os.path.join(dist, fn)
        if not os.path.exists(p):
            problems.append("스탬프에 있는 tarball 이 없다: %s" % fn)
        elif os.stat(p).st_size != meta.get("size"):
            problems.append("tarball 크기가 스탬프와 다르다(빌드 후 덮어썼나?): %s" % fn)
        elif meta.get("sha256"):
            with open(p, "rb") as fh:
                got = hashlib.sha256(fh.read()).hexdigest()
            if got != meta["sha256"]:
                problems.append(
                    "🔴 tarball 내용이 스탬프의 sha256 과 다르다: %s\n"
                    "    스탬프: %s\n    실제  : %s\n"
                    "    → 빌드 후 파일이 바뀌었다. 크기가 같아도 내용은 다르다."
                    % (fn, meta["sha256"][:16], got[:16]))
    return (not problems), problems


def cmd_check(args):
    ok, problems = check(args.root, args.dist)
    if ok:
        print("[stamp] ✅ tarball 이 현재 소스와 일치한다.")
        return 0
    for p in problems:
        sys.stderr.write(p + "\n")
    return 1


def main(argv=None):
    root_default = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description="빌드 신선도 원장")
    ap.add_argument("command", choices=["write", "check"])
    ap.add_argument("--root", default=root_default)
    ap.add_argument("--dist", default=None)
    args = ap.parse_args(argv)
    args.dist = args.dist or os.path.join(args.root, "src", "dist")
    if not os.path.isdir(args.dist):
        sys.stderr.write("dist 디렉터리가 없다: %s\n" % args.dist)
        return 1
    return cmd_write(args) if args.command == "write" else cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
