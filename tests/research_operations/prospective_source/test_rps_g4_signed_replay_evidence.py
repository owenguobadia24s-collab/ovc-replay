from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_ROOT = ROOT / "docs/releases/prospective-source-v0-1/rps-wp4/evidence"
INDEX_PATH = ROOT / "docs/releases/prospective-source-v0-1/rps-wp4/RPS_WP4_COMPACT_SIGNING_EVIDENCE_INDEX.json"
STATE_PATH = ROOT / "registries/research_operations/prospective_source/RPS_G4_GATE_STATE_v0_1.json"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RpsG4SignedReplayEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.binding = json.loads((EVIDENCE_ROOT / "operator-signing-binding.json").read_text(encoding="utf-8"))
        cls.acceptance = json.loads((EVIDENCE_ROOT / "time-gated-replay-acceptance.json").read_text(encoding="utf-8"))
        cls.receipt = json.loads((EVIDENCE_ROOT / "signature-verification-receipt.json").read_text(encoding="utf-8"))
        cls.gate = json.loads((EVIDENCE_ROOT / "rps-g4-operator-gate-input.json").read_text(encoding="utf-8"))
        cls.index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE_PATH.read_text(encoding="utf-8"))

    def test_compact_file_byte_inventory_is_exact(self) -> None:
        for item in self.index["compact_files"]:
            path = ROOT / item["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(path.stat().st_size, item["size_bytes"])
            self.assertEqual(file_sha256(path), item["sha256"])
        self.assertEqual(
            self.gate["operator_signing_binding_file_sha256"],
            file_sha256(EVIDENCE_ROOT / "operator-signing-binding.json"),
        )
        self.assertEqual(
            self.gate["time_gated_replay_acceptance_file_sha256"],
            file_sha256(EVIDENCE_ROOT / "time-gated-replay-acceptance.json"),
        )
        self.assertEqual(
            self.gate["signature_verification_receipt_file_sha256"],
            file_sha256(EVIDENCE_ROOT / "signature-verification-receipt.json"),
        )

    def test_signing_binding_identity_and_public_key_reproduce(self) -> None:
        identity = {
            "operator_id": self.binding["operator_id"],
            "algorithm": self.binding["algorithm"],
            "signature_format": self.binding["signature_format"],
            "signature_namespace": self.binding["signature_namespace"],
            "public_key_sha256": self.binding["public_key_sha256"],
            "public_key_fingerprint": self.binding["public_key_fingerprint"],
            "run_id": self.binding["run_id"],
            "binding_id": self.binding["binding_id"],
        }
        self.assertEqual(
            self.binding["signing_binding_id"],
            f"RPS.SIGNING.{canonical_sha256(identity)[:24]}",
        )
        key_parts = self.binding["public_key"].split()
        self.assertEqual(key_parts[0], "ssh-ed25519")
        key_blob = base64.b64decode(key_parts[1])
        fingerprint = base64.b64encode(hashlib.sha256(key_blob).digest()).decode("ascii").rstrip("=")
        self.assertEqual(
            self.binding["public_key_fingerprint"],
            f"SHA256:{fingerprint}",
        )
        public_file = f'{self.binding["public_key"]} {self.binding["operator_id"]}\n'.encode("utf-8")
        self.assertEqual(
            self.binding["public_key_sha256"],
            hashlib.sha256(public_file).hexdigest(),
        )

    def test_acceptance_and_signed_payload_identities_reproduce(self) -> None:
        signature_fields = {
            "signature_algorithm",
            "signature_format",
            "signature_namespace",
            "signed_payload_sha256",
            "signature_sha256",
            "signature",
            "status",
        }
        signed_payload = {
            key: value
            for key, value in self.acceptance.items()
            if key not in signature_fields
        }
        body = dict(signed_payload)
        acceptance_id = body.pop("acceptance_id")
        self.assertEqual(
            acceptance_id,
            f"RPS.REPLAY-ACCEPT.{canonical_sha256(body)[:24]}",
        )
        self.assertEqual(
            self.acceptance["signed_payload_sha256"],
            canonical_sha256(signed_payload),
        )
        self.assertEqual(
            self.acceptance["signature_sha256"],
            hashlib.sha256(self.acceptance["signature"].encode("utf-8")).hexdigest(),
        )
        self.assertEqual(self.receipt["signed_payload_sha256"], self.acceptance["signed_payload_sha256"])
        self.assertEqual(self.receipt["signature_sha256"], self.acceptance["signature_sha256"])
        self.assertTrue(self.receipt["signature_verified"])

    @unittest.skipUnless(shutil.which("ssh-keygen"), "OpenSSH ssh-keygen unavailable")
    def test_ed25519_sshsig_verifies_independently(self) -> None:
        signature_fields = {
            "signature_algorithm",
            "signature_format",
            "signature_namespace",
            "signed_payload_sha256",
            "signature_sha256",
            "signature",
            "status",
        }
        signed_payload = {
            key: value
            for key, value in self.acceptance.items()
            if key not in signature_fields
        }
        with tempfile.TemporaryDirectory(prefix="rps-g4-verify-") as temporary:
            root = Path(temporary)
            signature_path = root / "acceptance.sig"
            allowed_path = root / "allowed_signers"
            signature_path.write_text(self.acceptance["signature"], encoding="utf-8")
            allowed_path.write_text(
                f'{self.binding["operator_id"]} namespaces="ovc-rps" {self.binding["public_key"]}\n',
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    shutil.which("ssh-keygen") or "ssh-keygen",
                    "-Y",
                    "verify",
                    "-f",
                    str(allowed_path),
                    "-I",
                    self.binding["operator_id"],
                    "-n",
                    "ovc-rps",
                    "-s",
                    str(signature_path),
                ],
                input=canonical_bytes(signed_payload),
                capture_output=True,
            )
            self.assertEqual(
                result.returncode,
                0,
                result.stderr.decode("utf-8", errors="replace"),
            )

    def test_exact_source_compute_and_authority_bindings_close(self) -> None:
        expected = {
            "source_slice_id": "RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1",
            "run_id": "RPS.RUN.7aeb551335d766ee3bf503e6",
            "binding_id": "RPS.BINDING.32fb3003efa072916c11e907",
            "operator_id": "OVC.OPERATOR.PRIMARY.LOCAL.V1",
            "signing_binding_id": "RPS.SIGNING.50092c28981fef08f53a6cb5",
            "acceptance_id": "RPS.REPLAY-ACCEPT.0844eddf74e144ced487cc48",
        }
        for key in ("source_slice_id", "run_id", "binding_id", "acceptance_id"):
            self.assertEqual(self.index[key], expected[key])
        self.assertEqual(self.index["operator"]["operator_id"], expected["operator_id"])
        self.assertEqual(
            self.index["operator"]["signing_binding_id"],
            expected["signing_binding_id"],
        )
        for key, value in expected.items():
            self.assertEqual(self.gate[key], value)
        for key in ("source_slice_id", "run_id", "binding_id", "operator_id", "signing_binding_id"):
            self.assertEqual(self.binding[key], expected[key])
        for key in expected:
            if key in self.acceptance:
                self.assertEqual(self.acceptance[key], expected[key])
        self.assertEqual(self.acceptance["operation_mode"], "TIME_GATED_REPLAY")
        self.assertEqual(self.acceptance["coverage_state"], "GAPPED")
        self.assertEqual(self.acceptance["payload_file_count"], 21)
        self.assertEqual(self.acceptance["payload_bytes"], 5_557_327)
        self.assertTrue(self.acceptance["deterministic_replay"])
        self.assertTrue(self.acceptance["lineage_complete"])

    def test_gate_is_operator_required_and_non_activating(self) -> None:
        self.assertEqual(self.gate["gate_id"], "RPS-G4")
        self.assertTrue(self.gate["operator_approval_required"])
        self.assertEqual(
            self.gate["proposed_delta"],
            "ACTIVATE_EXACT_BINDING_FOR_ACTIVE_RESEARCH_TRIAGE_AND_ENABLE_PD_WP5_FIRST_LIVE_PROSPECTIVE_OPERATION",
        )
        self.assertIsNone(self.gate["active_binding_id"])
        self.assertFalse(self.gate["active_research_triage"])
        self.assertFalse(self.gate["write_authority"])
        self.assertEqual(self.gate["live_prospective_append"], "DENIED")
        for record in (self.binding, self.acceptance, self.receipt):
            self.assertFalse(record["active_research_triage"])
            self.assertFalse(record["write_authority"])
        self.assertFalse(self.binding["private_key_in_git"])
        self.assertFalse(self.receipt["private_key_in_git"])
        self.assertFalse(self.receipt["private_key_material_in_receipt"])
        self.assertEqual(self.acceptance["release_status"], "NOT_A_RELEASE")
        self.assertEqual(self.acceptance["selector_eligibility"], "NONE")
        self.assertEqual(self.acceptance["r2_publication"], "DENIED")
        self.assertEqual(self.acceptance["validation_consumption"], "DENIED")
        self.assertEqual(self.acceptance["live_prospective_append"], "DENIED")
        for field in (
            "probability_authority",
            "exposure_authority",
            "trading_authority",
            "execution_authority",
            "agent_write_authority",
        ):
            self.assertEqual(self.acceptance[field], "NONE")

    def test_programme_state_stops_at_operator_gate(self) -> None:
        self.assertEqual(self.state["packet_id"], "RPS-WP4")
        self.assertEqual(self.state["packet_status"], "GATE_READY")
        self.assertEqual(self.state["gate_id"], "RPS-G4")
        self.assertEqual(self.state["gate_status"], "GATE_READY")
        self.assertTrue(self.state["operator_approval_required"])
        self.assertIsNone(self.state["active_binding_id"])
        self.assertFalse(self.state["active_research_triage"])
        self.assertFalse(self.state["write_authority"])
        self.assertEqual(self.state["live_prospective_append"], "DENIED")
        self.assertEqual(self.state["next_action"], "OVC APPROVE RPS-G4")


if __name__ == "__main__":
    unittest.main()
