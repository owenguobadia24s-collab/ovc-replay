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
    def test_a0_preflight_defers_physical_transaction_freeze_to_siq_lane(self) -> None:
        record = {
            "schema": "ovc-vit-routing-lineage/v1",
            "status": "ADMITTED",
        }
        validated = SimpleNamespace(
            pip_id="a" * 64,
            generation_id="b" * 64,
        )
        event = {
            "number": 42,
            "pull_request": {
                "body": "VIT-Lineage-B64: source",
                "head": {"sha": "c" * 40},
            },
        }
        pr = {
            "number": 42,
            "body": "VIT-Lineage-B64: source",
            "head": {"sha": "c" * 40},
        }
        with tempfile.TemporaryDirectory() as tmp:
            event_path = Path(tmp) / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf-8")
            output_path = Path(tmp) / "output.txt"
            with (
                patch.dict(
                    TOOL.os.environ,
                    {
                        "GITHUB_EVENT_NAME": "pull_request",
                        "GITHUB_EVENT_PATH": str(event_path),
                        "GITHUB_OUTPUT": str(output_path),
                    },
                    clear=False,
                ),
                patch.object(TOOL, "_live_pr_payload", return_value=pr),
                patch.object(
                    TOOL,
                    "resolve_lineage_source",
                    return_value=SimpleNamespace(
                        record=record,
                        source="PR_BODY",
                        immutable_ref="pr-body:42",
                    ),
                ),
                patch.object(TOOL, "validate_vit_lineage_record", return_value=validated),
                patch("sys.stdout", new_callable=io.StringIO) as stdout,
            ):
                self.assertEqual(TOOL.main(), 0)

        text = stdout.getvalue()
        self.assertIn("OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_DEFERRED=SIQ_PHYSICAL_LANE", text)
        self.assertIn("OVC_VIT_ASSURANCE_ASSURANCE_SCOPE=A0_PIP_ONLY", text)
        self.assertNotIn("OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64=", text)
        self.assertNotIn("build_live_transaction_freeze", TOOL_PATH.read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
