from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"
POINTER = ROOT / "registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json"
G6_STATE = ROOT / "records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_25_G6_PROVENANCE_SUPERSESSION_APPROVED.json"
STAGE2_PREP = "ASOCSI-WP8-S01-STAGE2-C2-PRIMITIVE-STRUCTURE-PREPARATION"
STAGE2_HUMAN = "ASOCSI-WP8-S01-STAGE2-C2-PRIMITIVE-STRUCTURE-HUMAN-ADJUDICATION"
STAGE2_NATIVE_ROUTE = "ASOCSI-WP8-S01-STAGE2-C2-NATIVE-OBSERVATION-ROUTE-AMENDMENT"
STAGE2_NATIVE_REPLAY = "ASOCSI-WP8-S01-STAGE2-C2-NATIVE-OBSERVATION-REPLAY"
STAGE2_NATIVE_HUMAN = "ASOCSI-WP8-S01-STAGE2-C2-NATIVE-OBSERVATION-HUMAN-ADJUDICATION"

# Successor-state assertions distinguish immutable historical evidence from the lawful current Stage-2 reveal state.


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_operator_pass_supersedes_only_exact_manifest_reproduction_precondition() -> None:
    decision = _json(WP8 / "ASOCSI_G6_PROVENANCE_SUPERSESSION_OPERATOR_DECISION_v0_1.json")
    effect = _json(WP8 / "ASOCSI_G6_PROVENANCE_SUPERSESSION_AUTHORITY_EFFECT_v0_1.json")
    assert decision["decision"] == "PASS"
    assert decision["authority"] == "OPERATOR"
    assert decision["provenance_disposition"]["classification"] == "UNRECOVERABLE_PROVENANCE"
    assert decision["provenance_disposition"]["permanent_warning_required"] is True
    assert effect["authority_delta"] == "SUPERSEDE_ONE_G3_REPRODUCTION_ACCEPTANCE_PRECONDITION_ONLY"
    assert "RESUME_ASOCSI_WP8_STAGE1_REVEAL_PREPARATION" in effect["grants"]
    assert "RESUME_STAGE1_HUMAN_FIDELITY_ADJUDICATION_UNDER_EXISTING_NONAUTHORITATIVE_ASOCS_RESEARCH_SCOPE" in effect["grants"]
    assert {"VALIDATION", "EC1", "PUBLICATION", "PROBABILITY", "RISK", "EXPOSURE", "TRADING", "EXECUTION", "AGENT_WRITE"}.issubset(set(effect["non_grants"]))


def test_approved_g6_state_remains_immutable_while_current_state_may_advance_lawfully() -> None:
    g6 = _json(G6_STATE)
    assert g6["status"] == "APPROVED"
    assert g6["gate_id"] == "ASOCSI-G6-PROVENANCE-SUPERSESSION"
    assert g6["authority_required"] == "SATISFIED_OPERATOR_PASS"
    assert g6["next_packet"] == "ASOCSI-WP8-STAGE1-HUMAN-FIDELITY-ADJUDICATION"
    assert g6["preserved"]["g3_frozen_generation"] is True
    assert g6["preserved"]["g4_review_population"] is True
    assert g6["preserved"]["g5_human_evidence"] is True
    assert g6["preserved"]["stage1_reveal_started"] is False
    assert g6["preserved"]["unrecoverable_provenance_warning"] is True

    pointer = _json(POINTER)
    current = _json(ROOT / pointer["current_state"])
    assert pointer["programme_id"] == current["programme_id"] == g6["programme_id"]
    assert pointer["status"] == current["status"]
    assert pointer["next_packet"] == current["next_packet"]
    assert current["preserved"]["g3_frozen_generation"] is True
    assert current["preserved"]["g4_review_population"] is True
    assert current["preserved"]["g5_human_evidence"] is True
    assert current["preserved"]["wp8_g3_reproduction_block"] is True
    assert current["preserved"]["unrecoverable_provenance_warning"] is True
    assert current.get("human_adjudication_started", False) is False

    if current["packet_id"] in {STAGE2_PREP, STAGE2_HUMAN, STAGE2_NATIVE_ROUTE, STAGE2_NATIVE_HUMAN}:
        assert current["stage2_reveal_started"] is True
        assert current["stage2_reveal_prepared"] is True
        assert current["stage2_human_adjudication_started"] is False
        assert current["required_human_input_started"] is False
        assert current["stage2_complete_session_freeze_required_before_stage3"] is True
        assert current["stage3_reveal_started"] is False
        assert current["stage1_review_route_status"] == "SUPERSEDED_UNCOMPLETED"
        assert current["stage1_scientific_conclusion"] == "NOT_ESTABLISHED"
        if current["packet_id"] == STAGE2_NATIVE_ROUTE:
            assert current["status"] == "APPROVED"
            assert current["authority_required"] == "OPERATOR_REQUIRED_SATISFIED"
            assert current["repository_effective"] is False
            assert current["stage2_human_scientific_input_required"] is True
            assert current["stage2_human_answer_synthesis_allowed"] is False
            assert current["next_packet"] == STAGE2_NATIVE_REPLAY
        elif current["packet_id"] == STAGE2_NATIVE_HUMAN:
            assert current["status"] == "GATE_READY"
            assert current["authority_required"] == "HUMAN_SCIENTIFIC_INPUT"
            assert current["stage2_human_answer_count"] == 0
            assert current["next_packet"] == STAGE2_NATIVE_HUMAN
        else:
            assert current["next_packet"] == STAGE2_HUMAN
            if current["packet_id"] == STAGE2_HUMAN:
                assert current["status"] == "GATE_READY"
                assert current["authority_required"] == "HUMAN_SCIENTIFIC_INPUT"
                assert current["stage2_human_answer_count"] == 0
    elif current["packet_id"] == "ASOCSI-WP8-S01-STAGE1-TO-STAGE2-TRANSITION-SUPERSESSION":
        assert current.get("stage2_reveal_started", False) is False
        assert current["stage1_review_route_status"] == "SUPERSEDED_UNCOMPLETED"
        assert current["stage1_scientific_conclusion"] == "NOT_ESTABLISHED"
        assert current["stage1_complete_session_freeze_required_for_stage2"] is False
        assert current["stage2_preparation_authorized"] is True
        assert current["stage2_human_scientific_input_required"] is True
        assert current["stage2_human_answer_synthesis_allowed"] is False
        assert current["next_packet"] == STAGE2_PREP
    elif current["packet_id"] == "ASOCSI-WP8-S01-STAGE1-C1-CASE-NARRATIVE-FIDELITY-SUPERSESSION":
        assert current.get("stage2_reveal_started", False) is False
        assert current["next_packet"] == "ASOCSI-WP8-S01-STAGE1-C1-CASE-NARRATIVE-HUMAN-ADJUDICATION"
    else:
        assert current.get("stage2_reveal_started", False) is False
        assert current["next_packet"] == "ASOCSI-WP8-STAGE1-HUMAN-FIDELITY-ADJUDICATION"
