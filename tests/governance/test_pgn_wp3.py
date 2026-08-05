from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "registries/governance/programme_genesis/PGN_WP3_CLASS_REGISTRY_v0_1.json"
CANDIDATE_DIR = ROOT / "registries/governance/programme_genesis/pgn_candidates"
MANIFEST = CANDIDATE_DIR / "PGN_WP3_NATIVE_CANDIDATE_PORTFOLIO_v0_1.json"
QUEUE = CANDIDATE_DIR / "PGN_WP3_PROGRESSIVE_REVIEW_QUEUE_v0_1.json"
SCRIPT = ROOT / "scripts/governance/build_pgn_wp3_native_candidates.py"
G2B_DECISION = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g2b/PGN_G2B_OPERATOR_DECISION.json"
REVIEW_RECEIPT_DIR = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews"

EXPECTED_IDS = [
    "OVC-C1-WICK-BALANCE-CORRECTIVE-PROGRAMME-0.1",
    "OVC-C2.5-BOUNDED-EVENT-CONTRACT-v0.1",
    "OVC-C2E-NEUTRAL-EPISODE-v0.1",
    "OVC-CLOCK-CONTINUITY-REVIEW-v0.1",
    "OVC-DEV-ACCEL-v0.1",
    "OVC-DEV-ACCEL-v0.2",
    "OVC-DISCOVERY-OPERATING-HUB.v0.1",
    "OVC-MTA-v0.2",
    "OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2",
    "OVC-PD-JUNE-2026-OPERATOR-REVIEW-AND-MARKET-DESCRIPTION-ASSURANCE.v0.1",
    "OVC-RESEARCH-CONSOLE.v0.2",
    "OVC-RESEARCH-CONSOLE.v0.3",
    "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.1",
    "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.2",
    "OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.4",
    "PD-JUNE-FULL-MONTH-MDR",
]


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path}")
    return value


