import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs/plans/governance/OVC_Native_Genesis_Portfolio_Adoption_Dependency_Canon_and_Control_Plane_Implementation_Plan_v0_2_REVISED.md"
STATE = ROOT / "registries/governance/programme_genesis/OVC_PGN_PORTFOLIO_LEDGER_v0_2.json"
STATE_MARKER = ROOT / "registries/governance/programme_genesis/OVC_PGN_PROGRAMME_STATE_v0_2.json"
BASELINE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g0/PGN_G0_BASELINE_MANIFEST.json"
SOURCE_HASH = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g0/PGN_G0_SOURCE_PLAN_HASH.json"
QA = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g0/PGN_G0_QA_PACKET.json"
GATE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g0/PGN_G0_OPERATOR_GATE_PACKET.json"
DECISION = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2/pgn-g0/PGN_G0_OPERATOR_DECISION.json"


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class NativeGenesisPortfolioG0Tests(unittest.TestCase):
    def test_baseline_and_source_plan_are_exactly_pinned(self) -> None:
        baseline = load(BASELINE)
        source = load(SOURCE_HASH)
        self.assertEqual("2e5b577e51cde05b027c6220560432c11513af14", baseline["baseline_commit"])
        self.assertEqual("gate/pgn-g0-ratification", baseline["candidate_branch"])
        self.assertEqual("2991ea0556c2ccc21cb2159bfe7b14af74d221a08a8f49e1ee72ced1fb79ce1d", source["source_docx_sha256"])
        self.assertEqual("file_0000000092a081f79225cc1bef1d6249", source["source_file_identity"])
        logical_hash = hashlib.sha256(PLAN.read_bytes()).hexdigest()
        self.assertEqual(source["repository_markdown_sha256"], logical_hash)
        self.assertEqual(8, baseline["portfolio_baseline"]["read_model_programme_count"])
        self.assertEqual(7, baseline["portfolio_baseline"]["provisional_migrated_programme_count"])
        self.assertEqual(14, baseline["portfolio_baseline"]["migration_warning_count"])
        self.assertEqual(7, baseline["portfolio_baseline"]["health_warning_count"])
        self.assertEqual(0, baseline["portfolio_baseline"]["health_blocking_count"])
        self.assertEqual([], baseline["blockers"])

    def test_revised_safeguards_are_materialised(self) -> None:
        text = PLAN.read_text(encoding="utf-8").lower()
        for required in (
            "pgn-g2a census acknowledgement",
            "maximum three candidates",
            "48-hour owner challenge window",
            "non-binding advisory evidence only",
            "at least two distinct programme sources",
            "within 60 seconds",
            "rebuild_latency_warning",
        ):
            self.assertIn(required, text)

    def test_operator_pass_advances_only_bounded_implementation(self) -> None:
        state = load(STATE)
        marker = load(STATE_MARKER)
        decision = load(DECISION)
        packets = {packet["packet_id"]: packet for packet in state["packets"]}
        self.assertEqual("OVC-PG-NATIVE-PORTFOLIO-v0.2", state["programme_id"])
        self.assertEqual("APPROVED", state["status"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual("PGN-G0.OPERATOR.PASS.20260804T102500+0100", state["operator_decision_id"])
        self.assertEqual("PASS", decision["decision"])
        self.assertEqual("OVC APPROVE PGN-G0 PASS", decision["operator_command"])
        self.assertEqual("APPROVED", packets["PGN-00"]["status"])
        self.assertEqual("PLANNED", packets["PGN-WP1"]["status"])
        self.assertIn("PGN-G2A", state["mandatory_operator_gates"])
        self.assertIn("PGN-G3-R*", state["mandatory_operator_gates"])
        self.assertIn("PGN-G9A", state["mandatory_operator_gates"])
        self.assertEqual("DENIED_PENDING_PGN_G3", state["authority"]["native_genesis_adoption"])
        self.assertEqual("DENIED_PENDING_PGN_G2A", state["authority"]["census_acknowledgement"])
        self.assertEqual("DEFERRED_DISABLED_PENDING_PGN_G10", state["authority"]["admission_enforcement"])
        self.assertEqual("RUN_EXACT_HEAD_ASSURANCE_SQUASH_MERGE_PR_280_THEN_START_PGN_WP1", state["next_action"])
        self.assertEqual([], state["blockers"])
        self.assertNotIn("programme_id", marker)
        self.assertEqual(str(STATE.relative_to(ROOT)).replace("\\", "/"), marker["authoritative_candidate_path"])

    def test_gate_packet_is_complete_and_non_authorising(self) -> None:
        gate = load(GATE)
        qa = load(QA)
        self.assertEqual("GATE_READY_PENDING_EXACT_HEAD_CI", gate["status"])
        self.assertTrue(gate["operator_decision_required"])
        self.assertEqual("OVC APPROVE PGN-G0 PASS", gate["exact_operator_command"])
        self.assertEqual(["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"], gate["allowed_decisions"])
        self.assertEqual("NONE_UNTIL_OPERATOR_PGN_G0_PASS", qa["authority_delta"])
        self.assertEqual("PASS_IF_EXACT_HEAD_REQUIRED_CHECKS_PASS", qa["qa_recommendation"])
        self.assertEqual([], gate["unresolved_issues"])
        self.assertEqual([], qa["blockers"])
        self.assertIn("PGN_G2A_OPERATOR_ACKNOWLEDGEMENT_BLOCKS_ALL_CANDIDATE_CONSTRUCTION_AFTER_CENSUS", gate["acceptance_conditions"])
        self.assertIn("ADMISSION_PREVIEW_IS_PERMANENTLY_NON_BINDING_WITH_ACKNOWLEDGED_INVOCATION_LOGGING", gate["acceptance_conditions"])


if __name__ == "__main__":
    unittest.main()
