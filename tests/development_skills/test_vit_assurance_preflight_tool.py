from __future__ import annotations

import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch


TOOL_PATH = Path(__file__).resolve().parents[2] / "tools" / "ci" / "vit_assurance_preflight.py"
SPEC = importlib.util.spec_from_file_location("vit_assurance_preflight_tool", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class VitAssurancePreflightToolTests(unittest.TestCase):
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
