from __future__ import annotations

import base64
import hashlib
import json
from collections import Counter
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
GATE_ROOT = ROOT / "docs/releases/pattern-discovery-v0-3/pd-g5p"
RAW_ROOT = GATE_ROOT / "evidence/raw"
STATE_PATH = ROOT / "registries/research_operations/pattern_discovery/PD_G5P_PILOT_OPERATIONS_ACCEPTANCE_STATE_v0_1.json"
PD_WP5_STATE_PATH = ROOT / "registries/research_operations/pattern_discovery/PD_WP5_STATE_v0_1.json"
REGISTRY_PATH = ROOT / "registries/research_operations/pattern_discovery/PATTERN_DISCOVERY_IMPLEMENTATION_REGISTRY_v0_3.yaml"
SIGNING_PATH = ROOT / "docs/releases/prospective-source-v0-1/rps-wp4/evidence/operator-signing-binding.json"

PILOT_RUN_ID = "PD.PILOT.RUN.0cc5a59ca751583f3e50091c"
PILOT_NAMESPACE = "PD.PILOT.GBPUSD.20260622_20260625.v1"
SOURCE_SLICE_ID = "RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1"
RUN_ID = "RPS.RUN.7aeb551335d766ee3bf503e6"
BINDING_ID = "RPS.BINDING.32fb3003efa072916c11e907"
ACCEPTANCE_ID = "RPS.REPLAY-ACCEPT.0844eddf74e144ced487cc48"
SIGNING_BINDING_ID = "RPS.SIGNING.50092c28981fef08f53a6cb5"
OPERATOR_ID = "OVC.OPERATOR.PRIMARY.LOCAL.V1"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def logical_sha(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return value


def exact_bytes(name: str) -> bytes:
    encoded = (RAW_ROOT / f"{name}.b64").read_text(encoding="ascii").strip()
    return base64.b64decode(encoded, validate=True)


def exact_json(name: str) -> dict:
    value = json.loads(exact_bytes(name).decode("utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected exact JSON object: {name}")
    return value


class PDG5PGateReadyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = load_json(GATE_ROOT / "PD_G5P_COMPACT_EVIDENCE_INDEX.json")
        cls.qa_packet = load_json(GATE_ROOT / "PD_G5P_QA_PACKET.json")
        cls.gate_packet = load_json(GATE_ROOT / "PD_G5P_OPERATOR_GATE_PACKET.json")
        cls.state = load_json(STATE_PATH)
        cls.pd_wp5_state = load_json(PD_WP5_STATE_PATH)
        cls.signing = load_json(SIGNING_PATH)
        cls.files = {
            item["name"]: exact_json(item["name"])
            for item in cls.index["files"]
        }

    def test_exact_original_bytes_match_index(self) -> None:
        self.assertEqual(self.index["repository_storage_encoding"], "BASE64_OF_EXACT_ORIGINAL_BYTES")
        self.assertEqual(len(self.index["files"]), 7)
        for item in self.index["files"]:
            payload = exact_bytes(item["name"])
            self.assertEqual(len(payload), item["size_bytes"], item["name"])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), item["sha256"], item["name"])

    def test_identity_and_binding_chain_is_exact(self) -> None:
        for name, payload in self.files.items():
            self.assertEqual(payload.get("pilot_run_id"), PILOT_RUN_ID, name)
        for name in (
            "pilot-run.json",
            "output-manifest.json",
            "pd-g5p-gate-input.json",
            "pilot-review-receipt.json",
            "signed-pilot-evidence-inventory.json",
        ):
            self.assertEqual(self.files[name].get("pilot_namespace"), PILOT_NAMESPACE, name)
        for name in (
            "pilot-run.json",
            "output-manifest.json",
            "pd-g5p-gate-input.json",
            "signed-pilot-evidence-inventory.json",
        ):
            self.assertEqual(self.files[name].get("compute_run_id"), RUN_ID, name)
        for name in (
            "pilot-run.json",
            "output-manifest.json",
            "pd-g5p-gate-input.json",
            "signed-pilot-evidence-inventory.json",
        ):
            self.assertEqual(self.files[name].get("source_binding_id"), BINDING_ID, name)
        self.assertEqual(self.files["pd-g5p-gate-input.json"]["signed_replay_acceptance_id"], ACCEPTANCE_ID)
        self.assertEqual(self.files["pd-g5p-gate-input.json"]["signing_binding_id"], SIGNING_BINDING_ID)
        self.assertEqual(self.files["pd-g5p-gate-input.json"]["operator_id"], OPERATOR_ID)
        self.assertEqual(self.signing["signing_binding_id"], SIGNING_BINDING_ID)
        self.assertEqual(self.signing["operator_id"], OPERATOR_ID)
        self.assertEqual(self.signing["source_slice_id"], SOURCE_SLICE_ID)

    def test_manifest_and_inventory_hash_chain(self) -> None:
        manifest = self.files["output-manifest.json"]
        logical = dict(manifest)
        claimed = logical.pop("output_manifest_sha256")
        self.assertEqual(logical_sha(logical), claimed)
        self.assertEqual(claimed, "0133103e937da4a80fec63198a6a7a72bd9bbad53b57140dafeac90d78608778")

        indexed = {item["name"]: item for item in self.index["files"]}
        inventory = self.files["signed-pilot-evidence-inventory.json"]
        self.assertEqual(inventory["pilot_run_file_sha256"], indexed["pilot-run.json"]["sha256"])
        self.assertEqual(inventory["pilot_output_manifest_file_sha256"], indexed["output-manifest.json"]["sha256"])
        self.assertEqual(inventory["pilot_review_receipt_file_sha256"], indexed["pilot-review-receipt.json"]["sha256"])
        self.assertEqual(inventory["pilot_defect_ledger_file_sha256"], indexed["pilot-defect-ledger.json"]["sha256"])
        self.assertEqual(
            self.files["pd-g5p-gate-input.json"]["signed_pilot_evidence_inventory_file_sha256"],
            indexed["signed-pilot-evidence-inventory.json"]["sha256"],
        )

    def _verify_sshsig(self, record: dict, body: dict) -> None:
        self.assertEqual(record["signed_payload_sha256"], logical_sha(body))
        self.assertEqual(record["signature_sha256"], hashlib.sha256(record["signature"].encode("utf-8")).hexdigest())
        self.assertEqual(record["signature_algorithm"], "ED25519")
        self.assertEqual(record["signature_format"], "SSHSIG_OPENSSH_V1")
        self.assertEqual(record["signature_namespace"], "ovc-rps")
        ssh_keygen = shutil.which("ssh-keygen")
        self.assertIsNotNone(ssh_keygen, "ssh-keygen is required for PD-G5P signature verification")
        with tempfile.TemporaryDirectory(prefix="pd-g5p-verify-") as temporary:
            root = Path(temporary)
            signature = root / "signature"
            allowed = root / "allowed_signers"
            signature.write_text(record["signature"], encoding="utf-8")
            allowed.write_text(
                f'{OPERATOR_ID} namespaces="ovc-rps" {self.signing["public_key"]}\n',
                encoding="utf-8",
            )
            result = subprocess.run(
                [ssh_keygen, "-Y", "verify", "-f", str(allowed), "-I", OPERATOR_ID, "-n", "ovc-rps", "-s", str(signature)],
                input=canonical_bytes(body),
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))

    def test_all_three_ed25519_signatures_verify(self) -> None:
        run = self.files["pilot-run.json"]
        run_body = {key: value for key, value in run.items() if key not in {
            "signature_algorithm", "signature_format", "signature_namespace",
            "signed_payload_sha256", "signature_sha256", "signature",
        }}
        self._verify_sshsig(run, run_body)

        review = self.files["pilot-review-receipt.json"]
        review_body = {key: value for key, value in review.items() if key not in {
            "signature_algorithm", "signature_format", "signature_namespace",
            "signed_payload_sha256", "signature_sha256", "signature",
        }}
        self._verify_sshsig(review, review_body)

        inventory = self.files["signed-pilot-evidence-inventory.json"]
        inventory_body_fields = (
            "schema", "pilot_run_id", "pilot_namespace", "source_slice_id", "compute_run_id",
            "source_binding_id", "signed_replay_acceptance_id", "pilot_run_file_sha256",
            "pilot_output_manifest_file_sha256", "pilot_review_receipt_file_sha256",
            "pilot_defect_ledger_file_sha256", "pilot_only", "promotion_eligibility", "canonical_append",
        )
        inventory_body = {field: inventory[field] for field in inventory_body_fields}
        self.assertEqual(inventory["inventory_id"], f"PD.PILOT.EVIDENCE.{logical_sha(inventory_body)[:24]}")
        self._verify_sshsig(inventory, inventory_body)

    def test_operator_dispositions_reconcile_to_defect_ledger(self) -> None:
        review = self.files["pilot-review-receipt.json"]
        defects = self.files["pilot-defect-ledger.json"]
        self.assertEqual(review["status"], "OPERATOR_REVIEW_COMPLETE")
        self.assertEqual(review["decision_count"], 6)
        dispositions = Counter(item["review_disposition"] for item in review["decisions"])
        self.assertEqual(dispositions, Counter({
            "WORKFLOW_ACCEPTED": 1,
            "FLAG_WORKFLOW_DEFECT": 1,
            "FLAG_UI_FRICTION": 1,
            "DEFER_PILOT_OBJECT": 2,
            "REJECT_PILOT_OBJECT": 1,
        }))
        nonaccepted = {
            item["candidate_window_id"]
            for item in review["decisions"]
            if item["review_disposition"] != "WORKFLOW_ACCEPTED" or item["ui_friction_codes"]
        }
        defect_ids = {item["candidate_window_id"] for item in defects["defects"]}
        self.assertEqual(nonaccepted, defect_ids)
        self.assertEqual(defects["defect_count"], 5)
        self.assertTrue(defects["contract_changes_required"])
        self.assertEqual(defects["status"], "REVIEWED_VERSIONED_CORRECTION_REQUIRED")

    def test_gate_is_operator_required_and_defer_recommended(self) -> None:
        gate_input = self.files["pd-g5p-gate-input.json"]
        self.assertTrue(gate_input["operator_approval_required"])
        self.assertTrue(gate_input["contract_changes_required"])
        self.assertEqual(gate_input["identity_reset_before_canonical"], "REQUIRED")
        self.assertEqual(gate_input["status"], "PD_G5P_EVIDENCE_CANDIDATE")

        self.assertEqual(self.gate_packet["gate_status"], "GATE_READY")
        self.assertEqual(self.gate_packet["recommended_decision"], "DEFER")
        self.assertEqual(self.gate_packet["proposed_delta_status"], "NOT_GRANTED")
        self.assertIsNone(self.gate_packet["decision_record"])
        self.assertEqual(self.qa_packet["qa_recommendation"], "DEFER")
        self.assertEqual(self.qa_packet["operational_acceptance_result"], "DEFER_VERSIONED_CORRECTION_REQUIRED")

        self.assertEqual(self.state["gate_status"], "GATE_READY")
        self.assertEqual(self.state["recommended_decision"], "DEFER")
        self.assertTrue(self.state["operator_approval_required"])
        self.assertFalse(self.state["canonical_discovery_available"])
        self.assertIsNone(self.state["decision_record"])

    def test_authority_remains_fail_closed(self) -> None:
        for source in (self.files["pilot-run.json"], self.files["output-manifest.json"], self.files["pd-g5p-gate-input.json"]):
            self.assertTrue(source["pilot_only"])
            self.assertEqual(source["promotion_eligibility"], "NON_PROMOTABLE")
            self.assertEqual(source["canonical_append"], "DENIED")
        self.assertEqual(self.files["pd-g5p-gate-input.json"]["live_prospective_relabelling"], "DENIED")
        self.assertFalse(self.files["pd-g5p-gate-input.json"]["canonical_discovery_population"])
        self.assertFalse(self.pd_wp5_state["canonical_discovery_population"])
        self.assertEqual(self.pd_wp5_state["canonical_append"], "DENIED")
        self.assertEqual(self.pd_wp5_state["next_gate"], "PD-G5P")
        registry = REGISTRY_PATH.read_text(encoding="utf-8")
        self.assertIn("current_authority: PILOT_DISCOVERY_OPERATION_COMPLETE_PD_G5P_DECISION_REQUIRED", registry)
        self.assertIn("status: GATE_READY", registry)
        self.assertIn("canonical_append_enabled: false", registry)
        self.assertIn("future_live_gate_status: DEFERRED_NOT_AUTHORISED", registry)


if __name__ == "__main__":
    unittest.main()
