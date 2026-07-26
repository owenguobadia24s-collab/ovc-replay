from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTHORITY = ROOT / "registries" / "authority" / "ACTIVE_AUTHORITY.yaml"
RELEASES = ROOT / "registries" / "releases"
INACTIVE_DOWNSTREAM_SELECTORS = ("opt_b_c2", "c2e", "c2_5", "c3", "opt_c", "opt_d")
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
    "state: C1_B1_G2_PASS_PUBLICATION_READY_WP5_AUTHORISED_NO_SELECTOR",
    "state: C1_WP5_PASS_REMOTE_VERIFIED_PENDING_B1_G4_NO_SELECTOR",
    "state: C1_B1_G5_PASS_SHADOW_ACTIVE_C2_DENIED",
    "state: C1_B1_G5_SHADOW_C2_G5_LOCAL_CANDIDATES_NO_SELECTOR",
}
ALLOWED_GOVERNANCE_RECORDS = {
    "README.md",
    "OPT_A_RELEASE_REGISTRY.yaml",
    "OPT_A_ACTIVE_SELECTORS.yaml",
    "OPT_A_VALIDATION_ACCESS_REGISTRY.yaml",
}


class NoLegacySelectorAuthorityTests(unittest.TestCase):
    def test_only_opt_a_and_bounded_c1_shadow_are_selected(self) -> None:
        text = AUTHORITY.read_text(encoding="utf-8")
        repository_state = next(line for line in text.splitlines() if line.startswith("state: "))
        self.assertIn(repository_state, ALLOWED_REPOSITORY_STATES)
        self.assertIn("  opt_a: ACTIVE", text)
        self.assertIn("  opt_b_c1: SHADOW", text)
        for selector in INACTIVE_DOWNSTREAM_SELECTORS:
            self.assertIn(f"  {selector}: NONE", text)
        self.assertIn("local_candidate_release: FROZEN_DISCOVERY_AND_DEVELOPMENT_LOCAL_ONLY", text)
        self.assertIn("publication: AUTHORISED_EXACT_RELEASES_ONLY", text)
        self.assertIn("publication_executed: false", text)
        self.assertIn("selector: NONE", text)
        self.assertIn("activation: NONE", text)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", text)
        self.assertIn("selector_rollback: ALL_C1_ROLE_SELECTORS_NONE", text)
        for denial in (
            "runtime_imports: DENIED",
            "release_parent_eligibility: DENIED",
            "selector_eligibility: DENIED",
            "rollback_target: DENIED",
            "parameter_source: DENIED",
            "discovery_seed_eligibility: DENIED",
        ):
            self.assertIn(denial, text)

    def test_release_registry_root_contains_governance_only(self) -> None:
        records = {path.name for path in RELEASES.rglob("*") if path.is_file()}
        self.assertEqual(ALLOWED_GOVERNANCE_RECORDS, records)

    def test_active_v2_selector_set_is_exact_and_rollback_safe(self) -> None:
        selectors = (RELEASES / "OPT_A_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        self.assertIn("state: ACTIVE", selectors)
        self.assertEqual(selectors.count("selector_state: ACTIVE"), 3)
        self.assertIn("authority_state: ACTIVE_DISCOVERY", selectors)
        self.assertIn("authority_state: ACTIVE_DEVELOPMENT", selectors)
        self.assertIn("authority_state: ACTIVE_VALIDATION", selectors)
        self.assertIn("consumption_state: LOCKED_UNCONSUMED", selectors)
        self.assertIn("all_role_selectors: NONE", selectors)
        self.assertIn("historical_v1_reactivation: PROHIBITED", selectors)


if __name__ == "__main__":
    unittest.main()
