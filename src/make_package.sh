#!/bin/bash
# 사용자에게 보낼 tarball **2개**를 만든다 (CPU 클러스터 / GPU 머신은 물리적으로 분리).
#   ./make_package.sh [출력디렉터리]
# 산출물: dist/sei_pilot_cpu.tar.gz , dist/sei_pilot_gpu.tar.gz (+ .sha256)
set -eu

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${1:-$HERE/dist}"
mkdir -p "$OUT_DIR"

# --- [0/7] DISK PREFLIGHT ---------------------------------------------------------------
# 🔴 A FULL /tmp HAS ABORTED THIS BUILD TWICE (HANDOFF §44.6, §41.4). Both times the failure
#    surfaced as a `cp` error mid-build, dist/ left empty and the old artefacts stranded in
#    .stale.* -- which looks exactly like "never built". §44.6's own words: the disk-space
#    preflight "is no longer hypothetical".
# 🔴 AND /tmp ON THIS BOX IS REAPED WITHIN A SESSION -- free space at the start of your work is
#    not evidence about free space now, in either direction. Measure it here, at the build.
# The suite writes its temp trees under $TMPDIR (default /tmp) and the build copies a ~19 MB
# tarball twice; the floor below is deliberately generous and cheap to satisfy.
MIN_FREE_MB="${SEI_MIN_FREE_MB:-500}"
for target in "${TMPDIR:-/tmp}" "$OUT_DIR"; do
  free_mb="$(df -Pm "$target" 2>/dev/null | awk 'NR==2 {print $4}')"
  if [ -z "$free_mb" ]; then
    echo "[0/7] ⚠ could not read free space for $target -- proceeding, but if this build dies in"
    echo "      a cp/tar step, check the disk BEFORE reading it as a code failure."
    continue
  fi
  echo "[0/7] free space $target: ${free_mb} MB (floor ${MIN_FREE_MB} MB)"
  if [ "$free_mb" -lt "$MIN_FREE_MB" ]; then
    echo "🔴 BUILD REFUSED: only ${free_mb} MB free on $target, below the ${MIN_FREE_MB} MB floor."
    echo "   Refusing rather than aborting mid-flight: a build that dies after [0/5] leaves dist/"
    echo "   empty with a .stale.* beside it, and that state is indistinguishable from"
    echo "   'never built' (HANDOFF §45.1). Free space, or raise SEI_MIN_FREE_MB deliberately."
    exit 1
  fi
done

# 🔴 낡은 산출물을 **먼저** 치운다. 안 그러면 교착이 난다:
#    "dist 가 낡았다" 는 테스트가 실패 → 테스트가 실패해서 빌드 중단 → 영원히 못 고침.
#    (실제로 이 교착에 걸렸다.) 치우고 나면 그 테스트는 '검사할 것 없음'으로 건너뛴다.
STALE="$OUT_DIR/.stale.$$"
if ls "$OUT_DIR"/sei_pilot_*.tar.gz > /dev/null 2>&1; then
  mkdir -p "$STALE"
  mv "$OUT_DIR"/sei_pilot_*.tar.gz "$OUT_DIR"/sei_pilot_*.tar.gz.sha256 \
     "$OUT_DIR"/BUILD_STAMP.json "$STALE"/ 2>/dev/null || true
  echo "[0/5] 낡은 산출물을 $STALE 로 치웠다 (빌드 성공 시 삭제)"
fi

