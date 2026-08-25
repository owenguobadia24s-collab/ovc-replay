#!/usr/bin/env python3
"""Patch only live CURRENT_STATE_POINTER expectations for superseding G3 GATE_READY.

Historical v0_15 state assertions remain untouched. This is a construction helper
for the no-authority superseding gate-ready packet.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# This helper is copied to /tmp before execution by the bounded diagnostic
# workflow, so __file__ is not a stable repository locator. The workflow runs
# it from the checked-out repository root; bind to that exact working tree.
ROOT = Path.cwd().resolve()
TEST_ROOT = ROOT / "tests/governance/grt_v0_2"
OUT = Path("/tmp/grt2-g3-superseding-currentness-files.json")

POINTER_VAR = re.compile(r"\b(?:pointer|current_pointer|p)\s*\[")
REPLACEMENTS = (
    (
        "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_15.json",
        "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_16_SUPERSEDING_GATE_READY.json",
    ),
    ("OVC_GRT2_STATE_v0_15.json", "OVC_GRT2_STATE_v0_16_SUPERSEDING_GATE_READY.json"),
    ("GATE_READY_OPERATOR_REQUIRED", "GATE_READY_OPERATOR_REQUIRED_PENDING_EXACT_FINAL_PR_ASSURANCE"),
    ("GRT2-G3-GATE-READY", "GRT2-G3-SUPERSEDING-GATE-READY"),
    ("GRT2-G3-OPERATOR-DECISION", "GRT2-G3-SUPERSEDING-OPERATOR-DECISION"),
    (
        "STOP_FOR_OPERATOR_GRT2_G3_DECISION",
        "COMPLETE_EXACT_FINAL_PR_ASSURANCE_AND_INTEGRATE_GATE_READY_THEN_REVALIDATE",
    ),
)


def main() -> int:
    changed: list[str] = []
    for path in sorted(TEST_ROOT.glob("test_grt2_*.py")):
        original = path.read_text(encoding="utf-8")
        lines: list[str] = []
        for line in original.splitlines(keepends=True):
            updated = line
            if POINTER_VAR.search(line):
                for old, new in REPLACEMENTS:
                    updated = updated.replace(old, new)
            # The current G3 gate-ready contract reads the state through the live
            # CURRENT_STATE_POINTER. Patch only that exact historical test's live
            # state-status assertion; leave immutable v0_15 assertions elsewhere.
            if path.name == "test_grt2_g3_gate_ready.py":
                updated = updated.replace(
                    'assert state["status"] == "GATE_READY_OPERATOR_REQUIRED"',
                    'assert state["status"] == "GATE_READY_OPERATOR_REQUIRED_PENDING_EXACT_FINAL_PR_ASSURANCE"',
                )
            lines.append(updated)
        revised = "".join(lines)
        if revised != original:
            path.write_text(revised, encoding="utf-8")
            changed.append(path.relative_to(ROOT).as_posix())
    OUT.write_text(json.dumps({"changed_files": changed}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"changed_files": changed}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
