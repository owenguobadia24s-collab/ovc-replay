from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from ovc.opt_b.srfd.wp10_execution_substrate_hardening import (
    capture_execution_environment_profile,
    run_full_2020_unit_rehearsal,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run SRFDI execution-substrate hardening without real June scientific payloads."
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    output = args.output.resolve()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)

    profile = capture_execution_environment_profile(artifact_root=root)
    (output / "EXECUTION_ENVIRONMENT_PROFILE.json").write_text(
        json.dumps(profile, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    if not profile["required_profile_fields_complete"]:
        raise SystemExit("EXECUTION_ENVIRONMENT_PROFILE_INCOMPLETE")

    rehearsal = run_full_2020_unit_rehearsal(root)
    (output / "SRFDI_2020_UNIT_SYNTHETIC_REHEARSAL.json").write_text(
        json.dumps(rehearsal, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    summary = {
        "schema": "ovc-srfdi-execution-substrate-hardening-summary/v1",
        "status": "PASS",
        "execution_environment_profile_sha256": profile["logical_sha256"],
        "rehearsal_sha256": rehearsal["logical_sha256"],
        "ordered_unit_count": rehearsal["ordered_unit_count"],
        "checkpoint_sequence": rehearsal["checkpoint_sequence"],
        "real_june_payload_used": False,
        "scientific_delta": "NONE",
        "next_action": "ELIGIBLE_TO_RECORD_V10_FAILURE_AND_PREPARE_V11_EXACT_REBIND",
    }
    (output / "SRFDI_EXECUTION_SUBSTRATE_HARDENING_SUMMARY.json").write_text(
        json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
