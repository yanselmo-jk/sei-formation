"""항목별 PBS `-A` 계정 매핑.

🔴 왜 이 테스트가 필요한가: 이 클러스터의 계정은 프로젝트 단위가 아니라 **소프트웨어
단위**다(Gaussian→`gaussian`, xTB→`etc`, probing→`etc`, VASP→`vasp`). 전역 `--account`
하나를 전파하면 **어떤 값을 넣어도 항목의 절반이 틀리고**, PBS 는 계정이 틀리면 제출
자체를 거부한다. 10개 항목이 전부 거부되면 왕복 1회(3.5일)가 그대로 날아간다.

여기서 고정하는 것:
  1. 표대로 매핑되는가
  2. 계정 문자열이 **설정 한 곳**에서만 오는가 (항목에 하드코딩되지 않았는가)
  3. 미확인 계정이 **조용히** 쓰이지 않는가
  4. 사용자가 덮어쓸 수 있는가
"""

import json
import os
import re
import unittest

import context  # noqa: F401
from sei_pilot import accounts, budget, plan

# 🔴 P2f(CP2K) 제거 후 계산 코드는 Gaussian16 + xtb 둘뿐이다(사용자 요구).
EXPECTED = {"probe_node": "etc", "probe_throughput": "etc", "probe_queuewait": "etc",
            "P1": "gaussian", "P1b": "gaussian", "P5": "gaussian",
            # 🔒 §R22.10 P6(κ 앵커) 3항목 — G16 이므로 `-A gaussian` 이다.
            "P6_t1": "gaussian", "P6_t16": "gaussian", "P6_t64": "gaussian",
            # 🔴 ADR-099 — endpoint_prep.sh 도 G16 이다.
            "endpoint_prep_reactant": "gaussian",
            # 🔴 [coder13, 2026-08-21] u56_2.released 가 lead/사용자 승인으로 true 로
            #    뒤집혔다(ADR-109 ruling 2) — U56-2 의 5항목 전부 G16.
            "endpoint_prep_product": "gaussian",
            "endpoint_prep_rc_reactant": "gaussian",
            "U56_RA_scan": "gaussian", "U56_RA_qst2": "gaussian",
            "U56_RB_scan": "gaussian",
            }   # 🔒 ADR-049: P3 제거(이미 측정됨)


def _plan_items(**resolver_kw):
    env = {"scheduler": "none", "cores_per_node": 8, "software": {},
           "gpus": {}, "modules": []}
    r = accounts.Resolver(**resolver_kw) if resolver_kw else None
    planned, summary = plan.build_plan(env, budget.guard_for_profile("cpu"),
                                       profile="cpu", account_resolver=r)
    return dict((e["key"], e) for e in planned), summary


class TestMappingMatchesTheUsersRule(unittest.TestCase):
    def test_every_cpu_item_gets_the_expected_account(self):
        items, _s = _plan_items()
        got = dict((k, v["account"]) for k, v in items.items())
        self.assertEqual(EXPECTED, got)

    def test_gaussian_items_are_exactly_the_g16_ones(self):
        items, _s = _plan_items()
        g16_items = sorted(k for k, v in items.items() if v["account"] == "gaussian")
        # 🔒 의도된 변화: §R22.10 으로 P6(κ 앵커) 3항목이 신설됐고 전부 G16 이다.
        #    사유: §R21 KNL 판명(κ=3.4~6.8)에 따른 재산정 — 종전 값은 κ=1 단위였다. P6_t1/t16/t64(κ 앵커)가 신설됐다.
        self.assertEqual(sorted(["P1", "P1b", "P5", "P6_t1", "P6_t16", "P6_t64",
                                 "endpoint_prep_reactant", "endpoint_prep_product",
                                 "endpoint_prep_rc_reactant", "U56_RA_scan", "U56_RA_qst2",
                                 "U56_RB_scan"]), g16_items)

    def test_every_item_declares_a_software_key(self):
        for item in plan.default_items("cpu") + plan.default_items("gpu"):
            self.assertTrue(getattr(item, "account_key", None),
                            "%s 에 account_key 가 없다" % item.key)


