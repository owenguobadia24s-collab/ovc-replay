from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"
STATE = ROOT / "records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_21_WP8_G3_REPRODUCTION_BLOCKED.json"
POINTER = ROOT / "registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json"
BLOCK_PACKET = "ASOCSI-WP8-G3-REPRODUCTION-INTEGRITY-PREFLIGHT"
STAGE2_PREP = "ASOCSI-WP8-S01-STAGE2-C2-PRIMITIVE-STRUCTURE-PREPARATION"
STAGE2_HUMAN = "ASOCSI-WP8-S01-STAGE2-C2-PRIMITIVE-STRUCTURE-HUMAN-ADJUDICATION"
STAGE2_NATIVE_ROUTE = "ASOCSI-WP8-S01-STAGE2-C2-NATIVE-OBSERVATION-ROUTE-AMENDMENT"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _cid(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _state_generation(path: str) -> int:
    match = re.search(r"ASOCSI_PROGRAMME_STATE_v0_(\d+)_", path)
    assert match is not None, path
    return int(match.group(1))


def test_wp8_source_recovers_exact_g1_but_g3_identity_blocks_reveal():
    source = _json(WP8 / "ASOCSI_WP8_SOURCE_REPRODUCTION_RECEIPT_v0_1.json")
    repro = _json(WP8 / "ASOCSI_WP8_G3_REPRODUCTION_INTEGRITY_v0_1.json")
    authority = _json(WP8 / "ASOCSI_WP8_AUTHORITY_MANIFEST_v0_1.json")
    frontier = _json(WP8 / "ASOCSI_WP8_DEPENDENCY_FRONTIER_v0_1.json")
    packet = _json(WP8 / "ASOCSI_WP8_G3_REPRODUCTION_PACKET_v0_1.json")
    qa = _json(WP8 / "ASOCSI_WP8_G3_REPRODUCTION_QA_v0_1.json")
    decision = _json(WP8 / "ASOCSI_G6_G3_REPRODUCTION_BLOCK_DECISION_v0_1.json")
    state = _json(STATE)
    pointer = _json(POINTER)
    current_path = Path(pointer["current_state"])
    current = _json(ROOT / current_path)

    assert source["source"]["sha256"] == "210233ec5761bf82998172832bb554ddf10dfeb3099f6bc6488d5bb0f6bec4f2"
    assert source["verification"]["g1_audit_15m"]["result"] == "PASS"
    assert source["verification"]["g1_audit_15m"]["observed_sha256"] == "df060a22bf8a6c1d990d22af90e189848bd2c5f3090ef65a8c5637e4456bb7d9"
    assert repro["reproduction_basis"]["clean_attempt_count"] == 2
    assert repro["reproduction_basis"]["clean_attempts_identical"] is True
    assert repro["population_reconciliation"]["counts_match_frozen"] is True
    assert repro["expected_frozen"]["census_sha256"] != repro["observed_reproduction"]["census_sha256"]
    assert repro["expected_frozen"]["ordered_trace_ids_sha256"] != repro["observed_reproduction"]["ordered_trace_ids_sha256"]
    assert repro["expected_frozen"]["observation_traces"]["sha256"] != repro["observed_reproduction"]["observation_traces"]["sha256"]
    assert all(repro["expected_frozen"]["checkpoints"][key] != repro["observed_reproduction"]["checkpoints"][key] for key in ("4392", "8784", "13176", "17568"))
    assert repro["result"] == "FAIL_G3_CONTENT_IDENTITY_MISMATCH"
    assert repro["stage1_reveal_allowed"] is False
    assert packet["authority_manifest_id"] == _cid(authority)
    assert packet["dependency_frontier_id"] == _cid(frontier)
    assert qa["qa_recommendation"] == "BLOCK"
    assert decision["decision"] == "BLOCK"
    assert decision["authority_delta"] == "NONE"
    assert decision["stage1_reveal_authorized"] is False
    assert decision["human_adjudication_started"] is False

    assert state["status"] == "BLOCKED"
    assert state["authority_delta"] == "NONE"
    assert state["human_adjudication_started"] is False
    assert state["stop_boundary"] == "ASOCSI-WP8-STAGED-REVEAL_NOT_AUTHORIZED_UNTIL_G3_REPRODUCIBLE"

    assert pointer["programme_id"] == current["programme_id"] == state["programme_id"]
    assert pointer["packet_id"] == current["packet_id"]
    assert pointer["status"] == current["status"]
    assert current["status"] in {"BLOCKED", "GATE_READY", "APPROVED", "COMPLETED"}
    assert pointer["next_packet"] == current["next_packet"]
    assert _state_generation(pointer["current_state"]) >= _state_generation(str(STATE.relative_to(ROOT)).replace("\\", "/"))
    assert current.get("human_adjudication_started", False) is False
    if current["packet_id"] in {STAGE2_PREP, STAGE2_HUMAN, STAGE2_NATIVE_ROUTE}:
        assert current["stage2_reveal_started"] is True
        assert current["stage2_human_adjudication_started"] is False
        assert current["stage3_reveal_started"] is False
        assert current["human_scientific_input_boundary"] is True
        if current["packet_id"] == STAGE2_HUMAN:
            assert current["status"] == "GATE_READY"
            assert current["authority_required"] == "HUMAN_SCIENTIFIC_INPUT"
            assert current["stage2_human_answer_count"] == 0
        elif current["packet_id"] == STAGE2_NATIVE_ROUTE:
            assert current["stage2_human_scientific_input_required"] is True
            assert current["stage2_human_answer_synthesis_allowed"] is False
            assert current["stage2_complete_session_freeze_required_before_stage3"] is True
            assert current["construct_survival_decision"] == "PROHIBITED_DURING_CASE_REVIEW"
    else:
        assert current.get("stage2_reveal_started", False) is False

    if current["packet_id"] == state["packet_id"]:
        assert current["status"] == "BLOCKED"
        assert current.get("stage1_reveal_started", False) is False
        assert current["stop_boundary"] == state["stop_boundary"]
        assert current["blockers"] == state["blockers"]
        if current_path != STATE.relative_to(ROOT):
            assert current["repository_effective"]["repository_effective"] is True
            assert current["frozen_g3_identity"]["census_sha256"] == repro["expected_frozen"]["census_sha256"]
            assert current["frozen_g3_identity"]["ordered_trace_ids_sha256"] == repro["expected_frozen"]["ordered_trace_ids_sha256"]
            assert current["frozen_g3_identity"]["observation_traces_sha256"] == repro["expected_frozen"]["observation_traces"]["sha256"]
    else:
        prerequisites = set(current.get("prerequisites", []))
        preserved = current.get("preserved", {})
        assert BLOCK_PACKET in prerequisites or preserved.get("wp8_g3_reproduction_block") is True
        assert current["evidence"]["frozen_census_sha256"] == repro["expected_frozen"]["census_sha256"]
        assert current["evidence"]["frozen_ordered_trace_ids_sha256"] == repro["expected_frozen"]["ordered_trace_ids_sha256"]
        assert current["evidence"]["frozen_observation_trace_sha256"] == repro["expected_frozen"]["observation_traces"]["sha256"]
        assert current["preserved"]["g3_frozen_generation"] is True
        assert current["preserved"]["g4_review_population"] is True
        assert current["preserved"]["g5_human_evidence"] is True
        if current["status"] == "GATE_READY":
            if current["packet_id"] == STAGE2_HUMAN:
                assert current["authority_required"] == "HUMAN_SCIENTIFIC_INPUT"
                assert current["blockers"] == ["HUMAN_SCIENTIFIC_INPUT_REQUIRED"]
                assert current["stage2_reveal_started"] is True
                assert current["stage2_human_adjudication_started"] is False
                assert current["stage3_reveal_started"] is False
            else:
                assert current.get("stage1_reveal_started", False) is False
                assert current["authority_required"] == "OPERATOR_REQUIRED"
                assert current["stop_boundary"] == "ASOCSI-G6-PROVENANCE-SUPERSESSION-OPERATOR-DECISION"
        elif current["status"] == "APPROVED":
            if current["packet_id"] == STAGE2_NATIVE_ROUTE:
                route_operator = _json(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_ROUTE_OPERATOR_DECISION_v0_1.json")
                assert route_operator["decision"] == "PASS" and route_operator["authority"] == "OPERATOR"
                assert current["authority_required"] == "OPERATOR_REQUIRED_SATISFIED"
                assert current["stage2_reveal_started"] is True
                assert current["stage2_human_adjudication_started"] is False
                assert current["stage3_reveal_started"] is False
                assert current["repository_effective"] is False
                assert current["preserved"]["wp8_g3_reproduction_block"] is True
                assert current["preserved"]["unrecoverable_provenance_warning"] is True
            else:
                operator = _json(WP8 / "ASOCSI_G6_PROVENANCE_SUPERSESSION_OPERATOR_DECISION_v0_1.json")
                assert current.get("stage1_reveal_started", False) is False
                assert current["authority_required"] == "SATISFIED_OPERATOR_PASS"
                assert current["gate_id"] == "ASOCSI-G6-PROVENANCE-SUPERSESSION"
                assert operator["decision"] == "PASS" and operator["authority"] == "OPERATOR"
                assert current["preserved"]["unrecoverable_provenance_warning"] is True
        elif current["status"] == "COMPLETED":
            if current["packet_id"] == "ASOCSI-WP8-S01-STAGE1-C1-CASE-NARRATIVE-FIDELITY-SUPERSESSION":
                assert current["authority_delta"] == "NONE"
                assert current["stage1_reveal_started"] is True
                assert current["human_scientific_input_boundary"] is True
                assert current["construct_survival_decision"] == "PROHIBITED_DURING_CASE_REVIEW"
            elif current["packet_id"] == "ASOCSI-WP8-S01-STAGE1-TO-STAGE2-TRANSITION-SUPERSESSION":
                assert current["authority_delta"] == "SCOPED_FROZEN_REVIEW_SEQUENCE_SUPERSESSION"
                assert current["stage1_reveal_started"] is True
                assert current["stage1_review_route_status"] == "SUPERSEDED_UNCOMPLETED"
                assert current["stage1_scientific_conclusion"] == "NOT_ESTABLISHED"
                assert current["stage1_human_completion_required"] is False
                assert current["stage1_complete_session_freeze_required_for_stage2"] is False
                assert current["stage2_preparation_authorized"] is True
                assert current["stage2_reveal_started"] is False
                assert current["stage2_human_scientific_input_required"] is True
                assert current["stage2_human_answer_synthesis_allowed"] is False
                assert current["stage2_to_stage3_freeze_requirement_changed"] is False
                assert current["construct_survival_decision"] == "PROHIBITED_DURING_CASE_REVIEW"
            elif current["packet_id"] == STAGE2_PREP:
                assert current["authority_delta"] == "NONE"
                assert current["stage1_review_route_status"] == "SUPERSEDED_UNCOMPLETED"
                assert current["stage1_scientific_conclusion"] == "NOT_ESTABLISHED"
                assert current["stage2_reveal_prepared"] is True
                assert current["stage2_reveal_started"] is True
                assert current["stage2_human_scientific_input_required"] is True
                assert current["stage2_human_adjudication_started"] is False
                assert current["stage2_human_answer_synthesis_allowed"] is False
                assert current["stage2_complete_session_freeze_required_before_stage3"] is True
                assert current["stage3_reveal_started"] is False
                assert current["human_scientific_input_boundary"] is True
                assert current["construct_survival_decision"] == "PROHIBITED_DURING_CASE_REVIEW"
            else:
                raise AssertionError(f"unrecognized completed ASOCSI WP8 state: {current['packet_id']}")
            assert current["preserved"]["wp8_g3_reproduction_block"] is True
            assert current["preserved"]["unrecoverable_provenance_warning"] is True
        else:
            assert current["stop_boundary"].startswith("ASOCSI-WP8-STAGED-REVEAL_NOT_AUTHORIZED")