def load_builder():
    spec = importlib.util.spec_from_file_location("build_pgn_wp3_native_candidates", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NativeGenesisPortfolioWP3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load(REGISTRY)
        self.manifest = load(MANIFEST)
        self.queue = load(QUEUE)
        self.decision = load(G2B_DECISION)
        self.builder = load_builder()

    def test_exact_acknowledged_population_has_sealed_commitment_once(self) -> None:
        acknowledged = self.decision["candidate_construction_scope"]["programme_ids"]
        registry_ids = [entry["programme_id"] for entry in self.registry["entries"]]
        commitment_ids = [item["programme_id"] for item in self.manifest["candidate_commitments"]]
        self.assertEqual(EXPECTED_IDS, acknowledged)
        self.assertCountEqual(EXPECTED_IDS, registry_ids)
        self.assertCountEqual(EXPECTED_IDS, commitment_ids)
        self.assertEqual(16, len(set(commitment_ids)))
        self.assertEqual(16, self.manifest["candidate_count"])

    def test_commitments_are_unapproved_and_authority_neutral(self) -> None:
        for commitment in self.manifest["candidate_commitments"]:
            self.assertEqual("CANDIDATE_UNAPPROVED", commitment["status"])
            self.assertEqual("NONE", commitment["authority_effect"])
            self.assertNotEqual("UNKNOWN_CLASS", commitment["candidate_class"])
            self.assertRegex(commitment["candidate_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual("SEALED_CANDIDATE_COMMITMENTS_UNAPPROVED", self.manifest["status"])
        self.assertEqual("NONE", self.manifest["authority_effect"])
        self.assertEqual("NONE", self.manifest["authority"]["reserved_authority"])

    def test_in_memory_candidates_preserve_source_authority_and_uncertainty(self) -> None:
        candidates = [self.builder.build_candidate(entry) for entry in self.registry["entries"]]
        for item in candidates:
            candidate = item["native_candidate"]
            self.assertEqual("NATIVE_CANDIDATE", item["object_type"])
            self.assertEqual("NONE", item["authority_effect"])
            self.assertEqual("CANDIDATE_UNAPPROVED", candidate["status"])
            self.assertTrue(candidate["authority_envelope"]["source_authority_preserved"])
            self.assertEqual("NONE", candidate["authority_envelope"]["authority_delta"])
            self.assertEqual("DENIED_PENDING_PGN_G3", candidate["authority_envelope"]["native_adoption"])
            self.assertEqual("NONE", candidate["authority_envelope"]["reserved_authority"])
            self.assertFalse(candidate["scope_audit"]["fabricated_historical_intent"])
            self.assertTrue(candidate["migration_crosswalk"]["identity_preserved"])
            self.assertFalse(candidate["migration_crosswalk"]["source_values_modified"])
            self.assertFalse(candidate["lifecycle"]["source_lifecycle_modified"])

    def test_commitment_hashes_match_deterministic_candidate_bodies(self) -> None:
        candidates = [self.builder.build_candidate(entry) for entry in self.registry["entries"]]
        for commitment, candidate in zip(self.manifest["candidate_commitments"], candidates):
            self.assertEqual(commitment["candidate_sha256"], self.builder.sha256(candidate))
        self.assertEqual(self.manifest["candidate_set_sha256"], self.builder.sha256(candidates))

    def test_progressive_queue_remains_sealed_and_non_authoritative(self) -> None:
        self.assertEqual(6, self.queue["group_count"])
        self.assertEqual(3, self.queue["maximum_candidates_per_group"])
        self.assertEqual("PGN-G3-R1", self.queue["rules"]["current_group"])
        self.assertEqual(EXPECTED_IDS[:3], self.queue["groups"][0]["candidate_ids"])
        for group in self.queue["groups"][1:]:
            self.assertEqual([], group["candidate_ids"])
            self.assertEqual("LOCKED_PENDING_PREVIOUS_GROUP_ACKNOWLEDGEMENT", group["disclosure_status"])
            self.assertRegex(group["sealed_candidate_bodies_sha256"], r"^[0-9a-f]{64}$")
        self.assertFalse(self.queue["rules"]["future_group_member_ids_disclosed"])
        self.assertFalse(self.queue["rules"]["group_acknowledgement_is_adoption"])

    def test_progressive_materialization_follows_exact_receipts(self) -> None:
        for group_id in ("PGN-G3-R1", "PGN-G3-R2", "PGN-G3-R3", "PGN-G3-R4", "PGN-G3-R5", "PGN-G3-R6"):
            group = self.builder.build_group(group_id, ROOT)
            self.assertEqual(group_id, group["review_group_id"])
            self.assertEqual("NONE", group["authority_effect"])
            self.assertEqual("DENIED_PENDING_PGN_G3", group["native_adoption"])
        r6 = self.builder.build_group("PGN-G3-R6", ROOT)
        self.assertEqual(
            ["OVC-PD-JUNE-2026-OPERATOR-REVIEW-AND-MARKET-DESCRIPTION-ASSURANCE.v0.1"],
            r6["candidate_ids"],
        )
        self.assertEqual("bfe34292f0815eeae2ec1da9438ee9d20e4436a9444c1d3627d233b26ea245c5", r6["candidate_group_sha256"])

    def test_materialized_manifest_and_queue_match_builder(self) -> None:
        manifest, queue = self.builder.build_bundle(ROOT)
        self.assertEqual(self.manifest, manifest)
        self.assertEqual(self.queue, queue)
        print(
            "PGN_WP3_SUMMARY="
            + json.dumps(
                {
                    "candidate_count": manifest["candidate_count"],
                    "candidate_set_sha256": manifest["candidate_set_sha256"],
                    "commitment_set_sha256": manifest["commitment_set_sha256"],
                    "manifest_sha256": self.builder.sha256(manifest),
                    "queue_sha256": self.builder.sha256(queue),
                    "group_count": queue["group_count"],
                    "current_group": queue["rules"]["current_group"],
                    "authority_effect": manifest["authority_effect"],
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )

    def test_no_adoption_decision_and_receipts_are_progressive(self) -> None:
        self.assertEqual(
            "DENIED_PENDING_PROGRESSIVE_PGN_G3_REVIEW_AND_PGN_G3",
            self.manifest["authority"]["native_adoption"],
        )
        self.assertEqual([], list(ROOT.glob("**/PGN_G3_NATIVE_ADOPTION_DECISION*")))
        receipts = sorted(path.name for path in REVIEW_RECEIPT_DIR.glob("PGN_G3_R*_ACKNOWLEDGEMENT_RECEIPT.json"))
        self.assertEqual(
            [
                "PGN_G3_R1_ACKNOWLEDGEMENT_RECEIPT.json",
                "PGN_G3_R2_ACKNOWLEDGEMENT_RECEIPT.json",
                "PGN_G3_R3_ACKNOWLEDGEMENT_RECEIPT.json",
                "PGN_G3_R4_ACKNOWLEDGEMENT_RECEIPT.json",
                "PGN_G3_R5_ACKNOWLEDGEMENT_RECEIPT.json",
            ],
            receipts,
        )
        expected_effects = [
            "DISCLOSE_AND_MATERIALISE_PGN_G3_R2_ONLY",
            "DISCLOSE_AND_MATERIALISE_PGN_G3_R3_ONLY",
            "DISCLOSE_AND_MATERIALISE_PGN_G3_R4_ONLY",
            "DISCLOSE_AND_MATERIALISE_PGN_G3_R5_ONLY",
            "DISCLOSE_AND_MATERIALISE_PGN_G3_R6_ONLY",
        ]
        for name, effect in zip(receipts, expected_effects):
            receipt = load(REVIEW_RECEIPT_DIR / name)
            self.assertEqual("NONE", receipt["native_adoption"])
            self.assertEqual(effect, receipt["authority_effect"])


if __name__ == "__main__":
    unittest.main()
