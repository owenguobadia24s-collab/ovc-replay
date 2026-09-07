import copy
import hashlib
import json
from pathlib import Path

import pytest

from ovc.research_operations.spto.factorised_diagnostics import (
    CLAIMS,
    SPECIFICATIONS,
    DiagnosticError,
    build_diagnostic_pack,
    synthetic_diagnostic_population,
    validate_complete_population,
)
from ovc.research_operations.spto.factorised_mechanics import DECLARED_REPRESENTATIONS, content_id
from ovc.research_operations.spto.factorised_nulls import NULL_SPECS


ROOT = Path(__file__).resolve().parents[3]
PACK = "docs/programmes/c2s-sptoi-v0-1/wp9/C2S_SPTOI_WP9_FACTORISED_DIAGNOSTIC_QUALIFICATION_PACK_v0_1.json"


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_filed_pack_rebuilds_exactly_and_schema_validates():
    filed = load(PACK)
    assert filed == build_diagnostic_pack()
    body = copy.deepcopy(filed)
    identity = body.pop("pack_id")
    assert identity == content_id("FactorisedDiagnosticQualificationPack/v1", body)
    jsonschema = pytest.importorskip("jsonschema")
    schema = load("schemas/research_operations/spto/FACTORISED_DIAGNOSTIC_QUALIFICATION_PACK_v0_1.schema.json")
    jsonschema.Draft202012Validator(schema).validate(filed)


def test_population_manifest_retains_complete_universal_denominators():
    pack = build_diagnostic_pack()
    manifest = pack["population_manifest"]
    assert manifest["owner_transition_opportunities"] == 8
    assert manifest["grammar_evaluation_opportunities"] == 6
    assert manifest["representation_views"] == 6 * len(DECLARED_REPRESENTATIONS)
    assert sum(count for _, count in manifest["micro_path_applicability"]) == 8


def test_raw_and_run_collapsed_recurrence_are_separate_scoped_denominators():
    recurrence = build_diagnostic_pack()["recurrence"]
    assert recurrence["universal_population"] == {
        "unit": "OwnerTransitionOpportunity", "denominator": 8, "explicit_non_eligible": 2
    }
    assert recurrence["raw"]["recurrent_among_eligible"]["rendering"] == "5/6"
    assert recurrence["run_collapsed"]["recurrent_runs"]["rendering"] == "3/4"
    assert recurrence["raw"]["scope"].endswith("NOT_UNIVERSAL")
    assert recurrence["run_collapsed"]["scope"].endswith("NOT_UNIVERSAL")


def test_every_declared_representation_has_an_explicit_row_without_computability_inflation():
    completeness = build_diagnostic_pack()["representation_set_completeness"]
    assert completeness["declared_representation_set"] == list(DECLARED_REPRESENTATIONS)
    assert completeness["recorded_views"]["rendering"] == "40/40"
    assert completeness["computed_views"]["rendering"] == "29/40"
    assert completeness["missing_declared_view_rows"] == 0


def test_missing_representation_row_fails_closed():
    population = synthetic_diagnostic_population()
    population["opportunities"][2]["representation_views"].pop()
    with pytest.raises(DiagnosticError, match="DECLARED_REPRESENTATION_SET_INCOMPLETE"):
        build_diagnostic_pack(population)


def test_noneligible_recurrence_value_cannot_be_promoted():
    population = synthetic_diagnostic_population()
    population["opportunities"][-1]["recurrent"] = False
    with pytest.raises(DiagnosticError, match="CONDITIONAL_SURVIVOR_PROMOTED"):
        validate_complete_population(population)


def test_support_backoff_and_target_sensitivities_preserve_rows():
    sensitivity = build_diagnostic_pack()["backoff_hierarchy_target_sensitivity"]
    assert [row["support_min"] for row in sensitivity["support_thresholds"]] == [2, 3, 5]
    assert all(row["dropped_rows"] == 0 for row in sensitivity["support_thresholds"])
    assert set(sensitivity["antecedent_hierarchies_exercised"]) == set(DECLARED_REPRESENTATIONS)
    assert sensitivity["eligible_view_denominator"] == 30


def test_temporal_and_segment_breadth_use_universal_context_denominator():
    context = build_diagnostic_pack()["temporal_segment_context"]
    assert context["context_denominator"] == 8
    assert context["temporal_breadth"]["rendering"] == "4/5"
    assert context["segment_breadth"]["rendering"] == "3/4"
    assert sum(row["universal_opportunities"] for row in context["temporal_stability_vector"]) == 8


