from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.development.skills.dias import (
    CanonicalIdentityGateRegistry,
    CurrentExecutionProjection,
    DependencyToken,
    DiasContractError,
    OwnerFactCandidate,
    OwnerFactConflict,
    OwnerFactUnresolved,
    ProgrammeAuthorityEnvelope,
    TestDependency as DiasTestDependency,
    TestDependencyManifest as DiasTestDependencyManifest,
    build_current_execution_projection,
    classify_consequence,
    resolve_owner_fact,
)


ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "fixtures/development_skills/dias/DIASI_WP1_ADVERSARIAL_CLASSIFIER_CORPUS_v0_1.json"
BLOB_A = "a" * 40
BLOB_B = "b" * 40
BLOB_C = "c" * 40


def candidate(*, value: object, source_class: str, blob: str, path: str, observed_at: str) -> OwnerFactCandidate:
    return OwnerFactCandidate(
        owner="DSAI_VIT",
        fact_key="current_packet",
        value=value,
        source_class=source_class,
        source_path=path,
        source_blob=blob,
        observed_at=observed_at,
    )


def test_adversarial_classifier_corpus() -> None:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    for case in corpus["cases"]:
        observed = classify_consequence(case["action"])
        assert list(observed.planes) == case["expected"]["planes"], case["id"]
        assert observed.controlling_plane == case["expected"]["controlling_plane"], case["id"]
        assert observed.requires_split is case["expected"]["requires_split"], case["id"]
        assert len(observed.classification_id) == 64
    for case in corpus["negative_cases"]:
        with pytest.raises(DiasContractError):
            classify_consequence(case["action"])


def test_classifier_determinism_is_order_independent() -> None:
    first = classify_consequence({"action_id": "mixed", "effects": ["CUTOVER", "PRODUCE_EVIDENCE", "ROUTE"]})
    second = classify_consequence({"action_id": "mixed", "effects": ["ROUTE", "CUTOVER", "PRODUCE_EVIDENCE"]})
    assert first == second
    assert first.planes == ("FLOW", "EVIDENCE", "AUTHORITY")
    assert first.disposition == "SPLIT_AND_HOLD_AUTHORITY_CONSEQUENCE"


def test_programme_authority_envelope_is_exact_and_non_transitive() -> None:
    envelope = ProgrammeAuthorityEnvelope(
        programme_id="OVC-DIAS-CONFORMANCE-v0.1",
        plan_id="OVC-DIAS-CONFORMANCE-PLAN-0.1-R1",
        packet_id="DIASI-WP1",
        gate_id="DIASI-G0",
        authority_class="AUTO_EXECUTABLE",
        authority_sources=("docs/programmes/dias-v0-1/wp0/DIASI_G0_OPERATOR_DECISION.json",),
        allowed_actions=("SHADOW_EXECUTION", "BRANCH_REVERSIBLE_IMPLEMENTATION"),
        denied_actions=("LIVE_CUTOVER", "PROOF_SUBSTITUTION"),
        write_families=("src/ovc/development/skills/dias.py",),
        reserved_boundaries=("DIASI-G-DGS-CUTOVER-DRAIN",),
    )
    assert envelope.permits("SHADOW_EXECUTION") is True
    assert envelope.permits("LIVE_CUTOVER") is False
    assert envelope.permits("UNDECLARED") is False
    assert len(envelope.envelope_id) == 64
    with pytest.raises(DiasContractError):
        ProgrammeAuthorityEnvelope(
            programme_id="p",
            plan_id="q",
            packet_id="r",
            gate_id="s",
            authority_class="AUTO_EXECUTABLE",
            authority_sources=("a.json",),
            allowed_actions=("X",),
            denied_actions=("X",),
            write_families=("x.json",),
        )


def test_dependency_tokens_and_test_manifest_are_canonical() -> None:
    assert DependencyToken.parse("MAIN:abc").render() == "MAIN:abc"
    with pytest.raises(DiasContractError):
        DependencyToken.parse("UNKNOWN:value")
    with pytest.raises(DiasContractError):
        DependencyToken.parse("CREDENTIAL_REF:TOKEN=raw")
    first = DiasTestDependency(
        test_id="dias::classifier",
        assurance_class="AA1",
        dependency_tokens=("TREE:abc", "MAIN:def"),
    )
    second = DiasTestDependency(
        test_id="dias::projection",
        assurance_class="AA2",
        dependency_tokens=("OWNER_STATE:vit-v19",),
        reference_route_required=True,
    )
    manifest = DiasTestDependencyManifest(
        programme_id="OVC-DIAS-CONFORMANCE-v0.1",
        packet_id="DIASI-WP1",
        tests=(second, first),
    )
    assert [test.test_id for test in manifest.tests] == ["dias::classifier", "dias::projection"]
    assert len(manifest.manifest_id) == 64


