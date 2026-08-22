from __future__ import annotations

import base64
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

from ovc.development.skills.vit_routing import build_vit_payload_lineage_record
from tools.ci.vit_lineage_source import resolve_candidate_lineage
from tools.ci.vit_qualification_store import (
    LEDGER_ROOT,
    POINTER_SCHEMA,
    build_qualification_envelope,
    validate_qualification_envelope,
)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def legacy_marker(record: dict) -> str:
    return "VIT-Lineage-B64: " + base64.urlsafe_b64encode(canonical(record)).decode("ascii").rstrip("=")


class DetachedQualificationTests(unittest.TestCase):
    def _fixture(self) -> tuple[TemporaryDirectory, Path, str, dict, dict, dict[str, bytes]]:
        tmp = TemporaryDirectory()
        root = Path(tmp.name)
        git(root, "init", "-q")
        git(root, "config", "user.email", "vit@example.invalid")
        git(root, "config", "user.name", "VIT Test")
        (root / "base.txt").write_text("base\n", encoding="utf-8")
        git(root, "add", "base.txt")
        git(root, "commit", "-qm", "base")
        (root / "payload.txt").write_text("payload\n", encoding="utf-8")
        git(root, "add", "payload.txt")
        git(root, "commit", "-qm", "payload")
        head = git(root, "rev-parse", "HEAD")
        blob = git(root, "rev-parse", "HEAD:payload.txt")
        pip = {
            "schema_version": "packet-integration-payload/v0.1",
            "programme_id": "PROGRAMME",
            "packet_id": "PACKET",
            "logical_changes": [
                {"op": "ADD", "path": "payload.txt", "blob_sha": blob, "mode": "100644"}
            ],
            "authority_manifest_id": "2" * 64,
            "dependency_frontier_id": "3" * 64,
            "completion_transition": {"status": "COMPLETED"},
        }
        record = build_vit_payload_lineage_record(
            programme_id="PROGRAMME",
            packet_id="PACKET",
            pip_identity_payload=pip,
        )
        envelope = dict(build_qualification_envelope(root=root, head_sha=head, lineage_record=record))
        qid = envelope["qualification_id"]
        pointer = {
            "schema_version": POINTER_SCHEMA,
            "candidate_head_sha": head,
            "qualification_id": qid,
        }
        files = {
            f"{LEDGER_ROOT}/heads/{head}.json": canonical(pointer),
            f"{LEDGER_ROOT}/envelopes/{qid}.json": canonical(envelope),
        }
        return tmp, root, head, record, envelope, files

    def test_exact_head_resolves_detached_envelope_without_pr_metadata(self) -> None:
        tmp, root, head, record, envelope, files = self._fixture()
        self.addCleanup(tmp.cleanup)
        source = resolve_candidate_lineage(
            root=root,
            head_sha=head,
            body="Human review text only; no VIT marker.",
            fetch_qualification_file=lambda path: files.get(path),
        )
        assert source is not None
        self.assertEqual(source.source, "DETACHED_QUALIFICATION_LEDGER")
        self.assertEqual(source.immutable_ref, envelope["qualification_id"])
        self.assertEqual(source.record, record)

    def test_conflicting_pr_body_cannot_override_detached_qualification(self) -> None:
        tmp, root, head, record, envelope, files = self._fixture()
        self.addCleanup(tmp.cleanup)
        other = build_vit_payload_lineage_record(
            programme_id="OTHER",
            packet_id="OTHER",
            pip_identity_payload={
                "schema_version": "packet-integration-payload/v0.1",
                "programme_id": "OTHER",
                "packet_id": "OTHER",
                "logical_changes": [{"op": "ADD", "path": "fake", "blob_sha": "1" * 40, "mode": "100644"}],
                "authority_manifest_id": "4" * 64,
                "dependency_frontier_id": "5" * 64,
                "completion_transition": {"status": "COMPLETED"},
            },
        )
        source = resolve_candidate_lineage(
            root=root,
            head_sha=head,
            body=legacy_marker(other),
            fetch_qualification_file=lambda path: files.get(path),
        )
        assert source is not None
        self.assertEqual(source.record, record)
        self.assertEqual(source.immutable_ref, envelope["qualification_id"])

    def test_pr_body_lineage_is_not_decision_bearing_without_explicit_legacy_mode(self) -> None:
        tmp, root, head, record, _, _ = self._fixture()
        self.addCleanup(tmp.cleanup)
        with self.assertRaisesRegex(RuntimeError, "VIT_QUALIFICATION_REQUIRED"):
            resolve_candidate_lineage(
                root=root,
                head_sha=head,
                body=legacy_marker(record),
                fetch_qualification_file=lambda _: None,
            )
        source = resolve_candidate_lineage(
            root=root,
            head_sha=head,
            body=legacy_marker(record),
            allow_legacy_pr_body=True,
            fetch_qualification_file=lambda _: None,
        )
        assert source is not None
        self.assertEqual(source.source, "LEGACY_INLINE_B64")

    def test_envelope_is_content_addressed_and_bound_to_exact_head_tree(self) -> None:
        tmp, root, head, _, envelope, _ = self._fixture()
        self.addCleanup(tmp.cleanup)
        resolved = validate_qualification_envelope(envelope, expected_head_sha=head)
        self.assertEqual(resolved.qualification_id, envelope["qualification_id"])
        tampered = json.loads(json.dumps(envelope))
        tampered["authority_manifest_id"] = "9" * 64
        with self.assertRaisesRegex(RuntimeError, "VIT_QUALIFICATION_ID_MISMATCH"):
            validate_qualification_envelope(tampered, expected_head_sha=head)

    def test_same_head_can_point_to_new_immutable_qualification_without_git_mutation(self) -> None:
        tmp, root, head, record, first, files = self._fixture()
        self.addCleanup(tmp.cleanup)
        modified = json.loads(json.dumps(record))
        modified["pip"]["completion_transition"] = {"status": "QA_REVIEW"}
        modified = build_vit_payload_lineage_record(
            programme_id="PROGRAMME",
            packet_id="PACKET",
            pip_identity_payload=modified["pip"],
        )
        second = dict(build_qualification_envelope(root=root, head_sha=head, lineage_record=modified))
        self.assertNotEqual(first["qualification_id"], second["qualification_id"])
        self.assertEqual(first["candidate_head_sha"], second["candidate_head_sha"])
        self.assertEqual(first["candidate_head_tree"], second["candidate_head_tree"])

        pointer = {
            "schema_version": POINTER_SCHEMA,
            "candidate_head_sha": head,
            "qualification_id": second["qualification_id"],
        }
        files[f"{LEDGER_ROOT}/heads/{head}.json"] = canonical(pointer)
        files[f"{LEDGER_ROOT}/envelopes/{second['qualification_id']}.json"] = canonical(second)
        source = resolve_candidate_lineage(
            root=root,
            head_sha=head,
            body="",
            fetch_qualification_file=lambda path: files.get(path),
        )
        assert source is not None
        self.assertEqual(source.immutable_ref, second["qualification_id"])
        self.assertEqual(source.record, modified)


if __name__ == "__main__":
    unittest.main()