class TestSingleSourceOfTruth(unittest.TestCase):
    """🔴 계정 문자열이 두 곳에 있으면 한쪽만 갱신된다 — 이 프로젝트의 반복 실패다."""

    def test_account_strings_are_not_hardcoded_in_plan_py(self):
        with open(os.path.join(context.PKG_ROOT, "sei_pilot", "plan.py")) as fh:
            src = fh.read()
        for literal in ('"gaussian"', '"vasp"', '"etc"'):
            hits = [l for l in src.splitlines()
                    if literal in l and not l.strip().startswith("#")
                    and "account_key" not in l]
            self.assertEqual([], hits,
                             "plan.py 에 계정 문자열 %s 가 박혀 있다 — "
                             "config/accounts.json 에서 와야 한다" % literal)

    def test_config_file_is_the_source(self):
        path = os.path.join(context.PKG_ROOT, "config", "accounts.json")
        self.assertTrue(os.path.exists(path))
        with open(path) as fh:
            cfg = json.load(fh)
        self.assertEqual({"probe", "gaussian", "xtb", "vasp"}, set(cfg["map"]))

    def test_changing_the_config_changes_the_plan(self):
        """설정이 진짜 출처인지 — 값을 바꿔 계획이 따라오는지 본다."""
        r = accounts.Resolver(overrides={"gaussian": "somethingelse"})
        items, _s = _plan_items(overrides={"gaussian": "somethingelse"})
        self.assertEqual("somethingelse", items["P1"]["account"])
        self.assertEqual("somethingelse", r.account_for("gaussian"))


class TestUnconfirmedIsNeverSilent(unittest.TestCase):
    def test_no_unconfirmed_account_remains(self):
        """🔴 P2f(CP2K, 미확인 계정) 제거로 추정 계정이 하나도 남지 않았다.

        전에는 cp2k 가 유일한 미확인 항목이었다. 경고 **기구 자체**는 살아 있어야
        하므로(다른 클러스터에서 다시 쓰인다) 아래 test_warning_mechanism_still_works
        가 그걸 따로 지킨다."""
        items, summary = _plan_items()
        self.assertEqual([], [k for k, v in items.items()
                              if v["account_unconfirmed"]])
        self.assertEqual([], summary["account_warnings"])

    def test_warning_mechanism_still_works(self):
        """항목이 없어졌다고 경고 기구까지 죽으면 다음 클러스터에서 조용히 추정한다."""
        r = accounts.Resolver()
        r.map["madeup"] = {"account": "guess", "confirmed": False, "note": "시험용"}
        self.assertTrue(r.warnings(["madeup"]))

    def test_confirmed_items_produce_no_warning(self):
        r = accounts.Resolver()
        self.assertEqual([], r.warnings(["probe", "gaussian", "xtb"]))

    def test_warning_tells_the_user_how_to_fix_it(self):
        r = accounts.Resolver()
        r.map["madeup"] = {"account": "guess", "confirmed": False, "note": ""}
        self.assertIn("--account madeup=", "\n".join(r.warnings(["madeup"])))

    def test_user_override_is_never_flagged_as_a_guess(self):
        """사용자가 직접 준 값은 우리 추정이 아니다."""
        r = accounts.Resolver(overrides={"xtb": "myproj"})
        self.assertTrue(r.is_confirmed("xtb"))
        self.assertEqual("myproj", r.account_for("xtb"))

    def test_plan_text_shows_the_account_column(self):
        """🔴 제출 전에 눈으로 확인할 수 있어야 한다."""
        env = {"scheduler": "none", "cores_per_node": 8, "software": {},
               "gpus": {}, "modules": []}
        planned, summary = plan.build_plan(env, budget.guard_for_profile("cpu"),
                                           profile="cpu")
        text = plan.format_plan_text(planned, summary, env)
        self.assertIn("-A", text)
        for key, acct in EXPECTED.items():
            row = [l for l in text.splitlines() if l.strip().startswith(key + " ")]
            self.assertTrue(row, "%s 행이 표에 없다" % key)
            self.assertIn(acct, row[0], "%s 행에 계정이 안 보인다" % key)

    def test_unconfirmed_marker_is_still_rendered(self):
        """표기 기구는 남아 있어야 한다(항목만 사라졌다)."""
        env = {"scheduler": "none", "cores_per_node": 8, "software": {},
               "gpus": {}, "modules": []}
        r = accounts.Resolver()
        # 🔒 ADR-049 로 P3(xtb)가 빠졌으므로 G16 계정으로 같은 기구를 확인한다.
        r.map["gaussian"] = {"account": "etc", "confirmed": False, "note": "시험용"}
        planned, summary = plan.build_plan(env, budget.guard_for_profile("cpu"),
                                           profile="cpu", account_resolver=r)
        text = plan.format_plan_text(planned, summary, env)
        # 🔒 ADR-049 로 P3 가 빠졌으므로 xtb 계정 대신 G16 항목으로 확인한다.
        row = [l for l in text.splitlines() if l.strip().startswith("P1 ")][0]
        self.assertIn("etc*", row)