echo "[1/5] 테스트 실행"
( cd "$HERE/.." && python3 -m unittest discover -s tests -q ) || {
  echo "테스트 실패 — 패키지를 만들지 않는다."
  [ -d "$STALE" ] && { mv "$STALE"/* "$OUT_DIR"/ 2>/dev/null; rmdir "$STALE"; \
                       echo "  ↳ 이전 산출물을 되돌렸다."; }
  exit 1; }

echo "[2/5] dry-run 스모크 (두 프로파일 모두)"
for prof in cpu gpu; do
  echo "$prof" > "$HERE/pilot_package/PROFILE"
  ( cd "$HERE/pilot_package" && SEI_WORKDIR="$(mktemp -d)" ./run.sh --dry-run > /dev/null ) || {
    echo "dry-run($prof) 실패 — 패키지를 만들지 않는다."; exit 1; }
done

echo "[3/5] tarball 2개 생성"
BUILD="$(mktemp -d)"
for prof in cpu gpu; do
  DEST="$BUILD/sei_pilot_${prof}"
  rm -rf "$DEST"
  cp -r "$HERE/pilot_package" "$DEST"
  rm -rf "$DEST/sei_pilot_work" "$DEST/dist"
  find "$DEST" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
  find "$DEST" -name '*.pyc' -delete 2>/dev/null || true
  echo "$prof" > "$DEST/PROFILE"
  # 프로파일별 사용자 안내만 남긴다 (다른 쪽 문서를 보고 헷갈리지 않게)
  mv "$DEST/README_USER.${prof}.md" "$DEST/README_USER.md"
  rm -f "$DEST"/README_USER.*.md
  # 🔴 동봉 xtb 는 P3(조합 폭발 계수) 전용이고 P3 는 cpu 프로파일에만 있다.
  #    GPU 패키지에 넣으면 쓰지도 않을 19 MB 를 사용자가 옮기게 된다.
  if [ "$prof" = "gpu" ]; then
    rm -rf "$DEST/vendor"
  fi
  tar czf "$OUT_DIR/sei_pilot_${prof}.tar.gz" -C "$BUILD" "sei_pilot_${prof}"
done
rm -rf "$BUILD"
echo "cpu" > "$HERE/pilot_package/PROFILE"

echo "[4/7] 지문 기록"
( cd "$OUT_DIR" && for f in sei_pilot_cpu.tar.gz sei_pilot_gpu.tar.gz; do
    sha256sum "$f" > "$f.sha256"; done )

# 🔴 [5/6] 신선도 원장 — "tarball이 소스보다 낡았다"를 다음번엔 **자동으로** 잡는다.
#    lead가 mtime을 우연히 봐서 잡았고, 그 방식은 다음에 반복되지 않는다.
python3 "$HERE/build_stamp.py" write --root "$HERE/.." --dist "$OUT_DIR"
echo "[5/7] 빌드 스탬프 기록 완료"

echo "[7/7] 요약"
python3 - "$HERE/pilot_package" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from sei_pilot import budget, plan, version
print("package_version    :", version.PKG_VERSION)
print("schema_version     :", version.SCHEMA_VERSION)
print("package_fingerprint:", version.package_fingerprint(sys.argv[1]))
for prof in plan.PROFILES:
    g = budget.guard_for_profile(prof)
    items = plan.default_items(prof)
    print("  %-3s: %2d개 항목 %-52s 가드 %.0f core-h / %.0f GPU-h / %.0f h wall"
          % (prof, len(items), ",".join(i.key for i in items)[:52],
             g.max_core_hours, g.max_gpu_hours, g.max_wall_h))
PY
echo
# 🔴 **동일성 지표를 맨 위에 찍는다.** 사람이 먼저 보는 숫자가 인용되기 때문이다.
#    사고 경위: 동결·리뷰 대상 지시를 tarball `sha256` 으로 내다가 **네 번 어긋났다.**
#    원인의 절반은 "낡은 값을 인용한 것"이 아니라 **그 값이 애초에 동일성 지표가 아니었던 것**이다
#    — gzip 에 mtime 이 들어가서 **같은 소스도 재빌드하면 sha256 이 달라진다.**
#    ⟹ 도구(`build_stamp`)는 원래부터 내용 해시로 옳게 동작하고 있었고, **출력이 사람을
#      잘못된 숫자로 유도**하고 있었다. (가드 거부 화면이 `--max-core-hours` 를 권하던 것과 같은 부류다.)
echo " ─────────────────────────────────────────────────────────────────"
python3 - "$OUT_DIR" <<'PY2'
import json, os, sys
try:
    d = json.load(open(os.path.join(sys.argv[1], "BUILD_STAMP.json")))
    print("  source_digest : %s   ← 🔒 **동결·리뷰·인도본 동일성은 이 값으로**"
          % d.get("source_digest"))
    print("                  (소스 내용 해시. 소스가 실제로 바뀌어야 변한다)")
except Exception as exc:                      # noqa: BLE001
    print("  🔴 BUILD_STAMP 를 읽지 못했다: %s" % exc)
PY2
echo " ─────────────────────────────────────────────────────────────────"
ls -lh "$OUT_DIR"/*.tar.gz | awk '{print " ", $9, $5}'
for f in "$OUT_DIR"/*.tar.gz; do
  echo "  sha256 $(basename "$f") : $(cut -d" " -f1 < "$f.sha256")"
done
echo "  ↳ sha256 은 **전송 무결성용**이다. 재빌드마다 바뀌므로 동일성 비교에 쓰지 마라."
# 🔒 [6/7] 산출물 검증 관문 — **빌드 후에** 실제 tarball 을 열어 검사한다.
#
# 🔴 왜 여기인가: 위 [1] 의 전체 스위트는 tarball 이 `.stale` 로 치워진 뒤에 돌기 때문에
#    tarball 을 여는 검사는 **반드시 skip 된다.** 그건 교착 회피를 위해 의도한 것이다
#    (주석 [0/5] 참조). 그 결과 **인도물이 만들어지는 바로 그 순간에 아무도 안 보는**
#    구간이 생겼다 — 이 프로젝트가 반복한 "검사는 있는데 안 도는" 형태다.
#    ⟹ 검사 대상이 **방금 생긴 뒤** 한 번 더 돌린다. [1] 의 skip 성질은 그대로 둔다.
#
# 🔴 실패 시 거동(lead 판정): tarball 을 **지우지도, 되돌리지도 않는다.**
#    · 지우면 "아직 안 만들었나 보다"로 오독된다.
#    · `.stale` 로 되돌리면 **낡은 tarball 과 낡은 스탬프가 서로 일치**해
#      `build_stamp check` 가 ✅ 를 낸다 — 실패가 완전히 건강해 보인다(최악).
#    ⟹ 남기되 **건강해 보이지 않게** 한다: VERIFICATION_FAILED.json 을 남기고,
#      `build_stamp.py check` 가 그 표시를 보면 절대 ✅ 를 내지 않는다.
#      (표시 파일만 두면 "다음 사람이 그 파일을 본다"는 **습관**에 기대게 된다.)
echo "[6/7] 산출물 검증 (인도물 tarball 을 열어 확인)"
# 🔴 `tests/` 디렉터리 **안에서** 돌린다. 저장소 루트에서 `tests.test_...` 로 부르면
#    `import context` 가 `ModuleNotFoundError` 로 죽고, unittest 는 그것을 **"테스트 1건 실패"**
#    로 보고한다 — 즉 **검증이 실패한 것처럼 보이지만 실은 실행조차 안 된 것**이다.
#    (실제로 이 관문의 첫 판이 그렇게 오작동했다. 다행히 **실패 쪽으로** 틀려서 눈에 띄었다.)
# 🔴 클래스 이름을 여기 적지 않는다. `packaged_gate` 가 **tarball 을 여는 검사를 스스로
#    찾아** 전부 돌린다. 이름을 적으면 새 검사를 만든 사람이 **여기에도 손으로 추가해야 하고
#    언젠가 잊는다** — 그건 우리가 없애려는 "사람이 기억해야 작동하는 보호"다.
if ( cd "$HERE/../tests" && python3 -m unittest -q packaged_gate ); then
  rm -f "$OUT_DIR/VERIFICATION_FAILED.json"
else
  python3 - "$OUT_DIR" <<'PYV'
import json, os, sys, time
json.dump({"reason": "인도물 tarball 검증 실패 — tarball 을 여는 검사 중 하나가 "
                     "실패했다. 재현: cd tests && python3 -m unittest packaged_gate",
           "failed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
          open(os.path.join(sys.argv[1], "VERIFICATION_FAILED.json"), "w"),
          ensure_ascii=False, indent=1)
PYV
  echo "🔴 산출물 검증 실패 — tarball 은 조사할 수 있게 남겨 뒀다."
  echo "   `build_stamp.py check` 가 이 상태를 ✅ 로 보고하지 않는다."
  exit 1
fi

echo
[ -d "$STALE" ] && rm -rf "$STALE"
python3 "$HERE/build_stamp.py" check --root "$HERE/.." --dist "$OUT_DIR" || {
  echo "🔴 빌드 직후인데 스탬프 점검이 실패했다 — 빌드 로직 자체를 확인하라."; exit 1; }
echo
echo "사용자에게 전달: CPU 클러스터에 sei_pilot_cpu.tar.gz, GPU 머신에 sei_pilot_gpu.tar.gz"
echo "               각각 ./run.sh 후 results/sei_probe_report.<프로파일>.json 회신"
