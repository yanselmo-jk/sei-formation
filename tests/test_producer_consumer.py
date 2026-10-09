"""생산자 → 소비자 경계 검사 — **만들어 놓고 아무도 안 읽는 값을 잡는다.**

🔴 이 검사가 왜 생겼나: **같은 병이 네 번 났고 전부 크래시가 없었다.**

| # | 유실된 값 | 형태 |
|---|---|---|
| 3 | `host` (probe_throughput) | payload 가 기록 → collector 가 꺼내 쓰지 않음 |
| 4 | 큐 wall 상한 | `sysprobe` 가 수집 → `build_plan` 이 안 봄 |
| 6 | **P5 `seed`/dual-seed 메타** | payload 가 기록 → `normalize_rows` 가 버림 |
| 7 | **`queue_selected`** | 계산만 되고 **읽는 코드가 0곳** |

**전부 "생산자는 만들고 소비자가 없다"이고, 전부 회신 JSON 이 정상 형태였다.**
그래서 사람 눈으로는 안 잡히고, **결함은 사용자 클러스터에서 며칠 뒤에 드러난다.**

🔴 **일회성 감사로는 못 막는다** — 감사는 다음에 새는 것을 막지 못한다.
그래서 **테스트**로 둔다(`TestNoDuplicateTestClassNames` 를 AST 로 만든 것과 같은 방식).

⚠ **오탐이 나온다.** 의도적으로 안 읽는 값(진단용 원문 등)이 있기 때문이다.
⟹ **화이트리스트를 두되 반드시 사유를 요구한다.** 사유 없는 면제는 이 검사를 껍데기로 만든다.
"""

import os
import re
import unittest

import context  # noqa: F401

PKG = context.PKG_ROOT
SEI = os.path.join(PKG, "sei_pilot")
PAYLOAD = os.path.join(PKG, "payload")


def python_sources(exclude=()):
    out = []
    for root, _dirs, files in os.walk(SEI):
        if "__pycache__" in root:
            continue
        for f in sorted(files):
            if f.endswith(".py") and f not in exclude:
                out.append(os.path.join(root, f))
    return out


def read_all(paths):
    return "\n".join(open(p, encoding="utf-8").read() for p in paths)


def is_referenced(key, text):
    """키가 소비되는가. 문자열 리터럴로 등장하면 소비로 본다."""
    return ('"%s"' % key) in text or ("'%s'" % key) in text


#: 🔴 면제에는 **사유가 필수**다. 사유 없는 면제는 이 검사를 껍데기로 만든다.
SYSPROBE_EXEMPT = {
    # (지금은 비어 있다. 새 면제를 넣을 때는 반드시 사유를 함께 적어라.)
}

