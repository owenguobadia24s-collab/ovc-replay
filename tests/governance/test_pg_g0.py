import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "registries/governance/programme_genesis/OVC_PG_PROGRAMME_STATE_v0_2.json"
BASELINE_PATH = ROOT / "docs/releases/programme-genesis-v0-2/pg-g0/PG_G0_BASELINE_MANIFEST.json"
QA_PATH = ROOT / "docs/releases/programme-genesis-v0-2/pg-g0/PG_G0_QA_PACKET.json"
DECISION_PATH = ROOT / "docs/releases/programme-genesis-v0-2/pg-g0/PG_G0_OPERATOR_DECISION.json"
MAINTENANCE_PATH = ROOT / "registries/governance/programme_genesis/MAINTENANCE_AUTHORITY_REGISTRY_v0_1.json"
SYNC_PATH = ROOT / "contracts/governance/programme_genesis/STATE_SYNCHRONISATION_CONTRACT_v0_1.md"
PLAN_PATH = ROOT / "docs/plans/governance/OVC_Programme_Genesis_Portfolio_Ledger_and_Dependency_Graph_v0_2_REVISED_Implementation_Plan.md"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class ProgrammeGenesisG0Tests(unittest.TestCase):
    def test_pg_g0_pass_is_recorded_and_releases_only_bounded_build(self) -> None:
        state = load_json(STATE_PATH)
        decision = load_json(DECISION_PATH)
        packets = {packet["packet_id"]: packet for packet in state["packets"]}
        self.assertEqual("OVC-PG-v0.2", state["programme_id"])
        self.assertEqual("0.2", state["plan_version"])
        self.assertEqual("PG-G0.OPERATOR.PASS.20260803T184400+0100", decision["decision_id"])
        self.assertEqual("PASS", decision["decision"])
        self.assertEqual("OVC APPROVE PG-G0 PASS", decision["operator_command"])
        self.assertEqual(263, decision["approved_pull_request"])
        self.assertEqual("COMPLETED", packets["PG-00"]["status"])
        self.assertEqual("docs/releases/programme-genesis-v0-2/pg-g0/PG_G0_OPERATOR_DECISION.json", packets["PG-00"]["decision_record"])
        self.assertEqual("DENIED_PENDING_PG_G3A", decision["authority_delta"]["portfolio_migration"])
        self.assertEqual("DENIED_PENDING_PG_G6", decision["authority_delta"]["admission_enforcement"])
        self.assertEqual("DENIED_PENDING_PG_G7", decision["authority_delta"]["automatic_upkeep"])
        authority = state["authority"]
        self.assertEqual("RATIFIED", authority["programme_governance_design"])
        self.assertEqual("APPROVED_BOUNDED_IMPLEMENTATION", authority["programme_governance_build"])
        self.assertEqual("DENIED_PENDING_PG_G6", authority["admission_enforcement"])
        self.assertEqual("DENIED_PENDING_PG_G7", authority["automatic_upkeep"])
        self.assertEqual("NONE", authority["market_model_selector_release_validation"])
        self.assertEqual("NONE", authority["agent_probability_risk_exposure_execution"])

    def test_pg_mandatory_operator_stops_are_preserved(self) -> None:
        state = load_json(STATE_PATH)
        self.assertEqual(["PG-G0", "PG-G3A", "PG-G6", "PG-G7"], state["mandatory_operator_gates"])
        packets = {packet["packet_id"]: packet for packet in state["packets"]}
        self.assertEqual("d0d2445b035f3fc93a177b94b23120be7dfa274b", packets["PG-00"]["merge_commit"])
        self.assertEqual("PG-G3A", packets["PG-WP3"]["next_packet"])
        self.assertEqual("OPERATOR_REQUIRED_COMPLETED", packets["PG-G3A"]["authority_required"])
        self.assertEqual(["PG-G3A_ACKNOWLEDGE_CONTINUE_MERGED"], packets["PG-WP4"]["prerequisites"])
        self.assertEqual("OPERATOR_REQUIRED_FOUR_PART_DECISION", packets["PG-G6"]["authority_required"])
        self.assertEqual("OPERATOR_REQUIRED_AT_PG_G7", packets["PG-WP6"]["authority_required"])

    def test_pg_g0_baseline_and_source_identity_are_pinned(self) -> None:
        baseline = load_json(BASELINE_PATH)
        self.assertEqual("5fb26ce08ff1a386f76bc8c6784350ab6fddcfb7", baseline["baseline_commit"])
        self.assertEqual("gate/pg-g0-ratification", baseline["candidate_branch"])
        self.assertEqual("PG", baseline["namespace_freeze"]["short_code"])
        self.assertEqual([], baseline["blockers"])
        plan_sources = {source["document_id"]: source for source in baseline["governing_source_documents"]}
        pg_source = plan_sources["OVC-PG-IMPLEMENTATION-PLAN-0.2"]
        self.assertEqual("file_00000000a0e4822f8ed73a5903ded4d7", pg_source["external_identity"])
        self.assertEqual(str(PLAN_PATH.relative_to(ROOT)).replace("\\", "/"), pg_source["repository_path"])

    def test_maintenance_registry_is_frozen_but_enforcement_remains_disabled(self) -> None:
        registry = load_json(MAINTENANCE_PATH)
        self.assertEqual("FROZEN_DISABLED_PENDING_PG_G6", registry["status"])
        self.assertEqual("NOT_EVALUABLE_REQUIRES_SCOPE_REVIEW", registry["default_outcome"])
        self.assertEqual("PG-G0", registry["decision_gate"])
        self.assertEqual("PG-G6", registry["activation_gate"])
        self.assertFalse(registry["enforcement_enabled"])
        self.assertGreaterEqual(len(registry["entries"]), 5)
        denials = set(registry["reserved_authority_denials"])
        self.assertTrue({
            "SELECTOR_ACTIVATION",
            "ACTIVE_DISCOVERY",
            "ACTIVE_DEVELOPMENT",
            "ACTIVE_VALIDATION",
            "CANONICAL_OR_R2_PUBLICATION",
            "AGENT_WRITE",
            "PROBABILITY_RISK_EXPOSURE_EXECUTION",
        }.issubset(denials))

    def test_state_synchronisation_preserves_source_authority(self) -> None:
        contract = SYNC_PATH.read_text(encoding="utf-8")
        self.assertIn("programme-owned machine-readable state", contract)
        self.assertIn("STATE_SOURCE_CONFLICT", contract)
        self.assertIn("STALE_PROJECTION", contract)
        self.assertIn("PG never repairs a programme-owned source file", contract)
        self.assertIn("Before `PG-G6`, all enforcement consumers remain disabled", contract)

    def test_predecision_qa_packet_remains_immutable_evidence(self) -> None:
        qa = load_json(QA_PATH)
        decision = load_json(DECISION_PATH)
        self.assertEqual("QA_REVIEW_PENDING_EXACT_HEAD_CI", qa["status"])
        self.assertEqual([], qa["blockers"])
        self.assertEqual("PASS_IF_EXACT_HEAD_REQUIRED_CHECKS_PASS", qa["qa_recommendation"])
        self.assertEqual("NONE_UNTIL_OPERATOR_PG_G0_PASS", qa["authority_delta"])
        self.assertEqual("SUCCESS", decision["assurance"]["tests"]["conclusion"])
        self.assertEqual("SUCCESS", decision["assurance"]["ovc_merge_readiness"]["conclusion"])


if __name__ == "__main__":
    unittest.main()
