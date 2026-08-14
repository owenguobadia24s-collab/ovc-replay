from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from ovc.development.skills.vit_core import (
    DependencyFrontier,
    IntegrationAuthorityManifest,
    PacketIntegrationPayload,
    ProspectiveTreeState,
    VitContractError,
    assert_tree_equivalent,
    classify_authority,
    git_tree_sha,
    validate_reason_code,
)

ROOT = Path(__file__).resolve().parents[2]

class DsaiVitV03Wp1Tests(unittest.TestCase):
    def _authority(self, authority_class: str = "AUTO_EXECUTABLE", delta: str = "NONE") -> IntegrationAuthorityManifest:
        return IntegrationAuthorityManifest(
            plan_id="PLAN", packet_id="WP1", gate_id="G1",
            authority_class=authority_class, authority_delta=delta,
            authority_sources=("source-a",), reserved_boundaries=("G-VIT-PILOT",),
        )

    def test_pip_identity_is_content_addressed_and_idempotent(self) -> None:
        dep = DependencyFrontier(("a", "b", "a"), "EXECUTION_COMPLETION_REQUIRED", ("owner",))
        a = PacketIntegrationPayload("P", "WP1", ({"path":"x","after":"1"},), self._authority(), dep, {"state":"COMPLETE"})
        b = PacketIntegrationPayload("P", "WP1", ({"path":"x","after":"1"},), self._authority(), dep, {"state":"COMPLETE"})
        self.assertEqual(a.payload_id, b.payload_id)
        self.assertEqual(len(a.payload_id), 64)

    def test_identity_ignores_branch_pr_worker_metadata_by_construction(self) -> None:
        dep = DependencyFrontier((), "NONE")
        pip = PacketIntegrationPayload("P", "WP1", ({"path":"x","after":"1"},), self._authority(), dep, {})
        identity = pip.identity_payload()
        self.assertNotIn("branch", identity)
        self.assertNotIn("pr_number", identity)
        self.assertNotIn("worker", identity)
        self.assertNotIn("commit_sha", identity)

    def test_unknown_authority_and_dependency_fail_closed(self) -> None:
        with self.assertRaises(VitContractError):
            self._authority("UNKNOWN")
        with self.assertRaises(VitContractError):
            DependencyFrontier((), "RELAXED_BY_GUESS")

    def test_operator_required_never_auto_allows(self) -> None:
        self.assertEqual(classify_authority(self._authority("OPERATOR_REQUIRED")), "WAITING_OPERATOR_AUTHORITY")
        self.assertEqual(classify_authority(self._authority("AUTO_EXECUTABLE", "SOME_DELTA")), "AUTHORITY_REVIEW_REQUIRED")

    def test_tree_equality_is_exact(self) -> None:
        assert_tree_equivalent("a"*40, "a"*40)
        with self.assertRaisesRegex(VitContractError, "POST_WRITE_TREE_MISMATCH"):
            assert_tree_equivalent("a"*40, "b"*40)
        self.assertNotEqual(ProspectiveTreeState("a"*40).state_id, ProspectiveTreeState("b"*40).state_id)

    def test_commit_metadata_does_not_change_tree_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git","init","-q",str(repo)], check=True)
            subprocess.run(["git","-C",str(repo),"config","user.email","vit@example.invalid"], check=True)
            subprocess.run(["git","-C",str(repo),"config","user.name","VIT Fixture"], check=True)
            (repo/"a.txt").write_text("same\n", encoding="utf-8")
            subprocess.run(["git","-C",str(repo),"add","a.txt"], check=True)
            subprocess.run(["git","-C",str(repo),"commit","-q","-m","first"], check=True)
            first = git_tree_sha(repo, "HEAD")
            subprocess.run(["git","-C",str(repo),"commit","--allow-empty","-q","-m","metadata only"], check=True)
            second = git_tree_sha(repo, "HEAD")
            self.assertEqual(first, second)

    def test_registry_bundle_and_schema_catalogue_are_closed(self) -> None:
        registry = json.loads((ROOT/"registries/development/skills/OVC_DSAI_VIT_REGISTRY_BUNDLE_v0_1.json").read_text())
        self.assertFalse(next(x for x in registry["authorized_main_writers"] if x["writer_identity"] == "DSAI_VIT_PHYSICAL_CONTROLLER")["active"])
        self.assertEqual(registry["tree_identity_profile"]["profile_id"], "TREE_IDENTITY_PROFILE_git-tree-v1")
        schema = json.loads((ROOT/"schemas/development/skills/vit_core_objects_v0_1.schema.json").read_text())
        self.assertIn("PacketIntegrationPayload", schema["$defs"])
        self.assertIn("ContinuousExecutionMandate", schema["$defs"])
        self.assertEqual(validate_reason_code("POST_WRITE_TREE_MISMATCH"), "POST_WRITE_TREE_MISMATCH")
        with self.assertRaises(VitContractError):
            validate_reason_code("UNKNOWN")

if __name__ == "__main__":
    unittest.main()