#: payload 가 쓰는 아티팩트 중, collector 가 **통째로 회신에 싣는** 것.
#: 이 경우 개별 키를 파이썬에서 이름으로 부르지 않아도 값은 보존된다.
WHOLE_DICT_PASSTHROUGH = {
    "adapter.json": "collect_p1/p1b/p5 가 res['adapter'] 로 통째로 싣는다",
    "u27_noneq.json": "collect_p1b 가 res['u27_noneq'] 로 통째로 싣는다",
    "smoke_levels.json": "collect_p1 이 res['smoke_levels'] 로 통째로 싣는다",
    "p5_seeds.json": "P5.sh 가 각 행의 seed_provenance 로 합쳐 넣는다",
    "crest_status.json": "collect.p1_degradation 이 필드를 개별로 읽는다",
    "p6_anchor.json": "collect_p6 가 필드를 개별로 읽는다",
    "p7_result.json": "P7 은 패키지 밖(ADR-050 게이트 대기)",
    "cp2k_env.txt": "P7 은 패키지 밖",
    "stage0_result.json": (
        "Stage 0 (MTD-pilot comparator, §39.40(d)-RESULT/§39.47(b))는 run.sh 의 "
        "plan-item/collect 파이프라인 밖에서 손으로 스테이징되는 잡이다 -- 이번 라운드의 "
        "다른 모든 진단 덱(candidate B/EulerPC/DVV/B+)과 같은 패턴, P7 과 같은 이유. "
        "stage0_result.json 은 이 빌드 자신의 README 가 지시하는 대로 사람이 직접 읽는다. "
        "stage0 이 나중에 실제 plan Item 으로 승격되면 그때 collector 를 같이 고쳐라."),
    # --- payload 내부 중간 파일 (collector 가 읽을 대상이 아니다) ---
    "candidate.json": "P3 내부: 후보별 중간 파일. 집계는 p3_attempts.json 이 한다",
    "meta.json": "종/스텝별 중간 메타. 집계본(p5_results.json 등)에 합쳐져 나간다",
    "1.json": "정규식 잡음 — `stages/$1.json` 의 셸 변수 치환 흔적이지 파일명이 아니다",
    # --- 🔴 진짜 휴면 유실 2건 (지금은 무해하지만 되살아나면 샌다) ---
    # 🔴🔴 아래 두 건은 **같은 조건(P3 부활)에서 함께 살아난다.** 하나만 고치지 마라.
    #    ADR-049 가 P3 를 뺀 이유는 *"비용이 아니라 **이미 측정됐기 때문**"* 이다
    #    (RT-1 에서 pass, 시도단가 0.10038 · 수렴률 31.7%).
    #    ⟹ **P3 를 되살리는 조건 = 그 측정을 다시 믿을 수 없게 된 때**이고,
    #      그때는 **이 두 아티팩트가 동시에 필요해진다** — 하나는 시도 품질, 하나는
    #      "어느 xtb 로 쟀는가"다. **품질만 알고 출처를 모르면 해석이 안 된다.**
    "p3_attempt_quality.json": (
        "🔴 **실제 미소비다.** P3 가 시도 품질을 기록하는데 collector 가 읽지 않는다. "
        "지금 무해한 이유는 **P3 가 ADR-049 로 계획에서 빠졌기 때문**이지 고쳐서가 아니다. "
        "🔒 P3 를 되살리면 **이 항목과 `xtb_source.json` 을 함께 고쳐라.**"),
    "xtb_source.json": (
        "🔴 **실제 미소비다.** 동봉본을 썼는지 사이트 설치본을 썼는지를 기록하는 "
        "**provenance** 인데 회신에 실리지 않는다. 버전이 다르면 단가 해석이 달라진다. "
        "지금 무해한 이유는 P3 가 계획에서 빠졌기 때문이다. "
        "🔒 P3 부활 시 `p3_attempt_quality.json` 과 **함께** 고쳐라 — 같은 조건에서 "
        "같이 살아나고, 둘 중 하나만 있으면 단가 해석이 성립하지 않는다."),
    # 🔴 [critic3 재재리뷰 신규] `p4_result.json` 은 **파일은 열리는데 필드가 샌다.**
    #    `gpu_error / cpu_error / fatal / gpu_failure_class / gpu_fix_hint(symptom, pip,
    #    why, ld_library_path) / memscan_error / memscan_stopped / oom_error /
    #    n_basis_functions / gpu_count / cpu_reference_machine` 가 `criteria/p4.py` 에서
    #    읽히지 않는다. **특히 `gpu_fix_hint` 는 GPU import 실패 시 구체적 pip 처방을 담은
    #    진단인데 통째로 사라진다** — 그게 없으면 왕복 하나를 더 써야 한다.
    #    🔴 지금 무해한 이유는 **ADR-037 로 GPU 패키지가 인도되지 않기 때문**이지
    #    고쳐서가 아니다. 🔒 **GPU 패키지를 되살리면 `pystack.json` 과 함께 고쳐라.**
    #    ⚠ 그리고 이 검사는 **파일 단위**만 본다 — 필드 단위 유실은 못 잡는다.
    #      (critic3 가 사람 손으로 잡았다. 검사의 한계를 여기 적어 둔다.)
    "p4_result.json": (
        "🔴 **필드 단위 미소비.** 파일은 collect_p4 가 열지만 위 12개 필드가 criteria/p4.py "
        "에서 안 읽힌다. ADR-037(GPU 드롭)로 지금 무해. GPU 부활 시 pystack.json 과 함께 고쳐라."),
    "pystack.json": (
        "🔴 **실제 미소비다.** GPU 프로파일 프로브 산출물인데 읽는 곳이 없다. "
        "지금 무해한 이유는 **ADR-037 로 GPU 패키지가 드롭됐기 때문**이다. "
        "🔒 GPU 부활 시 `p4_result.json` 의 필드 유실과 **함께** 고쳐라."),
    # 🔴 [§39.124/§1f, candidate D(i), coder15] 실제 미소비다 -- `payload/BPLUS_REOPT.sh`
    # 는 의도적으로 `plan.py`에 안 걸려 있다(STAGING ONLY: 새 Item 배선은 engineer/organizer
    # 스코프 결정이지 지금 이 라운드에서 내려진 적이 없다 -- 이 스크립트 자신의 헤더 참조).
    # 지금 무해한 이유는 이 아티팩트를 만드는 잡이 `./run.sh` 로 절대 제출되지 않기 때문이다.
    # 🔒 이 스크립트를 plan.py Item 으로 배선하는 순간 (ADR-110: `cores_per_task` 명시 필수)
    # `collect.py` 에도 같이 걸어라 -- 그때까지는 `bplus_reopt_verdict.json` 의 판독은
    # 수동(잡 디렉터리를 직접 열어) 이다, §39.124 finding (b)/(c) 를 사람이 읽는 동안은
    # 그걸로 충분하다.
    "bplus_reopt_verdict.json": (
        "🔴 **실제 미소비다.** `payload/BPLUS_REOPT.sh`(§39.124 candidate D(i))가 쓰지만 "
        "collector 는 읽지 않는다. 지금 무해한 이유는 **이 스크립트가 plan.py 에 배선되지 "
        "않았기 때문**이다(coder15, staging only -- 배선은 별도 scope 결정). "
        "🔒 plan.py Item 으로 배선하는 순간 collect.py 에도 같이 걸어라."),
}


