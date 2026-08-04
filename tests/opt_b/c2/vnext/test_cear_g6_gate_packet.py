from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FREEZE = ROOT / "registries/opt_b/c2/vnext/C2_INTEGRATED_FREEZE_CANDIDATE_v0_1.jsonc"
FORMULAS = ROOT / "registries/opt_b/c2/vnext/C2_FORMULA_PROFILE_CANDIDATES_v0_1.jsonc"
PACKET = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp6/CEAR_G6_OPERATOR_DECISION_PACKET.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_CEAR_G6_GATE_READY_STATE_v0_2.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class CEARG6GatePacketTests(unittest.TestCase):
    def test_freeze_candidate_names_every_revision_and_is_non_effective(self) -> None:
        freeze = load(FREEZE)
        self.assertFalse(freeze["effective"])
        self.assertEqual("NONE_PENDING_OPERATOR_DECISION", freeze["authority"])
        self.assertEqual(
            {
                "C2AR.OBSERVATION.SHADOW.r1",
                "C2AR.HORIZON.SHADOW.r1",
                "C2AR.LEVEL.SHADOW.r1",
                "C2AR.CONTAINER.SHADOW.r1",
                "C2AR.RELATION.SHADOW.r1",
            },
            {item["revision_id"] for item in freeze["normative_boundaries"]},
        )
        self.assertTrue(all(item["proposed_maturity"] == "SHADOW_FROZEN" for item in freeze["normative_boundaries"]))
        self.assertIn("NO_SELECTOR_ACTIVATION", freeze["explicit_non_effects"])
        self.assertIn("NO_RELEASE_PUBLICATION", freeze["explicit_non_effects"])

    def test_formula_profiles_cover_five_axes_without_activation_or_thresholds(self) -> None:
        registry = load(FORMULAS)
        self.assertIsNone(registry["active_profile_id"])
        self.assertIsNone(registry["canonical_profile_id"])
        self.assertEqual("NONE", registry["selector_effect"])
        self.assertEqual("NONE", registry["threshold_effect"])
        profiles = registry["profiles"]
        self.assertEqual({"LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY"}, {item["axis"] for item in profiles})
        for profile in profiles:
            self.assertFalse(profile["active"])
            self.assertFalse(profile["canonical"])
            self.assertEqual([], profile["numeric_thresholds"])
            self.assertTrue(profile["inputs"])
            self.assertTrue(profile["outputs"])
            self.assertTrue(profile["prohibited_outputs"])
        interaction = next(item for item in profiles if item["axis"] == "INTERACTION")
        self.assertTrue({"APPROACHING", "TESTING", "REJECTING", "ACCEPTING"}.issubset(interaction["prohibited_outputs"]))

    def test_operator_packet_is_one_complete_reserved_decision(self) -> None:
        packet = load(PACKET)
        self.assertEqual("CEAR-G6", packet["gate_id"])
        self.assertEqual("OPERATOR_REQUIRED", packet["gate_class"])
        self.assertTrue(packet["operator_decision_required"])
        self.assertEqual("PASS", packet["recommended_decision"])
        self.assertEqual("OVC APPROVE CEAR-G6 PASS", packet["exact_operator_decision_text"])
        self.assertEqual({"PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"}, set(packet["allowed_decisions"]))
        self.assertEqual([], packet["unresolved_issues"])
        self.assertEqual([], packet["tests_and_qa"]["blocking_warnings"])
        self.assertTrue(packet["rollback"]["before_pass"])
        self.assertTrue(packet["exact_work_after_approval"])
        self.assertIn("ACTIVE_SELECTOR_OR_REPLACEMENT", packet["proposed_authority_delta"]["explicitly_not_granted"])
        self.assertIn("VALIDATION_CONSUMPTION", packet["proposed_authority_delta"]["explicitly_not_granted"])
        self.assertEqual(7, len(packet["completed_packets"]))

    def test_gate_state_denies_execution_until_operator_decision(self) -> None:
        state = load(STATE)
        self.assertEqual("GATE_READY", state["status"])
        self.assertEqual("CEAR-G6", state["current_gate"])
        self.assertTrue(state["operator_decision_required"])
        self.assertEqual("GATE_READY_NO_EXECUTION_AUTHORITY", state["authority"]["wp6"])
        self.assertEqual("NOT_GRANTED", state["authority"]["integrated_freeze"])
        self.assertFalse(state["candidate_artifacts"]["effective"])
        self.assertEqual([], state["blockers"])

    def test_active_c2_selector_and_validation_remain_unchanged(self) -> None:
        active = (ROOT / "registries/opt_b/c2/C2_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        self.assertIn("SELECTOR.OPT-B.C2.GBPUSD.v2", active)
        self.assertIn("OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2", active)
        self.assertIn("LOCKED_UNCONSUMED", active)

    def test_candidate_digest_is_deterministic_and_emitted(self) -> None:
        body = {
            "freeze": load(FREEZE),
            "formulas": load(FORMULAS),
            "packet": load(PACKET),
            "state": load(STATE),
        }
        first = hashlib.sha256(canonical(body)).hexdigest()
        second = hashlib.sha256(canonical(json.loads(json.dumps(body)))).hexdigest()
        self.assertEqual(first, second)
        self.assertRegex(first, r"^[0-9a-f]{64}$")
        print("CEAR_G6_CANDIDATE_PACKET_SHA256=" + first)


if __name__ == "__main__":
    unittest.main()
