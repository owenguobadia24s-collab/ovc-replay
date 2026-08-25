from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from ovc.research_operations.asocs.session_batch import (
    ASOCSSessionBatchError,
    PERMANENT_WARNING,
    freeze_session_submission,
    validate_session_submission,
)


ROOT = Path(__file__).resolve().parents[3]
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"
SCHEMAS = ROOT / "schemas/research_operations/asocs"
PACKET = WP8 / "ASOCSI_WP8_S01_STAGE1_REVEAL_PACKET_v0_1.json"
TEMPLATE = WP8 / "ASOCSI_WP8_S01_STAGE1_HUMAN_INPUT_TEMPLATE_v0_1.json"
QA = WP8 / "ASOCSI_WP8_S01_STAGE1_SESSION_BATCH_QA_v0_1.json"
CONTRACT = WP8 / "ASOCSI_WP8_SESSION_BATCH_EXECUTION_CONTRACT_v0_1.json"
POINTER = ROOT / "registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json"


def _j(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _completed_fixture() -> dict:
    value = _j(TEMPLATE)
    for case in value["cases"]:
        judgement = case["human_judgement"]
        judgement["fidelity_disposition"] = "INDETERMINATE"
        judgement["observational_correspondence"] = "fixture-only human boundary value"
        judgement["prior_bridge_disposition"] = "INDETERMINATE"
        judgement["semantic_leakage"] = "INDETERMINATE"
        judgement["traceability"] = "INDETERMINATE"
        judgement["information_gap_disposition"] = "INDETERMINATE"
    value["cases"][0]["human_judgement"]["notes"] = "  exact operator text Ω\nline 2  "
    return value


def test_session_batch_contract_keeps_case_science_and_session_transport_distinct() -> None:
    contract = _j(CONTRACT)
    assert contract["scientific_evidence_unit"] == "INDIVIDUAL_REVIEW_CASE"
    assert contract["operator_transport_unit"] == "COMPLETE_SESSION_STAGE"
    assert contract["reveal_firewall"]["transition_boundary"] == "COMPLETE_SESSION_STAGE_FREEZE"
    assert contract["reveal_firewall"]["individual_case_completion_allows_next_stage"] is False
    assert contract["human_scientific_boundary"]["one_input_file_per_session_stage"] is True
    assert contract["human_scientific_boundary"]["agent_may_answer_for_reviewer"] is False
    assert contract["permanent_warning"] == PERMANENT_WARNING


def test_session1_stage1_packet_has_all_cases_exactly_once_in_frozen_order() -> None:
    packet = _j(PACKET)
    preparation = _j(WP8 / "ASOCSI_WP8_STAGE1_SESSION_01_REVEAL_PACK_v0_1.json")
    assert packet["session"] == packet["stage_index"] == 1
    assert packet["stage"] == "SOURCE_C1_FIDELITY"
    assert packet["case_count"] == len(packet["cases"]) == 25
    assert [case["presentation_ordinal"] for case in packet["cases"]] == list(range(1, 26))
    assert [case["case_id"] for case in packet["cases"]] == [
        case["case_id"] for case in preparation["cases"]
    ]
    assert [case["predecessor_blind_record_sha256"] for case in packet["cases"]] == [
        case["blind_sha256"] for case in preparation["cases"]
    ]
    assert [case["review_unit_id"] for case in packet["cases"]] == [
        case["review_unit_id"] for case in preparation["cases"]
    ]
    assert len({case["case_id"] for case in packet["cases"]}) == 25
    assert all(case["human_judgement"] is None for case in packet["cases"])
    assert all(case["information_gap_disposition"] is None for case in packet["cases"])
    assert all(case["case_validation_status"] == "PENDING_HUMAN_INPUT" for case in packet["cases"])


def test_stage1_packet_exposes_exact_source_and_c1_but_no_later_stage_case_evidence() -> None:
    packet = _j(PACKET)
    anchors = [case for case in packet["cases"] if case["revealed_evidence"]["kind"] == "ANCHOR_15M"]
    gaps = [case for case in packet["cases"] if case["revealed_evidence"]["kind"] == "SOURCE_GAP"]
    assert len(anchors) == 24
    assert len(gaps) == 1
    for case in anchors:
        evidence = case["revealed_evidence"]
        assert set(evidence["source_ohlc"]) == {"open", "high", "low", "close"}
        # The exact reproduced historical trace serialization lawfully omits the
        # redundant repair_applied=false field for complete anchors.
        assert evidence["source_lineage"].get("repair_applied") in {None, False}
        assert evidence["c1"]["construct"] == "C1_ARITHMETIC_PRIMITIVES"
        assert evidence["c1"]["route"] == "MORPHOLOGY_COMPATIBLE"
        assert evidence["c1"]["measurements"]
        assert len(case["relevant_frozen_lineage"]["trace_sha256"]) == 64
    assert gaps[0]["revealed_evidence"]["c1_disposition"] == "C1_NOT_EVALUABLE_SOURCE"
    assert gaps[0]["revealed_evidence"]["repair_applied"] is False
    serialized = PACKET.read_text(encoding="utf-8").casefold()
    assert "upper_stack" not in serialized
    assert "c2_primitive_structure" not in serialized
    assert "c2_composition" not in serialized
    assert "c2e_temporal" not in serialized
    assert "occurrence_context_firewall" not in serialized
    assert packet["later_stage_reveal_status"] == "NOT_CONSTRUCTED_NOT_REVEALED"


def test_one_template_binds_all_25_cases_and_is_deliberately_incomplete() -> None:
    packet = _j(PACKET)
    template = _j(TEMPLATE)
    assert template["reveal_packet_sha256"] == _sha(PACKET)
    assert len(template["cases"]) == 25
    assert [case["case_id"] for case in template["cases"]] == [
        case["case_id"] for case in packet["cases"]
    ]
    assert all(
        case["human_judgement"]["construct_survival_decision"]
        == "PROHIBITED_DURING_CASE_REVIEW"
        for case in template["cases"]
    )
    with pytest.raises(ASOCSSessionBatchError, match="FIDELITY_DISPOSITION_INVALID"):
        validate_session_submission(
            template, reveal_packet=packet, reveal_packet_sha256=_sha(PACKET)
        )


def test_complete_session_validation_rejects_omissions_reordering_and_bad_predecessors() -> None:
    packet = _j(PACKET)
    valid = _completed_fixture()
    validated = validate_session_submission(
        valid, reveal_packet=packet, reveal_packet_sha256=_sha(PACKET)
    )
    assert len(validated["cases"]) == 25
    assert validated["cases"][0]["human_judgement"]["notes"] == "  exact operator text Ω\nline 2  "

    omitted = copy.deepcopy(valid)
    omitted["cases"].pop()
    with pytest.raises(ASOCSSessionBatchError, match="CASE_COUNT_MISMATCH"):
        validate_session_submission(
            omitted, reveal_packet=packet, reveal_packet_sha256=_sha(PACKET)
        )

    reordered = copy.deepcopy(valid)
    reordered["cases"][0], reordered["cases"][1] = reordered["cases"][1], reordered["cases"][0]
    with pytest.raises(ASOCSSessionBatchError, match="ORDER_MISMATCH"):
        validate_session_submission(
            reordered, reveal_packet=packet, reveal_packet_sha256=_sha(PACKET)
        )

    bad_predecessor = copy.deepcopy(valid)
    bad_predecessor["cases"][3]["predecessor_blind_record_sha256"] = "0" * 64
    with pytest.raises(ASOCSSessionBatchError, match="PREDECESSOR_MISMATCH"):
        validate_session_submission(
            bad_predecessor, reveal_packet=packet, reveal_packet_sha256=_sha(PACKET)
        )


def test_complete_submission_freezes_atomically_per_case_and_binds_raw_input(tmp_path: Path) -> None:
    supplied = _completed_fixture()
    submission = tmp_path / "operator-input.json"
    raw_input = json.dumps(supplied, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    submission.write_bytes(raw_input)
    output_parent = tmp_path / "freeze"
    frozen = freeze_session_submission(
        submission_path=submission,
        reveal_packet_path=PACKET,
        output_parent=output_parent,
    )
    records = sorted(frozen.glob("CASE_*.json"))
    assert len(records) == 25
    input_sha = hashlib.sha256(raw_input).hexdigest()
    assert (frozen / "ASOCSI_WP8_S01_STAGE1_HUMAN_INPUT.json").read_bytes() == raw_input
    for path in records:
        record = _j(path)
        assert record["session_human_input_sha256"] == input_sha
        assert record["case_validation_status"] == "PASS"
        assert record["frozen_before_next_reveal"] is True
    receipt = _j(frozen / "ASOCSI_WP8_S01_STAGE1_FREEZE_RECEIPT.json")
    assert receipt["status"] == "FROZEN_COMPLETE_SESSION_STAGE"
    assert receipt["case_count"] == 25
    assert receipt["stage2_reveal_materialized"] is False
    assert not list(frozen.glob("*STAGE2*"))
    with pytest.raises(ASOCSSessionBatchError, match="TARGET_ALREADY_EXISTS"):
        freeze_session_submission(
            submission_path=submission,
            reveal_packet_path=PACKET,
            output_parent=output_parent,
        )


def test_qa_schemas_and_pointer_preserve_the_single_human_boundary() -> None:
    qa = _j(QA)
    assert qa["qa_disposition"] == "PASS_REVEAL_PACKET_AND_TEMPLATE_ONLY"
    assert qa["checks"]["single_session_human_input_template"] == "PASS_ONE_FILE_25_CASES"
    assert qa["checks"]["upper_stack_evidence_concealed"] == "PASS"
    assert qa["later_stage_reveal_status"] == "NOT_CONSTRUCTED_NOT_REVEALED"
    assert qa["reveal_packet_sha256"] == _sha(PACKET)
    assert qa["human_input_template_sha256"] == _sha(TEMPLATE)
    assert _j(SCHEMAS / "asocs_session_stage_human_input_v0_1.schema.json")
    reveal_record = _j(SCHEMAS / "asocs_reveal_stage_record_v0_1.schema.json")
    assert {
        "session",
        "presentation_ordinal",
        "review_unit_id",
        "session_human_input_sha256",
        "case_validation_status",
    }.issubset(reveal_record["required"])
    pointer = _j(POINTER)
    state = _j(ROOT / pointer["current_state"])
    assert state["gate_id"] == "ASOCSI-G6-PROVENANCE-SUPERSESSION"
    assert state["authority_required"] == "SATISFIED_OPERATOR_PASS"
    expected_next = (
        "ASOCSI-WP8-S01-STAGE1-C1-CASE-NARRATIVE-HUMAN-ADJUDICATION"
        if state["packet_id"]
        == "ASOCSI-WP8-S01-STAGE1-C1-CASE-NARRATIVE-FIDELITY-SUPERSESSION"
        else "ASOCSI-WP8-STAGE1-HUMAN-FIDELITY-ADJUDICATION"
    )
    assert pointer["next_packet"] == state["next_packet"] == expected_next
