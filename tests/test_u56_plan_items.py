"""[U56-2 B-3] plan.py 의 U56-2 Items — release 게이트와 항목 형태.

고정하는 것:
  1. 🔒 ADR-109: released 가 config 의 명시적 lead/사용자 행위로만 바뀐다 (아래
     `test_config_ships_released` 는 2026-08-21 그 행위와 함께 바뀌었다 — coder13,
     team-lead 경유 사용자 승인). released=false 였던 동안 default_items() 는 U56-2
     항목을 포함하지 않았다 — 그 gate 로직 자체는 `test_gate_would_exclude_...` 로
     계속 고정한다(명시적 cfg override, 실 config 값과 무관).
  2. 🔒 [S-2 패턴] 코드는 `u56_2.released` 를 절대 쓰지 않는다 — 올리는 것은
     lead/사용자 몫이다 (deck_verified 와 동일한 규칙, test_solvent_wiring 의
     test_code_never_flips_the_config_flag 와 같은 형태). 이것은 released 의 VALUE 와
     무관하게 항상 참이어야 한다 — 코드가 쓰지 않는다는 사실 자체를 고정한다.
  3. 항목 형태: array 금지(P6 주석의 "항목 N개면 새 분기가 0" + C-8-2 취소 기록의
     부활 규칙), payload 실존, 예산은 [ESTIMATE] placeholder 상수, depends_on 배선.
"""

import json
import os
import re
import unittest

import context  # noqa: F401
from sei_pilot import plan

PKG = context.PKG_ROOT


class TestReleaseGate(unittest.TestCase):
    def test_config_ships_released(self):
        """[coder13, 2026-08-21] lead 경유 사용자 승인으로 released=true 로 뒤집힘
        (ADR-109 ruling 2, R-A 자체 product 인증 — P1 부활 아님, see
        test_p1_excluded_sizing.py). 이 테스트는 그 명시적 행위와 함께만 바뀐다."""
        self.assertTrue(plan.u56_2_released(),
                        "config 의 u56_2.released 가 false 다 — flip 은 lead/사용자의 "
                        "명시적 행위였다; 되돌아갔다면 의도적인지 확인하라")

    def test_default_items_carry_u56_items_now_released(self):
        keys = set(i.key for i in plan.default_items("cpu"))
        for k in ("endpoint_prep_product", "endpoint_prep_rc_reactant",
                  "U56_RA_scan", "U56_RA_qst2", "U56_RB_scan"):
            self.assertIn(k, keys,
                         "%s 가 released=true 인데도 계획에 없다 — u56_2_items() 배선을 "
                         "확인하라" % k)

    def test_gate_would_exclude_u56_items_if_it_were_unreleased(self):
        """[coder13] 실 config 값과 무관하게, gate 로직 자체(flag=false -> 항목 미포함)를
        `default_items()` 실제 경로로 계속 고정한다 -- 위 test 가 지금 released=true
        로만 통과하는 것과 대칭(같은 monkeypatch 방식을 쓴다 -- test_p5_freq_recovery.py
        의 `plan.p5_freq_recovery_released = lambda ...` 패턴과 동일)."""
        orig = plan.u56_2_released
        plan.u56_2_released = lambda cfg=None: False
        try:
            keys = set(i.key for i in plan.default_items("cpu"))
        finally:
            plan.u56_2_released = orig
        for k in ("endpoint_prep_product", "endpoint_prep_rc_reactant",
                  "U56_RA_scan", "U56_RA_qst2", "U56_RB_scan"):
            self.assertNotIn(k, keys, k)

    def test_release_gate_reads_the_config_flag(self):
        self.assertTrue(plan.u56_2_released({"u56_2": {"released": True}}))
        self.assertFalse(plan.u56_2_released({"u56_2": {"released": "true"}}),
                         "문자열 'true' 는 승인이 아니다 — is True 만 통과한다")
        self.assertFalse(plan.u56_2_released({}))

    def test_code_never_flips_the_release_flag(self):
        """[S-2 패턴] sei_pilot 어디에도 released 쓰기가 없다."""
        offenders = []
        src_dir = os.path.join(PKG, "sei_pilot")
        for root, _d, files in os.walk(src_dir):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                text = open(os.path.join(root, fn), errors="replace").read()
                if re.search(r'''["']released["']\s*\]\s*=''', text):
                    offenders.append(fn)
        self.assertEqual([], offenders, "코드가 u56_2.released 를 씀 — ADR-109 위반")


