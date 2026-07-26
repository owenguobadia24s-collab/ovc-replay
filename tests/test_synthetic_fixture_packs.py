from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
EXPECTED_COUNTS = {"OPT_A": 14, "C1": 12, "C2": 16}
ALLOWED_REPOSITORY_STATES = {
    "state: V2_FOUNDATION_NO_MARKET_AUTHORITY",
    "state: V2_FOUNDATION_RESET_COMPLETE_NO_MARKET_AUTHORITY",
    "state: V2_OBSERVATION_CONSTRUCTION_REVIEW_PASS_NO_MARKET_AUTHORITY",
    "state: V2_ROLE_RELEASE_FREEZE_PASS_NO_MARKET_AUTHORITY",
    "state: V2_REMOTE_PUBLICATION_REVIEW_PASS_NO_MARKET_AUTHORITY",
    "state: V2_SELECTOR_SET_ACTIVE_NO_DOWNSTREAM_MARKET_AUTHORITY",
    "state: C1_WP1_BOUNDARY_PASS_NO_C1_MARKET_AUTHORITY",
    "state: C1_WP2_CONTRACT_FREEZE_PASS_NO_C1_MARKET_AUTHORITY",
}
FORBIDDEN = (
    "B-STATE-",
    "OPT-C-",
    "OPT-D-",
    "PAPER-PLAYBOOK",
    "story_id",
    "candidate_id",
    "outcome_label",
)


def git_blob_sha1(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


class SyntheticFixturePackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packs = {
            name: json.loads((FIXTURES / name / "FIXTURE_PACK.json").read_text(encoding="utf-8"))
            for name in ("opt_a", "c1", "c2")
        }
        cls.manifest = json.loads((FIXTURES / "FIXTURE_MANIFEST.json").read_text(encoding="utf-8"))

    def test_case_counts_and_unique_ids(self) -> None:
        counts = {pack["layer"]: pack["case_count"] for pack in self.packs.values()}
        self.assertEqual(counts, EXPECTED_COUNTS)
        ids: list[str] = [case["id"] for pack in self.packs.values() for case in pack["cases"]]
        self.assertEqual(len(ids), 42)
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_case_is_synthetic_and_non_authoritative(self) -> None:
        for pack in self.packs.values():
            self.assertIs(pack["synthetic"], True)
            self.assertEqual(pack["market_authority"], "NONE")
            for case in pack["cases"]:
                self.assertIs(case["synthetic"], True)
                self.assertEqual(case["authority"]["market"], "NONE")
                self.assertEqual(case["authority"]["discovery_seed"], "DENIED")
                self.assertEqual(case["authority"]["release_parent"], "DENIED")

    def test_manifest_matches_exact_git_blob_identities(self) -> None:
        self.assertEqual(self.manifest["case_count"], 42)
        self.assertEqual(self.manifest["layer_counts"], EXPECTED_COUNTS)
        for record in self.manifest["files"]:
            path = ROOT / record["path"]
            self.assertTrue(path.is_file(), record["path"])
            self.assertEqual(git_blob_sha1(path), record["git_blob_sha1"])

    def test_no_legacy_story_candidate_or_outcome_seeds(self) -> None:
        payload = "\n".join(json.dumps(pack, sort_keys=True) for pack in self.packs.values())
        for token in FORBIDDEN:
            self.assertNotIn(token, payload)

    def test_c1_pack_enforces_atomic_fact_boundary(self) -> None:
        rules = set(self.packs["c1"]["boundary_rules"])
        required = {
            "ATOMIC_FACTS_ONLY",
            "NO_THRESHOLDS",
            "NO_LEVELS",
            "NO_STATES",
            "NO_EVENTS",
            "NO_SEMANTIC_NAMES",
            "NO_FUTURE_OUTCOMES",
        }
        self.assertTrue(required <= rules)

    def test_c2_pack_has_five_independent_axes_and_no_winner(self) -> None:
        pack = self.packs["c2"]
        self.assertEqual(pack["axes"], ["LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY"])
        self.assertIn("ALL_AXES_INDEPENDENT", pack["boundary_rules"])
        self.assertIn("NO_OVERALL_WINNER", pack["boundary_rules"])

    def test_fixture_tree_contains_no_market_payload_files(self) -> None:
        self.assertFalse(any(FIXTURES.rglob("*.csv")))
        self.assertFalse(any(FIXTURES.rglob("*.parquet")))
        self.assertFalse(any(FIXTURES.rglob("*.feather")))

    def test_synthetic_fixtures_remain_non_authoritative(self) -> None:
        authority = (ROOT / "registries" / "authority" / "ACTIVE_AUTHORITY.yaml").read_text(encoding="utf-8")
        repository_state = next(line for line in authority.splitlines() if line.startswith("state: "))
        self.assertIn(repository_state, ALLOWED_REPOSITORY_STATES)
        self.assertIn("  opt_a: ACTIVE", authority)
        self.assertGreaterEqual(authority.count(": NONE"), 7)
        self.assertIn("discovery_seed_eligibility: DENIED", authority)


if __name__ == "__main__":
    unittest.main()
