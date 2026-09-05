from __future__ import annotations

import base64
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ovc.development.prvit_remediation import IntegrationAdmissionReceipt
from ovc.development.skills.vit_late_binding import LateBindingPlacement
from ovc.development.skills.vit_routing import build_vit_payload_lineage_record
from tools.ci.vit_lineage_source import ResolvedLineageSource


ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / "tools" / "ci" / "vit_post_merge_completion_late_binding.py"
WORKFLOW = ROOT / ".github" / "workflows" / "vit-post-merge-completion.yml"
REMOTE_WRAPPER = ROOT / "tools" / "ci" / "vit_post_merge_completion_remote.py"
RECOVERY = ROOT / "registries" / "development" / "skills" / "VIT_POST_MERGE_RECOVERY_REQUESTS_v0_1.json"
SPEC = importlib.util.spec_from_file_location("vit_post_merge_completion_late_binding_tool", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def _pip() -> dict:
    return {
        "schema_version": "packet-integration-payload/v0.1",
        "programme_id": "PROGRAMME",
        "packet_id": "PACKET",
        "logical_changes": [
            {"op": "ADD", "path": "x.txt", "blob_sha": "1" * 40, "mode": "100644"}
        ],
        "authority_manifest_id": "a" * 64,
        "dependency_frontier_id": "b" * 64,
        "completion_transition": {"status": "COMPLETED", "next_packet": "NEXT"},
    }


def _record() -> dict:
    return build_vit_payload_lineage_record(
        programme_id="PROGRAMME",
        packet_id="PACKET",
        pip_identity_payload=_pip(),
    )


def _body() -> str:
    raw = json.dumps(_record(), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    token = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return f"VIT-Lineage-B64: {token}"


def _detached_source() -> ResolvedLineageSource:
    return ResolvedLineageSource(
        record=_record(),
        source="DETACHED_QUALIFICATION_LEDGER",
        immutable_ref="e" * 64,
        content_sha256="f" * 64,
    )


class VitPostMergeLateBindingRecoveryTests(unittest.TestCase):
    def _evidence(self):
        placement = LateBindingPlacement(
            pip_id=_record()["pip_id"],
            candidate_head_sha="1" * 40,
            physical_base_sha="2" * 40,
            physical_base_tree="3" * 40,
            prospective_tree_sha="4" * 40,
            authority_manifest_id="a" * 64,
            dependency_frontier_id="b" * 64,
        )
        admission = IntegrationAdmissionReceipt(
            assurance_generation_id="c" * 64,
            pip_id=placement.pip_id,
            placement_id=placement.placement_id,
            result_tree=placement.prospective_tree_sha,
            grt_proof_binding_id="d" * 64,
            disposition="SHADOW_READY",
            reason_codes=("EXACT_ASSURANCE_BOUND", "DETACHED_QUALIFICATION_BOUND", "LATE_BINDING_PLACEMENT", "BASE_STABLE"),
        )
        return placement, admission

    def test_late_binding_freeze_is_reconstructed_from_exact_final_prewrite_log(self) -> None:
        placement, admission = self._evidence()

        def fake_json(url, token):
            if "/actions/runs?" in url:
                return {
                    "workflow_runs": [
                        {"id": 9002, "name": "OVC tiered test selection shadow", "conclusion": "success", "run_attempt": 3}
                    ]
                }
            if "/actions/runs/9002/jobs" in url:
                return {"jobs": [{"id": 8002, "name": "OVC merge readiness", "conclusion": "success"}]}
            raise AssertionError(url)

        log = (
            "2026-08-19T12:30:23Z "
            + TOOL.LATE_PLACEMENT_MARKER
            + json.dumps(asdict(placement), sort_keys=True, separators=(",", ":"))
            + "\n2026-08-19T12:30:28Z "
            + TOOL.ADMISSION_MARKER
            + json.dumps(asdict(admission), sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
        with TemporaryDirectory() as tmp:
            with (
                patch.object(TOOL.legacy, "_json", side_effect=fake_json),
                patch.object(TOOL.legacy, "_request_job_log", return_value=log),
                patch.object(TOOL, "resolve_candidate_lineage", return_value=_detached_source()),
            ):
                freeze = TOOL._late_binding_freeze_from_merge_readiness_logs(
                    repo_root=Path(tmp),
                    repository="o/r",
                    head_sha="1" * 40,
                    pr_number=42,
                    pr_body="Human review text only",
                    token="token",
                )

        self.assertIsNotNone(freeze)
        assert freeze is not None
        self.assertEqual(freeze["binding_policy"], "LATE_PHYSICAL_PLACEMENT")
        self.assertEqual(freeze["freeze_provenance"]["source"], "OVC_MERGE_READINESS_EXACT_FINAL_PREWRITE_EVIDENCE")
        self.assertEqual(freeze["freeze_provenance"]["qualification_source"], "DETACHED_QUALIFICATION_LEDGER")
        self.assertEqual(freeze["freeze_provenance"]["qualification_ref"], "e" * 64)
        self.assertEqual(freeze["generation_id"], placement.placement_id)
        self.assertEqual(freeze["placement_id"], placement.placement_id)
        self.assertEqual(freeze["transaction"]["expected_predecessor_commit"], placement.physical_base_sha)
        self.assertEqual(freeze["transaction"]["expected_result_tree"], placement.prospective_tree_sha)
        self.assertEqual(freeze["completion_context"]["next_packet"], "NEXT")

    def test_successful_merge_readiness_without_exact_markers_fails_closed(self) -> None:
        def fake_json(url, token):
            if "/actions/runs?" in url:
                return {"workflow_runs": [{"id": 9002, "name": "OVC tiered test selection shadow", "conclusion": "success"}]}
            return {"jobs": [{"id": 8002, "name": "OVC merge readiness", "conclusion": "success"}]}

        with TemporaryDirectory() as tmp:
            with (
                patch.object(TOOL.legacy, "_json", side_effect=fake_json),
                patch.object(TOOL.legacy, "_request_job_log", return_value=b"no markers\n"),
            ):
                with self.assertRaises(TOOL.legacy.PostMergeCompletionError):
                    TOOL._late_binding_freeze_from_merge_readiness_logs(
                        repo_root=Path(tmp),
                        repository="o/r",
                        head_sha="1" * 40,
                        pr_number=42,
                        pr_body=_body(),
                        token="token",
                    )

    def test_post_merge_workflow_preserves_late_binding_recovery_route_via_remote_wrapper(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        wrapper = REMOTE_WRAPPER.read_text(encoding="utf-8")
        self.assertIn("vit_post_merge_completion_remote.py", text)
        self.assertIn("VIT_POST_MERGE_RECOVERY_REQUESTS_v0_1.json", text)
        self.assertIn("vit_post_merge_completion_late_binding", wrapper)
        self.assertIn("late._recover_one", wrapper)
        self.assertNotIn("python tools/ci/vit_post_merge_completion.py --repo-root . --merge-sha", text)

    def test_recovery_manifest_is_authority_inert_and_retires_verified_cutover_row(self) -> None:
        value = json.loads(RECOVERY.read_text(encoding="utf-8"))
        self.assertEqual(value["schema"], TOOL.RECOVERY_SCHEMA)
        requests = value["requests"]
        self.assertTrue(requests)
        merge_shas = [row["merge_sha"] for row in requests]
        self.assertEqual(len(merge_shas), len(set(merge_shas)))
        self.assertTrue(all(len(sha) == 40 and all(ch in "0123456789abcdef" for ch in sha) for sha in merge_shas))
        self.assertTrue(all(row["authority_effect"] == "NONE" for row in requests))

        rows = {row["merge_sha"]: row for row in requests}
        historical = rows["b22ea057ddef98acc2e43dfff689b7fa56934385"]
        self.assertEqual(historical["packet_id"], "DSAI3V-LB-WP1")
        self.assertEqual(historical["authority_effect"], "NONE")
        self.assertNotIn("49d2bc7a36e3e8754eb9d26eed750d2d481a2eb2", rows)


if __name__ == "__main__":
    unittest.main()
