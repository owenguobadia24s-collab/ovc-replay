from __future__ import annotations

import json
from pathlib import Path

from ovc.research_operations.asocs.census import (
    build_census,
    checkpoint_prefix,
    prove_two_run_equality,
    verify_restart,
)

ROOT = Path(__file__).resolve().parents[3]


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _fixture() -> list[dict]:
    return [
        {"bucket_id": "A", "interval_start": "2026-01-02 00:00:00", "interval_end": "2026-01-02 00:15:00",
         "region": "TARGET", "status": "COMPLETE", "open": "1.1", "high": "1.2", "low": "1.0", "close": "1.15"},
        {"bucket_id": "B", "interval_start": "2026-01-02 00:15:00", "interval_end": "2026-01-02 00:30:00",
         "region": "TARGET", "status": "INCOMPLETE"},
        {"bucket_id": "C", "interval_start": "2026-01-02 00:30:00", "interval_end": "2026-01-02 00:45:00",
         "region": "TARGET", "status": "ABSENT"},
    ]


def test_census_preserves_complete_incomplete_absent_and_never_invents_upper_stack() -> None:
    census = build_census(_fixture())
    assert census["record_count"] == 3
    assert census["source_status_counts"] == {"ABSENT": 1, "COMPLETE": 1, "INCOMPLETE": 1}
    assert census["traces"][0]["c1"]["route"] == "MORPHOLOGY_COMPATIBLE"
    assert census["traces"][1]["c1"]["disposition"] == "NOT_EVALUABLE_SOURCE"
    assert all(v["disposition"] == "NOT_EVALUABLE" for v in census["traces"][0]["upper_stack"].values())


def test_checkpoint_restart_and_two_run_logical_equality() -> None:
    census = build_census(_fixture())
    checkpoint = checkpoint_prefix(census, 2)
    assert verify_restart(checkpoint, census)
    proof = prove_two_run_equality(_fixture())
    assert proof["result"] == "PASS"
    assert proof["logical_equal"] is True


def test_wp5_prebuild_does_not_claim_g3_without_exact_external_source() -> None:
    state = _json("records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_7_WP5_PREBUILD.json")
    assert state["status"] == "IMPLEMENTED"
    assert state["gate_status"] == "NOT_EVALUATED"
    assert "EXACT_BOUND_SOURCE_ARTIFACT_REQUIRED_FOR_G3" in state["blockers"]
    assert state["review_sampling_started"] is False
