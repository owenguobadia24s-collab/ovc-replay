from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3-native-adoption"
MATRIX = BASE / "PGN_G3_NATIVE_ADOPTION_READINESS_MATRIX.json"
TEMPLATE = BASE / "PGN_G3_OPERATOR_DECISION_TEMPLATE.json"
GATE = BASE / "PGN_G3_OPERATOR_GATE_PACKET.json"
QA = BASE / "PGN_G3_QA_PACKET.json"
STATE = BASE / "PGN_G3_PROGRAMME_STATE_UPDATE.json"
PORTFOLIO = ROOT / "registries/governance/programme_genesis/pgn_candidates/PGN_WP3_NATIVE_CANDIDATE_PORTFOLIO_v0_1.json"
RECEIPTS = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g3/reviews"

UNRESOLVED = {
    "PURPOSE_EXACT_SOURCE_TEXT",
    "INCLUDED_SCOPE_EXACT_SOURCE_TEXT",
    "EXCLUDED_SCOPE_EXACT_SOURCE_TEXT",
    "CONSTITUTIONAL_PARENT",
    "PROGRAMME_PARENTS",
    "CREATION_TRIGGERS",
    "AUTHORITY_ENVELOPE_FIELD_LEVEL_CROSSWALK",
    "LIFECYCLE_EXIT_CRITERIA",
}


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path}")
    return value


class PgnG3NativeAdoptionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = load(MATRIX)
        cls.template = load(TEMPLATE)
        cls.gate = load(GATE)
        cls.qa = load(QA)
        cls.state = load(STATE)
        cls.portfolio = load(PORTFOLIO)

    def test_exact_candidate_population_identity_class_and_hash(self) -> None:
        commitments = {
            item["programme_id"]: item
            for item in self.portfolio["candidate_commitments"]
        }
        entries = {item["programme_id"]: item for item in self.matrix["entries"]}
        self.assertEqual(16, self.portfolio["candidate_count"])
        self.assertEqual(16, self.matrix["candidate_count"])
        self.assertEqual(set(commitments), set(entries))
        self.assertEqual(
            self.portfolio["candidate_set_sha256"],
            self.matrix["candidate_set_sha256"],
        )
        self.assertEqual(
            self.portfolio["commitment_set_sha256"],
            self.matrix["commitment_set_sha256"],
        )
        for programme_id, commitment in commitments.items():
            entry = entries[programme_id]
            self.assertEqual(commitment["candidate_class"], entry["candidate_class"])
            self.assertEqual(commitment["candidate_sha256"], entry["candidate_sha256"])
            self.assertEqual("CANDIDATE_UNAPPROVED", entry["candidate_status"])
            self.assertEqual("NONE", entry["authority_effect"])

    def test_all_six_progressive_review_receipts_are_exactly_present(self) -> None:
        names = sorted(
            path.name
            for path in RECEIPTS.glob("PGN_G3_R*_ACKNOWLEDGEMENT_RECEIPT.json")
        )
        self.assertEqual(
            [f"PGN_G3_R{i}_ACKNOWLEDGEMENT_RECEIPT.json" for i in range(1, 7)],
            names,
        )
        r6 = load(RECEIPTS / names[-1])
        self.assertEqual("COMPLETED", r6["progressive_review_status"])
        self.assertEqual("NONE", r6["native_adoption"])
        self.assertEqual("NONE", r6["cross_programme_edge_acceptance"])

    def test_no_candidate_is_ready_for_pass(self) -> None:
        self.assertEqual(0, self.matrix["ready_for_pass_count"])
        self.assertEqual(
            {"PASS": 0, "DEFER": 16, "BLOCK": 0, "QUARANTINE": 0},
            self.matrix["recommended_decision_counts"],
        )
        self.assertEqual(UNRESOLVED, set(self.matrix["required_native_fields"]))
        for entry in self.matrix["entries"]:
            self.assertEqual(
                "NOT_READY_UNRESOLVED_REQUIRED_NATIVE_FIELDS",
                entry["adoption_readiness"],
            )
            self.assertEqual(8, entry["unresolved_field_count"])
            self.assertEqual("DEFER", entry["recommended_decision"])
            self.assertEqual("NONE", entry["authority_effect"])

    def test_decision_template_requires_one_operator_decision_per_programme(self) -> None:
        self.assertEqual("PER_PROGRAMME_REQUIRED", self.template["decision_mode"])
        self.assertEqual(16, self.template["candidate_count"])
        self.assertEqual(
            "OVC APPROVE PGN-G3 DECISIONS=DEFER_ALL",
            self.template["recommended_bundle_command"],
        )
        self.assertEqual(16, len(self.template["decisions"]))
        for decision in self.template["decisions"]:
            self.assertEqual(
                ["PASS", "DEFER", "BLOCK", "QUARANTINE"],
                decision["allowed_decisions"],
            )
            self.assertEqual("DEFER", decision["recommended_decision"])
            self.assertIsNone(decision["operator_decision"])

    def test_gate_and_qa_are_ready_but_do_not_grant_adoption(self) -> None:
        self.assertEqual("GATE_READY", self.gate["status"])
        self.assertTrue(self.gate["operator_decision_required"])
        self.assertEqual("DEFER_ALL", self.gate["recommended_decision"])
        self.assertEqual(
            "OVC APPROVE PGN-G3 DECISIONS=DEFER_ALL",
            self.gate["exact_recommended_command"],
        )
        self.assertEqual(0, self.gate["recommended_decision_effect"]["native_records_created"])
        self.assertEqual("NONE", self.gate["recommended_decision_effect"]["authority_effect"])
        self.assertEqual("PASS_GATE_READY_RECOMMEND_DEFER_ALL", self.qa["status"])
        self.assertEqual([], self.qa["gate_readiness_blockers"])
        self.assertEqual(16, self.qa["assessment"]["recommended_decision_counts"]["DEFER"])
        self.assertEqual(0, self.qa["assessment"]["ready_for_pass_count"])

    def test_programme_state_stops_at_operator_required_pgn_g3(self) -> None:
        self.assertEqual("GATE_READY", self.state["status"])
        self.assertEqual("OPERATOR_REQUIRED", self.state["authority_required"])
        self.assertEqual("PGN-G3", self.state["next_gate"])
        self.assertEqual(
            "PENDING_OPERATOR_PGN_G3_DECISIONS",
            self.state["authority"]["native_adoption"],
        )
        self.assertEqual(
            "DENIED_PENDING_PGN_G5",
            self.state["authority"]["cross_programme_edges"],
        )
        self.assertEqual("NONE", self.state["authority"]["reserved_authority"])
        self.assertIsNone(self.state["decision_record"])
        self.assertIsNone(self.state["merge_commit"])

    def test_no_operator_adoption_decision_or_native_record_is_materialised(self) -> None:
        self.assertFalse((BASE / "PGN_G3_OPERATOR_DECISION.json").exists())
        self.assertEqual(
            [],
            list(ROOT.glob(
                "docs/releases/programme-genesis-native-portfolio-v0-2/"
                "pgn-g3-native-adoption/native-records/*.json"
            )),
        )


if __name__ == "__main__":
    unittest.main()