class TestOverrideParsing(unittest.TestCase):
    def test_software_scoped_override(self):
        g, per = accounts.parse_overrides(["cp2k=myproj"])
        self.assertIsNone(g)
        self.assertEqual({"cp2k": "myproj"}, per)

    def test_bare_name_is_global(self):
        g, per = accounts.parse_overrides(["myproj"])
        self.assertEqual("myproj", g)
        self.assertEqual({}, per)

    def test_multiple_flags_accumulate(self):
        _g, per = accounts.parse_overrides(["cp2k=a", "gaussian=b"])
        self.assertEqual({"cp2k": "a", "gaussian": "b"}, per)

    def test_comma_separated_also_works(self):
        _g, per = accounts.parse_overrides(["cp2k=a,gaussian=b"])
        self.assertEqual({"cp2k": "a", "gaussian": "b"}, per)

    def test_global_override_beats_per_software(self):
        r = accounts.Resolver(global_override="one", overrides={"cp2k": "two"})
        self.assertEqual("one", r.account_for("cp2k"))

    def test_unknown_software_in_override_is_reported(self):
        """오타를 조용히 무시하면 사용자는 덮어썼다고 믿는다."""
        r = accounts.Resolver(overrides={"gausian": "x"})
        self.assertTrue(any("gausian" in w for w in r.warnings(["gaussian"])))


class TestQueueDefault(unittest.TestCase):
    def test_default_queue_is_normal(self):
        self.assertEqual("normal", accounts.default_queue())

    def test_plan_summary_carries_the_queue(self):
        _items, summary = _plan_items()
        self.assertEqual("normal", summary["queue_default"])


class TestP2Removal(unittest.TestCase):
    """P2/P2ext/p2_scaling 이 정말 사라졌는가 (부분 삭제는 더 나쁘다)."""

    def test_removed_items_are_gone_from_the_plan(self):
        items, _s = _plan_items()
        for key in ("P2", "P2ext", "p2_scaling", "P2f"):
            self.assertNotIn(key, items)

    def test_payload_files_are_gone(self):
        pdir = os.path.join(context.PKG_ROOT, "payload")
        for name in ("P2.sh", "P2ext.sh", "p2_scaling.sh", "P2f.sh",
                     "cp2k_common.sh"):
            self.assertFalse(os.path.exists(os.path.join(pdir, name)), name)

    def test_p2_criteria_module_is_gone(self):
        self.assertFalse(os.path.exists(os.path.join(
            context.PKG_ROOT, "sei_pilot", "criteria", "p2.py")))

    def test_nothing_still_imports_the_removed_module(self):
        offenders = []
        for root, _d, files in os.walk(os.path.join(context.PKG_ROOT, "sei_pilot")):
            for name in files:
                if not name.endswith(".py"):
                    continue
                with open(os.path.join(root, name)) as fh:
                    if re.search(r"^\s*from \.criteria import .*\bp2\b", fh.read(), re.M):
                        offenders.append(name)
        self.assertEqual([], offenders)

    def test_only_allowed_engines_remain(self):
        """🔴 **사용자가 직접 정한 허용 집합** (ADR-050). 원문:

            *"MOPAC 은 배제하고, Gaussian, VASP, LAMMPS, xTB 로 패키지를 한정해.
              만약 정말 필요하다면 CP2K 를 추가해도 좋아."*

        ⟹ 허용 `{g16, vasp, lammps, xtb}` + **조건부 `cp2k`**(게이트 통과 시).
        🔴 종전 판(*"VASP·Gaussian·xtb 로"*)은 **사용자가 스스로 개정한 것**이다 —
        코더가 완화한 것이 아니다. 이 구분이 중요해서 원문을 그대로 인용해 둔다.
        🔴 **LAMMPS 허용 ≠ ReaxFF 허용.** ReaxFF 는 사용자가 이전에 별도로 배제했고
        그 결정은 살아 있다(`sysprobe.EXCLUDED_ENGINES` 참조).

        현재 파일럿에는 VASP·LAMMPS 항목이 없으므로 계산 코드는 여전히 **G16 + xtb** 뿐이다.
        (P7/CP2K 는 U-46 게이트 대기, LAMMPS 는 proposer 판정 대기.)
        """
        items, _s = _plan_items()
        keys = set(items) - {"probe_node", "probe_throughput", "probe_queuewait"}
        # 🔒 의도된 변화: P6_t*(κ 앵커)는 **새 계산 코드가 아니라 G16 이다** —
        #    같은 계·같은 레벨을 스레드 수만 바꿔 돌린다. 사용자 제약(VASP/Gaussian/xtb)
        #    을 위반하지 않는다.
        #    🔴 반면 P7(CP2K)은 이 제약과 충돌하므로 **넣지 않았다**
        #       (src/experiments/p7_cp2k/ 에 사유와 함께 보관, lead 판정 대기).
        # 🔒 [coder13, 2026-08-21] u56_2.released=true (lead/사용자 승인) — 5항목 전부
        #    G16 이므로 이 제약을 위반하지 않는다.
        self.assertEqual({"P1", "P1b", "P5", "P6_t1", "P6_t16", "P6_t64",
                          "endpoint_prep_reactant", "endpoint_prep_product",
                          "endpoint_prep_rc_reactant", "U56_RA_scan", "U56_RA_qst2",
                          "U56_RB_scan"}, keys)

    def test_cp2k_availability_is_still_reported_by_probe_node(self):
        """P2f 는 지웠지만 CP2K **유무 보고**는 남아야 한다 — 축 3 폴백에서 되살린다."""
        from sei_pilot import sysprobe
        self.assertTrue(any("cp2k" in t for t in sysprobe.SOFTWARE_TARGETS))


