from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RELEASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp8"
DECISION = RELEASE / "CEAR_G8_OPERATOR_DECISION.json"
RECEIPT = RELEASE / "CEAR_G8_AUTHORITY_RECEIPT.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_CEAR_G8_APPROVED_STATE_v0_2.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CEARG8DecisionRecordTests(unittest.TestCase):
    def test_operator_pass_is_exact_immutable_and_bounded(self) -> None:
        decision = load(DECISION)
        self.assertEqual("CEAR-G8.OPERATOR.PASS.20260805T062900+0100", decision["decision_id"])
        self.assertEqual("PASS", decision["decision"])
        self.assertEqual("OVC APPROVE CEAR-G8 PASS", decision["decision_text"])
        self.assertEqual("OPERATOR", decision["decision_authority"])
        self.assertEqual("3f3dd1d2d1e0d482183210eacc53106d9ea71e0c", decision["assured_predecision_head"])
        delta = decision["approved_authority_delta"]
        self.assertEqual(
            "PARENT_CONTEXT_IS_A_TYPED_BUNDLE_OF_SEPARATE_LINKED_OBJECTS_NOT_ONE_BLENDED_PARENT_FIELD",
            delta["central_policy"],
        )
        self.assertEqual(4, len(delta["typed_contexts"]))
        self.assertEqual(
            "CLEAR_DEPENDENT_LINKS_WITHOUT_OLDER_PARENT_FALLBACK",
            delta["failed_slot_policy"],
        )
        denied = set(decision["explicitly_not_granted"])
        self.assertIn("ACTIVE_OR_CANONICAL_PARENT_SELECTION", denied)
        self.assertIn("NUMERIC_STALENESS_FRESHNESS_THRESHOLD", denied)
        self.assertIn("C2E_OR_C2_5_ACTIVATION", denied)
        self.assertIn("VALIDATION_CONSUMPTION", denied)

    def test_evidence_constraints_fail_closed_without_hidden_selection(self) -> None:
        constraints = load(DECISION)["evidence_constraints"]
        self.assertEqual(
            "PARENT_INTERVAL_END_MUST_NOT_EXCEED_LOCAL_FIRST_VALID_TIME",
            constraints["chronology"],
        )
        self.assertEqual(
            "RESOLVE_SCHEDULED_SLOT_BEFORE_COMPLETENESS_FILTERING",
            constraints["expected_slot"],
        )
        self.assertEqual(
            "FAIL_CLOSED_CLEAR_DEPENDENTS_NO_CARRY_FORWARD",
            constraints["failed_expected_slot"],
        )
        self.assertEqual(
            "LINK_AUTHORITATIVE_IDENTITIES_NEVER_RECREATE_AS_LOCAL_PARENT_RANGE",
            constraints["parent_objects"],
        )
        self.assertEqual("EXACTLY_ONE_ELIGIBLE_OBJECT_OR_EXPLICIT_NULL", constraints["selection"])
        self.assertEqual("COMPONENT_SCOPED_NO_GLOBAL_DEGRADED_COLLAPSE", constraints["computability"])

    def test_receipt_and_programme_state_release_only_bounded_implementation(self) -> None:
        receipt = load(RECEIPT)
        state = load(STATE)
        self.assertEqual("APPROVED_PENDING_DECISION_PR_MERGE", receipt["authority_state"])
        self.assertEqual("NONE", receipt["active_authority_changes"]["active_parent_selection"])
        self.assertEqual("NONE", receipt["active_authority_changes"]["canonical_parent_selection"])
        self.assertEqual("NONE", receipt["active_authority_changes"]["numeric_staleness_threshold"])
        self.assertEqual("NONE", receipt["active_authority_changes"]["semantic_event_episode"])
        self.assertEqual("APPROVED", state["status"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual("C2AR-WP8-IMPLEMENTATION", state["active_packet"])
        self.assertEqual(
            "SHADOW_FROZEN_IMPLEMENTATION_APPROVED_INACTIVE_NONCANONICAL",
            state["authority"]["parent_context_resolver"],
        )
        self.assertEqual("NOT_GRANTED", state["authority"]["universal_staleness_threshold"])
        self.assertEqual("SEPARATE_NOT_GRANTED", state["authority"]["episode_context"])
        self.assertEqual("NONE", state["authority"]["release_publication_validation"])


if __name__ == "__main__":
    unittest.main()
