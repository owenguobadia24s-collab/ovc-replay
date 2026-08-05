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
        raise AssertionError(path)
    return value


def load_builder():
    spec = importlib.util.spec_from_file_location("pgn_builder", SCRIPT)
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

    def test_exact_population_and_deterministic_commitments(self) -> None:
        acknowledged = self.decision["candidate_construction_scope"]["programme_ids"]
        registry_ids = [entry["programme_id"] for entry in self.registry["entries"]]
        commitments = self.manifest["candidate_commitments"]
        self.assertEqual(EXPECTED_IDS, acknowledged)
        self.assertCountEqual(EXPECTED_IDS, registry_ids)
        self.assertCountEqual(EXPECTED_IDS, [item["programme_id"] for item in commitments])
        self.assertEqual(16, len(commitments))
        candidates = [self.builder.build_candidate(entry) for entry in self.registry["entries"]]
        for commitment, candidate in zip(commitments, candidates):
            self.assertEqual("CANDIDATE_UNAPPROVED", commitment["status"])
            self.assertEqual("NONE", commitment["authority_effect"])
            self.assertEqual(commitment["candidate_sha256"], self.builder.sha256(candidate))
            self.assertTrue(candidate["native_candidate"]["authority_envelope"]["source_authority_preserved"])
            self.assertFalse(candidate["native_candidate"]["scope_audit"]["fabricated_historical_intent"])
        self.assertEqual(self.manifest["candidate_set_sha256"], self.builder.sha256(candidates))

    def test_queue_remains_sealed_and_acknowledgement_is_not_adoption(self) -> None:
        self.assertEqual(6, self.queue["group_count"])
        self.assertEqual(3, self.queue["maximum_candidates_per_group"])
        self.assertFalse(self.queue["rules"]["future_group_member_ids_disclosed"])
        self.assertFalse(self.queue["rules"]["group_acknowledgement_is_adoption"])
        self.assertEqual("NONE", self.manifest["authority"]["reserved_authority"])
        self.assertEqual([], list(ROOT.glob("**/PGN_G3_NATIVE_ADOPTION_DECISION*")))

    def test_progressive_materialisation_follows_exact_receipts(self) -> None:
        for index in range(1, 6):
            group_id = f"PGN-G3-R{index}"
            group = self.builder.build_group(group_id, ROOT)
            self.assertEqual(group_id, group["review_group_id"])
            self.assertEqual("NONE", group["authority_effect"])
            self.assertEqual("DENIED_PENDING_PGN_G3", group["native_adoption"])
        with self.assertRaises(PermissionError):
            self.builder.build_group("PGN-G3-R6", ROOT)

    def test_manifest_and_queue_match_builder(self) -> None:
        manifest, queue = self.builder.build_bundle(ROOT)
        self.assertEqual(self.manifest, manifest)
        self.assertEqual(self.queue, queue)

    def test_receipts_are_progressive_and_authority_neutral(self) -> None:
        receipts = sorted(path.name for path in REVIEW_RECEIPT_DIR.glob("PGN_G3_R*_ACKNOWLEDGEMENT_RECEIPT.json"))
        self.assertEqual(
            [f"PGN_G3_R{index}_ACKNOWLEDGEMENT_RECEIPT.json" for index in range(1, 5)],
            receipts,
        )
        expected_effects = [
            "DISCLOSE_AND_MATERIALISE_PGN_G3_R2_ONLY",
            "DISCLOSE_AND_MATERIALISE_PGN_G3_R3_ONLY",
            "DISCLOSE_AND_MATERIALISE_PGN_G3_R4_ONLY",
            "DISCLOSE_AND_MATERIALISE_PGN_G3_R5_ONLY",
        ]
        for name, effect in zip(receipts, expected_effects):
            receipt = load(REVIEW_RECEIPT_DIR / name)
            self.assertEqual("NONE", receipt["native_adoption"])
            self.assertEqual(effect, receipt["authority_effect"])


if __name__ == "__main__":
    unittest.main()
