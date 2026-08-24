"""Temporary GRT2-G3 activation diagnostic.

This packet is diagnostic-only and MUST NOT be merged. It proves the exact
source-bound identity drift between the operator-approved generation-0 floor
and the current protected-main full-G3 snapshot without changing enforcement,
authority, rules, or the approved floor.
"""
from __future__ import annotations

import json
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.g3_floor import full_g3_snapshot_at_commit

ROOT = Path(__file__).resolve().parents[3]
GATE_READY_COMMIT = "0287c81400c3a2536096b2a1691d5486096e87b0"
CURRENT_MAIN_COMMIT = "98d369dceb3467eceebcd90345a15a56bd1ac139"
APPROVED_FLOOR_PATH = ROOT / "docs/programmes/grt-v0-2/g3/GRT2_G3_PROPOSED_DEBT_FLOOR_GENERATION_0.json"


def _index(snapshot: dict) -> dict[str, dict]:
    return {str(row["finding_id"]): row for row in snapshot.get("findings", [])}


def test_report_exact_g3_floor_identity_drift() -> None:
    gate_snapshot = full_g3_snapshot_at_commit(ROOT, commit=GATE_READY_COMMIT)
    current_snapshot = full_g3_snapshot_at_commit(ROOT, commit=CURRENT_MAIN_COMMIT)
    approved = json.loads(APPROVED_FLOOR_PATH.read_text(encoding="utf-8"))

    approved_ids = set(map(str, approved["open_grandfathered_findings"]))
    gate_rows = _index(gate_snapshot)
    current_rows = _index(current_snapshot)
    current_ids = set(current_rows)

    missing_ids = sorted(approved_ids - current_ids)
    added_ids = sorted(current_ids - approved_ids)

    payload = {
        "schema": "ovc-grt2-g3-floor-drift-diagnostic/v1",
        "authority_effect": "NONE_DIAGNOSTIC_ONLY",
        "gate_ready_commit": GATE_READY_COMMIT,
        "current_main_commit": CURRENT_MAIN_COMMIT,
        "approved_floor_hash": approved.get("floor_hash"),
        "approved_count": len(approved_ids),
        "gate_ready_snapshot_hash": gate_snapshot.get("snapshot_hash"),
        "gate_ready_count": len(gate_rows),
        "current_snapshot_hash": current_snapshot.get("snapshot_hash"),
        "current_count": len(current_rows),
        "missing_from_current": [
            {"finding_id": finding_id, "gate_ready_row": gate_rows.get(finding_id)}
            for finding_id in missing_ids
        ],
        "added_on_current": [
            {"finding_id": finding_id, "current_row": current_rows.get(finding_id)}
            for finding_id in added_ids
        ],
    }

    # Intentionally fail so GitHub Actions preserves the complete source-bound
    # diagnostic in the job log. This branch/PR is never an integration candidate.
    raise AssertionError("GRT2_G3_FLOOR_DRIFT_DIAGNOSTIC=" + json.dumps(payload, sort_keys=True))
