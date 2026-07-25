from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTHORITY = ROOT / "registries" / "authority" / "ACTIVE_AUTHORITY.yaml"
RELEASES = ROOT / "registries" / "releases"
SELECTORS = ("opt_a", "opt_b_c1", "opt_b_c2", "c2e", "c2_5", "c3", "opt_c", "opt_d")
ALLOWED_REPOSITORY_STATES = {
    "state: V2_FOUNDATION_NO_MARKET_AUTHORITY",
    "state: V2_FOUNDATION_RESET_COMPLETE_NO_MARKET_AUTHORITY",
    "state: V2_OBSERVATION_CONSTRUCTION_REVIEW_PASS_NO_MARKET_AUTHORITY",
}
ALLOWED_GOVERNANCE_RECORDS = {
    "README.md",
    "OPT_A_RELEASE_REGISTRY.yaml",
    "OPT_A_ACTIVE_SELECTORS.yaml",
    "OPT_A_VALIDATION_ACCESS_REGISTRY.yaml",
}


class NoLegacySelectorAuthorityTests(unittest.TestCase):
    def test_all_market_selectors_are_none(self) -> None:
        text = AUTHORITY.read_text(encoding="utf-8")
        repository_state = next(line for line in text.splitlines() if line.startswith("state: "))
        self.assertIn(repository_state, ALLOWED_REPOSITORY_STATES)
        for selector in SELECTORS:
            self.assertIn(f"  {selector}: NONE", text)
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
        records = {
            path.name
            for path in RELEASES.rglob("*")
            if path.is_file()
        }
        self.assertEqual(ALLOWED_GOVERNANCE_RECORDS, records)

    def test_no_active_v2_selector_record_exists(self) -> None:
        selectors = (RELEASES / "OPT_A_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        self.assertIn("state: NONE", selectors)
        self.assertNotIn("selector_state: ACTIVE", selectors)
        self.assertIn("all_role_selectors: NONE", selectors)
        self.assertIn("historical_v1_reactivation: PROHIBITED", selectors)


if __name__ == "__main__":
    unittest.main()
