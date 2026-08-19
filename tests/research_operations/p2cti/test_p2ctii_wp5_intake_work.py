from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.canonical import canonical_sha256
from ovc.research_operations.p2cti.intake import (
    IntakeValidationError,
    build_intake_triage,
    build_theory_seed,
    exact_source_reference,
)
from ovc.research_operations.p2cti.work import (
    WorkValidationError,
    build_abandonment,
    build_deferral,
    build_reentry,
    build_work_ticket,
    project_work_queue,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/research_operations/p2cti/P2CTII_WP5_SYNTHETIC_INTAKE_FIXTURE_v0_1.json"
FRONTIER = "p2cti:frontier:" + "a" * 64


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _assert_record(record: dict, object_type: str) -> None:
    assert record["schema_family"] == "P2CTI_CONTROL"
    assert record["schema_version"] == "0.1"
    assert record["object_type"] == object_type
    assert record["authority_effect"] == "NONE"
    assert record["source_frontier_id"] == FRONTIER
    body = {key: value for key, value in record.items() if key != "content_sha256"}
    assert record["content_sha256"] == canonical_sha256(body)


def test_theory_seed_is_reference_only_content_addressed_and_non_authoritative() -> None:
    fixture = _fixture()
    first = build_theory_seed(
        source_frontier_id=FRONTIER,
        seed_key=fixture["seed_key"],
        title=fixture["title"],
        source_ref=fixture["source_ref"],
    )
    second = build_theory_seed(
        source_frontier_id=FRONTIER,
        seed_key=fixture["seed_key"],
        title=fixture["title"],
        source_ref=dict(reversed(list(fixture["source_ref"].items()))),
    )
    changed_title = build_theory_seed(
        source_frontier_id=FRONTIER,
        seed_key=fixture["seed_key"],
        title=fixture["title"] + " amended",
        source_ref=fixture["source_ref"],
    )
    assert first == second
    assert changed_title["record_id"] != first["record_id"]
    assert changed_title["payload"]["seed_id"] != first["payload"]["seed_id"]
    _assert_record(first, "THEORY_SEED")
    payload = first["payload"]
    assert payload["source_ref"]["scientific_payload_copied"] is False
    assert payload["owner_object_created"] is False
    assert payload["write_activation"] is False
    assert payload["scientific_effect"] == "NONE"
    assert payload["candidate_effect"] == "NONE"
    assert payload["visibility_state"] == "RESTRICTED"


def test_source_reference_fails_closed_on_payload_copy_and_bad_shape() -> None:
    source = _fixture()["source_ref"]
    with pytest.raises(IntakeValidationError):
        exact_source_reference({**source, "scientific_payload_copied": True})
    with pytest.raises(IntakeValidationError):
        exact_source_reference({**source, "scientific_payload": {"claim": "copied"}})
    with pytest.raises(IntakeValidationError):
        exact_source_reference({**source, "content_sha256": "BAD"})


@pytest.mark.parametrize(
    ("design", "expected", "action"),
    [
        ("FORMALISE_NOW", "READY_FOR_GUIDED_FORMALISATION", None),
        ("DEFER", "DEFERRED", None),
        ("DESCRIPTIVE_LANGUAGE_ONLY", "DESCRIPTIVE_LANGUAGE_ONLY", None),
        ("DUPLICATE_OR_NEAR_DUPLICATE", "UNMAPPED_REVIEW_REQUIRED", "LINEAGE_REVIEW"),
        ("DEPENDENCY_UNAVAILABLE", "UNMAPPED_REVIEW_REQUIRED", "DEPENDENCY_REVIEW"),
        ("OUT_OF_SCOPE", "UNMAPPED_REVIEW_REQUIRED", "SCOPE_REVIEW"),
    ],
)
def test_intake_triage_reuses_exact_dmrp_mapping_without_silent_coercion(design: str, expected: str, action: str | None) -> None:
    record = build_intake_triage(
        source_frontier_id=FRONTIER,
        seed_or_theory_ref="p2cti:seed:synthetic",
        design_disposition=design,
        reason_codes=[],
    )
    _assert_record(record, "INTAKE_TRIAGE")
    assert record["payload"]["disposition"] == expected
    assert record["payload"]["required_action"] == action
    assert record["payload"]["write_activation"] is False
    assert record["payload"]["candidate_effect"] == "NONE"


def test_intake_rejects_unknown_disposition_reason_code_and_decision_bearing_fields() -> None:
    with pytest.raises(IntakeValidationError):
        build_intake_triage(source_frontier_id=FRONTIER, seed_or_theory_ref="x", design_disposition="FORMALISE_BEST", reason_codes=[])
    with pytest.raises(IntakeValidationError, match="unknown reason codes"):
        build_intake_triage(source_frontier_id=FRONTIER, seed_or_theory_ref="x", design_disposition="DEFER", reason_codes=["CONVENIENT_UNREGISTERED_REASON"])
    source = _fixture()["source_ref"]
    with pytest.raises(IntakeValidationError):
        build_theory_seed(source_frontier_id=FRONTIER, seed_key="x", title="x", source_ref={**source, "risk_score": 1})


def test_work_ticket_is_closed_registry_advisory_telemetry_not_priority() -> None:
    ticket = build_work_ticket(
        source_frontier_id=FRONTIER,
        ticket_key="T1",
        subject_ref="theory:g1",
        work_class="THEORY_FORMALISATION",
        work_state="READY",
        authority_refs=["P2CTII-G0", "P2CTII-G4-ALG-PASS"],
        created_at="2026-08-19T12:00:00Z",
        operator_touch_count=2,
        effort_units=3,
    )
    _assert_record(ticket, "WORK_TICKET")
    assert ticket["payload"]["priority_score"] is None
    assert ticket["payload"]["quota_effect"] == "NONE"
    assert ticket["payload"]["execution_authority"] == "NONE"
    with pytest.raises(WorkValidationError):
        build_work_ticket(source_frontier_id=FRONTIER, ticket_key="T2", subject_ref="x", work_class="ALPHA_HUNT", work_state="READY", authority_refs=["P2CTII-G0"], created_at="2026-08-19T12:00:00Z")


def test_deferral_abandonment_and_reentry_are_append_only_non_scientific_controls() -> None:
    deferral = build_deferral(source_frontier_id=FRONTIER, subject_ref="theory:g1", reason_codes=["CURRENTNESS_UNRESOLVED"], wake_triggers=["OWNER_FRONTIER_ADVANCES"])
    abandonment = build_abandonment(source_frontier_id=FRONTIER, subject_ref="theory:g1", reason_codes=["DESIGN_CONTRADICTION"])
    reentry = build_reentry(source_frontier_id=FRONTIER, subject_ref="theory:g1", prior_disposition_ref=deferral["record_id"], trigger_refs=["owner:evidence:g2"])
    _assert_record(deferral, "DEFERRAL")
    _assert_record(abandonment, "ABANDONMENT")
    _assert_record(reentry, "REENTRY")
    assert abandonment["payload"]["preserve_evidence"] is True
    assert abandonment["payload"]["scientific_deletion"] is False
    assert all(record["payload"]["write_activation"] is False for record in (deferral, abandonment, reentry))


def test_queue_projection_is_order_independent_non_decision_bearing_and_age_only() -> None:
    early = build_work_ticket(source_frontier_id=FRONTIER, ticket_key="A", subject_ref="A", work_class="EVIDENCE_REVIEW", work_state="READY", authority_refs=["P2CTII-G0"], created_at="2026-08-19T11:00:00Z")
    late = build_work_ticket(source_frontier_id=FRONTIER, ticket_key="B", subject_ref="B", work_class="THEORY_FORMALISATION", work_state="BLOCKED", authority_refs=["P2CTII-G0"], created_at="2026-08-19T12:00:00Z")
    one = project_work_queue([early, late], as_of="2026-08-19T13:00:00Z")
    two = project_work_queue([late, early], as_of="2026-08-19T13:00:00Z")
    assert one == two
    assert one["decision_bearing"] is False
    assert one["priority_score"] is None
    assert one["quota_effect"] == "NONE"
    assert one["write_activation"] is False
    assert sorted(row["queue_age_seconds"] for row in one["rows"]) == [3600, 7200]


def test_queue_rejects_mutated_or_future_ticket() -> None:
    ticket = build_work_ticket(source_frontier_id=FRONTIER, ticket_key="A", subject_ref="A", work_class="EVIDENCE_REVIEW", work_state="READY", authority_refs=["P2CTII-G0"], created_at="2026-08-19T14:00:00Z")
    with pytest.raises(WorkValidationError):
        project_work_queue([ticket], as_of="2026-08-19T13:00:00Z")
    mutated = dict(ticket)
    mutated["payload"] = {**ticket["payload"], "work_state": "COMPLETED"}
    with pytest.raises(WorkValidationError):
        project_work_queue([mutated], as_of="2026-08-19T15:00:00Z")
