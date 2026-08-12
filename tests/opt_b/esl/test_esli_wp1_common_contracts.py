from __future__ import annotations

import pytest

from ovc.opt_b.esl import (
    DependencyRef,
    DependencyRole,
    EvidenceFrontier,
    EvidenceState,
    ESLValidationError,
    OccurrenceAnchor,
    OccurrencePack,
    StructuralDimension,
    StructuralFacet,
    StructuralOccurrenceRecord,
    validate_occurrence,
)


def _record(*, refs=None, first_valid_time="2026-06-03T10:15:00Z", domain="GBPUSD.BID.15M.v1"):
    refs = tuple(refs or (
        DependencyRef(ref_id="C2.OBS.1", owner="C2", object_type="C2Observation", role=DependencyRole.REQUIRED, evidence_state=EvidenceState.AVAILABLE, first_valid_time="2026-06-03T10:15:00Z", generation_id="C2.GEN.1", comparability_domain_id=domain),
        DependencyRef(ref_id="C2E.EP.1", owner="C2E", object_type="EpisodeSnapshot", role=DependencyRole.OPTIONAL, evidence_state=EvidenceState.MISSING, first_valid_time=None, generation_id="C2E.GEN.1", comparability_domain_id=domain, identity_defining=False),
    ))
    required_ids = tuple(ref.ref_id for ref in refs if ref.role is DependencyRole.REQUIRED)
    optional_ids = tuple(ref.ref_id for ref in refs if ref.role is DependencyRole.OPTIONAL)
    missing_ids = tuple(ref.ref_id for ref in refs if ref.evidence_state is not EvidenceState.AVAILABLE)
    required_fvts = tuple(ref.first_valid_time for ref in refs if ref.role is DependencyRole.REQUIRED and ref.first_valid_time)
    frontier = EvidenceFrontier(evaluation_cutoff="2026-06-03T10:15:00Z", required_ref_ids=required_ids, optional_ref_ids=optional_ids, missing_ref_ids=missing_ids, source_generation_ids=tuple(sorted({ref.generation_id for ref in refs})), latest_required_fvt=max(required_fvts) if required_fvts else None, dependency_roles={ref.ref_id: ref.role for ref in refs}, comparability_domain_id=domain)
    return StructuralOccurrenceRecord(occurrence_record_id=None, occurrence_pack_id="OPTB-ESL-OCCURRENCE-PACK-GBPUSD-BID-15M-v0.1", anchor=OccurrenceAnchor("C2_OBSERVATION", "C2.OBS.1", "GBPUSD", "BID", "15M"), evaluation_cutoff="2026-06-03T10:15:00Z", first_valid_time=first_valid_time, effective_time="2026-06-03T10:00:00Z", facets=(StructuralFacet(StructuralDimension.LOCATION, EvidenceState.AVAILABLE, ("C2.OBS.1",), {"bucket": "MID"}), StructuralFacet(StructuralDimension.MOTION, EvidenceState.AVAILABLE, ("C2.OBS.1",), {"state": "UP"}), StructuralFacet(StructuralDimension.ORGANISATION, EvidenceState.NOT_EVALUABLE, ("C2.OBS.1",), None, ("NO_ORGANISATION_INPUT",)), StructuralFacet(StructuralDimension.INTERACTION, EvidenceState.MISSING, (), None, ("OPTIONAL_INPUT_MISSING",))), dependency_refs=refs, evidence_frontier=frontier, source_generation_ids=tuple(sorted({ref.generation_id for ref in refs})), comparability_domain_id=domain)


PACK = OccurrencePack(occurrence_pack_id="OPTB-ESL-OCCURRENCE-PACK-GBPUSD-BID-15M-v0.1", anchor_kind="C2_OBSERVATION", required_dimensions=tuple(StructuralDimension), required_source_types=("C2Observation",), optional_source_types=("C2PObjectAssertion", "C2EEpisode"), comparability_domain_id="GBPUSD.BID.15M.v1")


def test_valid_partial_occurrence_is_lawful():
    validate_occurrence(_record(), PACK)


