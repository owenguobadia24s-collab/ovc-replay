from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from ovc.opt_b.esl.compiler import (
    BOOTSTRAP_PACK,
    OccurrenceCompileError,
    compile_structural_occurrence,
    measure_reference_compiler,
)
from ovc.opt_b.esl.model import DependencyRef, DependencyRole, EvidenceState, StructuralDimension

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures" / "opt_b" / "esl" / "wp3" / "bootstrap_c2_input.json"


def _input():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_bootstrap_reference_compiler_preserves_field_level_missingness():
    source = _input()
    record = compile_structural_occurrence(source["c2_observation"], source["profile_outputs"], source_generation_id=source["source_generation_id"])
    assert record.occurrence_record_id.startswith("so1:")
    states = {facet.dimension: facet.evidence_state for facet in record.facets}
    assert states == {
        StructuralDimension.LOCATION: EvidenceState.AVAILABLE,
        StructuralDimension.MOTION: EvidenceState.AVAILABLE,
        StructuralDimension.ORGANISATION: EvidenceState.NOT_EVALUABLE,
        StructuralDimension.INTERACTION: EvidenceState.MISSING,
    }
    motion = next(facet for facet in record.facets if facet.dimension is StructuralDimension.MOTION)
    assert len(motion.value["components"]) == 2
    assert {item["computability"] for item in motion.value["components"]} == {"COMPUTABLE", "NOT_COMPUTABLE"}
    organisation = next(facet for facet in record.facets if facet.dimension is StructuralDimension.ORGANISATION)
    assert organisation.value is None
    assert "NO_CONTAINER_INVENTORY" in organisation.reason_codes


def test_compiler_is_deterministic_under_profile_input_reordering():
    source = _input()
    forward = compile_structural_occurrence(source["c2_observation"], source["profile_outputs"], source_generation_id=source["source_generation_id"])
    reverse = compile_structural_occurrence(source["c2_observation"], list(reversed(source["profile_outputs"])), source_generation_id=source["source_generation_id"])
    assert forward == reverse


def test_optional_missing_c2e_does_not_invalidate_base_occurrence():
    source = _input()
    c2e = DependencyRef(
        ref_id="C2E.E12",
        owner="C2E",
        object_type="C2EEpisode",
        role=DependencyRole.OPTIONAL,
        evidence_state=EvidenceState.MISSING,
        first_valid_time=None,
        generation_id="C2E.GEN.EXAMPLE.v1",
        comparability_domain_id=BOOTSTRAP_PACK.comparability_domain_id,
        identity_defining=False,
    )
    record = compile_structural_occurrence(source["c2_observation"], source["profile_outputs"], source_generation_id=source["source_generation_id"], optional_dependencies=(c2e,))
    assert "C2E.E12" in record.evidence_frontier.missing_ref_ids
    assert record.evidence_frontier.latest_required_fvt == source["c2_observation"]["first_valid_time"]
    assert any(facet.evidence_state is EvidenceState.AVAILABLE for facet in record.facets)


def test_ineligible_required_c2_observation_fails_closed():
    source = _input()
    source["c2_observation"]["projection_eligibility"]["eligible"] = False
    with pytest.raises(OccurrenceCompileError, match="ESL_REQUIRED_C2_OBSERVATION_NOT_ELIGIBLE"):
        compile_structural_occurrence(source["c2_observation"], source["profile_outputs"], source_generation_id=source["source_generation_id"])


def test_hindsight_and_global_quality_inputs_fail_closed():
    source = _input()
    polluted = copy.deepcopy(source["c2_observation"])
    polluted["outcome"] = {"next_return": 1}
    with pytest.raises(OccurrenceCompileError, match="ESL_PROHIBITED_EVIDENCE_KEY"):
        compile_structural_occurrence(polluted, source["profile_outputs"], source_generation_id=source["source_generation_id"])
    quality = {"axis": "QUALITY", "profile_output_id": "Q1", "as_of_time": "2026-06-24T14:30:00Z", "computability": "COMPUTABLE", "facts": {}, "reason_codes": []}
    with pytest.raises(OccurrenceCompileError, match="ESL_GLOBAL_QUALITY_PROFILE_FORBIDDEN"):
        compile_structural_occurrence(source["c2_observation"], [*source["profile_outputs"], quality], source_generation_id=source["source_generation_id"])


def test_profile_after_cutoff_fails_closed():
    source = _input()
    late = copy.deepcopy(source["profile_outputs"])
    late[0]["as_of_time"] = "2026-06-24T14:30:01Z"
    with pytest.raises(OccurrenceCompileError, match="ESL_C2_PROFILE_AFTER_CUTOFF"):
        compile_structural_occurrence(source["c2_observation"], late, source_generation_id=source["source_generation_id"])


def test_all_axis_absence_is_explicit_not_zero_or_synthetic_family():
    source = _input()
    record = compile_structural_occurrence(source["c2_observation"], [], source_generation_id=source["source_generation_id"])
    assert all(facet.evidence_state is EvidenceState.MISSING and facet.value is None for facet in record.facets)
    text = repr(record).lower()
    assert "family_id" not in text and "quality" not in text


def test_reference_measurement_has_no_budget_or_scientific_authority():
    source = _input()
    measurement = measure_reference_compiler(source["c2_observation"], source["profile_outputs"], source_generation_id=source["source_generation_id"], repetitions=20)
    assert measurement["p50_ms"] >= 0
    assert measurement["p95_ms"] >= measurement["p50_ms"]
    assert measurement["measurement_status"] == "REFERENCE_MEASUREMENT_NOT_YET_BUDGET"
    assert measurement["authority"] == "MEASUREMENT_ONLY_NO_SLO_OR_BUDGET"


def test_bootstrap_pack_is_exact_and_family_independent():
    pack = json.loads((ROOT / "registries" / "opt_b" / "esl" / "OCCURRENCE_PACK_GBPUSD_BID_15M_v0_1.json").read_text(encoding="utf-8"))
    assert pack["occurrence_pack_id"] == BOOTSTRAP_PACK.occurrence_pack_id
    assert (pack["instrument"], pack["side"], pack["scale"], pack["clock"]) == ("GBPUSD", "BID", "15M", "UTC")
    assert pack["required_dimensions"] == ["LOCATION", "MOTION", "ORGANISATION", "INTERACTION"]
    assert all("family" not in item.lower() for item in pack["required_source_types"] + pack["optional_source_types"])