def test_support_representation_uncertainty_is_conditional_and_explicit():
    uncertainty = build_diagnostic_pack()["support_representation_uncertainty"]
    assert uncertainty["universal_opportunity_denominator"] == 8
    assert uncertainty["conditional_evaluable_denominator"] == 6
    assert uncertainty["support_representation_uncertain"]["rendering"] == "1/6"
    assert uncertainty["scope"].endswith("NOT_UNIVERSAL")


def test_source_generation_drift_is_descriptive_only_and_reconciles_population():
    drift = build_diagnostic_pack()["source_generation_drift"]
    assert drift["generation_denominator"] == 2
    assert sum(row["universal_opportunities"] for row in drift["generation_summaries"]) == 8
    assert drift["disposition"] == "NO_EMPIRICAL_SOURCE_DRIFT_CLAIM"


def test_specification_opportunity_ledger_is_rectangular_and_complete():
    ledger = build_diagnostic_pack()["specification_opportunity_ledger"]
    assert ledger["contract"] == "TVXGrammarSpecificationOpportunityLedger"
    assert ledger["specification_denominator"] == len(SPECIFICATIONS)
    assert ledger["universal_opportunity_denominator"] == 8
    assert ledger["row_denominator"] == len(SPECIFICATIONS) * 8 == len(ledger["rows"])
    assert ledger["complete"] is True
    assert {row["disposition"] for row in ledger["rows"]} == {
        "ELIGIBLE", "NOT_APPLICABLE", "NOT_EVALUABLE_DECLARED_VIEW"
    }


def test_design_exposure_manifest_covers_all_predeclared_dimensions():
    manifest = build_diagnostic_pack()["design_exposure_manifest"]
    assert manifest["contract"] == "TVXDesignExposureManifest"
    assert manifest["dimensions"]["representation"] == list(DECLARED_REPRESENTATIONS)
    assert set(manifest["dimensions"]["null_family"]) == set(NULL_SPECS)
    assert manifest["row_denominator"] == len(manifest["rows"])
    assert manifest["post_outcome_design_selection"] == "FORBIDDEN"


def test_claim_exposure_and_freshness_caps_cannot_be_empirical():
    pack = build_diagnostic_pack()
    matrix = pack["claim_exposure_matrix"]
    assert [row["claim_id"] for row in matrix] == list(CLAIMS)
    assert all(row["status"] == "NOT_AN_EMPIRICAL_CLAIM" for row in matrix)
    assert pack["claim_freshness_cap"]["empirical_freshness"] == "UNASSESSED_PROTECTED_SOURCE_DENIED"


def test_diagnostics_are_deterministic_and_population_sensitive():
    first = build_diagnostic_pack()
    assert first == build_diagnostic_pack()
    population = synthetic_diagnostic_population()
    population["opportunities"][0]["recurrent"] = False
    changed = build_diagnostic_pack(population)
    assert changed["pack_id"] != first["pack_id"]
    assert changed["recurrence"]["raw"]["recurrent_among_eligible"]["rendering"] == "4/6"


def test_authority_remains_source_free_and_scientifically_inactive():
    pack = build_diagnostic_pack()
    assert pack["protected_source_access"] == "NONE"
    assert pack["factorised_evidence_execution"] == "DENIED"
    assert pack["validation"] == "LOCKED_UNCONSUMED"
    assert pack["scientific_claims"] == "NONE"


def test_pointer_advances_to_integrated_assurance_only():
    pointer = load("registries/implementation/c2s_sptoi_v0_1/CURRENT_STATE_POINTER.json")
    state = load("records/research_operations/spto/C2S_SPTOI_PROGRAMME_STATE_v0_10.json")
    gate = load("docs/programmes/c2s-sptoi-v0-1/wp9/C2S_SPTOI_G9_DIAGNOSTICS_DELEGATED_DECISION_v0_1.json")
    assert pointer["current_packet"] in {"C2S-SPTOI-WP9", "C2S-SPTOI-WP10"}
    assert pointer["next_packet"] in {"C2S-SPTOI-WP10", "C2S-SPTOI-WP11"}
    assert state["protected_source_access"] == "NONE"
    assert state["factorised_evidence_execution"] == "DENIED"
    assert gate["decision"] == "PASS_SOURCE_FREE_DIAGNOSTIC_QUALIFICATION"


def test_wp9_authority_and_dependency_frontier_identities_are_exact():
    authority = load("docs/programmes/c2s-sptoi-v0-1/wp9/C2S_SPTOI_WP9_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load("docs/programmes/c2s-sptoi-v0-1/wp9/C2S_SPTOI_WP9_DEPENDENCY_FRONTIER_v0_1.json")
    canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical(authority["authority_manifest"])).hexdigest() == authority["authority_manifest_id"]
    body = copy.deepcopy(frontier)
    identity = body.pop("dependency_frontier_id")
    assert hashlib.sha256(canonical(body)).hexdigest() == identity
