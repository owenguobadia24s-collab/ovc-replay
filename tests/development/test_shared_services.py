from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from ovc.development.artifacts import ArtifactRef, verify_artifact
from ovc.development.decisions import DecisionRecord
from ovc.development.gates import GatePacket
from ovc.development.identity import IdentityError, canonical_json_bytes, canonical_sha256, normalize_relative_path
from ovc.development.profiles import ProfileError, load_profile
from ovc.development.qa import QAAssertion, aggregate_assertions
from ovc.development.rollback import RollbackRecord


ROOT = Path(__file__).resolve().parents[2]
ZERO = "0" * 64
ONE = "1" * 64
TWO = "2" * 64


class IdentityTests(unittest.TestCase):
    def test_canonical_order_and_role_binding(self) -> None:
        self.assertEqual(canonical_json_bytes({"b": 2, "a": 1}), b'{"a":1,"b":2}')
        self.assertEqual(canonical_sha256({"a": 1}), canonical_sha256({"a": 1}))
        self.assertNotEqual(canonical_sha256({"a": 1}, role="A"), canonical_sha256({"a": 1}, role="B"))

    def test_path_safety(self) -> None:
        self.assertEqual(normalize_relative_path("docs\\x.json"), "docs/x.json")
        for value in ("../x", "/tmp/x", "C:\\tmp\\x", ".git/config", "x/../y", ""):
            with self.assertRaises(IdentityError, msg=value):
                normalize_relative_path(value)


class ProfileTests(unittest.TestCase):
    def test_pass_fixture_is_deterministic(self) -> None:
        profile = load_profile(ROOT / "fixtures/development/artifact_profile_pass_v0_1.json")
        self.assertEqual(profile.packet_id, "FIXTURE-WP1")
        self.assertEqual(profile.authority["repository_bot_write"], "DENIED")
        self.assertEqual(profile.profile_hash, load_profile(ROOT / "fixtures/development/artifact_profile_pass_v0_1.json").profile_hash)

    def test_block_fixture_is_rejected(self) -> None:
        with self.assertRaises(ProfileError):
            load_profile(ROOT / "fixtures/development/artifact_profile_block_v0_1.json")


class ArtifactTests(unittest.TestCase):
    def test_exact_artifact_and_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = root / "compact.json"
            payload = b'{"ok":true}\n'
            path.write_bytes(payload)
            ref = ArtifactRef("compact", "compact.json", len(payload), hashlib.sha256(payload).hexdigest(), "example/v1", "application/json")
            self.assertEqual(verify_artifact(root, ref)["status"], "PASS")
            bad = ArtifactRef("compact", "compact.json", len(payload), ZERO)
            self.assertEqual(verify_artifact(root, bad)["reason"], "SHA256_MISMATCH")


class AssuranceTests(unittest.TestCase):
    def assertion(self, status: str, check_id: str) -> QAAssertion:
        return QAAssertion(check_id, "fixture", status, "BLOCKING", ("fixture",), "2026-08-01T00:00:00Z", ZERO, ONE, TWO)

    def test_qa_precedence_and_empty_fail_closed(self) -> None:
        self.assertEqual(aggregate_assertions([])["status"], "NOT_EVALUABLE")
        result = aggregate_assertions([self.assertion("PASS", "B"), self.assertion("WARN", "A"), self.assertion("BLOCK", "C")])
        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(result["blocking"])
        self.assertEqual([row["check_id"] for row in result["assertions"]], ["A", "B", "C"])

    def test_gate_decision_and_rollback_identity(self) -> None:
        gate = GatePacket(
            gate_id="DA-G1", plan_id="P", plan_version="1", programme_id="X", packet_id="WP1",
            baseline_commit="a", candidate_commit="b", authority_delta="LOCAL_COMPUTE",
            acceptance_conditions=("deterministic",), tests=("unit",), qa_status="PASS",
            warnings=(), unresolved_issues=(), changed_files=("src/ovc/development/identity.py",),
            rollback="revert", recommended_decision="PASS", next_packet="WP2",
        )
        self.assertEqual(gate.gate_packet_id, GatePacket(**{key: value for key, value in gate.__dict__.items()}).gate_packet_id)
        decision = DecisionRecord("PASS", "DELEGATED", "P", "1", "X", "WP1", "DA-G1", "a", "b", ("unit",), "PASS", "LOCAL_COMPUTE", "NONE", "revert", "all checks pass", "WP2")
        self.assertEqual(len(decision.decision_id), 64)
        rollback = RollbackRecord("X", "WP1", "b", "REVERT_COMMIT", ("docs/releases/x.json",), ("DELETE_HISTORY", "FORCE_PUSH", "REWRITE_ACCEPTED_ARTIFACT"), "preserve evidence")
        self.assertEqual(len(rollback.rollback_id), 64)


class SchemaTests(unittest.TestCase):
    def test_all_development_schemas_are_closed_draft_2020_objects(self) -> None:
        paths = sorted((ROOT / "schemas/development").glob("*.schema.json"))
        self.assertGreaterEqual(len(paths), 6)
        for path in paths:
            obj = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(obj["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(obj["type"], "object")
            self.assertFalse(obj["additionalProperties"], path)


if __name__ == "__main__":
    unittest.main()
