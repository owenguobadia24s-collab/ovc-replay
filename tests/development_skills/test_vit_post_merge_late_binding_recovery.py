from __future__ import annotations

import base64
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ovc.development.skills.vit_routing import build_vit_placement
from tools.ci import vit_post_merge_completion_late_binding as TOOL


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "vit-post-merge-completion.yml"
RECOVERY = ROOT / "registries" / "development" / "skills" / "VIT_POST_MERGE_RECOVERY_REQUESTS_v0_1.json"
REMOTE_WRAPPER = ROOT / "tools" / "ci" / "vit_post_merge_completion_remote.py"


def _body() -> str:
    return """## VIT lineage

<!-- OVC_VIT_PAYLOAD_LINEAGE_BEGIN -->
```json
{"schema":"ovc-vit-payload-lineage/v2","status":"PAYLOAD_ADMITTED","programme_id":"P","packet_id":"K","pip_id":"a","authority_manifest_id":"b","dependency_frontier_id":"c","route_class":"VIT_MANDATORY","routing":{"route_class":"VIT_MANDATORY","controller":"DSAI_VIT_PHYSICAL_CONTROLLER","physical_gateway":"DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY"},"binding_policy":"LATE_PHYSICAL_PLACEMENT"}
```
<!-- OVC_VIT_PAYLOAD_LINEAGE_END -->
"""


class VitPostMergeLateBindingRecoveryTests(unittest.TestCase):
    def test_freeze_recovers_late_bound_physical_placement(self) -> None:
        placement = build_vit_placement(
            pip_id="a",
            physical_base_sha="b" * 40,
            prospective_tree_sha="c" * 40,
            physical_target="main",
            serialization_order=1,
            placement_observation="obs",
        )
        record = {
            "schema": "ovc-vit-physical-transaction-freeze/v1",
            "freeze_id": "d" * 64,
            "pip_id": "a",
            "packet_id": "K",
            "programme_id": "P",
            "generation_id": placement.placement_id,
            "placement_id": placement.placement_id,
            "freeze_provenance": {"qualification_ref": "e" * 64},
            "transaction": {
                "expected_predecessor_commit": placement.physical_base_sha,
                "expected_result_tree": placement.prospective_tree_sha,
            },
            "completion_context": {"next_packet": "NEXT"},
        }
        encoded = base64.b64encode(json.dumps(record).encode("utf-8")).decode("ascii")

        def fake_json(url, token):
            if "/actions/runs?" in url:
                return {"workflow_runs": [{"id": 9001, "name": "OVC tiered test selection shadow", "conclusion": "success"}]}
            return {"jobs": [{"id": 8001, "name": "OVC merge readiness", "conclusion": "success"}]}

        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with (
                patch.object(TOOL.legacy, "_json", side_effect=fake_json),
                patch.object(
                    TOOL.legacy,
                    "_request_job_log",
                    return_value=(
                        f"OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64={encoded}\n"
                        f"OVC_VIT_QUALIFICATION_REF={'e' * 64}\n"
                    ).encode("utf-8"),
                ),
            ):
                freeze = TOOL._late_binding_freeze_from_merge_readiness_logs(
                    repo_root=repo,
                    repository="o/r",
                    head_sha="1" * 40,
                    pr_number=42,
                    pr_body=_body(),
                    token="token",
                )

        self.assertEqual(freeze["freeze_id"], "d" * 64)
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

    def test_recovery_manifest_is_authority_inert_and_names_first_late_binding_merge(self) -> None:
        value = json.loads(RECOVERY.read_text(encoding="utf-8"))
        self.assertEqual(value["schema"], TOOL.RECOVERY_SCHEMA)
        self.assertEqual(len(value["requests"]), 1)
        row = value["requests"][0]
        self.assertEqual(row["merge_sha"], "b22ea057ddef98acc2e43dfff689b7fa56934385")
        self.assertEqual(row["packet_id"], "DSAI3V-LB-WP1")
        self.assertEqual(row["authority_effect"], "NONE")


if __name__ == "__main__":
    unittest.main()
