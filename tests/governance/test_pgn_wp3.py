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
    spec = importlib.util.spec_from_file_location(
        "build_pgn_wp3_native_candidates", SCRIPT
    )
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
        commitment_ids = [
            item["programme_id"] for item in self.manifest["candidate_commitments"]
        ]
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
        self.assertEqual(
            "SEALED_CANDIDATE_COMMITMENTS_UNAPPROVED", self.manifest["status"]
        )
        self.assertEqual("NONE", self.manifest["authority_effect"])
        self.assertEqual("NONE", self.manifest["authority"]["reserved_authority"])

    def test_in_memory_candidates_preserve_source_authority_and_uncertainty(self) -> None:
        entries = self.registry["entries"]
        candidates = [self.builder.build_candidate(entry) for entry in entries]
        for item in candidates:
            self.assertEqual("NATIVE_CANDIDATE", item["object_type"])
            self.assertEqual("NONE", item["authority_effect"])
            candidate = item["native_candidate"]
            self.assertEqual("CANDIDATE_UNAPPROVED", candidate["status"])
            envelope = candidate["authority_envelope"]
            self.assertTrue(envelope["source_authority_preserved"])
            self.assertEqual("NONE", envelope["authority_delta"])
            self.assertEqual("DENIED_PENDING_PGN_G3", envelope["native_adoption"])
            self.assertEqual("NONE", envelope["reserved_authority"])
            audit = candidate["scope_audit"]
            self.assertEqual("RETROSPECTIVE_SOURCE_PRESERVING", audit["profile"])
            self.assertFalse(audit["fabricated_historical_intent"])
            self.assertEqual("UNRESOLVED_EXACT_SOURCE_TEXT", audit["purpose"])
            crosswalk = candidate["migration_crosswalk"]
            self.assertTrue(crosswalk["identity_preserved"])
            self.assertFalse(crosswalk["source_values_modified"])
            self.assertRegex(crosswalk["source_set_sha256"], r"^[0-9a-f]{64}$")
            self.assertFalse(candidate["lifecycle"]["source_lifecycle_modified"])

    def test_commitment_hashes_match_deterministic_candidate_bodies(self) -> None:
        entries = self.registry["entries"]
        candidates = [self.builder.build_candidate(entry) for entry in entries]
        for commitment, candidate in zip(
            self.manifest["candidate_commitments"], candidates
        ):
            self.assertEqual(
                commitment["candidate_sha256"], self.builder.sha256(candidate)
            )
        self.assertEqual(
            self.manifest["candidate_set_sha256"], self.builder.sha256(candidates)
        )

    def test_progressive_queue_discloses_only_r1(self) -> None:
        self.assertEqual(6, self.queue["group_count"])
        self.assertEqual(3, self.queue["maximum_candidates_per_group"])
        self.assertEqual("PGN-G3-R1", self.queue["rules"]["current_group"])
        self.assertEqual(EXPECTED_IDS[:3], self.queue["groups"][0]["candidate_ids"])
        for group in self.queue["groups"][1:]:
            self.assertEqual([], group["candidate_ids"])
            self.assertEqual(
                "LOCKED_PENDING_PREVIOUS_GROUP_ACKNOWLEDGEMENT",
                group["disclosure_status"],
            )
            self.assertRegex(group["sealed_candidate_bodies_sha256"], r"^[0-9a-f]{64}$")
        self.assertFalse(self.queue["rules"]["future_group_member_ids_disclosed"])
        self.assertFalse(self.queue["rules"]["group_acknowledgement_is_adoption"])

    def test_r1_materializes_but_r2_fails_closed_without_receipt(self) -> None:
        r1 = self.builder.build_group("PGN-G3-R1", ROOT)
        self.assertEqual(3, r1["candidate_count"])
        self.assertEqual(EXPECTED_IDS[:3], r1["candidate_ids"])
        self.assertEqual("NONE", r1["authority_effect"])
        self.assertEqual("DENIED_PENDING_PGN_G3", r1["native_adoption"])
        with self.assertRaises(PermissionError):
            self.builder.build_group("PGN-G3-R2", ROOT)

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

    def test_no_adoption_decision_or_future_group_receipt_exists(self) -> None:
        self.assertEqual(
            "DENIED_PENDING_PROGRESSIVE_PGN_G3_REVIEW_AND_PGN_G3",
            self.manifest["authority"]["native_adoption"],
        )
        self.assertEqual([], list(ROOT.glob("**/PGN_G3_NATIVE_ADOPTION_DECISION*")))
        self.assertEqual(
            [],
            list(
                ROOT.glob(
                    "docs/releases/programme-genesis-native-portfolio-v0-2/"
                    "pgn-g3/reviews/PGN_G3_R*_ACKNOWLEDGEMENT_RECEIPT.json"
                )
            ),
        )


if __name__ == "__main__":
    unittest.main()
