from __future__ import annotations

import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
GATE_ROOT = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/structured-review-v2/gate"
RAW = GATE_ROOT / "evidence/raw"
STATE = ROOT / "registries/research_operations/pattern_discovery/PD_C1C_G5_PILOT_CORRECTIVE_STATE_v0_1.json"
SIGNING = ROOT / "docs/releases/prospective-source-v0-1/rps-wp4/evidence/operator-signing-binding.json"
GATE_ID = "C1C-G5-CORRECTIVE-PILOT-REVIEW"
RUN_ID = "PD.PILOT.RUN.96c16f11717e787f971851ee"
NAMESPACE = "PD.PILOT.GBPUSD.20260622_20260625.v2"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(path)
    return value


def exact_b64(name: str) -> bytes:
    return base64.b64decode((RAW / f"{name}.b64").read_text(encoding="ascii"), validate=True)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


class C1cG5CorrectivePilotReviewGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gate_input_bytes = exact_b64("c1c-g5-corrective-pilot-review-gate-input.json")
        cls.inventory_bytes = exact_b64("signed-structured-review-evidence-inventory.json")
        cls.receipt_bytes = (RAW / "pilot-review-receipt-v2.json").read_bytes()
        cls.ledger_bytes = (RAW / "pilot-defect-ledger-v2.json").read_bytes()
        cls.gate_input = json.loads(cls.gate_input_bytes)
        cls.inventory = json.loads(cls.inventory_bytes)
        cls.receipt = json.loads(cls.receipt_bytes)
        cls.ledger = json.loads(cls.ledger_bytes)
        cls.index = load(GATE_ROOT / "C1C_G5_CORRECTIVE_PILOT_REVIEW_EVIDENCE_INDEX.json")
        cls.qa = load(GATE_ROOT / "C1C_G5_CORRECTIVE_PILOT_REVIEW_QA_PACKET.json")
        cls.gate = load(GATE_ROOT / "C1C_G5_CORRECTIVE_PILOT_REVIEW_GATE_PACKET.json")
        cls.state = load(STATE)
        cls.signing = load(SIGNING)

    def test_exact_file_hashes_and_signed_chain(self) -> None:
        files = {
            "c1c-g5-corrective-pilot-review-gate-input.json": self.gate_input_bytes,
            "pilot-defect-ledger-v2.json": self.ledger_bytes,
            "pilot-review-receipt-v2.json": self.receipt_bytes,
            "signed-structured-review-evidence-inventory.json": self.inventory_bytes,
        }
        indexed = {item["name"]: item for item in self.index["files"]}
        for name, payload in files.items():
            self.assertEqual(len(payload), indexed[name]["size_bytes"], name)
            self.assertEqual(hashlib.sha256(payload).hexdigest(), indexed[name]["sha256"], name)
        self.assertEqual(self.gate_input["structured_review_receipt_file_sha256"], indexed["pilot-review-receipt-v2.json"]["sha256"])
        self.assertEqual(self.gate_input["structured_defect_ledger_file_sha256"], indexed["pilot-defect-ledger-v2.json"]["sha256"])
        self.assertEqual(self.gate_input["signed_structured_inventory_file_sha256"], indexed["signed-structured-review-evidence-inventory.json"]["sha256"])
        self.assertEqual(self.inventory["structured_review_v2_file_sha256"], indexed["pilot-review-receipt-v2.json"]["sha256"])
        self.assertEqual(self.inventory["structured_defect_ledger_v2_file_sha256"], indexed["pilot-defect-ledger-v2.json"]["sha256"])
        self.assertEqual(self.ledger["source_review_receipt_v2_file_sha256"], indexed["pilot-review-receipt-v2.json"]["sha256"])
        self.assertTrue(all(self.index["hash_chain"].values()))

    def _verify(self, record: dict, *, inventory: bool = False) -> None:
        excluded = {
            "signature_algorithm","signature_format","signature_namespace",
            "signed_payload_sha256","signature_sha256","signature",
        }
        if inventory:
            excluded.update({"inventory_id","status"})
        body = {key: value for key, value in record.items() if key not in excluded}
        payload = canonical_bytes(body)
        self.assertEqual(hashlib.sha256(payload).hexdigest(), record["signed_payload_sha256"])
        self.assertEqual(hashlib.sha256(record["signature"].encode("utf-8")).hexdigest(), record["signature_sha256"])
        ssh_keygen = shutil.which("ssh-keygen")
        self.assertIsNotNone(ssh_keygen)
        with tempfile.TemporaryDirectory(prefix="c1c-g5-gate-") as temporary:
            root = Path(temporary)
            signature = root / "signature"
            allowed = root / "allowed_signers"
            signature.write_text(record["signature"], encoding="utf-8")
            allowed.write_text(
                f'OVC.OPERATOR.PRIMARY.LOCAL.V1 namespaces="ovc-rps" {self.signing["public_key"]}\n',
                encoding="utf-8",
            )
            result = subprocess.run(
                [ssh_keygen, "-Y", "verify", "-f", str(allowed), "-I",
                 "OVC.OPERATOR.PRIMARY.LOCAL.V1", "-n", "ovc-rps", "-s", str(signature)],
                input=payload,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))

    def test_both_operator_signatures_verify(self) -> None:
        self._verify(self.receipt)
        self._verify(self.inventory, inventory=True)

    def test_review_is_complete_but_contains_five_findings(self) -> None:
        self.assertEqual(self.receipt["pilot_run_id"], RUN_ID)
        self.assertEqual(self.receipt["pilot_namespace"], NAMESPACE)
        self.assertEqual(self.receipt["decision_count"], 6)
        dispositions = Counter(item["review_disposition"] for item in self.receipt["decisions"])
        self.assertEqual(dispositions, Counter({
            "WORKFLOW_ACCEPTED": 1,
            "FLAG_WORKFLOW_DEFECT": 1,
            "FLAG_UI_FRICTION": 1,
            "DEFER_PILOT_OBJECT": 2,
            "REJECT_PILOT_OBJECT": 1,
        }))
        self.assertEqual(self.ledger["defect_count"], 5)
        self.assertTrue(self.ledger["contract_changes_required"])
        self.assertEqual(self.gate_input["gate_id"], GATE_ID)
        self.assertTrue(self.gate_input["operator_approval_required"])
        self.assertFalse(self.gate_input["second_machine_replay_required"])

    def test_gate_is_ready_and_fail_closed(self) -> None:
        self.assertEqual(self.gate["gate_status"], "GATE_READY")
        self.assertTrue(self.gate["operator_approval_required"])
        self.assertEqual(self.gate["recommended_decision"], "DEFER")
        self.assertEqual(self.qa["qa_recommendation"], "DEFER")
        self.assertEqual(self.qa["qa_status"], "PASS_EVIDENCE_DEFER_OPERATIONAL_ACCEPTANCE")
        self.assertEqual(self.state["status"], "GATE_READY_OPERATOR_DECISION_REQUIRED")
        self.assertEqual(self.state["next_gate"], GATE_ID)
        self.assertEqual(self.state["recommended_decision"], "DEFER")
        self.assertEqual(self.state["blocker_resolution"]["status"], "RESOLVED_TO_OPERATOR_GATE")
        self.assertIsNone(self.state["blocker_id"])
        retained = self.state["retained_authority"]
        for key in (
            "semantic_promotion","family_promotion","candidate_promotion","novelty_promotion",
            "threshold_change","probability","risk","exposure","trading","execution","agent_write",
        ):
            self.assertEqual(retained[key], "NONE", key)
        self.assertEqual(retained["canonical_discovery_processing"], "DENIED")
        self.assertEqual(retained["canonical_append"], "DENIED")
        self.assertEqual(retained["validation_consumption"], "LOCKED_UNCONSUMED")


if __name__ == "__main__":
    unittest.main()