class TestSysprobeFieldsAreConsumed(unittest.TestCase):
    """🔴 #4(큐 wall)·이번 라운드의 `engine_policy`/`modules_raw` 가 여기서 샜다."""

    def produced_keys(self):
        src = open(os.path.join(SEI, "sysprobe.py"), encoding="utf-8").read()
        m = re.search(r"def collect_login\(.*?\n(?=\ndef )", src, re.S)
        self.assertIsNotNone(m, "collect_login 을 찾지 못했다")
        return sorted(set(re.findall(r'info\["([a-z_0-9]+)"\]\s*=', m.group(0))))

    def test_every_collected_field_is_read_somewhere(self):
        """🔴 `sysprobe` 가 수집한 값은 **누군가 읽어야 한다.**

        실제 사고: `queue_info.max_walltime_h` 를 수집해 놓고 `build_plan` 이 안 봐서
        PBS 에서 wall 상한 판정이 `sinfo`(SLURM 전용, 항상 빈값)에 걸려 있었다.
        그리고 이번 라운드에 내가 만든 `engine_policy`(ADR-050)·`modules_raw`(ADR-043)도
        **똑같이 새고 있었다** — 이 검사가 그 자리에서 잡았다.
        """
        consumers = read_all(python_sources(exclude=("sysprobe.py",)))
        orphans = [k for k in self.produced_keys()
                   if not is_referenced(k, consumers) and k not in SYSPROBE_EXEMPT]
        self.assertEqual([], orphans,
                         "sysprobe 가 수집했는데 아무도 읽지 않는 필드: %s\n"
                         "  → 회신 JSON 에 싣거나, 면제라면 SYSPROBE_EXEMPT 에 "
                         "**사유와 함께** 등록하라." % orphans)

    def test_exemptions_carry_a_reason(self):
        """면제에 사유가 없으면 이 검사는 껍데기가 된다."""
        for key, reason in SYSPROBE_EXEMPT.items():
            self.assertTrue(str(reason).strip(), "%s 의 면제 사유가 비었다" % key)


class TestPayloadArtifactsAreRead(unittest.TestCase):
    """🔴 #3(`host`)·#6(P5 seed) 이 여기서 샜다."""

    def artifacts(self):
        """payload 가 만드는 JSON 아티팩트 파일명."""
        names = set()
        for fn in sorted(os.listdir(PAYLOAD)):
            if not fn.endswith(".sh"):
                continue
            txt = open(os.path.join(PAYLOAD, fn), encoding="utf-8").read()
            names |= set(re.findall(r'([a-z0-9_]+\.json)', txt))
        return sorted(names)

    def test_every_payload_artifact_is_read_by_the_collector(self):
        """payload 가 쓴 파일을 **아무도 열지 않으면** 그 측정은 존재하지 않는 것과 같다."""
        collectors = read_all([os.path.join(SEI, "collect.py")]
                              + python_sources())
        missing = [a for a in self.artifacts()
                   if a not in collectors and a not in WHOLE_DICT_PASSTHROUGH]
        self.assertEqual([], missing,
                         "payload 가 쓰는데 collector 가 열지 않는 아티팩트: %s" % missing)

    def test_passthrough_whitelist_carries_a_reason(self):
        for name, reason in WHOLE_DICT_PASSTHROUGH.items():
            self.assertTrue(str(reason).strip(), "%s 의 사유가 비었다" % name)


class TestKnownLostFieldsStayConsumed(unittest.TestCase):
    """🔴 **이미 한 번 샌 값들**은 다시 새지 않는지 이름으로 못 박는다.

    일반 검사(위 두 클래스)는 형태를 막고, 이 검사는 **재발을 막는다.**
    네 건 다 실제로 core-h 를 태우고도 목적을 잃을 뻔했던 값이다.
    """

    def test_throughput_host_is_consumed(self):
        src = open(os.path.join(SEI, "collect.py"), encoding="utf-8").read()
        self.assertIn('rec.get("host")', src, "probe_throughput 의 host 가 또 샜다")

    def test_p5_seed_is_consumed(self):
        src = open(os.path.join(SEI, "criteria", "p5.py"), encoding="utf-8").read()
        for field in ("seed", "seed_provenance", "failure_reason"):
            self.assertIn('r.get("%s")' % field, src,
                          "P5 의 %s 가 또 샜다 — dual-seed 2배 비용의 목적이 사라진다"
                          % field)

    def test_queue_wall_is_consumed_by_planning(self):
        src = open(os.path.join(SEI, "plan.py"), encoding="utf-8").read()
        self.assertIn("max_walltime_h", src,
                      "큐 wall 상한이 계획에서 다시 안 읽히고 있다")

    def test_engine_policy_and_raw_modules_reach_the_report(self):
        """ADR-043/050 — 이번 라운드에 내가 만들어 놓고 안 읽던 것들."""
        src = open(os.path.join(SEI, "report.py"), encoding="utf-8").read()
        for field in ("engine_policy", "modules_raw", "software_probed"):
            self.assertIn(field, src, "%s 가 회신 JSON 에 실리지 않는다" % field)


if __name__ == "__main__":
    unittest.main()
