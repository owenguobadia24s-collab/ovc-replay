from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
REG = ROOT / "registries/development/skills/cers"


def load(name: str):
    return json.loads((REG / name).read_text(encoding="utf-8"))


def load_path(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class CersPersistentSupervisorWp1Tests(unittest.TestCase):
    def test_policy_is_fail_closed_and_preactivation_quiescent(self):
        policy = load("CERS_PERSISTENT_SUPERVISOR_POLICY_v0_1.json")
        self.assertEqual(policy["status"], "INACTIVE_PREACTIVATION")
        self.assertEqual(policy["preactivation_quiescence"], "DISABLE_NEW_DISPATCH")
        self.assertEqual(policy["missing_admission"], "DENY")
        self.assertEqual(policy["unknown_owner_authority"], "DENY")
        self.assertEqual(policy["operator_required_boundary"], "PARK")
        self.assertFalse(policy["future_programme_auto_admission"])
        self.assertFalse(policy["direct_main_mutation"])
        self.assertEqual(policy["merge_capability"], "NONE")
        self.assertFalse(policy["parallel_physical_merge"])
        self.assertFalse(policy["force_push"])
        self.assertFalse(policy["history_rewrite"])
        self.assertFalse(policy["irreversible_external_side_effects"])

    def test_admission_registry_starts_empty_and_cannot_auto_admit_future_programmes(self):
        registry = load("CERS_PERSISTENT_PROGRAMME_ADMISSION_REGISTRY_v0_1.json")
        self.assertEqual(registry["status"], "INACTIVE_PREACTIVATION")
        self.assertEqual(registry["unknown_or_absent_programme"], "DENY")
        self.assertFalse(registry["future_programme_auto_admission"])
        self.assertEqual(registry["entries"], [])

    def test_executor_binding_reuses_existing_packet_executor_without_merge_authority(self):
        binding = load("CERS_PERSISTENT_EXECUTOR_BINDING_v0_1.json")
        self.assertIn("OVC-SKILL-030@0.1.0", binding["executor_identity"])
        self.assertEqual(binding["maturity"], "TRUSTED")
        self.assertEqual(binding["action_classes"], ["WRITE_FILE", "GIT_COMMIT", "PUSH_BRANCH"])
        self.assertTrue(binding["repository_write"])
        self.assertTrue(binding["branch_ref_write"])
        self.assertFalse(binding["merge"])
        self.assertFalse(binding["force_push"])
        self.assertFalse(binding["history_rewrite"])
        self.assertFalse(binding["irreversible_external_side_effects"])
        self.assertTrue(binding["start_ack_required"])
        self.assertTrue(binding["heartbeat_required"])
        self.assertTrue(binding["fencing_required"])
        self.assertIn("DENIED_PENDING", binding["persistent_unattended_use"])

    def test_action_registry_denies_reserved_and_unknown_actions(self):
        registry = load("CERS_PERSISTENT_ACTION_SIDE_EFFECT_REGISTRY_v0_1.json")
        denies = set(registry["explicit_denies"])
        for required in {"MERGE","DIRECT_MAIN_WRITE","PARALLEL_PHYSICAL_MERGE","FORCE_PUSH","HISTORY_REWRITE","IRREVERSIBLE","IRREVERSIBLE_OR_UNKNOWN","VALIDATION_READ","SCIENTIFIC_PROMOTION","CANONICAL_PUBLICATION","R2_PUBLICATION","PROBABILITY","RISK","EXPOSURE","TRADING","MARKET_EXECUTION"}:
            self.assertIn(required, denies)
        self.assertEqual(registry["unknown_action"]["decision"], "DENY")

    def test_quiescence_is_durable_disable_new_dispatch(self):
        state = load("CERS_PERSISTENT_QUIESCENCE_STATE_v0_1.json")
        self.assertEqual(state["mode"], "DISABLE_NEW_DISPATCH")
        self.assertEqual(state["persistent_general_dispatch"], "DENIED")
        self.assertEqual(state["authority_effect"], "NONE")

    def test_reason_registry_contains_all_fail_closed_frontiers(self):
        reasons = set(load("CERS_PERSISTENT_REASON_CODE_REGISTRY_v0_1.json")["codes"])
        for code in {"PROGRAMME_NOT_ADMITTED","OWNER_AUTHORITY_UNKNOWN","OPERATOR_REQUIRED_BOUNDARY","EXECUTOR_UNKNOWN_OR_INACTIVE","ACTION_UNKNOWN_OR_DENIED","SIDE_EFFECT_UNKNOWN_OR_DENIED","WRITE_DOMAIN_UNKNOWN_OR_DENIED","STALE_FENCE","UNKNOWN_START_STATE","DUPLICATE_AUTHORITATIVE_START","CURRENT_POINTER_UNRESOLVED"}:
            self.assertIn(code, reasons)

    def test_wp6_live_pilot_evidence_remains_exactly_preserved(self):
        pilot = load_path("docs/releases/development-skills-v0-3/cers-conformance/wp6/CERS_WP6_LIVE_PILOT_RUN_v0_1.json")
        qa = load_path("docs/releases/development-skills-v0-3/cers-conformance/wp6/CERS_WP6_QA_PACKET_v0_1.json")
        decision = load_path("docs/releases/development-skills-v0-3/cers-conformance/wp6/CERS_G6_DECISION_v0_1.json")
        state7 = load_path("registries/implementation/dsai3v_cers_v0_1/OVC_DSAI3V_CERS_STATE_v0_7.json")
        state8 = load_path("registries/implementation/dsai3v_cers_v0_1/OVC_DSAI3V_CERS_STATE_v0_8.json")
        self.assertEqual(state7["packet_id"], "CERS-G-LIVE-DISPATCH")
        self.assertEqual(state7["runtime_authority"], "AUTHORIZED_PENDING_WP6_IMPLEMENTATION_AND_PILOT")
        self.assertEqual(state7["live_unattended_dispatch"], "AUTHORIZED_CERS_WP6_BOUNDED_PILOT_ONLY")
        self.assertEqual(state8["packet_id"], "CERS-WP6")
        self.assertEqual(state8["runtime_authority"], "CERS_WP6_BOUNDED_LIVE_PILOT_EXECUTED")
        self.assertEqual(state8["post_pilot_dispatch_state"], "DISABLE_NEW_DISPATCH_AFTER_BRANCH_PILOT_COMPLETION")
        self.assertEqual(pilot["programme_id"], "OVC-DSAI3V-CERS-CONFORMANCE-v0.1")
        self.assertEqual(pilot["packet_id"], "CERS-WP6")
        self.assertEqual(pilot["worker_concurrency"], 1)
        self.assertEqual(pilot["max_speculative_depth"], 1)
        self.assertEqual(pilot["post_pilot_quiescence"], "DISABLE_NEW_DISPATCH")
        self.assertEqual(pilot["incidents"], [])
        phases = [row["phase"] for row in pilot["transaction_timeline"]]
        self.assertIn("START_ACKNOWLEDGED", phases)
        self.assertIn("HEARTBEAT", phases)
        self.assertIn("COMPLETED", phases)
        self.assertTrue(pilot["caller_absent_at_start"])
        self.assertFalse(pilot["direct_main_mutation"])
        self.assertFalse(pilot["merge_attempted"])
        self.assertFalse(pilot["parallel_physical_merge"])
        self.assertFalse(pilot["force_push"])
        self.assertFalse(pilot["history_rewrite"])
        self.assertFalse(pilot["irreversible_external_side_effects"])
        self.assertEqual(qa["packet_id"], "CERS-WP6")
        self.assertEqual(decision["gate_id"], "CERS-G6")
        self.assertEqual(decision["terminal_on_effectivity"], "CERS_IMPLEMENTED_QUALIFIED_LIVE_PILOT_PASS")


if __name__ == "__main__":
    unittest.main()
