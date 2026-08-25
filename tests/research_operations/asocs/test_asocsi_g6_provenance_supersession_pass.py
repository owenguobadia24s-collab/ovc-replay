from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"
POINTER = ROOT / "registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json"


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
    assert {"VALIDATION","EC1","PUBLICATION","PROBABILITY","RISK","EXPOSURE","TRADING","EXECUTION","AGENT_WRITE"}.issubset(set(effect["non_grants"]))


def test_approved_state_preserves_frozen_lineage_and_points_to_stage1() -> None:
    pointer = _json(POINTER)
    state = _json(ROOT / pointer["current_state"])
    assert pointer["status"] == state["status"] == "APPROVED"
    assert pointer["next_packet"] == state["next_packet"] == "ASOCSI-WP8-STAGE1-HUMAN-FIDELITY-ADJUDICATION"
    assert state["authority_required"] == "SATISFIED_OPERATOR_PASS"
    assert state["preserved"]["g3_frozen_generation"] is True
    assert state["preserved"]["g4_review_population"] is True
    assert state["preserved"]["g5_human_evidence"] is True
    assert state["preserved"]["stage1_reveal_started"] is False
    assert state["preserved"]["unrecoverable_provenance_warning"] is True
