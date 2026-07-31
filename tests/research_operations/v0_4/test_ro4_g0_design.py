from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


class RO4G0DesignTests(unittest.TestCase):
    def test_design_validator_passes(self) -> None:
        path = ROOT / "scripts" / "research_operations" / "validate_ro4_g0_design.py"
        spec = importlib.util.spec_from_file_location("validate_ro4_g0_design", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.main(), 0)

    def test_gate_is_operator_required_not_preapproved(self) -> None:
        gate = json.loads((ROOT / "docs/releases/research-operations-foundation-v0-4/ro4-g0/RO4_G0_GATE_PACKET.json").read_text())
        self.assertEqual(gate["status"], "GATE_READY_OPERATOR_DECISION_REQUIRED")
        self.assertEqual(gate["recommended_decision"], "PASS")
        self.assertIsNone(gate["candidate_commit"])
        self.assertIn("OPERATOR_DECISION_RO4_G0_REQUIRED", gate["unresolved_issues"])

    def test_source_canon_and_merged_pd_closure_are_explicit(self) -> None:
        packet = json.loads((ROOT / "docs/releases/research-operations-foundation-v0-4/ro4-00/RO4_00_BASELINE_AND_SOURCE_HASH_PACKET.json").read_text())
        self.assertEqual(packet["court_record_main_tip"], '306e449acdaddbb0131fd01aca6098dd8ab0b7ef')
        self.assertEqual(packet["source_canon"]["state_record_count"], 404434)
        self.assertEqual(packet["source_canon"]["transition_record_count"], 323910)
        self.assertEqual(packet["source_canon"]["validation_consumption"], "LOCKED_UNCONSUMED")
        self.assertEqual(packet["open_pull_requests"], [])
        self.assertEqual(packet["parent_foundations"]["june_controlled_review_disposition"], "DEFER_NO_CONTINUATION")
        self.assertEqual(packet["parent_foundations"]["june_controlled_review_merge_commit"], "306e449acdaddbb0131fd01aca6098dd8ab0b7ef")

    def test_reserved_authority_is_retained(self) -> None:
        state = json.loads((ROOT / "registries/research_operations/v0_4/RO4_PROGRAMME_STATE_v0_1.json").read_text())
        for denied in (
            "C2_MUTATION", "SELECTOR_CHANGE", "VALIDATION_CONSUMPTION",
            "PD_POPULATION_MERGE_OR_WRITE", "C2E_EPISODE_AUTHORITY",
            "PROBABILITY", "RISK", "EXPOSURE", "TRADING", "EXECUTION",
            "AGENT_WRITE", "R2_WRITE", "REMOTE_DEPLOYMENT",
        ):
            self.assertIn(denied, state["retained_prohibitions"])

    def test_route_is_disabled_and_write_free(self) -> None:
        route = (ROOT / "registries/research_operations/v0_4/RO4_ROUTE_REGISTRY_v0_1.yaml").read_text()
        self.assertIn("state: DISABLED_PENDING_RC_G5", route)
        self.assertIn("writes: NONE", route)
        self.assertIn("buttons: NONE", route)
        self.assertIn("remote_deployment: DENIED", route)

    def test_count_schema_denies_probability_shaped_fields(self) -> None:
        schema = json.loads((ROOT / "schemas/research_operations/v0_4/count_denominator_cell_v0_1.schema.json").read_text())
        denied = {item["required"][0] for item in schema["not"]["anyOf"]}
        self.assertTrue({"percentage", "ratio", "normalized_frequency", "probability", "rank"} <= denied)
        self.assertEqual(schema["properties"]["display_style"]["const"], "UNIFORM_NON_DATA_DRIVEN_IDENTITY_ORDERED")

    def test_pd_trace_schema_is_trigger_only(self) -> None:
        schema = json.loads((ROOT / "schemas/research_operations/v0_4/pd_trigger_trace_ref_v0_1.schema.json").read_text())
        self.assertEqual(schema["required"], ["pd_trigger_id", "pd_run_id", "trigger_first_valid_at", "trace_authority"])
        denied = {item["required"][0] for item in schema["not"]["anyOf"]}
        self.assertIn("fingerprint", denied)
        self.assertIn("review", denied)
        self.assertIn("promotion", denied)

    def test_machine_ablation_is_not_operator_evidence(self) -> None:
        policy = (ROOT / "registries/research_operations/v0_4/RO4_AXIS_ABLATION_ASSURANCE_POLICY_v0_1.yaml").read_text()
        self.assertIn("artifact_class: MACHINE_QA_ONLY", policy)
        self.assertIn("operator_facing_schemas: DENY", policy)
        self.assertIn("blinded_review_batches: DENY", policy)

    def test_c2e_opening_is_planning_only(self) -> None:
        threshold = (ROOT / "registries/research_operations/v0_4/RO4_C2E_DESIGN_OPENING_THRESHOLD_v0_1.yaml").read_text()
        self.assertIn("minimum_strata: 3", threshold)
        self.assertIn("multi_operator_kappa_minimum: '0.70'", threshold)
        self.assertIn("decision_effect: DRAFT_SEPARATE_C2E_IMPLEMENTATION_PLAN_ONLY", threshold)


if __name__ == "__main__":
    unittest.main()
