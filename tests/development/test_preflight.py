from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from ovc.development.artifacts import ArtifactRef
from ovc.development.preflight import DestinationCheck, PreflightRequest, run_preflight
from ovc.development.profiles import parse_profile


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "fixtures/development/preflight"
PROFILE_PATH = FIXTURE_ROOT / "profile_pass_v0_1.json"
REFS_PATH = FIXTURE_ROOT / "refs_pass_v0_1.json"
ZERO = "0" * 64


def load_ref(path: Path = REFS_PATH) -> ArtifactRef:
    row = json.loads(path.read_text(encoding="utf-8"))[0]
    return ArtifactRef(**row)


def snapshot(root: Path) -> dict[str, bytes | None]:
    if not root.exists():
        return {}
    result: dict[str, bytes | None] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        result[rel] = path.read_bytes() if path.is_file() and not path.is_symlink() else None
    return result


def profile_with_inputs(inputs: list[dict[str, object]]):
    return parse_profile({
        "schema": "ovc-artifact-profile/v1",
        "profile_id": "TEST.PREFLIGHT.v0.1",
        "programme_id": "TEST",
        "packet_id": "TEST-WP",
        "authority": {
            "provider_access": "DENIED",
            "release": "DENIED",
            "selector": "DENIED",
            "r2": "DENIED",
            "validation": "DENIED",
            "repository_bot_write": "DENIED",
            "direct_main_write": "DENIED",
            "force_push": "DENIED",
        },
        "inputs": inputs,
        "test_profile": "PACKET",
        "export_profile": None,
    })


class PreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = parse_profile(json.loads(PROFILE_PATH.read_text(encoding="utf-8")))
        self.ref = load_ref()

    def test_pass_is_deterministic_root_independent_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw_a, tempfile.TemporaryDirectory() as raw_b:
            destination_a = Path(raw_a)
            destination_b = Path(raw_b)
            (destination_a / "outputs/empty-packet").mkdir(parents=True)
            (destination_b / "outputs/empty-packet").mkdir(parents=True)
            destinations = (
                DestinationCheck("new-output", "outputs/new-packet", "ABSENT"),
                DestinationCheck("empty-output", "outputs/empty-packet", "ABSENT_OR_EMPTY"),
            )
            request = PreflightRequest(self.profile, (self.ref,), destinations)
            before_input = snapshot(FIXTURE_ROOT)
            before_a = snapshot(destination_a)
            started = time.perf_counter()
            result_a = run_preflight(FIXTURE_ROOT, destination_a, request)
            elapsed = time.perf_counter() - started
            result_b = run_preflight(FIXTURE_ROOT, destination_b, request)
            self.assertEqual(result_a["status"], "PASS")
            self.assertEqual(result_a, result_b)
            self.assertEqual(result_a["preflight_receipt_id"], result_b["preflight_receipt_id"])
            self.assertEqual(before_input, snapshot(FIXTURE_ROOT))
            self.assertEqual(before_a, snapshot(destination_a))
            self.assertLess(elapsed, 30.0)
            self.assertFalse(result_a["authority"]["writes_performed"])
            self.assertEqual(result_a["authority"]["repository_bot_write"], "DENIED")

    def test_missing_required_and_optional_refs_fail_closed(self) -> None:
        required = run_preflight(FIXTURE_ROOT, FIXTURE_ROOT, PreflightRequest(self.profile, ()))
        self.assertEqual(required["status"], "BLOCK")
        self.assertIn("REQUIRED_REF_MISSING", {row["reason"] for row in required["checks"]})

        optional_profile = profile_with_inputs([
            {"logical_name": "compact-input", "relative_path": "input/compact.json", "identity_policy": "EXACT_FILE", "required": True},
            {"logical_name": "optional-input", "relative_path": "input/optional.json", "identity_policy": "EXACT_FILE", "required": False},
        ])
        optional = run_preflight(FIXTURE_ROOT, FIXTURE_ROOT, PreflightRequest(optional_profile, (self.ref,)))
        self.assertEqual(optional["status"], "WARN")
        self.assertIn("OPTIONAL_REF_MISSING", {row["reason"] for row in optional["checks"]})

    def test_exact_bytes_schema_and_profile_mismatches_block(self) -> None:
        wrong_hash = ArtifactRef(
            self.ref.logical_name, self.ref.relative_path, self.ref.size_bytes, ZERO,
            self.ref.schema_id, self.ref.media_type, self.ref.identity_policy,
        )
        result = run_preflight(FIXTURE_ROOT, FIXTURE_ROOT, PreflightRequest(self.profile, (wrong_hash,)))
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("SHA256_MISMATCH", {row["reason"] for row in result["checks"]})

        bad_schema = ArtifactRef(
            self.ref.logical_name, self.ref.relative_path, self.ref.size_bytes, self.ref.sha256,
            "wrong-schema/v1", self.ref.media_type, self.ref.identity_policy,
        )
        result = run_preflight(FIXTURE_ROOT, FIXTURE_ROOT, PreflightRequest(self.profile, (bad_schema,)))
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("SCHEMA_ID_MISMATCH", {row["reason"] for row in result["checks"]})

        wrong_path = ArtifactRef(
            self.ref.logical_name, "input/other.json", self.ref.size_bytes, self.ref.sha256,
            self.ref.schema_id, self.ref.media_type, self.ref.identity_policy,
        )
        result = run_preflight(FIXTURE_ROOT, FIXTURE_ROOT, PreflightRequest(self.profile, (wrong_path,)))
        self.assertIn("PATH_MISMATCH", {row["reason"] for row in result["checks"]})

        undeclared = ArtifactRef("extra", self.ref.relative_path, self.ref.size_bytes, self.ref.sha256)
        result = run_preflight(FIXTURE_ROOT, FIXTURE_ROOT, PreflightRequest(self.profile, (undeclared,)))
        self.assertIn("UNDECLARED_INPUT_REF", {row["reason"] for row in result["checks"]})

    def test_unsupported_identity_policy_blocks(self) -> None:
        profile = profile_with_inputs([
            {"logical_name": "compact-input", "relative_path": "input/compact.json", "identity_policy": "LOGICAL_JSON", "required": True},
        ])
        ref = ArtifactRef(
            self.ref.logical_name, self.ref.relative_path, self.ref.size_bytes, self.ref.sha256,
            self.ref.schema_id, self.ref.media_type, "LOGICAL_JSON",
        )
        result = run_preflight(FIXTURE_ROOT, FIXTURE_ROOT, PreflightRequest(profile, (ref,)))
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("UNSUPPORTED_IDENTITY_POLICY", {row["reason"] for row in result["checks"]})

    def test_destination_collisions_and_invalid_roots_block(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "occupied").mkdir()
            (root / "occupied/value.txt").write_text("occupied", encoding="utf-8")
            result = run_preflight(
                FIXTURE_ROOT,
                root,
                PreflightRequest(self.profile, (self.ref,), (DestinationCheck("out", "occupied"),)),
            )
            self.assertEqual(result["status"], "BLOCK")
            self.assertIn("DESTINATION_COLLISION", {row["reason"] for row in result["checks"]})

            file_path = root / "file-target"
            file_path.write_text("x", encoding="utf-8")
            result = run_preflight(
                FIXTURE_ROOT,
                root,
                PreflightRequest(self.profile, (self.ref,), (DestinationCheck("file", "file-target"),)),
            )
            self.assertIn("DESTINATION_NOT_DIRECTORY", {row["reason"] for row in result["checks"]})

        missing_root = Path(raw) / "missing-after-cleanup"
        result = run_preflight(FIXTURE_ROOT, missing_root, PreflightRequest(self.profile, (self.ref,), (DestinationCheck("out", "x"),)))
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("ROOT_MISSING", {row["reason"] for row in result["checks"]})

    def test_duplicate_request_identities_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PreflightRequest(self.profile, (self.ref, self.ref))
        with self.assertRaises(ValueError):
            PreflightRequest(
                self.profile,
                (self.ref,),
                (DestinationCheck("a", "out"), DestinationCheck("a", "other")),
            )
        with self.assertRaises(ValueError):
            PreflightRequest(
                self.profile,
                (self.ref,),
                (DestinationCheck("a", "out"), DestinationCheck("b", "out")),
            )

    def test_symlink_escape_is_blocked_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as outside_raw:
            root = Path(raw)
            outside = Path(outside_raw)
            payload = b'{"schema":"fixture-compact/v1","ok":true}\n'
            target = outside / "outside.json"
            target.write_bytes(payload)
            (root / "input").mkdir()
            link = root / "input/compact.json"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            ref = ArtifactRef(
                "compact-input", "input/compact.json", len(payload), hashlib.sha256(payload).hexdigest(),
                "fixture-compact/v1", "application/json", "EXACT_FILE",
            )
            result = run_preflight(root, root, PreflightRequest(self.profile, (ref,)))
            self.assertEqual(result["status"], "BLOCK")
            self.assertIn("ARTIFACT_VERIFICATION_ERROR", {row["reason"] for row in result["checks"]})

    def test_cli_pass_and_block_exit_codes(self) -> None:
        script = ROOT / "scripts/development/ovc_preflight.py"
        with tempfile.TemporaryDirectory() as raw:
            destination = Path(raw)
            command = [
                sys.executable, str(script),
                "--profile", str(PROFILE_PATH),
                "--refs", str(REFS_PATH),
                "--input-root", str(FIXTURE_ROOT),
                "--destination-root", str(destination),
            ]
            passed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(passed.returncode, 0, passed.stderr + passed.stdout)
            self.assertEqual(json.loads(passed.stdout)["status"], "PASS")

            bad_refs = destination / "bad-refs.json"
            rows = json.loads(REFS_PATH.read_text(encoding="utf-8"))
            rows[0]["sha256"] = ZERO
            bad_refs.write_text(json.dumps(rows), encoding="utf-8")
            blocked_command = command[:5] + [str(bad_refs)] + command[6:]
            blocked = subprocess.run(blocked_command, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(blocked.returncode, 1, blocked.stderr + blocked.stdout)
            self.assertEqual(json.loads(blocked.stdout)["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
