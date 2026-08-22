from __future__ import annotations

from dataclasses import replace

import pytest

from ovc.shared_systems.assurance import (
    AssuranceAssertionResult,
    AssuranceAssertionSpec,
    AssurancePacket,
    AssuranceSuite,
    ChangeAssessment,
    ImpactDependencyEdge,
    IncidentRecord,
    QualificationRecord,
    QuarantineRecord,
    SharedAssuranceError,
    build_invalidation_plan,
    deterministic_read_model,
    qualification_currentness,
)


def assertion() -> AssuranceAssertionSpec:
    return AssuranceAssertionSpec(
        "A1",
        "v1",
        "OWNER",
        "CONTRACT_CONFORMANCE",
        "C.v1",
        "exact fields",
        "ALL",
        ("P1",),
        ("E1",),
        "EXACT",
        "BLOCK",
        "BLOCK",
    )


def qualification(status: str = "QUALIFIED") -> QualificationRecord:
    return QualificationRecord(
        "Q1",
        "SERVICE.1",
        "RELEASE.1",
        "GEN.1",
        "CAP",
        "REFERENCE",
        "ENV.1",
        "SOURCE.1",
        "SCOPE.1",
        ("E1",),
        status,
    )


def currentness(record: QualificationRecord, **changes: object):
    scope = {
        "target_ref": "SERVICE.1",
        "release_ref": "RELEASE.1",
        "generation_ref": "GEN.1",
        "capability": "CAP",
        "role": "REFERENCE",
        "environment_ref": "ENV.1",
        "source_ref": "SOURCE.1",
        "semantic_scope": "SCOPE.1",
    }
    scope.update(changes)
    return qualification_currentness(record, **scope)


def test_claim_scoped_assurance_cannot_launder_authority() -> None:
    assert assertion().authority_effect == "NONE"
    with pytest.raises(SharedAssuranceError, match="LAUNDERING"):
        replace(assertion(), authority_effect="SCIENTIFIC_AUTHORITY")
    with pytest.raises(SharedAssuranceError, match="LAUNDERING"):
        AssuranceAssertionResult(
            "A1", "S", "PASS", ("E",), authority_effect="OPERATOR_PASS"
        )


def test_non_transitivity_is_an_explicit_assurance_class() -> None:
    assert replace(assertion(), assurance_class="NON_TRANSITIVITY").assurance_class == (
        "NON_TRANSITIVITY"
    )


def test_mandatory_failure_cannot_be_averaged_away() -> None:
    result = AssuranceAssertionResult("A1", "S", "FAIL", ("E",), ("MISMATCH",))
    with pytest.raises(SharedAssuranceError, match="AVERAGING"):
        AssurancePacket("P", "SUITE", "S", (result,), "PASS")
    assert AssurancePacket("P", "SUITE", "S", (result,), "BLOCKED").disposition == (
        "BLOCKED"
    )


def test_not_evaluable_requires_reason_and_cannot_pass() -> None:
    with pytest.raises(SharedAssuranceError, match="REASON_REQUIRED"):
        AssuranceAssertionResult("A1", "S", "NOT_EVALUABLE", ())
    result = AssuranceAssertionResult(
        "A1", "S", "NOT_EVALUABLE", (), ("EVIDENCE_MISSING",)
    )
    with pytest.raises(SharedAssuranceError, match="AVERAGING"):
        AssurancePacket("P", "SUITE", "S", (result,), "PASS")


def test_suite_and_packet_are_deterministic_and_unambiguous() -> None:
    suite = AssuranceSuite("S", (assertion(),))
    result = AssuranceAssertionResult("A1", "T", "PASS", ("E1",))
    first = AssurancePacket("P", suite.suite_id, "T", (result,), "PASS")
    assert first.logical_id == AssurancePacket(
        "P", suite.suite_id, "T", (result,), "PASS"
    ).logical_id
    with pytest.raises(SharedAssuranceError, match="AMBIGUOUS"):
        AssuranceSuite("S", (assertion(), assertion()))


def test_qualification_is_fully_scoped_and_currentness_drifts() -> None:
    record = qualification()
    assert currentness(record).status == "CURRENT"
    stale = currentness(
        record,
        release_ref="RELEASE.2",
        generation_ref="GEN.2",
        source_ref="SOURCE.2",
    )
    assert stale.status == "STALE"
    assert stale.reason_codes == (
        "RELEASE_DRIFT",
        "GENERATION_DRIFT",
        "SOURCE_DRIFT",
    )
    assert currentness(record, quarantined=True).status == "QUARANTINED"
    assert currentness(record, superseded=True).status == "SUPERSEDED"


def test_nonqualified_record_never_projects_current() -> None:
    projection = currentness(qualification("NOT_QUALIFIED"))
    assert projection.status == "UNKNOWN"
    assert projection.reason_codes == ("QUALIFICATION_RECORD_NOT_QUALIFIED",)