def test_owner_pointer_wins_over_newer_derived_observation() -> None:
    pointer = candidate(
        value="DIASI-WP1",
        source_class="OWNER_CURRENT_POINTER",
        blob=BLOB_A,
        path="registries/owner/current.json",
        observed_at="2026-08-26T00:00:00Z",
    )
    newer = candidate(
        value="DIASI-WP99",
        source_class="DERIVED_OBSERVATION",
        blob=BLOB_B,
        path="var/derived/current.json",
        observed_at="2026-08-27T23:59:59Z",
    )
    resolved = resolve_owner_fact([newer, pointer])
    assert resolved.value == "DIASI-WP1"
    assert resolved.controlling_source_class == "OWNER_CURRENT_POINTER"
    assert newer.fact_id in resolved.ignored_lower_precedence_fact_ids


def test_content_addressed_external_owner_receipt_is_admissible() -> None:
    receipt = OwnerFactCandidate(
        owner="DSAI_VIT",
        fact_key="physical_completion",
        value=True,
        source_class="OWNER_SIGNED_RECEIPT",
        source_path="OVC_EXTERNAL_ARTIFACT_ROOT/receipts/proofs/example.json",
        source_blob="d" * 64,
    )
    assert resolve_owner_fact([receipt]).value is True


def test_equally_authoritative_conflict_blocks() -> None:
    first = candidate(
        value="DIASI-WP1",
        source_class="OWNER_CURRENT_POINTER",
        blob=BLOB_A,
        path="registries/owner/a.json",
        observed_at="2026-08-27T00:00:00Z",
    )
    second = candidate(
        value="DIASI-WP2",
        source_class="OWNER_CURRENT_POINTER",
        blob=BLOB_B,
        path="registries/owner/b.json",
        observed_at="2026-08-27T01:00:00Z",
    )
    with pytest.raises(OwnerFactConflict):
        resolve_owner_fact([first, second])
    with pytest.raises(OwnerFactUnresolved):
        resolve_owner_fact([])


def test_duplicate_equal_owner_pointers_are_deterministically_coalesced() -> None:
    first = candidate(
        value={"packet": "DIASI-WP1"},
        source_class="OWNER_CURRENT_POINTER",
        blob=BLOB_A,
        path="registries/owner/z.json",
        observed_at="2026-08-27T02:00:00Z",
    )
    second = candidate(
        value={"packet": "DIASI-WP1"},
        source_class="OWNER_CURRENT_POINTER",
        blob=BLOB_B,
        path="registries/owner/a.json",
        observed_at="2026-08-27T01:00:00Z",
    )
    resolved = resolve_owner_fact([first, second])
    assert resolved.controlling_source_paths == ("registries/owner/a.json", "registries/owner/z.json")


def test_current_execution_projection_is_derivative_shadow_only() -> None:
    current = candidate(
        value="DIASI-WP1",
        source_class="OWNER_CURRENT_POINTER",
        blob=BLOB_A,
        path="registries/owner/current.json",
        observed_at="2026-08-27T00:00:00Z",
    )
    projection = build_current_execution_projection("OVC-DIAS-CONFORMANCE-v0.1", {"current_packet": [current]})
    assert projection.shadow_only is True
    assert projection.derivative is True
    assert projection.authority_effect == "NONE"
    assert len(projection.projection_id) == 64
    with pytest.raises(DiasContractError):
        CurrentExecutionProjection(
            programme_id="OVC-DIAS-CONFORMANCE-v0.1",
            resolved_facts=projection.resolved_facts,
            shadow_only=False,
        )


def test_canonical_registry_denies_unknown_identities() -> None:
    registry = CanonicalIdentityGateRegistry(
        programme_id="OVC-DIAS-CONFORMANCE-v0.1",
        plan_id="OVC-DIAS-CONFORMANCE-PLAN-0.1-R1",
        packet_ids=("DIASI-WP0", "DIASI-WP1"),
        gate_ids=("DIASI-G0", "DIASI-G1-MECHANICAL"),
    )
    assert registry.require_packet("DIASI-WP1") == "DIASI-WP1"
    assert registry.require_gate("DIASI-G1-MECHANICAL") == "DIASI-G1-MECHANICAL"
    with pytest.raises(DiasContractError):
        registry.require_packet("DGS-WP1")
    with pytest.raises(DiasContractError):
        registry.require_gate("DIASI-G-MAGIC")