def test_required_missing_dependency_fails_closed():
    bad = DependencyRef(ref_id="C2.OBS.1", owner="C2", object_type="C2Observation", role=DependencyRole.REQUIRED, evidence_state=EvidenceState.MISSING, first_valid_time=None, generation_id="C2.GEN.1", comparability_domain_id="GBPUSD.BID.15M.v1")
    with pytest.raises(ESLValidationError, match="ESL_REQUIRED_DEPENDENCY_UNAVAILABLE"):
        validate_occurrence(_record(refs=(bad,)), PACK)


def test_reverse_dependency_to_c3_fails_closed():
    bad = DependencyRef(ref_id="C3.PROP.1", owner="C3", object_type="C3SemanticProposition", role=DependencyRole.OPTIONAL, evidence_state=EvidenceState.AVAILABLE, first_valid_time="2026-06-03T10:15:00Z", generation_id="C3.GEN.1", comparability_domain_id="GBPUSD.BID.15M.v1")
    with pytest.raises(ESLValidationError, match="ESL_REVERSE_EDGE_FORBIDDEN"):
        validate_occurrence(_record(refs=(bad,)), PACK)


def test_backdated_first_valid_time_fails():
    with pytest.raises(ESLValidationError, match="ESL_FVT_BACKDATED"):
        validate_occurrence(_record(first_valid_time="2026-06-03T10:14:59Z"), PACK)


def test_comparability_mismatch_fails():
    refs = (DependencyRef(ref_id="C2.OBS.1", owner="C2", object_type="C2Observation", role=DependencyRole.REQUIRED, evidence_state=EvidenceState.AVAILABLE, first_valid_time="2026-06-03T10:15:00Z", generation_id="C2.GEN.1", comparability_domain_id="GBPUSD.ASK.15M.v1"),)
    with pytest.raises(ESLValidationError, match="ESL_COMPARABILITY_DOMAIN_MISMATCH"):
        validate_occurrence(_record(refs=refs), PACK)


def test_nonavailable_facet_cannot_smuggle_zero_equivalent():
    record = _record()
    facets = list(record.facets)
    facets[2] = StructuralFacet(StructuralDimension.ORGANISATION, EvidenceState.NOT_EVALUABLE, ("C2.OBS.1",), {"score": 0}, ("NO_ORGANISATION_INPUT",))
    record = StructuralOccurrenceRecord(**{**record.__dict__, "facets": tuple(facets)})
    with pytest.raises(ESLValidationError, match="ESL_NONAVAILABLE_FACET_VALUE_PRESENT"):
        validate_occurrence(record, PACK)


def test_frozen_registries_and_schema_fixture_are_materialized():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[3]
    expected = {"DEPENDENCY_ROLES_v0_1.json": ["REQUIRED", "OPTIONAL", "CONDITIONAL_REQUIRED", "STRATIFIER", "FILTER", "DISPLAY_ONLY", "PROVENANCE_ONLY", "FORBIDDEN"], "EVIDENCE_STATES_v0_1.json": ["AVAILABLE", "MISSING", "NOT_EVALUABLE", "NOT_COMPARABLE", "CENSORED", "AMBIGUOUS", "CONFLICT", "QUARANTINED", "UNRESOLVED"], "EXECUTION_PROFILES_v0_1.json": ["BASE_STRUCTURAL", "ORGANISATION_ENRICHED", "CONSTRAINT_ENRICHED", "FULL_RESEARCH"], "STRUCTURAL_DIMENSIONS_v0_1.json": ["LOCATION", "MOTION", "ORGANISATION", "INTERACTION"]}
    for filename, values in expected.items():
        payload = json.loads((root / "registries/opt_b/esl" / filename).read_text(encoding="utf-8"))
        assert payload["values"] == values
        assert payload["mutable"] is False
    fixture = json.loads((root / "fixtures/opt_b/esl/wp1/valid_partial_occurrence.json").read_text(encoding="utf-8"))
    assert fixture["authority_state"] == "INACTIVE_CONFORMANCE_ONLY"
    assert fixture["facets"][2]["evidence_state"] == "NOT_EVALUABLE"
    assert fixture["facets"][2]["value"] is None
    schema = json.loads((root / "schemas/opt_b/esl/structural_occurrence_v0_1.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["authority_state"]["const"] == "INACTIVE_CONFORMANCE_ONLY"
