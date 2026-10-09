"""[02_METHOD_SPEC.md 39.113(d), proposer housekeeping, Track A] `U56_RA_scan` (relaxed_scan)
did not resolve a certified product even when one is declared, unlike `U56_RA_qst2` for the
SAME reaction -- so the bracket check's two-sided half ran for qst2 only, evaluating the two
methods on unequal footing. Fixed: resolve the product cert whenever the item declares
`SEI_U56_PRODUCT_ENDPOINT_KEY`, regardless of method; still OPTIONAL for relaxed_scan (only
qst2 refuses if none resolves).

Reuses `test_c8_gate.py`'s real subprocess harness (`_U56Run`) rather than re-deriving it.
"""

import json
import os
import unittest

import context  # noqa: F401
from test_c8_gate import (HAVE_BASH, U56_FIXTURE_CERTS_LEVEL3, U56_FIXTURE_GSCAN_PASS, _U56Run)


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class TestRelaxedScanNowResolvesADeclaredProductCert(_U56Run):
    """Same fixture shape as `TestU56SingleEndedOpensOnCertifiedReactantOnly`, plus a declared
    product endpoint key -- the exact shape `plan.py`'s `U56_RA_scan` Item now has."""

    METHOD = "relaxed_scan"
    INJECT_ENDPOINTS = U56_FIXTURE_CERTS_LEVEL3
    PRODUCT_XYZ = "inputs/li_ec_radical_product.xyz"
    EXTRA_ENV = {"SEI_U56_PRODUCT_ENDPOINT_KEY": "endpoint_prep_product"}
    PRE_JOB_FILES = {"gscan_verdict.json": U56_FIXTURE_GSCAN_PASS}

    def test_product_cert_is_resolved_not_left_null(self):
        certs = json.load(open(os.path.join(self.job_dir, "endpoint_certs.json")))
        self.assertIsNotNone(certs["product_xyz"],
                             "relaxed_scan declared a product endpoint key but "
                             "endpoint_certs.json still shows product_xyz=null")
        self.assertIsNotNone(certs["product_cert"])
        self.assertTrue(os.path.exists(certs["product_xyz"]))

    def test_chain_still_completes_single_ended(self):
        """The fix must not turn the product into a REQUIREMENT for relaxed_scan."""
        self.assertEqual(0, self.proc.returncode,
                         self.proc.stdout[-2000:] + self.proc.stderr[-800:])


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class TestRelaxedScanWithoutTheKeyStillLeavesProductNull(_U56Run):
    """Negative control: no `SEI_U56_PRODUCT_ENDPOINT_KEY` declared (e.g. `U56_RB_scan`, whose
    product IS the claim under test, §39.39(d)) -- must NOT resolve a product from thin air."""

    METHOD = "relaxed_scan"
    INJECT_ENDPOINTS = U56_FIXTURE_CERTS_LEVEL3
    PRE_JOB_FILES = {"gscan_verdict.json": U56_FIXTURE_GSCAN_PASS}

    def test_product_cert_stays_null(self):
        certs = json.load(open(os.path.join(self.job_dir, "endpoint_certs.json")))
        self.assertIsNone(certs["product_xyz"])
        self.assertIsNone(certs["product_cert"])


if __name__ == "__main__":
    unittest.main()
