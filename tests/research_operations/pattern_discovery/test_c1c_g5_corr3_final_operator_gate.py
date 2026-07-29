from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
GATE_ROOT = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/final-gate"
PACKET_PATH = GATE_ROOT / "C1C_G5_CORR3_FINAL_OPERATOR_GATE_PACKET.json"
RAW = GATE_ROOT / "evidence/corr3/raw"
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


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(path)
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_signature(record: dict[str, object], body: dict[str, object]) -> None:
    assert record["signed_payload_sha256"] == logical_sha(body)
    assert record["signature_sha256"] == hashlib.sha256(str(record["signature"]).encode("utf-8")).hexdigest()
    with tempfile.TemporaryDirectory(prefix="c1c-g5-corr3-final-") as directory:
        root = Path(directory)
        allowed = root / "allowed_signers"
        signature = root / "signature"
        allowed.write_text(
            f'{OPERATOR_ID} namespaces="{NAMESPACE}" {PUBLIC_KEY}\n',
            encoding="utf-8",
        )
        signature.write_text(str(record["signature"]), encoding="utf-8")
        result = subprocess.run(
            [
                "ssh-keygen", "-Y", "verify", "-f", str(allowed), "-I", OPERATOR_ID,
                "-n", NAMESPACE, "-s", str(signature),
            ],
            input=canonical_bytes(body),
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr.decode("utf-8", errors="replace"))


class C1cG5Corr3FinalGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = load(PACKET_PATH)
        cls.files = {item["name"]: item for item in cls.packet["evidence"]["files"]}
        cls.docs = {name: load(RAW / name) for name in cls.files}

    def test_exact_raw_file_hashes_and_sizes(self) -> None:
        self.assertEqual(
            set(self.files),
            {
                "c1c-g5-corr3-closure-ledger.json",
                "c1c-g5-corr3-review-receipt.json",
                "c1c-g5-corrective-pilot-review-final-gate-input.json",
                "signed-c1c-g5-corr3-evidence-inventory.json",
            },
        )
        for name, item in self.files.items():
            path = RAW / name
            self.assertEqual(path.stat().st_size, item["size_bytes"], name)
            self.assertEqual(sha(path), item["sha256"], name)

    def test_hash_chain_and_logical_ledger(self) -> None:
        receipt_name = "c1c-g5-corr3-review-receipt.json"
        ledger_name = "c1c-g5-corr3-closure-ledger.json"
        inventory_name = "signed-c1c-g5-corr3-evidence-inventory.json"
        gate_name = "c1c-g5-corrective-pilot-review-final-gate-input.json"
        receipt = self.docs[receipt_name]
        ledger = self.docs[ledger_name]
        inventory = self.docs[inventory_name]
        gate = self.docs[gate_name]
        ledger_body = dict(ledger)
        claimed = ledger_body.pop("ledger_sha256")
        self.assertEqual(claimed, logical_sha(ledger_body))
        self.assertEqual(ledger["source_corr3_review_receipt_file_sha256"], sha(RAW / receipt_name))
        self.assertEqual(inventory["corr3_review_receipt_file_sha256"], sha(RAW / receipt_name))
        self.assertEqual(inventory["corr3_closure_ledger_file_sha256"], sha(RAW / ledger_name))
        self.assertEqual(gate["corr3_review_receipt_file_sha256"], sha(RAW / receipt_name))
        self.assertEqual(gate["corr3_closure_ledger_file_sha256"], sha(RAW / ledger_name))
        self.assertEqual(gate["signed_corr3_inventory_file_sha256"], sha(RAW / inventory_name))

    def test_operator_signatures_verify(self) -> None:
        receipt = self.docs["c1c-g5-corr3-review-receipt.json"]
        receipt_body = {key: value for key, value in receipt.items() if key not in SIGNATURE_FIELDS}
        verify_signature(receipt, receipt_body)
        inventory = self.docs["signed-c1c-g5-corr3-evidence-inventory.json"]
        inventory_body = {
            key: value for key, value in inventory.items()
            if key not in SIGNATURE_FIELDS | {"inventory_id", "status"}
        }
        verify_signature(inventory, inventory_body)

    def test_pass_recommendation_and_operator_boundary(self) -> None:
        receipt = self.docs["c1c-g5-corr3-review-receipt.json"]
        ledger = self.docs["c1c-g5-corr3-closure-ledger.json"]
        gate = self.docs["c1c-g5-corrective-pilot-review-final-gate-input.json"]
        self.assertEqual(receipt["decision"]["final_disposition"], "WORKFLOW_ACCEPTED")
        self.assertEqual(ledger["remaining_deferred_object_count"], 0)
        self.assertEqual(ledger["resolution_status"], "CLOSED_BY_OPERATOR_REREVIEW")
        self.assertEqual(gate["recommended_decision"], "PASS")
        self.assertTrue(gate["operator_approval_required"])
        self.assertFalse(gate["second_machine_replay_performed"])
        self.assertEqual(gate["canonical_append"], "DENIED")
        self.assertEqual(gate["validation_consumption"], "LOCKED_UNCONSUMED")
        self.assertEqual(self.packet["recommended_decision"], "PASS")
        self.assertTrue(self.packet["operator_approval_required"])
        self.assertEqual(self.packet["programme_state"]["authority_required"], "OPERATOR")
        self.assertEqual(
            self.packet["programme_state"]["authority_delta"],
            "NONE_UNTIL_OPERATOR_DECISION",
        )
        retained = self.packet["current_authority"]
        self.assertEqual(retained["canonical_discovery_processing"], "DENIED")
        self.assertEqual(retained["canonical_append"], "DENIED")
        self.assertEqual(retained["selector_mutation"], "DENIED")
        self.assertEqual(retained["release_mutation"], "DENIED")
        self.assertEqual(retained["r2_publication"], "DENIED")
        self.assertEqual(retained["validation_consumption"], "LOCKED_UNCONSUMED")
        for key in (
            "semantic_promotion", "family_promotion", "candidate_promotion",
            "novelty_promotion", "threshold_or_model_change", "probability",
            "risk", "exposure", "trading", "execution", "agent_write",
        ):
            self.assertEqual(retained[key], "NONE", key)


if __name__ == "__main__":
    unittest.main()
