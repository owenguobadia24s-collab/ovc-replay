from __future__ import annotations

import base64
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

from ovc.development.skills.vit_apply import REFERENCE_APPLY_PROFILE
from ovc.development.skills.vit_routing import build_vit_lineage_record
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


def lineage_record(*, predecessor: str, result: str, blob_sha: str, dependency_paths=()) -> dict:
    pip = {
        "schema_version": "packet-integration-payload/v0.1",
        "programme_id": "PROGRAMME",
        "packet_id": "PACKET",
        "logical_changes": [
            {"op": "ADD", "path": "payload.txt", "blob_sha": blob_sha, "mode": "100644"}
        ],
        "authority_manifest_id": "2" * 64,
        "dependency_frontier_id": "3" * 64,
        "completion_transition": {"status": "COMPLETED"},
        "dependency_footprint": {
            "dependency_paths": list(dependency_paths),
            "semantic_authority_paths": ["registries/authority/**"],
            "identity_binding_paths": ["schemas/owned/**"],
        },
    }
    return build_vit_lineage_record(
        programme_id="PROGRAMME",
        packet_id="PACKET",
        pip_identity_payload=pip,
        train_generation_id="TRAIN-1",
        ordinal=1,
        predecessor_tree_sha=predecessor,
        result_tree_sha=result,
        apply_profile=REFERENCE_APPLY_PROFILE,
    )


def prepare(tmp: str):
    root = Path(tmp) / "work"
    remote = Path(tmp) / "remote.git"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "vit@example.invalid")
    git(root, "config", "user.name", "VIT Test")
    (root / "base.txt").write_text("base-1\n", encoding="utf-8")
    git(root, "add", "base.txt")
    git(root, "commit", "-qm", "base-1")
    source_base_sha = git(root, "rev-parse", "HEAD")
    source_base_tree = git(root, "rev-parse", "HEAD^{tree}")
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    git(root, "remote", "add", "origin", str(remote))
    git(root, "push", "-q", "-u", "origin", "main")

    git(root, "checkout", "-qb", "feature")
    (root / "payload.txt").write_text("payload\n", encoding="utf-8")
    git(root, "add", "payload.txt")
    git(root, "commit", "-qm", "payload")
    head_sha = git(root, "rev-parse", "HEAD")
    head_tree = git(root, "rev-parse", "HEAD^{tree}")
    blob_sha = git(root, "rev-parse", "HEAD:payload.txt")

    git(root, "checkout", "-q", "main")
    register = root / "registries/development/skills/VIT_ROUTING_COVERAGE_REGISTER_v0_1.json"
    register.parent.mkdir(parents=True)
    register.write_text(
        json.dumps({"unregistered_bypass_policy": "FAIL_CLOSED", "registered_pr_exceptions": []}),
        encoding="utf-8",
    )
    # The register is a fixture for the checker, not a main movement in this test.
    return root, source_base_sha, source_base_tree, head_sha, head_tree, blob_sha


class Dsai3vVitLiveBasePreflightTests(unittest.TestCase):
    def test_unrelated_live_main_movement_recomposes_same_pr_and_pip(self) -> None:
        with TemporaryDirectory() as tmp:
            root, event_base_sha, base_tree, head_sha, head_tree, blob_sha = prepare(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "unrelated.md").write_text("later\n", encoding="utf-8")
            git(root, "add", "docs/unrelated.md")
            git(root, "commit", "-qm", "unrelated main")
            live_base_sha = git(root, "rev-parse", "HEAD")
            git(root, "push", "-q", "origin", "main")

            record = lineage_record(predecessor=base_tree, result=head_tree, blob_sha=blob_sha)
            event = {
                "number": 1,
                "pull_request": {
                    "body": f"VIT-Lineage-B64: {b64_lineage(record)}",
                    "head": {"sha": head_sha, "ref": "feature"},
                    "base": {"sha": event_base_sha, "ref": "main"},
                },
            }
            result = check_pull_request_event(root=root, event=event)
            self.assertIn("movement=PLACEMENT_RECOMPUTE_ONLY", result)
            self.assertIn("same_pr=true", result)
            self.assertNotEqual(event_base_sha, live_base_sha)

    def test_dependency_movement_blocks_same_pip_without_replacement_pr(self) -> None:
        with TemporaryDirectory() as tmp:
            root, event_base_sha, base_tree, head_sha, head_tree, blob_sha = prepare(tmp)
            target = root / "contracts" / "owned" / "spec.md"
            target.parent.mkdir(parents=True)
            target.write_text("changed dependency\n", encoding="utf-8")
            git(root, "add", "contracts/owned/spec.md")
            git(root, "commit", "-qm", "dependency main")
            git(root, "push", "-q", "origin", "main")

            record = lineage_record(
                predecessor=base_tree,
                result=head_tree,
                blob_sha=blob_sha,
                dependency_paths=("contracts/owned/**",),
            )
            event = {
                "number": 2,
                "pull_request": {
                    "body": f"VIT-Lineage-B64: {b64_lineage(record)}",
                    "head": {"sha": head_sha, "ref": "feature"},
                    "base": {"sha": event_base_sha, "ref": "main"},
                },
            }
            with self.assertRaisesRegex(RuntimeError, "PAYLOAD_REBUILD_REQUIRED"):
                check_pull_request_event(root=root, event=event)

if __name__ == "__main__":
    unittest.main()
