from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ovc.research_operations.asocs.audit_execution import (
    ASOCSAuditRouteError,
    UPPER_CONSTRUCTS,
    evaluate_c1_morphology,
    not_evaluable_record,
    route_for_construct,
)

ROOT = Path(__file__).resolve().parents[3]


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def test_wp4_route_is_fail_closed_and_no_exact_interface_is_claimed() -> None:
    matrix = _json(
        "docs/programmes/asocs-v0-1/implementation/wp4/"
        "ASOCSI_WP4_AUDIT_ROUTE_MATRIX_v0_1.json"
    )
    assert matrix["claim_class"] == "ASOCS_SINGLE_STREAM_MORPHOLOGY_COHERENCE"
    assert matrix["source_side_state"] == "UNRESOLVED_SINGLE_STREAM"
    assert matrix["source_clock_state"] == "SOURCE_TIMEZONE_UNRESOLVED"
    assert all(r["exact_active_interface"] == "NOT_EVALUABLE_EXACT_ACTIVE_INTERFACE" for r in matrix["rows"])
    routes = {r["construct"]: r["morphology_route"] for r in matrix["rows"]}
    assert routes["C1_ARITHMETIC_PRIMITIVES"] == "MORPHOLOGY_COMPATIBLE"
    assert all(routes[name] == "NOT_EVALUABLE" for name in UPPER_CONSTRUCTS)


def test_c1_morphology_reuses_exact_frozen_formula_without_fabricating_identity() -> None:
    result = evaluate_c1_morphology(
        {"open": "1.1000", "high": "1.1020", "low": "1.0990", "close": "1.1010"}
    )
    assert result["measurements"]["range_abs"] == "0.003"
    assert result["measurements"]["body_signed"] == "0.001"
    assert result["measurements"]["range_ticks"] is None
    assert result["null_reasons"]["range_ticks"] == "PRICE_INCREMENT_UNAVAILABLE"
    assert result["null_reasons"]["true_range_abs"] == "SOURCE_CONTINUITY_UNRESOLVED_OR_GAP"
    assert result["authority_class"] == "ASOCS_AUDIT_ONLY"
    assert result["active"] is result["canonical"] is result["publication"] is False


def test_c1_formula_blob_is_exactly_the_g2_frozen_owner_code() -> None:
    freeze = _json(
        "docs/programmes/asocs-v0-1/implementation/wp3/"
        "ASOCSI_G2_RUNTIME_IDENTITY_FREEZE_v0_1.json"
    )
    entry = next(x for x in freeze["c1"]["implementation_blobs"] if x["path"].endswith("/formulas.py"))
    assert _git_blob_sha(ROOT / entry["path"]) == entry["blob_sha"]


def test_adapter_rejects_semantic_identity_injection() -> None:
    with pytest.raises(ASOCSAuditRouteError, match="FORBIDDEN_SEMANTIC_INPUT"):
        evaluate_c1_morphology({
            "open": "1", "high": "2", "low": "0", "close": "1.5",
            "price_side": "BID",
        })


def test_upper_stack_never_receives_invented_morphology_semantics() -> None:
    for construct in UPPER_CONSTRUCTS:
        assert route_for_construct(construct) == "NOT_EVALUABLE"
        record = not_evaluable_record(construct)
        assert record["disposition"] == "NOT_EVALUABLE"
        assert "NO_MEANING_BEARING_SHADOW_REIMPLEMENTATION" in record["reason_codes"]
        assert record["active"] is record["canonical"] is record["publication"] is False


def test_wp4_qa_and_state_preserve_authority_and_route_to_wp5() -> None:
    qa = _json(
        "docs/programmes/asocs-v0-1/implementation/wp4/ASOCSI_WP4_QA_PACKET_v0_1.json"
    )
    decision = _json(
        "docs/programmes/asocs-v0-1/implementation/wp4/"
        "ASOCSI_WP4_DELEGATED_DECISION_v0_1.json"
    )
    state = _json("records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_6_WP4.json")
    pointer = _json("registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json")
    current_state = _json(pointer["current_state"])
    assert qa["qa_recommendation"] == "PASS"
    assert qa["blocking_findings"] == []
    assert qa["authority_delta"] == "NONE"
    assert decision["decision"] == "PASS_DELEGATED"
    assert state["status"] == "COMPLETED"
    assert state["next_packet"] == "ASOCSI-WP5"
    assert pointer["programme_id"] == "OVC-ASOCS-6M-v0.1"
    assert current_state["status"] == "COMPLETED"
    assert pointer["packet_id"] == current_state["packet_id"]
    assert pointer["next_packet"] == current_state["next_packet"]
