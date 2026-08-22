from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from ovc.shared_systems.foundation import (
    DSAISecurityAdapterBinding,
    DurableArtifactDescriptor,
    ExternalArtifactReceipt,
    HealthAssertion,
    InformationExposureRecord,
    PILOT_HARD_FLOOR_DIMENSIONS,
    PILOT_NUMERIC_CAP_DIMENSIONS,
    PilotAcceptanceBudget,
    PilotBaselineMeasurement,
    SECURITY_FACTORS,
    SecurityRequest,
    ServiceHealthSnapshot,
    ServiceLevelObjective,
    SharedFoundationError,
    TelemetryRecord,
    build_evidence_commit_manifest,
    decide_security,
    inspect_reachability,
    reveal_protected_metadata,
)


RAW = b"durable evidence"
SHA = hashlib.sha256(RAW).hexdigest()


def descriptor(ref: str = "ARTIFACT.1") -> DurableArtifactDescriptor:
    return DurableArtifactDescriptor(
        ref,
        f"LOGICAL.{ref}",
        SHA,
        len(RAW),
        "application/octet-stream",
        "EXTERNAL_CONTENT_ADDRESSED_DURABLE",
        "OWNER.1",
        "REPRODUCIBILITY_REQUIRED",
    )


def receipt(status: str = "VERIFIED") -> ExternalArtifactReceipt:
    return ExternalArtifactReceipt(
        "RECEIPT.1",
        "ARTIFACT.1",
        "OWNER.STORE.1",
        "sha256/locator-ref",
        SHA,
        len(RAW),
        "2026-08-22T00:00:00Z",
        status,
    )


def request() -> SecurityRequest:
    return SecurityRequest(
        "REQUEST.1",
        "PRINCIPAL.1",
        "PROTECTED.1",
        "CAP.1",
        "PERMISSION.1",
        "AUTHORITY.1",
        "SCOPE.1",
        "POLICY.1",
        "VALIDATION",
    )


def factors(**changes: bool) -> dict[str, bool]:
    values = {name: True for name in SECURITY_FACTORS}
    values.update(changes)
    return values


def hard_floor() -> tuple[tuple[str, int], ...]:
    return tuple((dimension, 0) for dimension in sorted(PILOT_HARD_FLOOR_DIMENSIONS))


def baselines() -> tuple[PilotBaselineMeasurement, ...]:
    return tuple(
        PilotBaselineMeasurement(
            f"BASELINE.{index}",
            dimension,
            unit,
            "ENV.1",
            "PROCEDURE.1",
            (float(index),),
            (f"EVIDENCE.{index}",),
        )
        for index, (dimension, unit) in enumerate(
            sorted(PILOT_NUMERIC_CAP_DIMENSIONS.items()), start=1
        )
    )


def test_evidence_commit_seals_only_exact_verified_receipts() -> None:
    manifest = build_evidence_commit_manifest("COMMIT.1", (descriptor(),), (receipt(),))
    assert manifest.status == "SEALED"
    assert manifest.missing_artifact_refs == manifest.invalid_artifact_refs == ()
    assert manifest.authority_effect == "NONE"


def test_missing_and_mismatched_evidence_fail_honestly() -> None:
    missing = build_evidence_commit_manifest("COMMIT.1", (descriptor(),), ())
    assert missing.status == "INCOMPLETE"
    assert missing.missing_artifact_refs == ("ARTIFACT.1",)
    mismatch = build_evidence_commit_manifest(
        "COMMIT.1",
        (descriptor(),),
        (replace(receipt(), blob_sha256="0" * 64),),
    )
    assert mismatch.status == "INVALID"
    assert mismatch.invalid_artifact_refs == ("ARTIFACT.1",)


