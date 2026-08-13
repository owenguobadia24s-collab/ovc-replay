from __future__ import annotations
import json
from pathlib import Path

from ovc.development.identity import canonical_sha256
from ovc.development.skills.orch345 import build_packet_descriptor
from ovc.development.skills.orch345_auto import run_automatic_orchestration
from ovc.development.skills.orch345_auto_receipt_core import load_receipt

ROOT=Path(__file__).resolve().parents[2]
AUTHORITY=ROOT/"registries/development/skills/orch345_bounded_authority_v0_1.json"

def test_real_automatic_path_persists_reloadable_orch345_receipts_without_identity_drift(tmp_path:Path)->None:
    authority=json.loads(AUTHORITY.read_text(encoding="utf-8"))
    programme_state={"schema":"ovc-programme-state/v1","programme_id":"AUTO-PROG","status":"RUNNING","next_packet":"AUTO-WP1"}
    p1=build_packet_descriptor(programme_id="AUTO-PROG",packet_id="AUTO-WP1",write_paths=("src/auto_wp1.py",),semantic_owners=("AUTO-WP1",),priority=1)
    p2=build_packet_descriptor(programme_id="AUTO-PROG",packet_id="AUTO-WP2",write_paths=("src/auto_wp2.py",),semantic_owners=("AUTO-WP2",),priority=2)
    result=run_automatic_orchestration(authority=authority,programme_state=programme_state,packet_states=(p1,p2),trigger_source="PROGRAMME_STATE_TRANSITION",max_parallel_builds=2,evidence_output=tmp_path,invocation_id="ORCH345-AUTO-IT-0001",observed_at_utc="2026-08-13T17:30:00Z")

    assert result["orch3_execution_record"]["record_id"]=="ad35c5d1931f2323b331f990f3a7369064252001fac57feb94743fda0d2a7898"
    assert [row["record_id"] for row in result["orch4_execution_records"]]==["260c628d27fb1f50d5bf73cb67c5a206514cc6af9612b0e1a5ff6e5c823864d7"]
    assert result["orch5_execution_record"]["record_id"]=="5e7617f3e6feb97d584f68993094b7e3cfa45b98a75db8c5a692b4efa615138d"

    paths=[Path(value) for value in result["persisted_receipt_paths"]]
    assert len(paths)==3 and all(path.is_file() for path in paths)
    receipts=[load_receipt(path) for path in paths]
    assert [r["orchestrator"] for r in receipts]==["ORCH-3","ORCH-4","ORCH-5"]
    assert [r["record_id"] for r in receipts]==result["diagnostic_receipt_ids"]
    expected_programme_state_id=canonical_sha256(programme_state,role="DSAI2_SOURCE_PROGRAMME_STATE")
    expected_packet_states={"AUTO-WP1":p1["record_id"],"AUTO-WP2":p2["record_id"]}
    for receipt in receipts:
        assert receipt["orchestration_run_id"]==result["orchestration_run_id"]
        assert receipt["invocation_id"]=="ORCH345-AUTO-IT-0001"
        assert receipt["invocation_mode"]=="AUTO"
        assert receipt["trigger_source"]=="PROGRAMME_STATE_TRANSITION"
        assert receipt["source_programme_id"]=="AUTO-PROG"
        assert receipt["source_programme_state_id"]==expected_programme_state_id
        assert receipt["source_packet_state_ids"]==expected_packet_states
        assert receipt["receipt_phase"]=="DECISION_SELECTED"
        assert receipt["execution_started_observed"] is False
        assert receipt["execution_completed_observed"] is False
    orch5=receipts[-1]
    assert orch5["scheduled_slot_count"]==2
    assert orch5["remaining_schedule_capacity"]==0
    assert orch5["schedule_selection_at_capacity"] is True
    assert orch5["actual_occupancy_observed"] is False
    assert "occupied_slots" not in orch5