if __name__ == "__main__":
    unittest.main()


class TestEngineePolicyADR050(unittest.TestCase):
    """🔒 ADR-050 — **사용자가 직접 정한 허용 집합**을 코드가 그대로 들고 있는가.

    사용자 원문:
        *"MOPAC 은 배제하고, Gaussian, VASP, LAMMPS, xTB 로 패키지를 한정해.
          만약 정말 필요하다면 CP2K 를 추가해도 좋아."*

    🔴 이 파일의 다른 테스트와 목적이 다르다: 저기는 *"패키지가 무엇을 쓰는가"* 를,
    여기는 *"무엇을 써도 되는가"* 를 지킨다. **있다 ≠ 써도 된다.**
    """

    def test_mopac_is_excluded_but_still_probed(self):
        """🔴 배제와 미조회를 구분한다.

        `mopac` 을 프로브 목록에서 **지우면** 다음 라운드에 누군가 다시 후보로 올리고,
        그때 회신에 없으니 또 "부재 확정"으로 오독한다 — 실제로 한 번 일어났다(§R21.10).
        ⟹ **탐지는 계속하고, 정책으로 배제한다.**
        """
        from sei_pilot import sysprobe
        self.assertIn("mopac", sysprobe.SOFTWARE_TARGETS)
        pol = sysprobe.engine_policy("mopac")
        self.assertFalse(pol["allowed"])
        self.assertIn("ADR-050", pol["reason"])

    def test_user_named_engines_are_allowed(self):
        from sei_pilot import sysprobe
        for name in ("g16", "vasp_std", "lammps", "xtb"):
            self.assertTrue(sysprobe.engine_policy(name)["allowed"], name)

    def test_cp2k_is_conditional_not_plain_allowed(self):
        """*"정말 필요하다면"* — 조건부다. 무조건 허용으로 읽히면 게이트가 무의미해진다."""
        from sei_pilot import sysprobe
        pol = sysprobe.engine_policy("cp2k.psmp")
        self.assertTrue(pol["allowed"])
        self.assertTrue(pol["conditional"])

    def test_lammps_allowed_does_not_imply_reaxff(self):
        """🔴 이 구분은 흐려지기 쉽다. LAMMPS 허용은 ReaxFF 배제를 뒤집지 않는다."""
        from sei_pilot import sysprobe
        self.assertTrue(sysprobe.engine_policy("lammps")["allowed"])
        self.assertFalse(sysprobe.engine_policy("reaxff")["allowed"])
        self.assertIn("ReaxFF", sysprobe.EXCLUDED_ENGINES["reaxff"])

    def test_policy_is_reported_next_to_detection(self):
        """탐지 결과 옆에 정책이 실려야 한다 — '설치돼 있으니 쓰자'를 막는다."""
        from sei_pilot import sysprobe
        from sei_pilot.shellrun import FakeShell
        info = sysprobe.collect_login(FakeShell(
            responses={"hostname -f": (0, "h\n", "")}, which_map={}))
        self.assertIn("engine_policy", info)
        self.assertFalse(info["engine_policy"]["mopac"]["allowed"])
