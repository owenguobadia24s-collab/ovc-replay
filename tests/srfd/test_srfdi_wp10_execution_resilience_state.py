from __future__ import annotations

import json
from pathlib import Path
import unittest

from srfd._current_pointer_compat import assert_lawful_v10_pointer

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "registries/research/srfd/wp10_execution_resilience_profile_v0_1.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_23_WP10_EXECUTION_RESILIENCE_READY.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
BLOCKER = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v0-6/SRFDI_WP10_V06_EXECUTION_BLOCKER.json"
FRESH_V09 = "SRFD.JUNE.AUTH.a5311fbade60d87553ad76b9085e1bd2ba62fe60c6d9654a2d338b624b5498c3"
V09_BINDING = "ca25077124a49a02808ed0c855906456d19415df5371266ebc1e90448d022d9a"


class SRFDIWP10ExecutionResilienceStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads(PROFILE.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.blocker = json.loads(BLOCKER.read_text())

    def test_v06_consumed_token_remains_immutable_history(self):
        token = self.blocker["authority_token"]
        self.assertEqual("SRFD.JUNE.AUTH.3c63cd70ea57151a264443b436f94075bd8fb13f8a45f318a245cff96fefd168", token["token_id"])
        self.assertEqual("CONSUMED_NOT_REUSABLE", token["state"])
        if self.pointer["authority_token_id"] == token["token_id"]:
            self.assertTrue(self.pointer["authority_token_consumed"])
            self.assertEqual("CONSUMED_NOT_REUSABLE", self.pointer["authority_token_state"])
        else:
            self.assertEqual(token["token_id"], self.pointer["prior_v0_6_authority_token_id"])
            self.assertEqual("CONSUMED_NOT_REUSABLE", self.pointer["prior_v0_6_authority_token_state"])
            self.assertEqual("BLOCKED_CONSUMED_TOKEN_PRESERVED", self.pointer["wp10_v0_6_execution_route"])

    def test_frozen_science_is_exact(self):
        frozen = self.profile["frozen_scientific_bindings"]
        self.assertEqual(8598, frozen["eligible_record_count"])
        self.assertEqual(36, frozen["comparability_domain_count"])
        self.assertEqual(35380668, frozen["exact_pair_opportunity_count"])
        self.assertEqual(1944, frozen["family_configuration_count"])
        self.assertEqual("68317db2ddb5608d0dd13bad67be78f70263dee5c2dc59790c1c995098c00866", frozen["capacity_catalog_grid_hash"])
        self.assertEqual("6ba46d446d799d7686ee038c80fb21fa899e8dbe0875ddd12779068b38e30cbb", frozen["scientific_manifest_logical_sha256"])
        self.assertEqual("f0da6203124a6aeaa83f89e3f27b2fc980754f874ae96e631009dfc9048f2fa3", frozen["preregistration_v0_4_logical_sha256"])
        self.assertEqual("FORBIDDEN", self.state["frozen_science"]["mutation"])

    def test_resilience_is_run_scoped_not_reusable_token_scope(self):
        scope = self.profile["run_scope"]
        self.assertEqual("ONE_TO_ONE", scope["token_to_run_cardinality"])
        self.assertEqual("FORBIDDEN", scope["token_reuse"])
        self.assertEqual("FORBIDDEN", scope["new_run_from_consumed_token"])
        self.assertEqual("SAME_RUN_ID_FROM_VERIFIED_COMMITTED_CHECKPOINT", scope["resume"])
        self.assertEqual("FAIL_CLOSED", scope["binding_drift"])

    def test_historical_resilience_state_required_fresh_authority_and_pointer_may_advance_after_it(self):
        if assert_lawful_v10_pointer(self, self.pointer):
            return
        self.assertEqual("READY", self.state["status"])
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.state["current_gate"])
        self.assertEqual("SRFDI-G-JUNE-AUTH-v0.7-PREP", self.state["next_packet"])
        self.assertTrue(self.state["authority"]["fresh_june_scientific_run"].startswith("DENIED"))
        if self.pointer.get("failure_reason") == "CAPACITY_EXCEEDED_EXTERNAL_BYTES":
            self.assertEqual("BLOCKED", self.pointer["status"])
            self.assertEqual("SRFDI-G10", self.pointer["current_gate"])
            self.assertEqual("SRFDI-WP10-v1.0-CAPACITY-REMEDIATION", self.pointer["next_packet"])
            self.assertEqual(FRESH_V09, self.pointer["fresh_authority_token_id"])
            self.assertEqual(V09_BINDING, self.pointer["run_binding_sha256"])
            self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["fresh_authority_token_state"])
            self.assertTrue(self.pointer["fresh_authority_token_consumed"])
            self.assertEqual("BLOCKED_CAPACITY_V09_PRESERVED_NOT_COMPLETED", self.pointer["june_execution"])
            return
        if self.pointer["next_packet"] == "SRFDI-G-JUNE-AUTH-v0.7-PREP":
            self.assertEqual("DENIED_PENDING_NEW_RUN_SCOPED_SRFDI_G_JUNE_AUTH", self.pointer["june_execution"])
        elif self.pointer["current_gate"] == "SRFDI-G10" and self.pointer["status"] == "READY":
            self.assertEqual("SRFDI-WP10-v0.9", self.pointer["next_packet"])
            self.assertEqual(FRESH_V09, self.pointer["fresh_authority_token_id"])
            self.assertEqual("AUTHORIZED_UNCONSUMED", self.pointer["fresh_authority_token_state"])
            self.assertFalse(self.pointer["fresh_authority_token_consumed"])
            self.assertEqual(V09_BINDING, self.pointer["run_binding_sha256"])
            self.assertEqual("AUTHORIZED_ONE_EXACT_BOUND_JUNE_RUN_READY", self.pointer["june_execution"])
            self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["authority_token_state"])
            self.assertTrue(self.pointer["authority_token_consumed"])
        elif self.pointer["current_gate"] == "SRFDI-G10" and self.pointer["status"] == "RUNNING":
            self.assertEqual("SRFDI-WP10-v0.9-RESUME", self.pointer["next_packet"])
            self.assertEqual(FRESH_V09, self.pointer["fresh_authority_token_id"])
            self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["fresh_authority_token_state"])
            self.assertTrue(self.pointer["fresh_authority_token_consumed"])
            self.assertEqual(V09_BINDING, self.pointer["run_binding_sha256"])
            self.assertEqual("RUNNING_EXACT_BOUND_V09_FROM_COMMITTED_CHECKPOINT", self.pointer["june_execution"])
            self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["authority_token_state"])
            self.assertTrue(self.pointer["authority_token_consumed"])
        elif self.pointer["status"] == "READY" and self.pointer.get("current_gate") != "SRFDI-G-JUNE-AUTH":
            self.assertEqual("SRFDI-WP10-v0.7", self.pointer["next_packet"])
            self.assertEqual("AUTHORIZED_ONE_EXACT_RUN_ID_UNCONSUMED", self.pointer["june_execution"])
            self.assertEqual("AUTHORIZED_UNCONSUMED", self.pointer["authority_token_state"])
            self.assertFalse(self.pointer["authority_token_consumed"])
        elif self.pointer["status"] == "AUTHORIZED_REMEDIATION_ONLY":
            self.assertEqual("SRFDI-G10B", self.pointer["current_gate"])
            self.assertEqual("SRFDI-WP10B", self.pointer["next_packet"])
            self.assertEqual("SRFDI-G10B-FREEZE", self.pointer["stop_at"])
            self.assertEqual("BLOCKED_CONSUMED_RUN_PRESERVED_NO_FRESH_RUN_AUTHORITY", self.pointer["june_execution"])
            self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["authority_token_state"])
            self.assertTrue(self.pointer["authority_token_consumed"])
        elif self.pointer["status"] == "GATE_READY":
            self.assertIn(self.pointer["current_gate"], {"SRFDI-G10B-FREEZE", "SRFDI-G-JUNE-AUTH"})
            self.assertIsNone(self.pointer["next_packet"])
            self.assertTrue(self.pointer["operator_decision_required"])
            if self.pointer["current_gate"] == "SRFDI-G10B-FREEZE":
                self.assertEqual("COMPLETED_ASSURED_CANDIDATE_PENDING_OPERATOR_FREEZE", self.pointer["wp10b_execution"])
                self.assertEqual("BLOCKED_CONSUMED_RUN_PRESERVED_NO_FRESH_RUN_AUTHORITY", self.pointer["june_execution"])
            else:
                self.assertTrue(self.pointer["wp10b_execution"].startswith("COMPLETED_FROZEN_ON_MAIN@"))
                self.assertTrue(self.pointer["june_execution"].startswith("DENIED"))
                self.assertIsNone(self.pointer["fresh_authority_token_id"])
                self.assertEqual("NOT_MINTED_PENDING_OPERATOR", self.pointer["fresh_authority_token_state"])
            self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["authority_token_state"])
            self.assertTrue(self.pointer["authority_token_consumed"])
        elif self.pointer.get("current_gate") == "SRFDI-G-JUNE-AUTH" and self.pointer["status"] in {"APPROVED", "READY", "RUNNING", "QA_REVIEW"}:
            self.assertFalse(self.pointer["operator_decision_required"])
            self.assertIsNotNone(self.pointer["fresh_authority_token_id"])
            self.assertTrue(self.pointer["june_execution"].startswith("AUTHORIZED"))
            self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["authority_token_state"])
            self.assertTrue(self.pointer["authority_token_consumed"])
        else:
            self.assertEqual("BLOCKED", self.pointer["status"])
            self.assertIsNone(self.pointer["next_packet"])
            self.assertEqual("HARD_BLOCKER_SEGMENTATION_BINDING_MISMATCH", self.pointer["stop_at"])
            self.assertEqual("BLOCKED_CONSUMED_RUN_PRESERVED", self.pointer["june_execution"])
            self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN", self.pointer["authority_token_state"])
            self.assertTrue(self.pointer["authority_token_consumed"])

    def test_reserved_authority_firewalls_remain_closed(self):
        for source in (self.profile["firewalls"], self.state["authority"], self.pointer):
            self.assertEqual("DENIED", source.get("provider_fetch", "DENIED"))
            self.assertEqual("LOCKED_UNCONSUMED", source.get("validation_2025", "LOCKED_UNCONSUMED"))
        self.assertEqual("NONE", self.pointer["scientific_promotion"])
        self.assertEqual("NONE", self.pointer["selector_family_semantic_publication"])
        self.assertEqual("NONE", self.pointer["probability_risk_exposure_execution"])


if __name__ == "__main__":
    unittest.main()
