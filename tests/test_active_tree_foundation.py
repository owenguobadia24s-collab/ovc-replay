from __future__ import annotations

import unittest
from pathlib import Path

import ovc
from ovc.opt_a import AUTHORITY_STATE as OPT_A_STATE
from ovc.opt_b.c1 import AUTHORITY_STATE as C1_STATE
from ovc.opt_b.c2 import AUTHORITY_STATE as C2_STATE


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_REPOSITORY_STATES = {
    "state: V2_FOUNDATION_NO_MARKET_AUTHORITY",
    "state: V2_FOUNDATION_RESET_COMPLETE_NO_MARKET_AUTHORITY",
    "state: V2_OBSERVATION_CONSTRUCTION_REVIEW_PASS_NO_MARKET_AUTHORITY",
    "state: V2_ROLE_RELEASE_FREEZE_PASS_NO_MARKET_AUTHORITY",
    "state: V2_REMOTE_PUBLICATION_REVIEW_PASS_NO_MARKET_AUTHORITY",
}


class ActiveTreeFoundationTests(unittest.TestCase):
    def test_clean_namespaces_import(self) -> None:
        self.assertEqual(ovc.__version__, "0.2.0")
        self.assertEqual(OPT_A_STATE, "DESIGN_AND_FIXTURES_ONLY")
        self.assertEqual(C1_STATE, "DESIGN_AND_FIXTURES_ONLY")
        self.assertEqual(C2_STATE, "DESIGN_AND_FIXTURES_ONLY")

    def test_legacy_engine_is_not_in_active_source_tree(self) -> None:
        self.assertFalse((ROOT / "src" / "ovc_opt_b").exists())
        self.assertTrue((ROOT / "legacy" / "quarantine" / "abcd-engine-v1-c0ad7ba").is_dir())

    def test_authority_registry_denies_market_selectors(self) -> None:
        authority = (ROOT / "registries" / "authority" / "ACTIVE_AUTHORITY.yaml").read_text(encoding="utf-8")
        repository_state = next(line for line in authority.splitlines() if line.startswith("state: "))
        self.assertIn(repository_state, ALLOWED_REPOSITORY_STATES)
        self.assertGreaterEqual(authority.count(": NONE"), 8)
        self.assertIn("runtime_imports: DENIED", authority)
        self.assertIn("discovery_seed_eligibility: DENIED", authority)


if __name__ == "__main__":
    unittest.main()
