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

    def test_no_v2_release_selector_record_exists(self) -> None:
        active_records = [
            path.relative_to(ROOT).as_posix()
            for path in RELEASES.rglob("*")
            if path.is_file() and path.name != "README.md"
        ]
        self.assertEqual([], active_records)


if __name__ == "__main__":
    unittest.main()
