from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.opt_b.sfc.comparison import (
    ComparabilityDomain,
    ComparisonSpec,
    comparability_metadata,
    compare,
    equivalent,
)
from ovc.research_orchestration.current_adapters import CurrentAdapterError, validate_occurrence_context_adapter_manifest
from ovc.research_orchestration.evidence import project_research_read_model
from ovc.research_orchestration.golden import (
    STRUCTURAL_DIMENSIONS,
    build_golden_plan,
    golden_adapter_trace,
    golden_run_receipt,
    run_golden_scientific_chain,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / "fixtures/research_orchestration/golden_v0_1/golden_full_chain.json"


def fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_golden_fixture_covers_required_wp9_scenarios() -> None:
    coverage = fixture()["scenario_coverage"]
    flat = {item for values in coverage.values() for item in values}
    required = {
        "ORDINARY_OBSERVATION",
        "GAP",
        "MISSING_PARENT",
        "NOT_EVALUABLE",
        "STATE_TRANSITION",
        "BIRTH",
        "CONTINUATION",
        "PHASE_MUTATION",
        "CENSOR_GAP",
        "CENSOR_RELEASE_END",
        "SPLIT",
        "MERGE",
        "RE_PARENT",
        "CONFLICT",
        "RAW",
        "NORMALIZED",
        "COMPARABLE",
        "NOT_COMPARABLE",
        "EXACT_EQUIVALENCE",
        "TOLERANCE_EQUIVALENCE",
        "RESIDUAL_OR_SINGLETON",
        "ZERO_FAMILY",
        "AMBIGUOUS",
        "STRATIFICATION_ONLY",
        "CACHE_REUSE",
        "CORRUPTED_CACHE",
        "CHECKPOINT_RESTART",
        "WORKER_ORDER_PERMUTATION",
    }
    assert required <= flat


def test_single_synthetic_population_reaches_family_evidence_surface() -> None:
    result = run_golden_scientific_chain(fixture())
    population = result["population"]
    assert population["denominator_total_seen"] == 4
    assert population["denominator_eligible"] == 3
    assert population["denominator_excluded"] == 1
    assert len(result["representations"]) == 3
    assert len(result["pair_records"]) == 3
    assert all(row["status"] == "EVALUATED" for row in result["pair_records"])
    assert result["catalog"]["evidence_status"] == "FAMILY_EVIDENCE_PRESENT"
    assert result["family_evidence_stream"]["status"] == "FAMILY_EVIDENCE_PRESENT"
    assert result["scientific_authority"] == "INACTIVE_CONFORMANCE_ONLY"


def test_zero_family_and_ambiguous_assignment_are_lawful_results() -> None:
    result = run_golden_scientific_chain(fixture())
    zero = result["zero_catalog"]
    assert zero["families"] == []
    assert zero["evidence_status"] == "NO_STABLE_FAMILY"
    assert result["zero_family_evidence_stream"]["status"] == "NO_STABLE_FAMILY"
    ambiguous = result["ambiguous_catalog"]
    statuses = {row["status"] for row in ambiguous["assignment_records"]}
    assert "AMBIGUOUS" in statuses
    assert "MEMBER" in statuses


def test_comparability_rejection_precedes_pair_identity_and_equivalence_is_declared() -> None:
    data = fixture()
    result = run_golden_scientific_chain(data)
    left, right = result["representations"][:2]
    spec = ComparisonSpec(
        spec_id="IROF.GOLDEN.COMP.TEST",
        kind="DISTANCE",
        formula="EUCLIDEAN",
        dimensions=STRUCTURAL_DIMENSIONS,
    )
    domain = ComparabilityDomain(data["comparability_domain_id"])
    left_meta = comparability_metadata(left)
    right_meta = comparability_metadata(right)
    right_meta["side"] = "ASK"
    rejected = compare(
        left,
        right,
        left_meta=left_meta,
        right_meta=right_meta,
        domain=domain,
        spec=spec,
        evaluation_cutoff=data["evaluation_cutoff"],
    )
    assert rejected["status"] == "NOT_COMPARABLE"
    assert rejected["pair_id"] is None
    assert "SFC_NOT_COMPARABLE_SIDE" in rejected["reason_codes"]
    assert equivalent("1.000000", "1.000000", kind="EXACT")
    assert equivalent("1.000000", "1.000001", kind="ABS_TOL", abs_tolerance="0.000001")
    assert not equivalent("1.000000", "1.010000", kind="ABS_TOL", abs_tolerance="0.000001")


def test_occurrence_context_is_attached_only_as_declared_nonstructural_projection() -> None:
    data = fixture()
    result = run_golden_scientific_chain(data)
    projected = result["occurrence_context_projection"]
    assert projected["fields"]["instrument_id"] == "GBPUSD"
    assert projected["fields"]["session.id"] == "LONDON"
    assert projected["authority_effect"] == "NONE"

    forbidden = json.loads(json.dumps(data["context_consumer_manifest"]))
    forbidden["field_dependencies"][0]["role"] = "REPRESENTATION_INPUT"
    with pytest.raises(CurrentAdapterError, match="IROF_OCCURRENCE_CONTEXT_REPRESENTATION_INPUT_NOT_AUTHORISED"):
        validate_occurrence_context_adapter_manifest(forbidden)


def test_current_owner_adapter_chain_is_synthetic_and_reference_only() -> None:
    plan = build_golden_plan()
    trace = golden_adapter_trace(plan)
    assert tuple(stage_id for stage_id, _ in trace) == plan.ordered_stage_ids
    assert all(refs and refs[0].startswith("golden://") for _, refs in trace)


def test_research_operations_evidence_rebuild_is_logically_identical() -> None:
    result = run_golden_scientific_chain(fixture())
    plan = build_golden_plan()
    receipt = golden_run_receipt(plan, result["logical_hash"])
    first = project_research_read_model(
        source_commit="IROF-WP9-GOLDEN",
        catalogue=None,
        run_receipt=receipt,
        plan=plan,
    )
    second = project_research_read_model(
        source_commit="IROF-WP9-GOLDEN",
        catalogue=None,
        run_receipt=receipt,
        plan=plan,
    )
    assert first.logical_sha256 == second.logical_sha256
    run_node = next(node for node in first.nodes if node.object_type == "IROF_INTEGRATED_RUN_RECEIPT")
    assert run_node.payload["lineage"]["stage_statuses"] == {stage_id: "COMPLETE" for stage_id in plan.ordered_stage_ids}
    assert run_node.authority == "DERIVED_EXECUTION_EVIDENCE_ONLY"