class TestU56ItemShapes(unittest.TestCase):
    def setUp(self):
        self.items = {i.key: i for i in plan.u56_2_items()}

    def test_exactly_the_post_cut_items_exist(self):
        """§39.41(d) 컷 이후: U56-2 = 3 attempts(전부 11원자) + 신규 endpoint cert 2건.
        🔴 U56_RC_scan(T21-se)은 **없어야 한다** — S3 wave 1 로 이동(삭제 아님, plan.py
        의 취소 기록 주석이 부활 조건을 든다)."""
        self.assertEqual(
            {"endpoint_prep_product", "endpoint_prep_rc_reactant",
             "U56_RA_scan", "U56_RA_qst2", "U56_RB_scan"},
            set(self.items))

    def test_the_t21_cut_leaves_a_revival_record_not_a_deletion(self):
        src = open(os.path.join(PKG, "sei_pilot", "plan.py"),
                   errors="replace").read()
        self.assertIn("S3 wave 1", src)
        self.assertIn("§39.41(d)", src)

    def test_e21_carries_the_adopted_1536_cap_not_the_11atom_one(self):
        """engineer7 §R39 채택(lead 2026-08-20): 6h/384 를 물려받으면 budget_exhausted
        가 '종이 실패함'으로 오독된다(li_ec2_cation 282.7 core-h 미수렴 실측).
        [ADR-114, coder13 2026-08-21] wall 24->48, core_hours_budget/트립와이어는
        의도적으로 그대로 1536 (lead 에게 별도 플래그된 열린 질문)."""
        rc = self.items["endpoint_prep_rc_reactant"]
        self.assertEqual(1536.0, rc.core_hours_budget)
        self.assertEqual(48.0, rc.explicit_wall_h)
        self.assertEqual("1536.0", rc.extra_env["SEI_ENDPOINT_BUDGET_CORE_H"])
        e11 = self.items["endpoint_prep_product"]
        self.assertEqual("384.0", e11.extra_env["SEI_ENDPOINT_BUDGET_CORE_H"])
        self.assertEqual(3.0, e11.explicit_wall_h)   # engineer9 §R39.52: 6 h -> 3 h (11-atom only)

    def test_product_item_declares_the_dual_start_alt_input_and_it_exists(self):
        """[§39.41 / 0.59 eV basin] packaged guess 단독 시작 금지 — ALT 시작점이
        선언돼 있고 파일이 provenance sidecar 와 함께 실존한다."""
        env = self.items["endpoint_prep_product"].extra_env
        rel = env["SEI_ENDPOINT_ALT_INPUT_XYZ"]
        self.assertTrue(os.path.exists(os.path.join(PKG, rel)), rel)
        self.assertTrue(os.path.exists(
            os.path.join(PKG, rel.replace(".xyz", ".provenance.json"))))

    def test_no_item_is_an_array(self):
        """🔒 C-8-2 취소 기록 + P6 주석: '항목 N개면 계획·사전검사·제출·emit·회신이
        기존 경로를 그대로 타고 새 분기가 0' — ADR-107 의 사고 형태(array 공유 마커)를
        구조적으로 재현 불가능하게 하는 선택이다."""
        for k, it in self.items.items():
            self.assertIsNone(it.array, "%s 가 array 다 — 금지" % k)

    def test_every_payload_file_exists_and_sources_common(self):
        for k, it in self.items.items():
            path = os.path.join(PKG, it.payload)
            self.assertTrue(os.path.exists(path), "%s: %s 없음" % (k, it.payload))
            text = open(path, errors="replace").read()
            self.assertIn("payload/common.sh", text,
                          "%s payload 가 common.sh 를 source 하지 않는다 — stage "
                          "마커(R-12 fingerprint 포함)가 통째로 빠진다" % k)

    def test_budgets_are_positive_and_marked_estimate_where_unpriced(self):
        """R-11: payload 작업은 budget model 에 보인다. 그리고 미가격 값은 [ESTIMATE]
        로 표시된 채로만 존재한다 — plan.py 상수 블록의 주석이 그 표시다."""
        for k, it in self.items.items():
            self.assertGreater(it.core_hours_budget, 0.0, k)
        src = open(os.path.join(PKG, "sei_pilot", "plan.py"),
                   errors="replace").read()
        block = src[src.index("U56_ENDPOINT_11ATOM_CORE_H"):
                    src.index("def u56_2_released")]
        self.assertGreaterEqual(block.count("[ESTIMATE]"), 2,
                                "U56-2 attempt 예산 상수의 [ESTIMATE] 표시가 지워졌다 — "
                                "engineer7 §R39 재가격 착지 전에는 placeholder 다")
        self.assertIn("[ADOPTED", block,
                      "E21 캡(24h/1,536)의 채택 표시가 지워졌다 — provenance label 필수")

    def test_dependencies_wire_attempts_to_their_endpoint_certs(self):
        self.assertIn("endpoint_prep_reactant", self.items["U56_RA_scan"].depends_on)
        self.assertIn("endpoint_prep_product", self.items["U56_RA_qst2"].depends_on)
        self.assertIn("endpoint_prep_reactant", self.items["U56_RA_qst2"].depends_on)
        self.assertIn("endpoint_prep_reactant", self.items["U56_RB_scan"].depends_on)

    def test_rc_input_geometry_is_packaged_with_provenance(self):
        """[lead Q1 판정 + §39.42(a)] R-C reactant 기하가 provenance(다중 seed 프로토콜
        기록 포함)와 함께 실려 있다. 사라지면 payload 가 input_missing 으로 거부한다 —
        그 거부 경로 자체는 test_endpoint_prep 이 지킨다."""
        self.assertEqual("product",
                         self.items["endpoint_prep_product"]
                         .extra_env["SEI_ENDPOINT_ROLE"])
        rc = self.items["endpoint_prep_rc_reactant"]
        self.assertEqual("reactant", rc.extra_env["SEI_ENDPOINT_ROLE"])
        rel = rc.extra_env["SEI_ENDPOINT_INPUT_XYZ"]
        path = os.path.join(PKG, rel)
        self.assertTrue(os.path.exists(path), rel)
        with open(path) as fh:
            n_atoms = int(fh.readline().split()[0])
            header = fh.readline()
        self.assertEqual(21, n_atoms)
        # provenance 최소 요건: 원본, kick seed, '끝단 아님' 선언이 헤더/사이드카에 있다.
        self.assertIn("seed 20260820", header)
        self.assertIn("NOT an endpoint", header)
        side = json.load(open(path.replace(".xyz", ".provenance.json")))
        self.assertEqual(6, side["multi_seed_protocol"]["n_seeds"])
        self.assertEqual(2, side["multi_seed_protocol"]["n_distinct_basins"])
        self.assertIn("lowest", side["multi_seed_protocol"]["selected"].lower())

    def test_attempt_env_declares_reaction_method_and_endpoint_keys(self):
        for k, rxn, method in (("U56_RA_scan", "R-A", "relaxed_scan"),
                               ("U56_RA_qst2", "R-A", "qst2"),
                               ("U56_RB_scan", "R-B", "relaxed_scan")):
            env = self.items[k].extra_env
            self.assertEqual(rxn, env["SEI_U56_REACTION"], k)
            self.assertEqual(method, env["SEI_U56_METHOD"], k)
            self.assertIn("SEI_U56_REACTANT_ENDPOINT_KEY", env, k)
        self.assertEqual("endpoint_prep_product",
                         self.items["U56_RA_qst2"]
                         .extra_env["SEI_U56_PRODUCT_ENDPOINT_KEY"])

    def test_ra_scan_does_not_yet_declare_a_product_endpoint_key(self):
        """🔴 [critic14, lead ruling 2026-08-21, held per §39.113(d)] R-A HAS a certified
        product and U56.sh already resolves it whenever this key is declared (not qst2-only) --
        but `extra_env` is a `state.SPEC_DIGEST_FIELDS` field, so adding this key to
        `U56_RA_scan` NOW would mark its spec stale and trigger an IMMEDIATE whole-item
        resubmit (336 core-h, measured) that would just repeat the identical IRC crash for
        zero new information. This key may be added back ONLY in the same build as the
        Track B IRC-integrator fix (whose settings ALSO belong on `extra_env`), so the two
        resubmits happen together. Same pattern as test_p1_excluded_sizing.py's deliberate-
        absence pins -- a future editor reading §39.113(d)'s housekeeping rationale alone
        would add this key back in good faith and reproduce exactly the resubmit the hold
        exists to prevent; this test is what stops them mid-edit instead of after."""
        self.assertNotIn(
            "SEI_U56_PRODUCT_ENDPOINT_KEY", self.items["U56_RA_scan"].extra_env,
            "U56_RA_scan now declares SEI_U56_PRODUCT_ENDPOINT_KEY -- this triggers an "
            "IMMEDIATE 336 core-h whole-item resubmit (spec_digest goes stale) that repeats "
            "the identical IRC crash for zero new information. Only add this back TOGETHER "
            "with the Track B IRC-integrator fix, in the same build, per §39.113(d)/lead's "
            "2026-08-21 ruling (option ii) -- not on its own.")

    def test_released_plan_carries_the_items_without_new_mechanisms(self):
        """released=true 인 가상 config 에서 항목들이 기존 경로(build_plan)를 그대로
        탄다 — 새 상태값·새 분기 없이. guard 초과로 뒷순위가 잘리는 것은 여기서
        검사하지 않는다(예산은 engineer7 착지 전의 placeholder 다)."""
        items = plan.u56_2_items()
        env = {"hostname": "x", "scheduler": "pbs", "cores_per_node": 64,
               "software": {"g16": {"path": "/opt/g16"}}, "partitions": []}
        planned, summary = plan.build_plan(env, items=items, cores_per_node=64,
                                           max_wall_h=48.0)
        keys = set(p["key"] for p in planned)
        self.assertEqual(set(i.key for i in items), keys)
        for p in planned:
            self.assertIn(p["status"], ("planned", "skipped"))


if __name__ == "__main__":
    unittest.main()
