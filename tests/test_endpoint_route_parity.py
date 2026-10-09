"""ADR-101 — the two endpoint routes must differ ONLY in thresholds.

🔴 WHY THIS EXISTS. `proposer6`'s Q2 ruling: rough runs at the SAME level as tight —
same functional, basis, solvent AND GRID — because a cheaper surface can order
near-degenerate Li+ coordination isomers differently. Stage 1 then SELECTS a basin,
stage 2 certifies honestly inside it, `n_imag == 0` is TRUE, and the minimum is the
wrong one. Nothing internal is inconsistent, so no other check we own can see it.

`Int(Grid=UltraFine)` was in fact omitted from the rough route on first implementation
(lead-caught, 2026-08-19) — proposer6 had written that a coarser grid "reintroduces the
basin error through a door nobody watches", and it went through that door within the hour.
🔒 So this guards the PROPERTY (everything outside the thresholds is identical), not the
string. A per-token check makes a future grid/basis/solvent divergence impossible to
introduce silently.
"""
import json
import os
import re
import unittest

import context  # noqa: F401  -- path shim, same convention as the rest of the suite

CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "src", "pilot_package", "config", "qc_levels.json")

#: the ONLY tokens the two routes are permitted to differ by
_THRESHOLD_CLAUSE = re.compile(r"(opt|irc)=\([^)]*\)")


def _surface_tokens(route):
    """Every token that defines the SURFACE — i.e. the route minus the thresholds/method
    clause (`opt=(...)`/`irc=(...)`) and the `freq` token."""
    return [t for t in _THRESHOLD_CLAUSE.sub("", route).split() if t != "freq"]


def _routes():
    with open(CONFIG) as fh:
        jt = json.load(fh)["gaussian16"]["job_types"]
    return jt["endpoint_opt_rough"], jt["endpoint_opt_freq"]


def _all_job_types():
    with open(CONFIG) as fh:
        return json.load(fh)["gaussian16"]["job_types"]


#: 🔴 [§39.41(b), lead 2026-08-20] C-8.1 은 endpoint 와 TS 탐색이 **같은 표면**일 것을
#: 요구한다 — grid 가 다르면 다른 표면이고, 다른 표면의 n_imag==0/"converged" 는 우리가
#: 인증한 표면의 사실이 아니다. UltraFine 이 endpoint 두 route 에만 있고 TS/IRC 전체에
#: 없던 결함이 실제로 출하 중이었다(이 파일 자신의 docstring 이 "rough 에서 grid 가 한
#: 번 빠졌다"고 적어 놓고 TS/IRC 는 보지 않았다 — 같은 문의 두 번째 통과).
TS_IRC_FAMILY = ("ts_opt", "ts_opt_from_guess", "ts_qst2",
                 "irc_forward", "irc_reverse",
                 "irc_forward_rcfc", "irc_reverse_rcfc",
                 "relaxed_scan")


class TestEndpointRouteParity(unittest.TestCase):
    def test_surface_tokens_are_identical(self):
        rough, tight = _routes()
        self.assertEqual(
            _surface_tokens(rough), _surface_tokens(tight),
            "ADR-101: the rough and tight endpoint routes must define the SAME SURFACE. "
            "They may differ only inside opt=(...) and by the `freq` token. A difference "
            "here is a cheaper-level rough stage, which selects a basin on a surface the "
            "certificate is not taken on (U-55).")

    def test_both_carry_the_ultrafine_grid_explicitly(self):
        for route in _routes():
            self.assertIn("Int(Grid=UltraFine)", route,
                          "ADR-101: the grid is part of the level. This was the token "
                          "actually omitted on first implementation.")

    def test_both_carry_nosymm(self):
        for route in _routes():
            self.assertIn("nosymm", route,
                          "B-2/C-9: G16 re-detects and re-imposes the point group. Missing "
                          "on the ROUGH stage is the easier one to forget -- 'it's only a "
                          "rough opt' is the sentence that omits it.")

    def test_the_thresholds_DO_differ(self):
        """Positive control: a test that passes when both routes are identical is not
        testing parity, it is testing nothing. The routes must actually be two routes."""
        rough, tight = _routes()
        self.assertNotEqual(rough, tight)
        self.assertIn("loose", rough)
        self.assertIn("tight", tight)
        self.assertIn("freq", tight)
        self.assertNotIn("freq", rough,
                         "a freq at stage 1 buys nothing and costs an analytic Hessian on a "
                         "non-final geometry (proposer6 Q3)")


class TestTsIrcFamilySitsOnTheSameSurfaceAsTheEndpoints(unittest.TestCase):
    """[§39.41(b)] endpoint 인증 route 와 TS/IRC family route 의 surface token 동일성.

    같은 `_surface_tokens` 비교를 endpoint 쌍 밖으로 넓힌 것 — nosymm 누락과 같은
    결함 부류이고, 이 확장이 없던 동안 UltraFine 누락이 실제로 이 문을 지나갔다."""

    def test_every_ts_irc_route_shares_the_endpoint_surface_tokens(self):
        jt = _all_job_types()
        _rough, tight = _routes()
        want = _surface_tokens(tight)
        for name in TS_IRC_FAMILY:
            with self.subTest(job_type=name):
                self.assertIn(name, jt)
                self.assertEqual(
                    want, _surface_tokens(jt[name]),
                    "%s 가 endpoint 인증과 다른 표면 위에 있다 — C-8.1 위반: 그 표면의 "
                    "'converged'/n_imag 는 인증된 표면의 사실이 아니다." % name)

    def test_every_ts_irc_route_carries_the_ultrafine_grid(self):
        jt = _all_job_types()
        for name in TS_IRC_FAMILY:
            with self.subTest(job_type=name):
                self.assertIn("Int(Grid=UltraFine)", jt[name],
                              "%s: §39.41(b) — grid 는 level 의 일부다" % name)

    def test_rcfc_variants_read_the_hessian_and_do_not_recompute_it(self):
        """engineer7 §R39.15 4a: rcfc route 는 chk 의 Hessian 을 읽는다(calcfc 재계산
        아님). 기본 irc_* route 는 calcfc 를 유지한다 — 스위치는 lead 가 켠다."""
        jt = _all_job_types()
        for d in ("forward", "reverse"):
            self.assertIn("rcfc", jt["irc_%s_rcfc" % d])
            self.assertNotIn("calcfc", jt["irc_%s_rcfc" % d])
            self.assertIn("calcfc", jt["irc_%s" % d])

    def test_the_readfc_switch_ships_off(self):
        """🔒 rcfc 경로는 dev box 에 G16 이 없어 미검증 — 다음 제출의 route smoke 통과
        후 lead 가 올린다. 코드는 올리지 않는다(deck_verified/released 와 같은 규칙)."""
        cfg_path = os.path.join(os.path.dirname(CONFIG), "b0_reactions.json")
        with open(cfg_path) as fh:
            cfg = json.load(fh)
        self.assertEqual("calcfc", cfg["u56_2"]["irc_hessian_source"])


if __name__ == "__main__":
    unittest.main()