def test_duplicate_evidence_records_are_ambiguous() -> None:
    with pytest.raises(SharedFoundationError, match="DESCRIPTOR_AMBIGUOUS"):
        build_evidence_commit_manifest(
            "COMMIT.1", (descriptor(), descriptor()), (receipt(),)
        )
    with pytest.raises(SharedFoundationError, match="RECEIPT_AMBIGUOUS"):
        build_evidence_commit_manifest(
            "COMMIT.1", (descriptor(),), (receipt(), receipt())
        )


def test_reachability_distinguishes_present_missing_and_corrupt() -> None:
    present = inspect_reachability("REACH.1", (descriptor(),), {"ARTIFACT.1": RAW})
    assert present.status == "REACHABLE"
    missing = inspect_reachability("REACH.1", (descriptor(),), {})
    assert missing.status == "GAPPED"
    assert missing.observations[0].status == "MISSING"
    corrupt = inspect_reachability(
        "REACH.1", (descriptor(),), {"ARTIFACT.1": b"wrong"}
    )
    assert corrupt.observations[0].status == "HASH_MISMATCH"


def test_security_requires_all_six_independent_factors() -> None:
    allowed = decide_security(
        "DECISION.1", request(), factor_results=factors(), dsai_decision_ref="DSAI.1"
    )
    assert allowed.status == "ALLOW" and not allowed.metadata_revealed
    denied = decide_security(
        "DECISION.2",
        request(),
        factor_results=factors(authority_permits=False),
        dsai_decision_ref="DSAI.2",
    )
    assert denied.status == "DENY"
    assert denied.reason_codes == ("AUTHORITY_PERMITS",)
    with pytest.raises(SharedFoundationError, match="FACTOR_SET"):
        decide_security(
            "DECISION.3",
            request(),
            factor_results={"capability_present": True},
            dsai_decision_ref="DSAI.3",
        )


def test_protected_denial_precedes_metadata_resolution() -> None:
    denied = decide_security(
        "DECISION.1",
        request(),
        factor_results=factors(permission_granted=False),
        dsai_decision_ref="DSAI.1",
    )
    with pytest.raises(SharedFoundationError, match="PRE_RESOLUTION_DENIAL"):
        reveal_protected_metadata(
            denied,
            {"path": "/protected", "count": 2, "timestamp": "secret"},
        )
    allowed = decide_security(
        "DECISION.2", request(), factor_results=factors(), dsai_decision_ref="DSAI.2"
    )
    assert reveal_protected_metadata(allowed, {"count": 2}) == {"count": 2}


def test_validation_exposure_is_irreversible_provenance() -> None:
    with pytest.raises(SharedFoundationError, match="PROVENANCE_REQUIRED"):
        InformationExposureRecord(
            "EXPOSURE.1",
            "DECISION.1",
            "PRINCIPAL.1",
            "PROTECTED.1",
            "VALIDATION",
            ("count",),
            False,
        )
    record = InformationExposureRecord(
        "EXPOSURE.1",
        "DECISION.1",
        "PRINCIPAL.1",
        "PROTECTED.1",
        "VALIDATION",
        ("count",),
        True,
    )
    assert record.validation_provenance_consumed


def test_dsai_adapter_cannot_create_parallel_security_stores() -> None:
    mapping = tuple((name, f"DSAI.{name}") for name in SECURITY_FACTORS)
    binding = DSAISecurityAdapterBinding("BINDING.1", ("DSAI.CONTRACT.1",), mapping)
    assert not binding.credential_store_created
    with pytest.raises(SharedFoundationError, match="PARALLEL_SECURITY_STORE"):
        replace(binding, credential_store_created=True)


