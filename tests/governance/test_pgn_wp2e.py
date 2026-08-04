from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/governance/build_pgn_wp2e_repository_genesis_census.py"
POLICY = ROOT / "registries/governance/programme_genesis/PGN_REPOSITORY_GENESIS_CLASSIFICATION_POLICY_v0_1.json"
PRIOR = ROOT / "registries/governance/programme_genesis/pgn_census/PGN_PORTFOLIO_CENSUS_v0_1.json"

EXPECTED_CLASSIFICATIONS = {
    "NATIVE_PROGRAMME",
    "LEGACY_PROGRAMME_REQUIRING_CONVERSION",
    "SUPERSEDED_PROGRAMME",
    "ABSORBED_INTO_SUCCESSOR",
    "BOUNDED_PACKET_NOT_A_PROGRAMME",
    "PROPOSAL_NOT_ADMITTED",
    "UNRESOLVED",
}


def load_builder():
    spec = importlib.util.spec_from_file_location("build_pgn_wp2e_repository_genesis_census", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class NativeGenesisRepositoryCensusWP2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_builder()
        cls.census = cls.module.build_census(ROOT)
        cls.by_id = {item["object_id"]: item for item in cls.census["objects"]}

    def test_policy_freezes_exact_operator_classification_enum(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(EXPECTED_CLASSIFICATIONS, set(policy["classification_enum"]))
        self.assertEqual("PGN-WP2E", policy["packet_id"])
        self.assertEqual("PGN-G2B", policy["gate_id"])
        self.assertEqual("DENIED_PENDING_PGN_G2B", policy["authority"]["candidate_construction"])

    def test_census_is_deterministic_and_every_object_is_classified_once(self) -> None:
        again = self.module.build_census(ROOT)
        self.assertEqual(self.census, again)
        ids = [item["object_id"] for item in self.census["objects"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(self.census["object_count"], len(ids))
        self.assertGreaterEqual(len(ids), 20)
        for item in self.census["objects"]:
            self.assertIn(item["classification"], EXPECTED_CLASSIFICATIONS)
            self.assertFalse(item["candidate_constructed"])
            self.assertEqual("NONE", item["authority_effect"])
            self.assertTrue(item["sources"])

    def test_source_paths_and_hashes_are_reproducible(self) -> None:
        for item in self.census["objects"]:
            for source in item["sources"]:
                path = ROOT / source["path"]
                self.assertTrue(path.exists(), source["path"])
                if path.is_file():
                    self.assertEqual(source["sha256"], sha256(path), source["path"])
                else:
                    self.assertEqual("MAJOR_BOUNDED_INITIATIVE_ROOT", source["role"])
                    self.assertGreater(source["member_count"], 0)

    def test_native_legacy_and_non_admitted_boundaries_are_explicit(self) -> None:
        self.assertEqual("NATIVE_PROGRAMME", self.by_id["OVC-PG-v0.2"]["classification"])
        self.assertEqual("NATIVE_PROGRAMME", self.by_id["OVC-PG-NATIVE-PORTFOLIO-v0.2"]["classification"])
        self.assertEqual("PROPOSAL_NOT_ADMITTED", self.by_id["OVC-PCCR-v0.1"]["classification"])
        for programme_id in (
            "OVC-DEV-ACCEL-v0.1",
            "OVC-DEV-ACCEL-v0.2",
            "OVC-MTA-v0.2",
            "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.4",
            "PD-JUNE-FULL-MONTH-MDR",
        ):
            self.assertIn(programme_id, self.by_id)
            self.assertEqual("LEGACY_PROGRAMME_REQUIRING_CONVERSION", self.by_id[programme_id]["classification"])

    def test_supersession_and_initial_history_gap_are_not_hidden(self) -> None:
        old_release = self.by_id["OPT-A.GBPUSD.2026H1.v1"]
        self.assertEqual("SUPERSEDED_PROGRAMME", old_release["classification"])
        self.assertEqual(3, len(old_release["successors"]))
        coverage = self.by_id["COVERAGE::PRE_C0AD7BA_GIT_HISTORY"]
        self.assertEqual("UNRESOLVED", coverage["classification"])
        self.assertFalse(self.census["coverage"]["initial_commit_resolved"])
        self.assertEqual("UNRESOLVED", self.census["coverage"]["pre_snapshot_history"])
        self.assertIn("COVERAGE::PRE_C0AD7BA_GIT_HISTORY", self.census["coverage_and_unresolved_ledger"]["unresolved_object_ids"])

    def test_lineage_has_no_self_loop_or_unknown_successor(self) -> None:
        ids = set(self.by_id)
        external_successor_prefixes = ("OPT-A.GBPUSD.",)
        for item in self.census["lineage_consolidation_ledger"]:
            self.assertNotIn(item["object_id"], item["successors"])
            for successor in item["successors"]:
                self.assertTrue(successor in ids or successor.startswith(external_successor_prefixes), successor)

    def test_exclusions_are_machine_readable_and_prior_census_is_preserved(self) -> None:
        exclusions = {item["object_id"] for item in self.census["exclusion_ledger"]}
        self.assertIn("OVC-PCCR-v0.1", exclusions)
        self.assertIn("OPT-A.GBPUSD.2026H1.v1", exclusions)
        self.assertTrue(any(item.startswith("INITIATIVE::docs/releases/") for item in exclusions))
        self.assertTrue(PRIOR.is_file())
        prior = json.loads(PRIOR.read_text(encoding="utf-8"))
        self.assertEqual(7, prior["adoption_target_count"])
        self.assertEqual("DENIED_PENDING_PGN_G2A", prior["candidate_construction_authority"])

    def test_wp3_candidate_construction_remains_absent_and_denied(self) -> None:
        self.assertEqual("DENIED_PENDING_PGN_G2B", self.census["authority"]["candidate_construction"])
        self.assertEqual("NONE", self.census["authority"]["authority_effect"])
        forbidden = list(ROOT.glob("**/PGN_WP3*")) + list(ROOT.glob("**/pgn-wp3*"))
        self.assertEqual([], forbidden)
        self.assertEqual("OPERATOR_ACKNOWLEDGE_EXPANDED_CENSUS_EXCLUSIONS_AND_LINEAGE_AT_PGN_G2B", self.census["next_action"])

    def test_compact_summary_is_printable_for_exact_head_materialisation(self) -> None:
        summary = {
            "object_count": self.census["object_count"],
            "classification_counts": self.census["classification_counts"],
            "object_kind_counts": self.census["object_kind_counts"],
            "unresolved_count": self.census["coverage_and_unresolved_ledger"]["unresolved_count"],
            "census_sha256": self.census["census_sha256"],
            "native_ids": sorted(item["object_id"] for item in self.census["objects"] if item["classification"] == "NATIVE_PROGRAMME"),
            "legacy_ids": sorted(item["object_id"] for item in self.census["objects"] if item["classification"] == "LEGACY_PROGRAMME_REQUIRING_CONVERSION"),
        }
        print("PGN_WP2E_SUMMARY=" + json.dumps(summary, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    unittest.main()
