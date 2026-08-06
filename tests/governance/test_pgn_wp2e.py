from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts/governance/build_pgn_wp2e_frozen_snapshot.py"
POLICY = ROOT / "registries/governance/programme_genesis/PGN_REPOSITORY_GENESIS_CLASSIFICATION_POLICY_v0_1.json"
PRIOR = ROOT / "registries/governance/programme_genesis/pgn_census/PGN_PORTFOLIO_CENSUS_v0_1.json"
MANIFEST = ROOT / "registries/governance/programme_genesis/pgn_census/PGN_REPOSITORY_GENESIS_CENSUS_v0_2.json"
ADMISSIONS = ROOT / "registries/governance/programme_genesis/post_snapshot/PGN_POST_SNAPSHOT_PROGRAMME_ADMISSION_LEDGER_v0_1.json"
CANDIDATES = ROOT / "registries/governance/programme_genesis/pgn_candidates/PGN_WP3_NATIVE_CANDIDATE_PORTFOLIO_v0_1.json"
DECISION = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/post-snapshot-admissions/MG_POST_SNAPSHOT_OPERATOR_ADMISSION_DECISION.json"
QA = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/post-snapshot-admissions/MG_POST_SNAPSHOT_ADMISSION_QA_PACKET.json"
STATE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/post-snapshot-admissions/MG_POST_SNAPSHOT_ADMISSION_STATE.json"
RECEIPT = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/post-snapshot-admissions/MG_POST_SNAPSHOT_ADMISSION_POST_MERGE_RECEIPT.json"

MG_PROGRAMME = "OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1"

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


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path}")
    return value


class NativeGenesisFrozenSnapshotAndAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module("build_pgn_wp2e_frozen_snapshot", BUILDER)
        cls.snapshot = cls.module.build_snapshot(ROOT)
        cls.manifest = cls.snapshot["manifest"]
        cls.objects = cls.snapshot["objects"]
        cls.by_id = {item["object_id"]: item for item in cls.objects}
        cls.admissions = cls.module.load_post_snapshot_admissions(ROOT)
        cls.candidates = load(CANDIDATES)
        cls.decision = load(DECISION)
        cls.qa = load(QA)
        cls.state = load(STATE)
        cls.receipt = load(RECEIPT)

    def test_policy_freezes_exact_operator_classification_enum(self) -> None:
        policy = load(POLICY)
        self.assertEqual(EXPECTED_CLASSIFICATIONS, set(policy["classification_enum"]))
        self.assertEqual("PGN-WP2E", policy["packet_id"])
        self.assertEqual("PGN-G2B", policy["gate_id"])
        self.assertEqual(
            "DENIED_PENDING_PGN_G2B",
            policy["authority"]["candidate_construction"],
        )

    def test_snapshot_manifest_identity_and_counts_are_immutable(self) -> None:
        self.assertEqual(108, self.manifest["object_count"])
        self.assertEqual(EXPECTED_COUNTS, self.manifest["classification_counts"])
        self.assertEqual(72, self.manifest["exclusion_ledger"]["entry_count"])
        self.assertEqual(
            "b3fe76028609c7ab45b0779411df8206f0aaf22eecaaf6ff20f4106f49387b68",
            self.manifest["bundle_manifest_sha256"],
        )
        self.assertEqual(
            "0ecec2bed3094cf659e25a1c74612d64ae10aec6f0c22114f4be6b11747c3584",
            self.manifest["child_file_identity_sha256"],
        )
        self.assertEqual(
            "d562b7427ab0c306df04e2472a517d1b0bceb8b7",
            self.snapshot["manifest_git_blob_sha1"],
        )
        self.assertEqual(6, len(self.manifest["object_ledgers"]))
        self.assertEqual(
            108,
            sum(item["object_count"] for item in self.manifest["object_ledgers"]),
        )

    def test_snapshot_objects_are_unique_and_not_rebuilt_from_later_files(self) -> None:
        ids = [item["object_id"] for item in self.objects]
        self.assertEqual(108, len(ids))
        self.assertEqual(108, len(set(ids)))
        self.assertNotIn(MG_PROGRAMME, ids)
        self.assertNotIn("NONE", ids)
        self.assertNotIn("DENIED", ids)
        for item in self.objects:
            self.assertIn(item["classification"], EXPECTED_CLASSIFICATIONS)
            self.assertTrue(item["primary_source_path"])
            self.assertTrue((ROOT / item["primary_source_path"]).exists())
            self.assertGreater(item["source_count"], 0)

    def test_native_legacy_and_non_admitted_boundaries_remain_historical(self) -> None:
        self.assertEqual(
            "NATIVE_PROGRAMME",
            self.by_id["OVC-PG-v0.2"]["classification"],
        )
        self.assertEqual(
            "NATIVE_PROGRAMME",
            self.by_id["OVC-PG-NATIVE-PORTFOLIO-v0.2"]["classification"],
        )
        self.assertEqual(
            "PROPOSAL_NOT_ADMITTED",
            self.by_id["OVC-PCCR-v0.1"]["classification"],
        )
        for programme_id in (
            "OVC-DEV-ACCEL-v0.1",
            "OVC-DEV-ACCEL-v0.2",
            "OVC-MTA-v0.2",
            "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.4",
            "PD-JUNE-FULL-MONTH-MDR",
        ):
            self.assertEqual(
                "LEGACY_PROGRAMME_REQUIRING_CONVERSION",
                self.by_id[programme_id]["classification"],
            )

    def test_snapshot_exclusions_lineage_and_prior_census_are_preserved(self) -> None:
        exclusions = {
            item["object_id"] for item in self.snapshot["exclusion_ledger"]
        }
        self.assertEqual(72, len(exclusions))
        self.assertIn("OVC-PCCR-v0.1", exclusions)
        self.assertIn("OPT-A.GBPUSD.2026H1.v1", exclusions)
        self.assertTrue(
            any(item.startswith("INITIATIVE::docs/releases/") for item in exclusions)
        )
        lineage = self.snapshot["lineage_consolidation_ledger"]
        self.assertEqual(1, len(lineage))
        self.assertEqual("OPT-A.GBPUSD.2026H1.v1", lineage[0]["object_id"])
        prior = load(PRIOR)
        self.assertEqual(7, prior["adoption_target_count"])
        self.assertEqual(
            "DENIED_PENDING_PGN_G2A",
            prior["candidate_construction_authority"],
        )

    def test_sealed_sixteen_candidate_population_is_unchanged(self) -> None:
        self.assertEqual(16, self.candidates["candidate_count"])
        self.assertEqual(
            "7dad0cee63ba6d533eff097f333645914e92d87e1964634786312f9ede58354a",
            self.candidates["candidate_set_sha256"],
        )
        candidate_ids = {
            item["programme_id"]
            for item in self.candidates["candidate_commitments"]
        }
        self.assertEqual(16, len(candidate_ids))
        self.assertNotIn(MG_PROGRAMME, candidate_ids)
        self.assertEqual(
            "SEALED_CANDIDATE_COMMITMENTS_UNAPPROVED",
            self.candidates["status"],
        )
        self.assertEqual("NONE", self.candidates["authority_effect"])

    def test_post_snapshot_admission_is_additive_and_bounded(self) -> None:
        self.assertEqual("ACTIVE_APPEND_ONLY", self.admissions["status"])
        self.assertEqual(1, self.admissions["admission_count"])
        self.assertEqual(1, len(self.admissions["admissions"]))
        admission = self.admissions["admissions"][0]
        self.assertEqual(MG_PROGRAMME, admission["programme_id"])
        self.assertEqual(
            "OPERATOR_ADMITTED_BOUNDED_PROGRAMME",
            admission["admission_status"],
        )
        self.assertEqual(
            "POST_SNAPSHOT_OUTSIDE_DEFERRED_PGN_NATIVE_MIGRATION",
            admission["admission_mode"],
        )
        self.assertEqual("NONE", admission["frozen_snapshot_effect"])
        self.assertEqual("NONE", admission["sealed_sixteen_candidate_population_effect"])
        self.assertEqual(
            "INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT_IMPLEMENTATION_ONLY",
            admission["authority"]["granted"],
        )
        self.assertEqual("NONE", admission["authority"]["selector_activation"])
        self.assertEqual("NONE", admission["authority"]["rule_promotion"])
        self.assertEqual(
            "NONE",
            admission["authority"][
                "publication_validation_probability_risk_exposure_execution"
            ],
        )
        frozen = self.admissions["frozen_snapshot"]
        self.assertEqual(108, frozen["object_count"])
        self.assertEqual(72, frozen["exclusion_count"])
        self.assertEqual(16, frozen["candidate_portfolio_count"])
        self.assertEqual("PROHIBITED", frozen["mutation"])

    def test_operator_decision_qa_state_and_receipt_match_admission(self) -> None:
        self.assertEqual(MG_PROGRAMME, self.decision["programme_id"])
        self.assertEqual(
            "PASS_BOUNDED_POST_SNAPSHOT_ADMISSION",
            self.decision["decision"],
        )
        self.assertEqual(
            "INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT_IMPLEMENTATION_ONLY",
            self.decision["authority_delta"],
        )
        self.assertEqual([], self.qa["blockers"])
        self.assertEqual("PASS_COMPLETED", self.qa["qa_recommendation"])
        self.assertEqual("PASS_COMPLETED", self.qa["status"])
        self.assertEqual("COMPLETED", self.state["status"])
        self.assertEqual(
            "SATISFIED_OPERATOR_DECISION",
            self.state["authority_required"],
        )
        self.assertEqual("MG-G0-REBASE_AND_RERUN", self.state["next_packet"])
        self.assertEqual(
            "448f8bfa85f4ddc9a7db6cfa8ae3f3aece1c1375",
            self.state["merge_commit"],
        )
        self.assertTrue(self.receipt["effective"])
        self.assertEqual(339, self.receipt["pull_request"])
        self.assertEqual(
            "e9a299b776f90801588bccf665d187d8c29f3382",
            self.receipt["final_head"],
        )
        self.assertEqual(
            "448f8bfa85f4ddc9a7db6cfa8ae3f3aece1c1375",
            self.receipt["merge_commit"],
        )
        self.assertEqual("NONE", self.receipt["reserved_authority"])

    def test_compact_summary_is_printable_for_exact_head_assurance(self) -> None:
        summary = {
            "snapshot_object_count": self.manifest["object_count"],
            "snapshot_exclusion_count": self.manifest["exclusion_ledger"]["entry_count"],
            "snapshot_bundle_manifest_sha256": self.manifest["bundle_manifest_sha256"],
            "sealed_candidate_count": self.candidates["candidate_count"],
            "post_snapshot_admission_count": self.admissions["admission_count"],
            "admitted_programme": self.admissions["admissions"][0]["programme_id"],
        }
        print(
            "PGN_FROZEN_SNAPSHOT_AND_ADMISSION_SUMMARY="
            + json.dumps(summary, sort_keys=True, separators=(",", ":"))
        )


if __name__ == "__main__":
    unittest.main()
