from __future__ import annotations

from datetime import datetime, timezone
import json
import platform
from pathlib import Path
import subprocess
import sys

from ovc.development.skills.cers.qualification import (
    derive_timing_freeze,
    run_persistent_qualification,
)


ROOT = Path(__file__).resolve().parents[2]


def _load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> int:
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    qualification = run_persistent_qualification(iterations=iterations)
    pilot = _load(
        "docs/releases/development-skills-v0-3/cers-conformance/wp6/"
        "CERS_WP6_LIVE_PILOT_RUN_v0_1.json"
    )
    start = datetime.fromisoformat(pilot["start_time_local"])
    completion = datetime.fromisoformat(pilot["completion_time_local"])
    duration_seconds = int((completion - start).total_seconds())
    heartbeat_sequence = int(pilot["heartbeat_sequence"])
    result = {
        "schema": "ovc-cers-persistent-supervisor-wp5-observed-qualification/v1",
        "programme_id": "OVC-DSAI3V-CERS-CONFORMANCE-v0.1",
        "packet_id": "CERS-PS-WP5",
        "status": "PASS",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "qualification_head": _git("rev-parse", "HEAD"),
        "qualification_tree": _git("rev-parse", "HEAD^{tree}"),
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "qualification": qualification,
        "pilot_capacity_source": {
            "record": "docs/releases/development-skills-v0-3/cers-conformance/wp6/CERS_WP6_LIVE_PILOT_RUN_v0_1.json",
            "status": pilot["status"],
            "duration_seconds": duration_seconds,
            "recorded_heartbeat_sequence": heartbeat_sequence,
            "worker_concurrency": pilot["worker_concurrency"],
            "max_speculative_depth": pilot["max_speculative_depth"],
            "visible_train_cap": pilot["visible_train_cap"],
            "incidents": pilot["incidents"],
        },
        "frozen_capacity": {
            "worker_concurrency": pilot["worker_concurrency"],
            "max_speculative_depth": pilot["max_speculative_depth"],
            "visible_train_cap": pilot["visible_train_cap"],
            "derivation": "exact already-proven CERS-WP6 live-pilot envelope; no increase",
        },
        "frozen_timing": derive_timing_freeze(
            qualification,
            pilot_duration_seconds=duration_seconds,
            pilot_heartbeat_sequence=heartbeat_sequence,
        ),
        "persistent_general_dispatch": "DENIED_PENDING_CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION",
        "post_pilot_dispatch_state": "DISABLE_NEW_DISPATCH",
        "authority_effect": "NONE_SHADOW_QUALIFICATION_ONLY",
    }
    print(json.dumps(result, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
