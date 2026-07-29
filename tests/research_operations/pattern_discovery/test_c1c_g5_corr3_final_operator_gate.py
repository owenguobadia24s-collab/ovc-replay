from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/final-gate/C1C_G5_CORR3_FINAL_OPERATOR_GATE_PACKET.json"
PUBLIC_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOjITxMioIXgGbApGohaq2J/dQltuluVvPzy5B3I3QKJ"
OPERATOR_ID = "OVC.OPERATOR.PRIMARY.LOCAL.V1"
NAMESPACE = "ovc-rps"
SIGNATURE_FIELDS = {
    "signature_algorithm", "signature_format", "signature_namespace",
    "signed_payload_sha256", "signature_sha256", "signature",
}


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def logical_sha(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def verify_sshsig(record: dict[str, object], body: dict[str, object]) -> None:
    with tempfile.TemporaryDirectory(prefix="c1c-g5-corr3-gate-") as temporary:
        root = Path(temporary)
        allowed = root / "allowed_signers"
        signature = root / "signature"
        allowed.write_text(f"{OPERATOR_ID} namespaces={NAMESPACE} {PUBLIC_KEY}\n", encoding="utf-8")
        signature.write_text(str(record["signature"]), encoding="utf-8")
        result = subprocess.run(
            ["ssh-keygen", "-Y", "verify", "-f", str(allowed), "-I", OPERATOR_ID,
             "-n", NAMESPACE, "-s", str(signature)],
            input=canonical_bytes(body), capture_output=True, check=False,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr.decode("utf-8", errors="replace"))


class C1cG5Corr3FinalGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = json.loads(PACKET.read_text(encoding="utf-8"))
        cls.raw: dict[str, bytes] = {}
        cls.docs: dict[str, dict[str, object]] = {}
        for item in cls.packet["evidence"]["files"]:
            payload = base64.b64decode(item["content_base64"], validate=True)
            if hashlib.sha256(payload).hexdigest() != item["sha256"]:
                raise AssertionError(item["name"])
            if len(payload) != item["size_bytes"]:
                raise AssertionError(item["name"])
            cls.raw[item["name"]] = payload
            value = json.loads(payload.decode("utf-8"))
            if not isinstance(value, dict):
                raise AssertionError(item["name"])
            cls.docs[item["name"]] = value

    def test_exact_hash_chain_and_logical_ledger(self) -> None:
        receipt_name = "c1c-g5-corr3-review-receipt.json"
        ledger_name = "c1c-g5-corr3-closure-ledger.json"
        inventory_name = "signed-c1c-g5-corr3-evidence-inventory.json"
        gate_name = "c1c-g5-corrective-pilot-review-final-gate-input.json"
        receipt = self.docs[receipt_name]
        ledger = self.docs[ledger_name]
        inventory = self.docs[inventory_name]
        gate = self.docs[gate_name]
        receipt_sha = hashlib.sha256(self.raw[receipt_name]).hexdigest()
        ledger_sha = hashlib.sha256(self.raw[ledger_name]).hexdigest()
        inventory_sha = hashlib.sha256(self.raw[inventory_name]).hexdigest()
        body = dict(ledger)
        claimed = body.pop("ledger_sha256")
        self.assertEqual(claimed, logical_sha(body))
        self.assertEqual(ledger["source_corr3_review_receipt_file_sha256"], receipt_sha)
        self.assertEqual(inventory["corr3_review_receipt_file_sha256"], receipt_sha)
        self.assertEqual(inventory["corr3_closure_ledger_file_sha256"], ledger_sha)
        self.assertEqual(gate["corr3_review_receipt_file_sha256"], receipt_sha)
        self.assertEqual(gate["corr3_closure_ledger_file_sha256"], ledger_sha)
        self.assertEqual(gate["signed_corr3_inventory_file_sha256"], inventory_sha)

    def test_operator_signatures_verify(self) -> None:
        receipt = self.docs["c1c-g5-corr3-review-receipt.json"]
        receipt_body = {key: value for key, value in receipt.items() if key not in SIGNATURE_FIELDS}
        self.assertEqual(receipt["signed_payload_sha256"], logical_sha(receipt_body))
        self.assertEqual(receipt["signature_sha256"], hashlib.sha256(str(receipt["signature"]).encode()).hexdigest())
        verify_sshsig(receipt, receipt_body)

        inventory = self.docs["signed-c1c-g5-corr3-evidence-inventory.json"]
        inventory_body = {
            key: value for key, value in inventory.items()
            if key not in SIGNATURE_FIELDS | {"inventory_id", "status"}
        }
        self.assertEqual(inventory["signed_payload_sha256"], logical_sha(inventory_body))
        self.assertEqual(inventory["signature_sha256"], hashlib.sha256(str(inventory["signature"]).encode()).hexdigest())
        verify_sshsig(inventory, inventory_body)

    def test_pass_recommendation_and_reserved_authority(self) -> None:
        receipt = self.docs["c1c-g5-corr3-review-receipt.json"]
        ledger = self.docs["c1c-g5-corr3-closure-ledger.json"]
        gate = self.docs["c1c-g5-corrective-pilot-review-final-gate-input.json"]
        self.assertEqual(receipt["decision"]["final_disposition"], "WORKFLOW_ACCEPTED")
        self.assertEqual(ledger["remaining_deferred_object_count"], 0)
        self.assertEqual(ledger["resolution_status"], "CLOSED_BY_OPERATOR_REREVIEW")
        self.assertEqual(gate["recommended_decision"], "PASS")
        self.assertTrue(gate["operator_approval_required"])
        self.assertEqual(self.packet["qa"]["recommendation"], "PASS")
        self.assertEqual(self.packet["qa"]["unresolved_issues"], [])
        state = self.packet["programme_state"]
        self.assertEqual(state["authority_required"], "OPERATOR")
        self.assertEqual(state["authority_delta"], "NONE_UNTIL_OPERATOR_DECISION")
        self.assertEqual(
            self.packet["operator_command"],
            "OVC APPROVE C1C-G5-CORRECTIVE-PILOT-REVIEW PASS",
        )
        retained = self.packet["current_authority"]
        self.assertEqual(retained["canonical_discovery_processing"], "DENIED")
        self.assertEqual(retained["canonical_append"], "DENIED")
        self.assertEqual(retained["validation_consumption"], "LOCKED_UNCONSUMED")
        for key in (
            "semantic_promotion", "family_promotion", "candidate_promotion",
            "novelty_promotion", "threshold_or_model_change", "probability",
            "risk", "exposure", "trading", "execution", "agent_write",
        ):
            self.assertEqual(retained[key], "NONE", key)


if __name__ == "__main__":
    unittest.main()
