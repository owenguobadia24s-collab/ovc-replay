from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ovc.development.skills.vit_apply import REFERENCE_APPLY_PROFILE
from ovc.development.skills.vit_routing import (
    build_vit_lineage_record,
    build_vit_payload_lineage_record,
)
from tools.ci.vit_qualification_store import (
    build_qualification_envelope,
    validate_qualification_envelope,
)
from tools.ci.vit_routing_preflight import check_pull_request_event


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def b64_lineage(record: dict) -> str:
    raw = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def pip(blob_sha: str) -> dict:
    return {
        "schema_version": "packet-integration-payload/v0.1",
        "programme_id": "PROGRAMME",
        "packet_id": "PACKET",
        "logical_changes": [{"op": "ADD", "path": "payload.txt", "blob_sha": blob_sha, "mode": "100644"}],
        "authority_manifest_id": "2" * 64,
        "dependency_frontier_id": "3" * 64,
        "completion_transition": {"status": "COMPLETED"},
    }


class Dsai3vVitLiveBasePreflightTests(unittest.TestCase):
    def _repo(self):
        td = TemporaryDirectory()
        root = Path(td.name) / "work"
        remote = Path(td.name) / "remote.git"
        root.mkdir()
        git(root, "init", "-q")
        git(root, "config", "user.email", "vit@example.invalid")
        git(root, "config", "user.name", "VIT Test")
        (root / "base.txt").write_text("base-1\n", encoding="utf-8")
        git(root, "add", "base.txt")
        git(root, "commit", "-qm", "base-1")
        git(root, "branch", "-M", "main")
        event_base_sha = git(root, "rev-parse", "HEAD")
        event_base_tree = git(root, "rev-parse", "HEAD^{tree}")
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        git(root, "remote", "add", "origin", str(remote))
        git(root, "push", "-q", "-u", "origin", "main")
        (root / "base.txt").write_text("base-2\n", encoding="utf-8")
        git(root, "add", "base.txt")
        git(root, "commit", "-qm", "base-2")
        git(root, "push", "-q", "origin", "main")
        git(root, "checkout", "-qb", "feature")
        (root / "payload.txt").write_text("payload\n", encoding="utf-8")
        git(root, "add", "payload.txt")
        git(root, "commit", "-qm", "payload")
        head_sha = git(root, "rev-parse", "HEAD")
        head_tree = git(root, "rev-parse", "HEAD^{tree}")
        blob_sha = git(root, "rev-parse", "HEAD:payload.txt")
        register = root / "registries/development/skills/VIT_ROUTING_COVERAGE_REGISTER_v0_1.json"
        register.parent.mkdir(parents=True)
        register.write_text(json.dumps({"unregistered_bypass_policy": "FAIL_CLOSED", "registered_pr_exceptions": []}), encoding="utf-8")
        return td, root, event_base_sha, event_base_tree, head_sha, head_tree, blob_sha

    def test_payload_only_lineage_does_not_bind_to_live_main(self) -> None:
        td, root, event_base_sha, _, head_sha, _, blob_sha = self._repo()
        with td:
            record = build_vit_payload_lineage_record(
                programme_id="PROGRAMME",
                packet_id="PACKET",
                pip_identity_payload=pip(blob_sha),
            )
            qualification = validate_qualification_envelope(
                build_qualification_envelope(root=root, head_sha=head_sha, lineage_record=record),
                expected_head_sha=head_sha,
            )
            event = {
                "number": 1,
                "pull_request": {
                    "body": "Human-only PR description; decision-bearing qualification is detached.",
                    "head": {"sha": head_sha, "ref": "feature"},
                    "base": {"sha": event_base_sha, "ref": "main"},
                },
            }
            with (
                patch(
                    "tools.ci.vit_lineage_source.resolve_qualification_envelope",
                    return_value=qualification,
                ),
                patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}, clear=False),
            ):
                result = check_pull_request_event(root=root, event=event)
            self.assertIn("VIT_MANDATORY_LATE_BINDING", result)
            self.assertIn("NO_PHYSICAL_BASE_BINDING", result)
            self.assertIn("DETACHED_QUALIFICATION_LEDGER", result)

    def test_legacy_stale_placement_is_provenance_not_blocking_order(self) -> None:
        td, root, event_base_sha, event_base_tree, head_sha, head_tree, blob_sha = self._repo()
        with td:
            stale = build_vit_lineage_record(
                programme_id="PROGRAMME",
                packet_id="PACKET",
                pip_identity_payload=pip(blob_sha),
                train_generation_id="TRAIN-1",
                ordinal=1,
                predecessor_tree_sha=event_base_tree,
                result_tree_sha=head_tree,
                apply_profile=REFERENCE_APPLY_PROFILE,
            )
            event = {
                "number": 2,
                "pull_request": {
                    "body": f"VIT-Lineage-B64: {b64_lineage(stale)}",
                    "head": {"sha": head_sha, "ref": "feature"},
                    "base": {"sha": event_base_sha, "ref": "main"},
                },
            }
            with (
                patch("tools.ci.vit_lineage_source.resolve_qualification_envelope", return_value=None),
                patch.dict(
                    os.environ,
                    {
                        "GITHUB_ACTIONS": "false",
                        "OVC_VIT_ALLOW_LEGACY_PR_BODY_LINEAGE": "true",
                    },
                    clear=False,
                ),
            ):
                result = check_pull_request_event(root=root, event=event)
            self.assertIn("VIT_MANDATORY_LEGACY_PAYLOAD_ACCEPTED", result)
            self.assertIn("PLACEMENT_NON_AUTHORITATIVE", result)
            self.assertIn("LEGACY_INLINE_B64", result)


if __name__ == "__main__":
    unittest.main()
