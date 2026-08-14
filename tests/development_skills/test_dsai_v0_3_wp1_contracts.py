from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts/development/skills/dsai3_continuous_execution_v0_1.json"
SCHEMA_ROOT = ROOT / "schemas/development/skills"
FIXTURE = ROOT / "fixtures/development/skills/dsai_v0_3/DSAI3_WP1_CONTRACT_FIXTURES_v1.json"

SCHEMAS = {
    "continuation": SCHEMA_ROOT / "dsai3_continuation_mandate_v0_1.schema.json",
    "execution": SCHEMA_ROOT / "dsai3_execution_lifecycle_receipt_v0_1.schema.json",
    "requeue": SCHEMA_ROOT / "dsai3_requeue_execution_intent_v0_1.schema.json",
    "capability": SCHEMA_ROOT / "dsai3_integration_capability_profile_v0_1.schema.json",
    "siq_binding": SCHEMA_ROOT / "dsai3_siq_binding_record_v0_1.schema.json",
}


class DsaiV03Wp1ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.schemas = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in SCHEMAS.items()}
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_contract_reuses_existing_siq_and_never_parallel_merges(self) -> None:
        landing = self.contract["landing"]
        self.assertEqual(landing["queue_owner"], "OVC.SIQ.RUNTIME.v0.1")
        self.assertFalse(landing["creates_second_queue"])
        self.assertEqual(landing["base_sensitive_assurance_owner"], "SIQ_QUEUE_HEAD_ONLY")
        self.assertTrue(landing["parallel_build"])
        self.assertFalse(landing["parallel_merge"])
        self.assertEqual(landing["target_branch"], "main")
        self.assertEqual(landing["merge_method"], "squash")

    def test_continue_semantics_persist_beyond_chat_and_stop_only_at_real_boundaries(self) -> None:
        continuation = self.contract["continuation"]
        self.assertTrue(continuation["repository_state_is_source_of_truth"])
        self.assertFalse(continuation["chat_history_is_source_of_truth"])
        self.assertFalse(continuation["completed_packet_is_stop"])
        self.assertFalse(continuation["qa_pass_is_stop"])
        self.assertFalse(continuation["eligible_merge_is_stop"])
        self.assertFalse(continuation["successful_merge_is_stop"])
        self.assertFalse(continuation["successor_ready_is_stop"])
        self.assertEqual(continuation["operator_gate_behavior"], "STOP")
        self.assertIn("OPERATOR_REQUIRED_GATE", self.contract["mandatory_stop_conditions"])
        self.assertIn("NON_NONE_AUTHORITY_DELTA", self.contract["mandatory_stop_conditions"])

    def test_every_new_schema_is_closed_and_non_authoritative(self) -> None:
        for name, schema in self.schemas.items():
            with self.subTest(schema=name):
                self.assertFalse(schema["additionalProperties"])
                self.assertIn("authority_effect", schema["required"])
                self.assertIn("schema", schema["required"])
        self.assertEqual(
            self.schemas["continuation"]["properties"]["authority_effect"]["const"],
            "CONTINUATION_SCOPE_ONLY",
        )
        self.assertEqual(
            self.schemas["execution"]["properties"]["authority_effect"]["const"],
            "NONE_OBSERVABILITY_ONLY",
        )
        self.assertEqual(
            self.schemas["requeue"]["properties"]["authority_effect"]["const"],
            "NONE_PLANNING_ONLY",
        )
        self.assertEqual(
            self.schemas["siq_binding"]["properties"]["authority_effect"]["const"],
            "NONE_BINDING_ONLY",
        )

    def test_fixture_encodes_operator_continue_and_explicit_single_packet_modes(self) -> None:
        mandates = self.fixture["continuation_mandates"]
        self.assertEqual(mandates[0]["mode"], "CONTINUE_UNTIL_MANDATORY_STOP")
        self.assertEqual(mandates[0]["start_packet_id"], "ESLI-WP10")
        self.assertFalse(mandates[0]["chat_history_required"])
        self.assertEqual(mandates[1]["mode"], "ONLY_PACKET")
        self.assertEqual(mandates[1]["start_packet_id"], "DMRPI-WP1")

    def test_lifecycle_receipt_distinguishes_simulation_from_observation(self) -> None:
        receipt = self.fixture["execution_receipt"]
        self.assertFalse(receipt["execution_observed"])
        self.assertTrue(receipt["execution_simulated"])
        self.assertEqual(receipt["phase"], "EXECUTION_STARTED")
        self.assertFalse(receipt["parallel_merge"])
        self.assertFalse(receipt["force_push"])
        self.assertFalse(receipt["history_rewrite"])

    def test_requeue_intent_is_fresh_branch_only_and_cannot_mutate_history(self) -> None:
        intent = self.fixture["requeue_intent"]
        self.assertEqual(intent["action"], "FRESH_BRANCH_FROM_CURRENT_MAIN")
        self.assertTrue(intent["fresh_branch_required"])
        self.assertTrue(intent["fresh_exact_head_assurance_required"])
        self.assertTrue(intent["preserve_packet_scope_identity"])
        self.assertTrue(intent["preserve_write_set_identity"])
        self.assertTrue(intent["preserve_semantic_owner_identity"])
        self.assertFalse(intent["side_effect_performed"])
        self.assertFalse(intent["force_push"])
        self.assertFalse(intent["history_rewrite"])

    def test_capability_and_siq_binding_model_current_connector_without_granting_authority(self) -> None:
        capability = self.fixture["capability_profile"]
        binding = self.fixture["siq_binding"]
        self.assertFalse(capability["native_stack_merge"])
        self.assertTrue(capability["immediate_squash_merge"])
        self.assertTrue(capability["fresh_branch_reconciliation"])
        self.assertFalse(capability["parallel_merge"])
        self.assertEqual(binding["queue_owner"], "OVC.SIQ.RUNTIME.v0.1")
        self.assertFalse(binding["creates_new_queue"])
        self.assertEqual(binding["queue_state"], "READY")
        self.assertFalse(binding["parallel_merge"])

    def test_activation_stays_reserved_at_dsai3_g7(self) -> None:
        activation = self.contract["activation"]
        self.assertEqual(activation["gate_id"], "DSAI3-G7")
        self.assertEqual(activation["gate_class"], "OPERATOR_REQUIRED")
        self.assertEqual(activation["production_actuation_pre_gate"], "DENIED")
        self.assertTrue(activation["self_grant_prohibited"])
        hard = self.contract["hard_boundaries"]
        self.assertFalse(hard["packet_class_expansion"])
        self.assertFalse(hard["parallel_merge"])
        self.assertFalse(hard["direct_main_mutation"])
        self.assertFalse(hard["force_push"])
        self.assertFalse(hard["history_rewrite"])
        self.assertFalse(hard["operator_gate_auto_cross"])


if __name__ == "__main__":
    unittest.main()