def test_qualification_cannot_create_authority_or_ambiguous_disposition() -> None:
    with pytest.raises(SharedAssuranceError, match="LAUNDERING"):
        replace(qualification(), authority_effect="ACTIVE")
    with pytest.raises(SharedAssuranceError, match="AMBIGUOUS"):
        currentness(qualification(), revoked=True, quarantined=True)


EDGES = (
    ImpactDependencyEdge("A", "B", "RETEST"),
    ImpactDependencyEdge("B", "C", "REPLAY"),
    ImpactDependencyEdge("X", "Y", "RETEST"),
)
UNIVERSE = ("A", "B", "C", "X", "Y")


def test_selective_invalidation_follows_only_explicit_closure() -> None:
    plan = build_invalidation_plan(
        ChangeAssessment("CH", ("A",), "SEMANTIC", ("IDENTITY_CHANGE",)),
        EDGES,
        UNIVERSE,
    )
    assert plan.invalidated_refs == ("A", "B", "C")
    assert plan.unaffected_refs == ("X", "Y")
    assert not plan.conservative_fallback
    assert plan.unaffected_proof
    assert plan.unresolved_impacts == ()


def test_implementation_equivalent_change_requires_proof_and_stays_local() -> None:
    with pytest.raises(SharedAssuranceError, match="PROOF_REQUIRED"):
        ChangeAssessment("CH", ("A",), "IMPLEMENTATION_EQUIVALENT", ("REFACTOR",))
    plan = build_invalidation_plan(
        ChangeAssessment(
            "CH",
            ("A",),
            "IMPLEMENTATION_EQUIVALENT",
            ("EXACT_EQUIVALENCE",),
            ("EQUIVALENCE_PROOF.1",),
        ),
        EDGES,
        UNIVERSE,
    )
    assert plan.invalidated_refs == ("A",)
    assert plan.unaffected_refs == ("B", "C", "X", "Y")


def test_ambiguous_change_uses_conservative_fallback() -> None:
    plan = build_invalidation_plan(
        ChangeAssessment("CH", ("A",), "AMBIGUOUS", ("UNRESOLVED",)),
        EDGES,
        UNIVERSE,
    )
    assert plan.invalidated_refs == tuple(sorted(UNIVERSE))
    assert plan.conservative_fallback
    assert plan.unresolved_impacts == ("DECLARED_UNIVERSE_IMPACT_UNRESOLVED",)


def test_unknown_or_ambiguous_graph_inputs_fail_closed() -> None:
    with pytest.raises(SharedAssuranceError, match="CHANGE_REF_UNKNOWN"):
        build_invalidation_plan(
            ChangeAssessment("CH", ("Z",), "SEMANTIC", ("IDENTITY_CHANGE",)),
            EDGES,
            UNIVERSE,
        )
    with pytest.raises(SharedAssuranceError, match="EDGE_REF_UNKNOWN"):
        build_invalidation_plan(
            ChangeAssessment("CH", ("A",), "SEMANTIC", ("IDENTITY_CHANGE",)),
            (*EDGES, ImpactDependencyEdge("A", "Z", "REPLAY")),
            UNIVERSE,
        )
    with pytest.raises(SharedAssuranceError, match="UNIVERSE_DUPLICATE"):
        build_invalidation_plan(
            ChangeAssessment("CH", ("A",), "SEMANTIC", ("IDENTITY_CHANGE",)),
            EDGES,
            (*UNIVERSE, "A"),
        )


def test_incident_quarantine_preserve_evidence_impact_and_rollback() -> None:
    incident = IncidentRecord(
        "I1",
        "RESULT.1",
        ("E1", "E2"),
        "defect",
        "IMPACT.1",
        "ROLLBACK.1",
    )
    quarantine = QuarantineRecord(
        "QR1",
        incident.incident_id,
        incident.subject_ref,
        incident.evidence_refs,
        incident.rollback_ref,
        "REQUALIFY.1",
    )
    model1 = deterministic_read_model((quarantine, incident))
    model2 = deterministic_read_model((incident, quarantine))
    assert model1 == model2
    assert model1["rebuildable"] and model1["authority_effect"] == "NONE"
    assert all(row["evidence_refs"] for row in model1["rows"])
    assert all(row["rollback_ref"] == "ROLLBACK.1" for row in model1["rows"])
    with pytest.raises(SharedAssuranceError, match="PRESERVATION"):
        replace(quarantine, deleted=True)


def test_read_model_rejects_untyped_rows() -> None:
    with pytest.raises(SharedAssuranceError, match="NOT_DATACLASS"):
        deterministic_read_model(({"incident_id": "I1"},))