def test_telemetry_and_health_are_multidimensional_and_non_authoritative() -> None:
    telemetry = TelemetryRecord(
        "T.1",
        "METRIC",
        "SVC.1",
        "RELEASE.1",
        "resolve",
        "ENV.1",
        "2026-08-22T00:00:00Z",
        "OPERATIONAL",
        12.5,
        monotonic_elapsed_ms=12,
    )
    snapshot = ServiceHealthSnapshot(
        "H.1",
        "SVC.1",
        "RELEASE.1",
        "ENV.1",
        (
            HealthAssertion("AVAILABILITY", "HEALTHY", (telemetry.telemetry_id,)),
            HealthAssertion(
                "QUALIFICATION",
                "UNKNOWN",
                (),
                ("QUALIFICATION_EVIDENCE_MISSING",),
            ),
        ),
        "2026-08-22T00:00:01Z",
    )
    assert {item.status for item in snapshot.assertions} == {"HEALTHY", "UNKNOWN"}
    assert telemetry.authority_effect == snapshot.authority_effect == "NONE"
    with pytest.raises(SharedFoundationError, match="DIMENSION_AMBIGUOUS"):
        replace(snapshot, assertions=(snapshot.assertions[0], snapshot.assertions[0]))


def test_slo_is_unbound_until_measured_derivation_exists() -> None:
    unbound = ServiceLevelObjective(
        "SLO.1",
        "SVC.1",
        "RELEASE.1",
        "resolve",
        "ENV.1",
        "INDICATOR.1",
        "WINDOW.1",
        "LTE",
        None,
        "UNBOUND",
        None,
    )
    assert unbound.status == "UNBOUND"
    with pytest.raises(SharedFoundationError, match="DERIVATION_REQUIRED"):
        replace(unbound, status="BOUND", target_value=10.0)


def test_budget_freeze_requires_pinned_baselines_caps_and_exact_zero_floor() -> None:
    rows = baselines()
    budget = PilotAcceptanceBudget.freeze_from_baselines(
        "BUDGET.1", rows, derivation_procedure_ref="DERIVATION.PROCEDURE.1"
    )
    expected = {row.dimension: max(row.sample_values) for row in rows}
    assert {dimension: cap for dimension, cap, _ in budget.numeric_caps} == expected
    assert budget.logical_id == replace(budget).logical_id
    assert not budget.relaxable_within_pilot and budget.authority_effect == "NONE"
    with pytest.raises(SharedFoundationError, match="HARD_FLOOR"):
        replace(
            budget,
            zero_tolerance_floor=(("AUTHORITY_SECURITY_FALSE_ALLOWS", 1),),
        )
    with pytest.raises(SharedFoundationError, match="FREEZE_REQUIRED"):
        replace(budget, relaxable_within_pilot=True)
    with pytest.raises(SharedFoundationError, match="DIMENSION_SET_INCOMPLETE"):
        PilotAcceptanceBudget.freeze_from_baselines(
            "BUDGET.BAD", rows[:-1], derivation_procedure_ref="DERIVATION.PROCEDURE.1"
        )


def test_wp6_schema_and_negative_fixture_cover_every_protected_boundary() -> None:
    root = Path(__file__).resolve().parents[2]
    schema = json.loads(
        (root / "schemas/shared_systems/persistence_security_observability_v0_1.schema.json").read_text()
    )
    fixture = json.loads(
        (root / "fixtures/shared_systems/foundation/SHSI_WP6_FOUNDATION_NEGATIVE_FIXTURES_v0_1.json").read_text()
    )
    expected = {
        "DurableArtifactDescriptor",
        "ExternalArtifactReceipt",
        "EvidenceCommitManifest",
        "EvidenceReachabilityManifest",
        "SecurityRequest",
        "SecurityDecisionRecord",
        "InformationExposureRecord",
        "DSAISecurityAdapterBinding",
        "TelemetryRecord",
        "ServiceHealthSnapshot",
        "ServiceLevelObjective",
        "PilotBaselineMeasurement",
        "PilotAcceptanceBudget",
    }
    assert expected <= set(schema["$defs"])
    assert fixture["stores_created"] == []
    assert fixture["protected_reads_executed"] == 0
    assert fixture["protected_denial"]["metadata_fields_revealed"] == []
    assert set(fixture["hard_floor"]) == PILOT_HARD_FLOOR_DIMENSIONS
    assert fixture["hard_floor_allowed_count"] == 0
    assert not fixture["budget_relaxable_within_pilot"]
