from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from ovc.research_operations.pattern_discovery import pilot_corrective_review_v2 as review_v2


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/corr2-return-gate"
RAW = RELEASE / "evidence/raw"
STATE = ROOT / "registries/research_operations/pattern_discovery/PD_C1C_G5_PILOT_CORRECTIVE_STATE_v0_1.json"
SIGNING = ROOT / "docs/releases/prospective-source-v0-1/rps-wp4/evidence/operator-signing-binding.json"
GATE_PACKET = RELEASE / "C1C_G5_CORR2_RETURN_GATE_PACKET.json"
QA_PACKET = RELEASE / "C1C_G5_CORR2_RETURN_QA_PACKET.json"

LEDGER = RAW / "c1c-g5-corr2-closure-ledger.json"
RECEIPT = RAW / "c1c-g5-corr2-review-receipt.json"
GATE_INPUT = RAW / "c1c-g5-corrective-pilot-review-final-gate-input.json"
INVENTORY = RAW / "signed-c1c-g5-corr2-evidence-inventory.json"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(path)
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def logical_sha(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class C1cG5Corr2ReturnGateTests(unittest.TestCase):
    def test_exact_hash_chain_and_ledger_logical_hash(self) -> None:
        ledger = load(LEDGER)
        receipt = load(RECEIPT)
        gate = load(GATE_INPUT)
        inventory = load(INVENTORY)

        self.assertEqual(sha(LEDGER), "65507b2acb691433cccc48a1e63311f89b783dabd3802763c362004effcdd3af")
        self.assertEqual(sha(RECEIPT), "86be15969ca26d9da83bffc018ec02f3f5f6b9f6eaf5cdca1b197d46b8dbc963")
        self.assertEqual(sha(GATE_INPUT), "5aadafcda41631f9a64575ede02136faa50ed2a2f546d8698a6ef294e781adb6")
        self.assertEqual(sha(INVENTORY), "7d57c8032465fca28508d9da8965a0abdec7c8a37a5b772ca8de87480d87e19f")

        self.assertEqual(ledger["source_corr2_review_receipt_file_sha256"], sha(RECEIPT))
        self.assertEqual(inventory["corr2_review_receipt_file_sha256"], sha(RECEIPT))
        self.assertEqual(inventory["corr2_closure_ledger_file_sha256"], sha(LEDGER))
        self.assertEqual(gate["corr2_review_receipt_file_sha256"], sha(RECEIPT))
        self.assertEqual(gate["corr2_closure_ledger_file_sha256"], sha(LEDGER))
        self.assertEqual(gate["signed_corr2_inventory_file_sha256"], sha(INVENTORY))

        body = dict(ledger)
        claimed = body.pop("ledger_sha256")
        self.assertEqual(logical_sha(body), claimed)

    def test_both_operator_signatures_verify_against_registered_key(self) -> None:
        public_key = load(SIGNING)["public_key"]
        receipt = load(RECEIPT)
        inventory = load(INVENTORY)

        receipt_body = {
            key: value
            for key, value in receipt.items()
            if key not in review_v2._SIGNATURE_FIELDS
        }
        inventory_body = {
            key: value
            for key, value in inventory.items()
            if key not in set(review_v2._SIGNATURE_FIELDS) | {"inventory_id", "status"}
        }
        review_v2._verify_signature(receipt, receipt_body, public_key=public_key)
        review_v2._verify_signature(inventory, inventory_body, public_key=public_key)

    def test_review_result_requires_defer(self) -> None:
        receipt = load(RECEIPT)
        ledger = load(LEDGER)
        gate = load(GATE_INPUT)
        dispositions = {
            item["candidate_window_id"]: item["final_disposition"]
            for item in receipt["decisions"]
        }
        self.assertEqual(
            dispositions["PDPILOT-CANDIDATE-4f41e21b6cd075e0fdbc40e4"],
            "REJECT_PILOT_OBJECT",
        )
        self.assertEqual(
            dispositions["PDPILOT-CANDIDATE-bab63b935155e4d9033aed81"],
            "DEFER_PILOT_OBJECT",
        )
        self.assertEqual(ledger["remaining_deferred_object_count"], 1)
        self.assertTrue(ledger["contract_changes_required"])
        self.assertEqual(gate["remaining_deferred_object_count"], 1)
        self.assertEqual(gate["recommended_decision"], "DEFER")
        self.assertFalse(gate["second_machine_replay_performed"])
        self.assertEqual(gate["canonical_append"], "DENIED")

    def test_programme_state_and_gate_packet_are_fail_closed(self) -> None:
        state = load(STATE)
        gate = load(GATE_PACKET)
        qa = load(QA_PACKET)

        self.assertEqual(state["programme_state"], "GATE_READY")
        self.assertEqual(
            state["status"],
            "C1C_G5_CORR2_RETURN_GATE_READY_OPERATOR_DECISION_REQUIRED",
        )
        self.assertEqual(state["blocker"]["status"], "RESOLVED_TO_OPERATOR_RETURN_GATE")
        self.assertEqual(state["corr2_local_review"]["remaining_deferred_object_count"], 1)
        self.assertTrue(state["corr2_local_review"]["signatures_verified"])
        self.assertEqual(state["continuation"], "OPERATOR_DECISION_REQUIRED")
        self.assertEqual(
            state["continuation_command"],
            "@GitHub OVC APPROVE C1C-G5-CORRECTIVE-PILOT-REVIEW DEFER",
        )
        self.assertEqual(gate["gate_status"], "GATE_READY")
        self.assertTrue(gate["operator_approval_required"])
        self.assertEqual(gate["recommended_decision"], "DEFEU")
        self.assertEqual(qa["qa_status"], "PASS_EVIDENCE_DEFER_OPERATIONAL_ACCEPTANCE")
        self.assertEqual(qa["qa_recommendation"], "DEFEU")

        authority = state["retained_authority"]
        for key in (
            "canonical_discovery_processing",
            "canonical_append",
            "selector_mutation",
            "release_mutation",
        ):
            self.assertEqual(authority[key], "DENIED")
        self.assertEqual(authority["validation_consumption"], "LOCKED_UNCONSUMED")
        for key in (
            "semantic_promotion",
            "family_promotion",
            "candidate_promotion",
            "novelty_promotion",
            "threshold_change",
            "probability",
            "risk",
            "exposure",
            "trading",
            "execution",
            "agent_write",
        ):
            self.assertEqual(authority[key], "NONE")


if __name__ == "__main__":
    unittest.main()
