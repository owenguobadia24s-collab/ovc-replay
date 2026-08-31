import json
from pathlib import Path

import pytest

from ovc.research_operations.c2_csm_reference.source_census import (
    LOAD_BEARING_SEMANTICS,
    classify_source_completeness,
    validate_no_derived_semantic_promotion,
)

ROOT = Path(__file__).resolve().parents[3]
COMPLETENESS = ROOT / "registries/research_operations/c2_csm_reference/C2CSM_REFERENCE_SOURCE_COMPLETENESS_v0_1.json"
GENERATION = ROOT / "registries/research_operations/c2_csm_reference/C2CSM_REFERENCE_GENERATION_P3_R5_T2_S2_v0_1.json"
FIXTURES = ROOT / "fixtures/research_operations/c2_csm_reference/C2CSM_REFERENCE_FIXTURE_CENSUS_v0_1.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_current_census_fails_closed_as_partial_source_limited():
    manifest = _load(COMPLETENESS)
    status, missing = classify_source_completeness(manifest)
    assert status == "REFERENCE_PARTIAL_SOURCE_LIMITED"
    assert missing == LOAD_BEARING_SEMANTICS
    assert manifest["status"] == status
    assert tuple(manifest["missing_exact_semantics"]) == missing
    assert manifest["prohibited_reconstruction"] is True


def test_source_derived_evidence_cannot_be_promoted_to_semantics():
    manifest = _load(COMPLETENESS)
    validate_no_derived_semantic_promotion(manifest)
    bad = json.loads(json.dumps(manifest))
    derived = next(item for item in bad["sources"] if item["source_confidence"] == "SOURCE_DERIVED")
    derived["implementation_binding"] = "EXACT_IMPLEMENTATION_BOUND"
    with pytest.raises(ValueError, match="cannot be implementation-bearing"):
        validate_no_derived_semantic_promotion(bad)


def test_exact_result_and_consumer_artifacts_do_not_satisfy_mechanics():
    manifest = _load(COMPLETENESS)
    evidence_only = [item for item in manifest["sources"] if item["source_confidence"] == "SOURCE_EXACT"]
    assert evidence_only
    assert all(item["implementation_binding"] != "EXACT_IMPLEMENTATION_BOUND" for item in evidence_only)


def test_reference_generation_has_no_active_c2_authority_and_exact_frozen_counts():
    generation = _load(GENERATION)
    assert generation["generation_id"] == "P3-R5-T2-S2"
    assert generation["authority_state"] == "ACTIVE_C2_AUTHORITY_NONE"
    assert generation["research_state"] == "DESCRIPTIVE_REFERENCE_ONLY"
    assert generation["source_completeness"] == "REFERENCE_PARTIAL_SOURCE_LIMITED"
    corpus = generation["historical_corpus"]
    assert corpus == {
        "development_cases": 15,
        "development_bars": 1392,
        "development_objects": 245,
        "holdout_cases": 10,
        "holdout_bars": 936,
        "holdout_objects": 163,
        "combined_cases": 25,
        "combined_bars": 2328,
        "combined_objects": 408,
        "holdout_integrity_pass": "10/10",
    }


def test_fixture_census_never_allows_external_evidence_to_define_mechanics():
    fixtures = _load(FIXTURES)
    assert fixtures["generation_id"] == "P3-R5-T2-S2"
    assert all(item["implementation_semantics_allowed"] is False for item in fixtures["fixtures"])
    assert any(item["fixture_id"] == "C2EXP-0009" for item in fixtures["fixtures"])
    assert any(item["fixture_id"] == "C2E-LIB-0001-R2" for item in fixtures["fixtures"])


def test_complete_state_requires_exact_binding_for_all_four_semantics():
    manifest = _load(COMPLETENESS)
    synthetic = {"sources": []}
    for semantic in LOAD_BEARING_SEMANTICS:
        synthetic["sources"].append(
            {
                "source_id": semantic,
                "source_confidence": "SOURCE_EXACT",
                "implementation_binding": "EXACT_IMPLEMENTATION_BOUND",
                "supports": [semantic],
            }
        )
    assert classify_source_completeness(synthetic) == ("REFERENCE_COMPLETE", ())
    assert classify_source_completeness(manifest)[0] != "REFERENCE_COMPLETE"
