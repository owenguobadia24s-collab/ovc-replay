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
    "state: V2_SELECTOR_SET_ACTIVE_NO_DOWNSTREAM_MARKET_AUTHORITY",
    "state: C1_WP1_BOUNDARY_PASS_NO_C1_MARKET_AUTHORITY",
    "state: C1_WP2_CONTRACT_FREEZE_PASS_NO_C1_MARKET_AUTHORITY",
    "state: C1_WP3_REFERENCE_ENGINE_PASS_NO_C1_MARKET_AUTHORITY",
    "state: C1_B1_G0_PASS_WP4_REPLAY_AUTHORISED_NO_C1_RELEASE_AUTHORITY",
    "state: C1_WP4_REPLAY_QA_PASS_LOCAL_CANDIDATE_NO_PUBLICATION_AUTHORITY",
    "state: C1_B1_G1_PASS_EXACT_CANDIDATE_FREEZE_AUTHORISED_NO_PUBLICATION_AUTHORITY",
}


class ActiveTreeFoundationTests(unittest.TestCase):
    def test_clean_namespaces_import(self) -> None:
        self.assertEqual(ovc.__version__, "0.2.0")
        self.assertEqual(OPT_A_STATE, "DESIGN_AND_FIXTURES_ONLY")
        self.assertEqual(C1_STATE, "B1_G1_CANDIDATE_INVENTORY_ACCEPTED_FREEZE_AUTHORISED")
        self.assertEqual(C2_STATE, "DESIGN_AND_FIXTURES_ONLY")

    def test_legacy_engine_is_not_in_active_source_tree(self) -> None:
        self.assertFalse((ROOT / "src" / "ovc_opt_b").exists())
        self.assertTrue((ROOT / "legacy" / "quarantine" / "abcd-engine-v1-c0ad7ba").is_dir())

    def test_authority_registry_limits_activation_to_opt_a(self) -> None:
        authority = (ROOT / "registries" / "authority" / "ACTIVE_AUTHORITY.yaml").read_text(encoding="utf-8")
        repository_state = next(line for line in authority.splitlines() if line.startswith("state: "))
        self.assertIn(repository_state, ALLOWED_REPOSITORY_STATES)
        self.assertIn("  opt_a: ACTIVE", authority)
        self.assertGreaterEqual(authority.count(": NONE"), 7)
        self.assertIn("active_handoff: NONE", authority)
        self.assertIn("runtime_imports: DENIED", authority)
        self.assertIn("discovery_seed_eligibility: DENIED", authority)
        self.assertIn("market_replay: COMPLETE_WP4_PASS", authority)
        self.assertIn("release_freeze: AUTHORISED_EXACT_CANDIDATE_ONLY_PENDING_EXECUTION", authority)
        self.assertIn("selector: NONE", authority)


if __name__ == "__main__":
    unittest.main()
