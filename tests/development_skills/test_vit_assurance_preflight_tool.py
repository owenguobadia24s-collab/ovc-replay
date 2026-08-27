from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch


TOOL_PATH = Path(__file__).resolve().parents[2] / "tools" / "ci" / "vit_assurance_preflight.py"
SPEC = importlib.util.spec_from_file_location("vit_assurance_preflight_tool", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class VitAssurancePreflightToolTests(unittest.TestCase):
    def test_workflow_dispatch_prewarm_resolves_exact_detached_qualification(self) -> None:
        target = "a" * 40
        source = SimpleNamespace(
            record={"schema": "ovc-vit-payload-lineage/v2"},
            source="DETACHED_QUALIFICATION_LEDGER",
            immutable_ref="b" * 64,
        )
        lineage = SimpleNamespace(pip_id="c" * 64, late_binding=True)
        with (
            patch.dict(
                TOOL.os.environ,
                {
                    "GITHUB_EVENT_NAME": "workflow_dispatch",
                    "GITHUB_WORKSPACE": str(Path.cwd()),
                    "OVC_AA0_PREWARM_TARGET_HEAD_SHA": target,
                    "OVC_ASSURANCE_TARGET_HEAD_SHA": target,
                },
                clear=True,
            ),
            patch.object(TOOL, "_validate_prewarm_checkout", return_value=("refs/remotes/origin/candidate",)),
            patch.object(TOOL, "resolve_candidate_lineage", return_value=source) as resolve,
            patch.object(TOOL, "validate_vit_lineage_record", return_value=lineage),
            patch.object(TOOL, "compile_prequalification", return_value={"receipt_id": "d" * 64}),
            patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            self.assertEqual(TOOL.main(), 0)

        resolve.assert_called_once_with(
            root=Path.cwd().resolve(),
            head_sha=target,
            require=True,
            allow_legacy_pr_body=False,
        )
        output = stdout.getvalue()
        self.assertIn("OVC_VIT_ASSURANCE_AA0_IDENTITY=" + "c" * 64, output)
        self.assertIn("OVC_VIT_ASSURANCE_GENERATION_ID=" + "b" * 64, output)
        self.assertIn("OVC_VIT_ASSURANCE_QUALIFICATION_ID=" + "b" * 64, output)
        self.assertIn("OVC_VIT_ASSURANCE_LINEAGE_SOURCE=DETACHED_QUALIFICATION_LEDGER", output)
        self.assertIn("OVC_VIT_ASSURANCE_AA0_PRODUCER_MODE=true", output)
        self.assertIn("OVC_VIT_ASSURANCE_AA0_REUSE_AUTHORIZED=false", output)
        self.assertIn("OVC_VIT_AA0_PREWARM_DISPOSITION=RUN_AA0", output)

    def test_missing_detached_qualification_fails_closed(self) -> None:
        target = "a" * 40
        with (
            patch.object(TOOL, "_validate_prewarm_checkout", return_value=("refs/remotes/origin/candidate",)),
            patch.object(
                TOOL,
                "resolve_candidate_lineage",
                side_effect=RuntimeError("VIT_QUALIFICATION_REQUIRED"),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "VIT_QUALIFICATION_REQUIRED"):
                TOOL._run_prewarm(root=Path.cwd(), target=target)

    def test_malformed_prewarm_target_fails_closed(self) -> None:
        with patch.dict(
            TOOL.os.environ,
            {
                "GITHUB_EVENT_NAME": "workflow_dispatch",
                "OVC_AA0_PREWARM_TARGET_HEAD_SHA": "ABC123",
                "OVC_ASSURANCE_TARGET_HEAD_SHA": "ABC123",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "TARGET_SHA_INVALID"):
                TOOL.main()

    def test_prewarm_assurance_target_mismatch_fails_closed(self) -> None:
        with patch.dict(
            TOOL.os.environ,
            {
                "GITHUB_EVENT_NAME": "workflow_dispatch",
                "OVC_AA0_PREWARM_TARGET_HEAD_SHA": "a" * 40,
                "OVC_ASSURANCE_TARGET_HEAD_SHA": "b" * 40,
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "ASSURANCE_TARGET_MISMATCH"):
                TOOL.main()

    def test_execution_head_mismatch_fails_closed(self) -> None:
        with patch.object(TOOL, "_git", side_effect=["", "b" * 40]):
            with self.assertRaisesRegex(RuntimeError, "EXECUTION_HEAD_MISMATCH"):
                TOOL._validate_prewarm_checkout(Path.cwd(), "a" * 40)

    def test_prewarm_and_pr_emit_identical_pip_and_generation_identity(self) -> None:
        source = SimpleNamespace(source="DETACHED_QUALIFICATION_LEDGER", immutable_ref="a" * 64)
        lineage = SimpleNamespace(pip_id="b" * 64)
        with patch("sys.stdout", new_callable=io.StringIO) as first:
            TOOL._emit_lineage_identity(source, lineage)
        with patch("sys.stdout", new_callable=io.StringIO) as second:
            TOOL._emit_lineage_identity(source, lineage)
        self.assertEqual(first.getvalue(), second.getvalue())

    def test_qualification_and_pip_changes_invalidate_exact_identity(self) -> None:
        def emitted(source_ref: str, pip_id: str) -> str:
            source = SimpleNamespace(source="DETACHED_QUALIFICATION_LEDGER", immutable_ref=source_ref)
            lineage = SimpleNamespace(pip_id=pip_id)
            with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                TOOL._emit_lineage_identity(source, lineage)
            return stdout.getvalue()

        baseline = emitted("a" * 64, "b" * 64)
        self.assertNotEqual(baseline, emitted("c" * 64, "b" * 64))
        self.assertNotEqual(baseline, emitted("a" * 64, "d" * 64))

    def test_ordinary_non_pr_behavior_remains_backward_compatible(self) -> None:
        with (
            patch.dict(
                TOOL.os.environ,
                {"GITHUB_EVENT_NAME": "push", "GITHUB_SHA": "a" * 40},
                clear=True,
            ),
            patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            self.assertEqual(TOOL.main(), 0)
        output = stdout.getvalue()
        self.assertIn("OVC_VIT_ASSURANCE_AA0_IDENTITY=" + "a" * 40, output)
        self.assertIn("OVC_VIT_ASSURANCE_LINEAGE_SOURCE=NON_PR", output)
        self.assertIn("OVC_VIT_ASSURANCE_AA0_PRODUCER_MODE=false", output)
        self.assertIn("OVC_VIT_ASSURANCE_AA0_REUSE_REASON=NON_PULL_REQUEST", output)

    def test_ordinary_pr_without_qualification_preserves_existing_fallback(self) -> None:
        event = {
            "number": 42,
            "pull_request": {
                "number": 42,
                "head": {"sha": "a" * 40},
                "base": {"sha": "b" * 40},
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            event_path = Path(temp_dir) / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf-8")
            with (
                patch.dict(
                    TOOL.os.environ,
                    {
                        "GITHUB_EVENT_NAME": "pull_request",
                        "GITHUB_EVENT_PATH": str(event_path),
                        "GITHUB_WORKSPACE": str(Path.cwd()),
                    },
                    clear=True,
                ),
                patch.object(TOOL, "_live_pr_payload", return_value=event["pull_request"]),
                patch.object(TOOL, "resolve_candidate_lineage", return_value=None),
                patch("sys.stdout", new_callable=io.StringIO) as stdout,
            ):
                self.assertEqual(TOOL.main(), 0)
        self.assertIn("REGISTERED_EXCEPTION_OR_NO_QUALIFICATION", stdout.getvalue())

    def test_prewrite_freeze_uses_observed_pr_and_workflow_identities(self) -> None:
        event = {"number": 42}
        pr = {
            "number": 42,
            "base": {"sha": "a" * 40},
            "head": {"sha": "b" * 40},
        }
        lineage = {"schema": "ovc-vit-routing-lineage/v1"}
        with (
            patch.dict(
                TOOL.os.environ,
                {"GITHUB_WORKSPACE": str(Path.cwd()), "GITHUB_RUN_ID": "9001", "GITHUB_RUN_ATTEMPT": "2"},
                clear=False,
            ),
            patch.object(TOOL, "_git_tree", side_effect=["c" * 40, "d" * 40]),
            patch.object(TOOL, "build_live_transaction_freeze", return_value={"freeze": True}) as build,
            patch.object(TOOL, "encode_freeze_marker", return_value="OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64=exact"),
            patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            TOOL._emit_prewrite_freeze(event=event, pr=pr, lineage_record=lineage)

        build.assert_called_once_with(
            lineage_record=lineage,
            pr_number=42,
            base_sha="a" * 40,
            head_sha="b" * 40,
            base_tree="c" * 40,
            head_tree="d" * 40,
            workflow_run_id="9001",
            run_attempt="2",
        )
        self.assertEqual(
            stdout.getvalue().strip(),
            "OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64=exact",
        )


if __name__ == "__main__":
    unittest.main()
