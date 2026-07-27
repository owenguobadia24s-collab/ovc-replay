from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from ovc.research_operations.prospective_source import operator_replay_acceptance as subject


class RpsWp4OperatorReplayAcceptanceTests(unittest.TestCase):
    def test_operator_identity_is_explicit_and_portable(self) -> None:
        operator_id = subject.validate_operator_id("ovc.operator.primary.local.v1")
        self.assertEqual(operator_id, "OVC.OPERATOR.PRIMARY.LOCAL.V1")
        self.assertEqual(
            subject.operator_slug(operator_id),
            "ovc-operator-primary-local-v1",
        )
        with self.assertRaisesRegex(subject.ReplayAcceptanceError, "operator ID"):
            subject.validate_operator_id("owner@example.com")

    def test_governed_constants_pin_rps_g3_evidence(self) -> None:
        self.assertEqual(subject.AUTHORITY_GATE, "RPS-G3")
        self.assertEqual(subject.RUN_ID, "RPS.RUN.7aeb551335d766ee3bf503e6")
        self.assertEqual(
            subject.BINDING_ID,
            "RPS.BINDING.32fb3003efa072916c11e907",
        )
        self.assertEqual(subject.OPERATION_MODE, "TIME_GATED_REPLAY")
        self.assertEqual(subject.ALGORITHM, "ED25519")
        self.assertEqual(subject.SIGNATURE_FORMAT, "SSHSIG_OPENSSH_V1")
        self.assertEqual(subject.SIGNATURE_NAMESPACE, "ovc-rps")

    def test_key_setup_and_acceptance_are_denied_in_ci(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(subject.ReplayAcceptanceError, "prohibited in CI"):
                subject.setup_key(
                    root,
                    operator_id="OVC.OPERATOR.PRIMARY.LOCAL.v1",
                    authority_gate="RPS-G3",
                    environ={"CI": "true"},
                )
            with self.assertRaisesRegex(subject.ReplayAcceptanceError, "prohibited in CI"):
                subject.accept_replay(
                    root,
                    operator_id="OVC.OPERATOR.PRIMARY.LOCAL.v1",
                    authority_gate="RPS-G3",
                    confirm_private_key_protected=True,
                    environ={"GITHUB_ACTIONS": "true"},
                )

    def test_exact_gate_and_private_key_confirmation_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(subject.ReplayAcceptanceError, "exact delegated authority"):
                subject.setup_key(
                    root,
                    operator_id="OVC.OPERATOR.PRIMARY.LOCAL.v1",
                    authority_gate="WRONG",
                    environ={},
                )
            with self.assertRaisesRegex(subject.ReplayAcceptanceError, "protection confirmation"):
                subject.accept_replay(
                    root,
                    operator_id="OVC.OPERATOR.PRIMARY.LOCAL.v1",
                    authority_gate="RPS-G3",
                    confirm_private_key_protected=False,
                    environ={},
                )

    @unittest.skipUnless(shutil.which("ssh-keygen"), "OpenSSH ssh-keygen unavailable")
    def test_openssh_ed25519_signature_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            private = root / "id_ed25519"
            subprocess.run(
                [
                    shutil.which("ssh-keygen") or "ssh-keygen",
                    "-q",
                    "-t",
                    "ed25519",
                    "-N",
                    "",
                    "-C",
                    "OVC.OPERATOR.TEST.LOCAL.v1",
                    "-f",
                    str(private),
                ],
                check=True,
                capture_output=True,
            )
            public_line = private.with_suffix(".pub").read_text(encoding="utf-8").split()
            payload = subject.canonical_bytes(
                {
                    "binding_id": subject.BINDING_ID,
                    "operation_mode": subject.OPERATION_MODE,
                    "run_id": subject.RUN_ID,
                }
            )
            signature, signature_sha = subject.sign_and_verify(
                private_key=private,
                public_key=" ".join(public_line[:2]),
                operator_id="OVC.OPERATOR.TEST.LOCAL.V1",
                payload=payload,
            )
            self.assertIn("BEGIN SSH SIGNATURE", signature)
            self.assertEqual(len(signature_sha), 64)

    def test_acceptance_output_never_activates_triage_or_write(self) -> None:
        operator_id = "OVC.OPERATOR.TEST.LOCAL.V1"
        with tempfile.TemporaryDirectory() as temporary:
            repository_root = Path(temporary) / "repo"
            external_root = Path(temporary) / "external"
            repository_root.mkdir()
            private = external_root / "prospective-source/operator-signing/ovc-operator-test-local-v1/id_ed25519"
            private.parent.mkdir(parents=True)
            private.write_text("private-placeholder", encoding="utf-8")
            private.with_suffix(".pub").write_text(
                "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest OVC.OPERATOR.TEST.LOCAL.V1\n",
                encoding="utf-8",
            )
            manifest = {
                "file_count": 21,
                "operation_mode": subject.OPERATION_MODE,
            }
            run = {
                "code_commit": "2fbcc114d55858c95fbfefe743fb98ba5800560b",
                "admissible_cutoff_utc": "2026-06-25T00:00:00Z",
            }
            binding = {
                "eligible_data_through_utc": "2026-06-25T00:00:00Z",
                "source_coverage_state": "GAPPED",
            }
            key = {
                "operator_id": operator_id,
                "algorithm": "ED25519",
                "signature_format": "SSHSIG_OPENSSH_V1",
                "signature_namespace": "ovc-rps",
                "public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest",
                "public_key_sha256": "a" * 64,
                "public_key_fingerprint": "SHA256:test",
                "private_key_in_git": False,
                "private_key_alias": "OVC_EXTERNAL_ARTIFACT_ROOT/prospective-source/operator-signing/test/id_ed25519",
            }
            with (
                patch.object(subject, "repository_state", return_value=("main", "f" * 40)),
                patch.object(subject, "verify_compute_run", return_value=(external_root, manifest, run, binding, {})),
                patch.object(subject, "key_paths", return_value=(private, private.with_suffix(".pub"))),
                patch.object(subject, "public_key_details", return_value=key),
                patch.object(subject, "sign_and_verify", return_value=("signature", "b" * 64)),
                patch.object(subject, "external_root", return_value=external_root),
            ):
                result = subject.accept_replay(
                    repository_root,
                    operator_id=operator_id,
                    authority_gate="RPS-G3",
                    confirm_private_key_protected=True,
                    environ={},
                )
            self.assertEqual(
                result["status"],
                "COMPLETE_LOCAL_SIGNING_AND_REPLAY_ACCEPTANCE_CANDIDATE",
            )
            self.assertFalse(result["active_research_triage"])
            self.assertFalse(result["write_authority"])
            self.assertEqual(result["live_prospective_append"], "DENIED")
            output_root = external_root / "prospective-source/replay-acceptance"
            acceptance_dirs = [path for path in output_root.iterdir() if path.is_dir() and not path.name.startswith(".")]
            self.assertEqual(len(acceptance_dirs), 1)
            gate = json.loads(
                (acceptance_dirs[0] / "rps-g4-operator-gate-input.json").read_text(encoding="utf-8")
            )
            self.assertTrue(gate["operator_approval_required"])
            self.assertIsNone(gate["active_binding_id"])
            self.assertFalse(gate["active_research_triage"])
            self.assertFalse(gate["write_authority"])
            self.assertEqual(gate["live_prospective_append"], "DENIED")


if __name__ == "__main__":
    unittest.main()
