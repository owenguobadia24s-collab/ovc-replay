from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/governance/build_pgn_wp2e_repository_genesis_census.py"
BUNDLE_SCRIPT = ROOT / "scripts/governance/materialize_pgn_wp2e_bundle.py"
POLICY = ROOT / "registries/governance/programme_genesis/PGN_REPOSITORY_GENESIS_CLASSIFICATION_POLICY_v0_1.json"
PRIOR = ROOT / "registries/governance/programme_genesis/pgn_census/PGN_PORTFOLIO_CENSUS_v0_1.json"
MANIFEST = ROOT / "registries/governance/programme_genesis/pgn_census/PGN_REPOSITORY_GENESIS_CENSUS_v0_2.json"

EXPECTED_CLASSIFICATIONS = {
    "NATIVE_PROGRAMME",
    "LEGACY_PROGRAMME_REQUIRING_CONVERSION",
    "SUPERSEDED_PROGRAMME",
    "ABSORBED_INTO_SUCCESSOR",
    "BOUNDED_PACKET_NOT_A_PROGRAMME",
    "PROPOSAL_NOT_ADMITTED",
    "UNRESOLVED",
}
EXPECTED_COUNTS = {
    "BOUNDED_PACKET_NOT_A_PROGRAMME": 70,
    "LEGACY_PROGRAMME_REQUIRING_CONVERSION": 16,
    "NATIVE_PROGRAMME": 2,
    "PROPOSAL_NOT_ADMITTED": 1,
    "SUPERSEDED_PROGRAMME": 1,
    "UNRESOLVED": 18,
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class NativeGenesisRepositoryCensusWP2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module("build_pgn_wp2e_repository_genesis_census", SCRIPT)
        cls.bundle_module = load_module("materialize_pgn_wp2e_bundle", BUNDLE_SCRIPT)
        cls.census = cls.module.build_census(ROOT)
        cls.by_id = {item["object_id"]: item for item in cls.census["objects"]}
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

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
        self.assertEqual(108, len(ids))
        self.assertEqual(EXPECTED_COUNTS, self.census["classification_counts"])
        self.assertNotIn("NONE", ids)
        self.assertNotIn("DENIED", ids)
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

    def test_materialized_bundle_matches_deterministic_builder_and_child_hashes(self) -> None:
        generated_manifest, _ = self.bundle_module.build_bundle(ROOT)
        self.assertEqual(self.manifest, generated_manifest)
        self.assertEqual(6, len(self.manifest["object_ledgers"]))
        self.assertEqual(108, sum(item["object_count"] for item in self.manifest["object_ledgers"]))
        refs = list(self.manifest["object_ledgers"]) + [
            self.manifest["exclusion_ledger"],
            self.manifest["lineage_consolidation_ledger"],
            self.manifest["coverage_and_unresolved_ledger"],
        ]
        for ref in refs:
            path = ROOT / ref["path"]
            self.assertTrue(path.is_file(), ref["path"])
            self.assertEqual(ref["bytes"], path.stat().st_size, ref["path"])
            self.assertEqual(ref["sha256"], sha256(path), ref["path"])

    def test_native_legacy_and_non_admitted_boundaries_are_explicit(self) -> None:
        self.assertEqual("NATIVE_PROGRAMME", self.by_id["OVC-PG-v0.2"]["classification"])
        self.assertEqual("NATIVE_PROGRAMME", self.by_id["OVC-PG-NATIVE-PORTFOLIO-v0.2"]["classification"])
        self.assertEqual("PROPOSAL_NOT_ADMITTED", self.by_id["OVC-PCCR-v0.1"]["classification"])
        self.assertEqual("BOUNDED_PACKET_NOT_A_PROGRAMME", self.by_id["OVC-PLANNED-CLOSURE-CONTINUITY-REMEDIATION-IMPLEMENTATION-PLAN-0.1"]["classification"])
        for programme_id in (
            "OVC-DEV-ACCEL-v0.1",
            "OVC-DEV-ACCEL-v0.2",
            "OVC-MTA-v0.2",
            "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.4",
            "PD-JUNE-FULL-MONTH-MDR",
        ):
            self.assertEqual("LEGACY_PROGRAMME_REQUIRING_CONVERSION", self.by_id[programme_id]["classification"])

    def test_supersession_absorption_and_initial_history_gap_are_not_hidden(self) -> None:
        old_release = self.by_id["OPT-A.GBPUSD.2026H1.v1"]
        self.assertEqual("SUPERSEDED_PROGRAMME", old_release["classification"])
        self.assertEqual(3, len(old_release["successors"]))
        self.assertEqual(0, self.census["classification_counts"].get("ABSORBED_INTO_SUCCESSOR", 0))
        coverage = self.by_id["COVERAGE::PRE_C0AD7BA_GIT_HISTORY"]
        self.assertEqual("UNRESOLVED", coverage["classification"])
        self.assertFalse(self.census["coverage"]["initial_commit_resolved"])
        self.assertEqual("UNRESOLVED", self.census["coverage"]["pre_snapshot_history"])
        self.assertIn("COVERAGE::PRE_C0AD7BA_GIT_HISTORY", self.census["coverage_and_unresolved_ledger"]["unresolved_object_ids"])

    def test_lineage_has_no_self_loop_or_name_only_absorption(self) -> None:
        ids = set(self.by_id)
        for item in self.census["lineage_consolidation_ledger"]:
            self.assertNotIn(item["object_id"], item["successors"])
            for successor in item["successors"]:
                self.assertIn(successor, ids)
        self.assertEqual(1, len(self.census["lineage_consolidation_ledger"]))
        self.assertEqual("OPT-A.GBPUSD.2026H1.v1", self.census["lineage_consolidation_ledger"][0]["object_id"])

    def test_exclusions_are_machine_readable_and_prior_census_is_preserved(self) -> None:
        exclusions = {item["object_id"] for item in self.census["exclusion_ledger"]}
        self.assertEqual(72, len(exclusions))
        self.assertIn("OVC-PCCR-v0.1", exclusions)
        self.assertIn("OPT-A.GBPUSD.2026H1.v1", exclusions)
        self.assertTrue(any(item.startswith("INITIATIVE::docs/releases/") for item in exclusions))
        prior = json.loads(PRIOR.read_text(encoding="utf-8"))
        self.assertEqual(7, prior["adoption_target_count"])
        self.assertEqual("DENIED_PENDING_PGN_G2A", prior["candidate_construction_authority"])

    def test_wp2e_census_remains_frozen_predecision_evidence_after_wp3(self) -> None:
        self.assertEqual("DENIED_PENDING_PGN_G2B", self.census["authority"]["candidate_construction"])
        self.assertEqual("NONE", self.census["authority"]["authority_effect"])
        candidate_manifest = json.loads(
            (
                ROOT
                / "registries/governance/programme_genesis/pgn_candidates/PGN_WP3_NATIVE_CANDIDATE_PORTFOLIO_v0_1.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual("SEALED_CANDIDATE_COMMITMENTS_UNAPPROVED", candidate_manifest["status"])
        self.assertEqual("NONE", candidate_manifest["authority_effect"])
        self.assertEqual(16, candidate_manifest["candidate_count"])
        self.assertEqual(
            "DENIED_PENDING_PROGRESSIVE_PGN_G3_REVIEW_AND_PGN_G3",
            candidate_manifest["authority"]["native_adoption"],
        )
        self.assertEqual("OPERATOR_ACKNOWLEDGE_EXPANDED_CENSUS_EXCLUSIONS_AND_LINEAGE_AT_PGN_G2B", self.census["next_action"])

    def test_compact_summary_is_printable_for_exact_head_assurance(self) -> None:
        summary = {
            "object_count": self.census["object_count"],
            "classification_counts": self.census["classification_counts"],
            "object_kind_counts": self.census["object_kind_counts"],
            "unresolved_count": self.census["coverage_and_unresolved_ledger"]["unresolved_count"],
            "census_sha256": self.census["census_sha256"],
            "bundle_manifest_sha256": self.manifest["bundle_manifest_sha256"],
            "native_ids": sorted(item["object_id"] for item in self.census["objects"] if item["classification"] == "NATIVE_PROGRAMME"),
            "legacy_ids": sorted(item["object_id"] for item in self.census["objects"] if item["classification"] == "LEGACY_PROGRAMME_REQUIRING_CONVERSION"),
        }
        print("PGN_WP2E_SUMMARY=" + json.dumps(summary, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    unittest.main()
