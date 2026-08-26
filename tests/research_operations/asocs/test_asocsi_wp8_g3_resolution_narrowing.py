from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
WP5 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp5"
WP6 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp6"
WP7 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp7"
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"
STATE = ROOT / "records/research_operations/asocs"
POINTER = ROOT / "registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json"

FROZEN_CENSUS = "c49f34e7af19f0110d24377a54ab8f0bd3fb183e83e924de07bf39cd586de2c7"
FROZEN_ORDERED = "bcd571f567068035592bb0d868747cfe85e8aaa01155b1fa8c798f488f6ef0d7"
FROZEN_TRACES = "22c856efdd24083d5339d2082ad9714597e326a6f40655bfb82b0afa9899f7dc"
FROZEN_G4 = "ff6eb37724aea5b2706666903f7b5a1bc063af8ef9026f4496429b5e33fa15fe"
NARROWED_STATE = "records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_23_WP8_G3_CENSUS_IDENTITY_BLOCKED.json"
RESOLUTION_EFFECTIVE = "ASOCSI-WP8-G3-REPRODUCTION-INTEGRITY-RESOLUTION_REPOSITORY_EFFECTIVE"
CHECKPOINTS = {
    "4392": "91004c82e3a4134a32b1afe4e41559652b978589b8043e9abe9f7e818ccf0709",
    "8784": "d005f3225ea5a268fc9a223995f5cadfbb6611f374002eca02df266407b781ee",
    "13176": "c99129aa61f5471f8e7574471fb190057def3efa918a72014e58a3232b607632",
    "17568": "8ea8eabd040a0bc193a34ff792c49f7eb83739c72c5caa69f7234a88159e6f0c",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def state_generation(path: str) -> int:
    match = re.search(r"ASOCSI_PROGRAMME_STATE_v0_(\d+)_", path)
    assert match is not None, path
    return int(match.group(1))


def test_resolution_evidence_reproduces_every_resolved_frozen_identity() -> None:
    evidence = load(WP8 / "ASOCSI_WP8_G3_REPRODUCTION_RESOLUTION_EVIDENCE_v0_1.json")
    reproduction = evidence["resolution_paths"]["historical_deterministic_reconstruction"]
    assert reproduction["source_sha256"] == "210233ec5761bf82998172832bb554ddf10dfeb3099f6bc6488d5bb0f6bec4f2"
    assert reproduction["g1_audit_15m_sha256"] == "df060a22bf8a6c1d990d22af90e189848bd2c5f3090ef65a8c5637e4456bb7d9"
    assert reproduction["frozen"]["observation_traces"] == {
        "byte_size": 10995130,
        "compression": "gzip-mtime-0-jsonl",
        "record_count": 17568,
        "sha256": FROZEN_TRACES,
    }
    assert reproduction["frozen"]["ordered_trace_ids_sha256"] == FROZEN_ORDERED
    assert reproduction["frozen"]["checkpoints"] == CHECKPOINTS
    assert reproduction["checkpoints_reproduced"] is True
    assert reproduction["observation_trace_bytes_reproduced"] is True
    assert reproduction["two_independent_clean_runs_equal"] is True
    assert {run["artifact_sha256"] for run in reproduction["independent_runs"]} == {FROZEN_TRACES}
    assert {run["byte_size"] for run in reproduction["independent_runs"]} == {10995130}
    assert reproduction["trace_serialization_cause"]["c1_formula_change"] is False
    assert reproduction["trace_serialization_cause"]["g1_change"] is False


def test_census_identity_remains_fail_closed_without_replacing_frozen_g3() -> None:
    evidence = load(WP8 / "ASOCSI_WP8_G3_REPRODUCTION_RESOLUTION_EVIDENCE_v0_1.json")
    census = evidence["resolution_paths"]["historical_deterministic_reconstruction"]["census_identity"]
    assert census["frozen_sha256"] == FROZEN_CENSUS
    assert census["status"] == "UNRESOLVED_HISTORICAL_IDENTITY_CONSTRUCTION"
    assert census["compact_manifest_expected_sha256"] == "b8b4caeca0c9e234339c07053bac6c65040d0cb14c9abfca08590526e5b4a3da"
    assert census["compact_manifest_expected_byte_size"] == 2712
    assert census["compact_manifest_original_bytes_recovered"] is False
    qa = load(WP8 / "ASOCSI_WP8_G3_REPRODUCTION_RESOLUTION_QA_v0_1.json")
    assert qa["qa_recommendation"] == "BLOCK"
    assert qa["checks"]["frozen_census_sha256"] == "FAIL_UNRESOLVED_IDENTITY_CONSTRUCTION"
    decision = load(WP8 / "ASOCSI_WP8_G3_REPRODUCTION_RESOLUTION_DECISION_v0_1.json")
    assert decision["decision"] == "BLOCK"
    assert decision["authority_delta"] == "NONE"
    assert decision["operator_decision_required"] is False


def test_historical_g3_g4_g5_frozen_evidence_is_unchanged_and_reveal_denied() -> None:
    g3 = load(WP5 / "ASOCSI_G3_CENSUS_FREEZE_v0_1.json")
    assert g3["census_sha256"] == FROZEN_CENSUS
    assert g3["freeze_scope"]["ordered_trace_ids_sha256"] == FROZEN_ORDERED
    assert g3["external_artifacts"]["observation_traces"]["sha256"] == FROZEN_TRACES

    g4 = load(WP6 / "ASOCSI_G4_REVIEW_POPULATION_FREEZE_v0_1.json")
    assert g4["review_population_sha256"] == FROZEN_G4
    assert g4["g3_census_sha256"] == FROZEN_CENSUS

    g5 = load(WP7 / "ASOCSI_G5_BLIND_EVIDENCE_FREEZE_v0_1.json")
    assert g5["status"] == "FROZEN"
    assert g5["identity_integrity"]["human_payload_mutation"] == "NONE"
    assert g5["blindness"]["reveal_started"] is False

    evidence = load(WP8 / "ASOCSI_WP8_G3_REPRODUCTION_RESOLUTION_EVIDENCE_v0_1.json")
    assert evidence["lineage_proof"]["result"] == "PASS_UNCHANGED"
    assert evidence["meaning_bearing_correction_attempted"] is False
    assert evidence["stage1_reveal_allowed"] is False


def test_programme_state_preserves_narrowed_block_across_lawful_successors() -> None:
    narrowed = load(ROOT / NARROWED_STATE)
    assert narrowed["status"] == "BLOCKED"
    assert narrowed["authority_delta"] == "NONE"
    assert narrowed["blockers"] == [
        "G3_FROZEN_CENSUS_IDENTITY_AND_COMPACT_MANIFEST_CONSTRUCTION_NOT_REPRODUCIBLE"
    ]
    assert narrowed["preserved"] == {
        "g3_frozen_generation": True,
        "g4_review_population": True,
        "g5_human_evidence": True,
    }
    assert narrowed["human_adjudication_started"] is False
    assert narrowed["stage1_reveal_started"] is False

    pointer = load(POINTER)
    current = load(ROOT / pointer["current_state"])
    assert pointer["programme_id"] == current["programme_id"] == narrowed["programme_id"]
    assert pointer["packet_id"] == current["packet_id"]
    assert pointer["status"] == current["status"]
    assert pointer["next_packet"] == current["next_packet"]
    assert state_generation(pointer["current_state"]) >= state_generation(NARROWED_STATE)
    assert current.get("human_adjudication_started", False) is False
    assert current.get("stage2_reveal_started", False) is False

    if pointer["current_state"] == NARROWED_STATE:
        assert current.get("stage1_reveal_started", False) is False
        assert pointer["packet_id"] == "ASOCSI-WP8-G3-REPRODUCTION-INTEGRITY-RESOLUTION"
        assert pointer["status"] == "BLOCKED"
        assert pointer["next_packet"] == "ASOCSI-WP8-G3-CENSUS-IDENTITY-RESOLUTION"
        return

    prerequisites = set(current.get("prerequisites", []))
    preserved = current.get("preserved", {})
    assert RESOLUTION_EFFECTIVE in prerequisites or preserved.get("wp8_g3_reproduction_block") is True
    assert preserved["g3_frozen_generation"] is True
    assert preserved["g4_review_population"] is True
    assert preserved["g5_human_evidence"] is True
    assert current["evidence"]["frozen_census_sha256"] == FROZEN_CENSUS
    assert current["evidence"]["frozen_ordered_trace_ids_sha256"] == FROZEN_ORDERED
    assert current["evidence"]["frozen_observation_trace_sha256"] == FROZEN_TRACES

    if current["status"] == "GATE_READY":
        assert current.get("stage1_reveal_started", False) is False
        assert current["authority_required"] == "OPERATOR_REQUIRED"
        assert current["stop_boundary"] == "ASOCSI-G6-PROVENANCE-SUPERSESSION-OPERATOR-DECISION"
    elif current["status"] == "APPROVED":
        operator = load(WP8 / "ASOCSI_G6_PROVENANCE_SUPERSESSION_OPERATOR_DECISION_v0_1.json")
        assert current.get("stage1_reveal_started", False) is False
        assert current["authority_required"] == "SATISFIED_OPERATOR_PASS"
        assert current["gate_id"] == "ASOCSI-G6-PROVENANCE-SUPERSESSION"
        assert operator["decision"] == "PASS" and operator["authority"] == "OPERATOR"
        assert preserved["unrecoverable_provenance_warning"] is True
    elif current["status"] == "COMPLETED":
        assert preserved["wp8_g3_reproduction_block"] is True
        assert preserved["unrecoverable_provenance_warning"] is True
        assert current["construct_survival_decision"] == "PROHIBITED_DURING_CASE_REVIEW"
        if current["packet_id"] == "ASOCSI-WP8-S01-STAGE1-TO-STAGE2-TRANSITION-SUPERSESSION":
            assert current["authority_delta"] == "SCOPED_FROZEN_REVIEW_SEQUENCE_SUPERSESSION"
            assert current["stage1_review_route_status"] == "SUPERSEDED_UNCOMPLETED"
            assert current["stage1_scientific_conclusion"] == "NOT_ESTABLISHED"
            assert current["stage1_complete_session_freeze_required_for_stage2"] is False
            assert current["stage1_human_completion_required"] is False
            assert current["stage2_preparation_authorized"] is True
            assert current["stage2_human_scientific_input_required"] is True
            assert current["stage2_human_answer_synthesis_allowed"] is False
            assert current["stage2_to_stage3_freeze_requirement_changed"] is False
            assert current["next_packet"] == "ASOCSI-WP8-S01-STAGE2-C2-PRIMITIVE-STRUCTURE-PREPARATION"
        else:
            assert current["packet_id"] in {
                "ASOCSI-WP8-S01-STAGE1-HUMAN-REVIEW-INTERFACE",
                "ASOCSI-WP8-S01-STAGE1-C1-CASE-NARRATIVE-FIDELITY-SUPERSESSION",
            }
            assert current["authority_delta"] == "NONE"
            assert current["stage1_reveal_started"] is True
            assert current["human_scientific_input_boundary"] is True
            expected_next = (
                "ASOCSI-WP8-S01-STAGE1-C1-CASE-NARRATIVE-HUMAN-ADJUDICATION"
                if current["packet_id"]
                == "ASOCSI-WP8-S01-STAGE1-C1-CASE-NARRATIVE-FIDELITY-SUPERSESSION"
                else "ASOCSI-WP8-STAGE1-HUMAN-FIDELITY-ADJUDICATION"
            )
            assert current["next_packet"] == expected_next
    else:
        raise AssertionError(f"unexpected successor status: {current['status']}")
