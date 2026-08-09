from __future__ import annotations

from copy import deepcopy
from itertools import combinations
from typing import Any, Mapping, Sequence

from ovc.context.occurrence_context.consumers import project_context
from ovc.opt_b.sfc.c2e_adapter import adapt_c2e_handoff
from ovc.opt_b.sfc.comparison import (
    ComparabilityDomain,
    ComparisonSpec,
    comparability_metadata,
    compare,
)
from ovc.opt_b.sfc.evidence import family_evidence_stream, residual_rate
from ovc.opt_b.sfc.fdi import (
    FamilyMethodSpec,
    assignment,
    build_catalog,
    deterministic_star_assign,
    family_id,
)
from ovc.opt_b.sfc.representation import (
    RepresentationPack,
    compile_population,
    compile_representation,
    fit_minmax,
)

from .checkpoint import StageCompletion
from .current_adapters import adapter_for_stage, validate_occurrence_context_adapter_manifest
from .models import (
    IntegratedRunReceipt,
    PipelineProfile,
    StageDependency,
    StageExecutionReceipt,
    StageInvocation,
    StageSpec,
)
from .planner import CanonicalPlan, build_plan
from .registry import build_registry_snapshot
from .serialization import logical_sha256

GOLDEN_STAGE_IDS = (
    "POPULATION_SOURCE_OPT_A",
    "C1",
    "C2_REVISED",
    "C2E_V0_2",
    "OCCURRENCE_CONTEXT",
    "SRI_REPRESENTATION",
    "COMPARABILITY_COMPARISON_DISTANCE",
    "FDI_C2G_FAMILY",
    "FAMILY_EVIDENCE_STREAM",
    "RESEARCH_OPERATIONS",
)

STRUCTURAL_DIMENSIONS = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION")


def _adapt_episode(raw: Mapping[str, Any], *, cutoff: str) -> dict[str, Any]:
    record = deepcopy(dict(raw))
    source_objects = record.pop("source_objects")
    return adapt_c2e_handoff(record, source_objects=source_objects, evaluation_cutoff=cutoff)


def run_golden_scientific_chain(
    fixture: Mapping[str, Any],
    *,
    episode_order: Sequence[str] | None = None,
    reverse_source_objects: bool = False,
) -> dict[str, Any]:
    """Execute the furthest currently lawful synthetic descriptive chain.

    The harness deliberately begins at a synthetic finalized C2E producer handoff. C2E is
    inactive for real replay, so no real-source or boundary-pack authority is implied. The
    resulting SRI/comparison/FDI/evidence outputs are conformance evidence only.
    """

    cutoff = str(fixture["evaluation_cutoff"])
    episodes = [deepcopy(item) for item in fixture["episodes"]]
    by_id = {str(item["episode_id"]): item for item in episodes}
    if episode_order is not None:
        episodes = [by_id[str(item)] for item in episode_order]
    if reverse_source_objects:
        for episode in episodes:
            episode["source_objects"] = dict(reversed(list(episode["source_objects"].items())))

    adapted = [_adapt_episode(item, cutoff=cutoff) for item in episodes]
    population = compile_population(
        adapted,
        population_rule_pack_id=str(fixture["population_rule_pack_id"]),
        population_cutoff=cutoff,
    )
    eligible_ids = set(population["eligible_source_ids"])
    eligible = [item for item in adapted if item["episode_id"] in eligible_ids]
    if not eligible:
        raise ValueError("golden fixture must contain at least one eligible episode")

    normalization = fit_minmax(
        eligible,
        STRUCTURAL_DIMENSIONS,
        fit_population_id=population["population_id"],
        fit_cutoff=cutoff,
    )
    representation_pack = RepresentationPack(
        str(fixture["representation_pack_id"]),
        "SRI-R4",
        STRUCTURAL_DIMENSIONS,
        comparability_domain_id=str(fixture["comparability_domain_id"]),
    )
    representations = [
        compile_representation(
            item,
            representation_pack,
            source_population_id=population["population_id"],
            normalization_pack=normalization,
        )
        for item in eligible
    ]
    representations.sort(key=lambda item: item["representation_id"])

    comparison_spec = ComparisonSpec(
        spec_id=str(fixture["comparison_spec_id"]),
        kind="DISTANCE",
        formula="EUCLIDEAN",
        dimensions=STRUCTURAL_DIMENSIONS,
        equivalence_kind="ABS_REL_TOL",
        abs_tolerance="0.000000000001",
        rel_tolerance="0.000000000001",
    )
    domain = ComparabilityDomain(str(fixture["comparability_domain_id"]))
    pair_records: list[dict[str, Any]] = []
    for left, right in combinations(representations, 2):
        pair_records.append(
            compare(
                left,
                right,
                left_meta=comparability_metadata(left),
                right_meta=comparability_metadata(right),
                domain=domain,
                spec=comparison_spec,
                evaluation_cutoff=cutoff,
            )
        )
    pair_records.sort(key=lambda item: str(item.get("pair_id")))

    method = FamilyMethodSpec(
        family_method_id=str(fixture["family_method_id"]),
        method_version="0.1",
        configuration_id=str(fixture["family_configuration_id"]),
        input_representation_pack_id=representation_pack.representation_pack_id,
        comparison_spec_id=comparison_spec.spec_id,
        minimum_support=2,
    )
    occurrence_ids = [item["representation_id"] for item in representations]
    catalog = deterministic_star_assign(
        pair_records,
        occurrence_ids=occurrence_ids,
        threshold=str(fixture["family_threshold"]),
        population_id=population["population_id"],
        representation_pack_id=representation_pack.representation_pack_id,
        comparison_spec_id=comparison_spec.spec_id,
        method=method,
        evaluation_cutoff=cutoff,
    )
    residual = residual_rate(catalog)
    evidence_stream = family_evidence_stream(
        source_population_id=population["population_id"],
        source_c2e_stream_id=str(fixture["source_c2e_stream_id"]),
        catalogs=(catalog,),
        evidence_objects=(residual,),
        evaluation_cutoff=cutoff,
    )

    zero_method = FamilyMethodSpec(
        family_method_id=str(fixture["family_method_id"]) + ".ZERO",
        method_version="0.1",
        configuration_id=str(fixture["family_configuration_id"]) + ".ZERO",
        input_representation_pack_id=representation_pack.representation_pack_id,
        comparison_spec_id=comparison_spec.spec_id,
        minimum_support=max(99, len(occurrence_ids) + 1),
    )
    zero_catalog = deterministic_star_assign(
        pair_records,
        occurrence_ids=occurrence_ids,
        threshold=str(fixture["family_threshold"]),
        population_id=population["population_id"],
        representation_pack_id=representation_pack.representation_pack_id,
        comparison_spec_id=comparison_spec.spec_id,
        method=zero_method,
        evaluation_cutoff=cutoff,
    )
    zero_stream = family_evidence_stream(
        source_population_id=population["population_id"],
        source_c2e_stream_id=str(fixture["source_c2e_stream_id"]),
        catalogs=(zero_catalog,),
        evidence_objects=(residual_rate(zero_catalog),),
        evaluation_cutoff=cutoff,
    )

    ambiguous_catalog = _ambiguous_catalog(
        occurrence_ids,
        population_id=population["population_id"],
        representation_pack_id=representation_pack.representation_pack_id,
        comparison_spec_id=comparison_spec.spec_id,
        evaluation_cutoff=cutoff,
    )

    context_manifest = validate_occurrence_context_adapter_manifest(fixture["context_consumer_manifest"])
    context_projection = project_context(fixture["occurrence_context"], context_manifest)

    result = {
        "population": population,
        "representations": representations,
        "pair_records": pair_records,
        "catalog": catalog,
        "zero_catalog": zero_catalog,
        "ambiguous_catalog": ambiguous_catalog,
        "family_evidence_stream": evidence_stream,
        "zero_family_evidence_stream": zero_stream,
        "occurrence_context_projection": context_projection,
        "scientific_authority": "INACTIVE_CONFORMANCE_ONLY",
    }
    result["logical_hash"] = logical_sha256(result)
    return result


def _ambiguous_catalog(
    occurrence_ids: Sequence[str],
    *,
    population_id: str,
    representation_pack_id: str,
    comparison_spec_id: str,
    evaluation_cutoff: str,
) -> dict[str, Any]:
    if len(occurrence_ids) < 3:
        raise ValueError("golden ambiguous fixture requires at least three eligible occurrences")
    ids = sorted(occurrence_ids)[:3]
    method = FamilyMethodSpec(
        family_method_id="IROF.GOLDEN.AMBIGUITY",
        method_version="0.1",
        configuration_id="IROF.GOLDEN.AMBIGUITY.CONFIG",
        input_representation_pack_id=representation_pack_id,
        comparison_spec_id=comparison_spec_id,
        minimum_support=2,
    )
    groups = {"A": (ids[0], ids[1]), "B": (ids[1], ids[2])}
    fid_a = family_id(
        population_id=population_id,
        representation_pack_id=representation_pack_id,
        comparison_spec_id=comparison_spec_id,
        method=method,
        member_ids=groups["A"],
    )
    fid_b = family_id(
        population_id=population_id,
        representation_pack_id=representation_pack_id,
        comparison_spec_id=comparison_spec_id,
        method=method,
        member_ids=groups["B"],
    )
    from ovc.opt_b.sfc.fdi import catalog_id

    cid = catalog_id(
        population_id=population_id,
        representation_pack_id=representation_pack_id,
        comparison_spec_id=comparison_spec_id,
        method=method,
    )
    rows = (
        assignment(ids[0], cid, "MEMBER", (fid_a,), first_valid_time=evaluation_cutoff, evaluation_cutoff=evaluation_cutoff),
        assignment(ids[1], cid, "AMBIGUOUS", (fid_a, fid_b), reason_codes=("EXACT_TIE",), first_valid_time=evaluation_cutoff, evaluation_cutoff=evaluation_cutoff),
        assignment(ids[2], cid, "MEMBER", (fid_b,), first_valid_time=evaluation_cutoff, evaluation_cutoff=evaluation_cutoff),
    )
    return build_catalog(
        population_id=population_id,
        representation_pack_id=representation_pack_id,
        comparison_spec_id=comparison_spec_id,
        method=method,
        family_members=groups,
        assignments=rows,
        eligible_ids=ids,
        evaluation_cutoff=evaluation_cutoff,
    )


def build_golden_plan() -> CanonicalPlan:
    dependencies: dict[str, tuple[str, ...]] = {
        "POPULATION_SOURCE_OPT_A": (),
        "C1": ("POPULATION_SOURCE_OPT_A",),
        "C2_REVISED": ("C1",),
        "C2E_V0_2": ("C2_REVISED",),
        "OCCURRENCE_CONTEXT": ("C2E_V0_2",),
        "SRI_REPRESENTATION": ("C2E_V0_2",),
        "COMPARABILITY_COMPARISON_DISTANCE": ("SRI_REPRESENTATION",),
        "FDI_C2G_FAMILY": ("COMPARABILITY_COMPARISON_DISTANCE",),
        "FAMILY_EVIDENCE_STREAM": ("FDI_C2G_FAMILY",),
        "RESEARCH_OPERATIONS": ("FAMILY_EVIDENCE_STREAM", "OCCURRENCE_CONTEXT"),
    }
    specs: list[StageSpec] = []
    for stage_id in GOLDEN_STAGE_IDS:
        specs.append(
            StageSpec(
                stage_id=stage_id,
                stage_version="0.1",
                stage_kind="GOLDEN_SYNTHETIC_INTEGRATION",
                implementation_identity=f"irof-golden:{stage_id}",
                contract_identity=f"irof-golden-contract:{stage_id}",
                schema_identity=f"irof-golden-schema:{stage_id}",
                input_types=(),
                output_types=(f"{stage_id}_OUT",),
                dependencies=tuple(StageDependency(parent, "REQUIRED") for parent in dependencies[stage_id]),
                checkpoint_capability="STAGE",
                cache_capability="SEMANTIC",
                adapter_identity=f"IROF.CURRENT.{stage_id}",
            )
        )
    profile = PipelineProfile(
        "IROF_GOLDEN_FULL_DESCRIPTIVE_WITH_CONTEXT",
        "0.1",
        GOLDEN_STAGE_IDS,
        required_terminal_outputs=("RESEARCH_OPERATIONS_OUT",),
    )
    return build_plan(
        snapshot=build_registry_snapshot(stage_specs=tuple(specs), profiles=(profile,)),
        profile_id=profile.profile_id,
    )


def golden_adapter_trace(plan: CanonicalPlan) -> tuple[tuple[str, tuple[str, ...]], ...]:
    spec_hashes = dict(plan.stage_spec_hashes)
    trace: list[tuple[str, tuple[str, ...]]] = []
    parent_hashes: tuple[str, ...] = ()
    for stage_id in plan.ordered_stage_ids:
        spec = StageSpec(
            stage_id=stage_id,
            stage_version="0.1",
            stage_kind="GOLDEN_SYNTHETIC_INTEGRATION",
            implementation_identity=f"irof-golden:{stage_id}",
            contract_identity=f"irof-golden-contract:{stage_id}",
            schema_identity=f"irof-golden-schema:{stage_id}",
            input_types=(),
            output_types=(f"{stage_id}_OUT",),
            checkpoint_capability="STAGE",
            cache_capability="SEMANTIC",
            adapter_identity=f"IROF.CURRENT.{stage_id}",
        )
        invocation = StageInvocation(stage_id, spec_hashes[stage_id], parent_artifact_hashes=parent_hashes)
        output_ref = f"golden://{stage_id.lower()}"
        result = adapter_for_stage(stage_id).execute(
            spec,
            invocation,
            {
                "population_mode": "SYNTHETIC_FIXTURE",
                "context_role": "STRATIFICATION_ONLY",
                "owner_output_refs": (output_ref,),
                "owner_scientific_payload_hash": logical_sha256({"stage_id": stage_id}),
            },
        )
        trace.append((stage_id, result.output_refs))
        parent_hashes = tuple(result.output_refs)
    return tuple(trace)


def golden_stage_completions(plan: CanonicalPlan, scientific_hash: str, *, attempt_id: str) -> tuple[StageCompletion, ...]:
    hashes = dict(plan.stage_spec_hashes)
    return tuple(
        StageCompletion(
            stage_id=stage_id,
            stage_spec_hash=hashes[stage_id],
            output_logical_hash=logical_sha256({"stage": stage_id, "scientific_hash": scientific_hash}),
            content_hash=logical_sha256({"content": stage_id, "scientific_hash": scientific_hash}),
            attempt_id=attempt_id,
        )
        for stage_id in plan.ordered_stage_ids
    )


def golden_run_receipt(plan: CanonicalPlan, scientific_hash: str, *, attempt_id: str = "IROF.GOLDEN.ATTEMPT.1") -> IntegratedRunReceipt:
    stage_receipts = tuple(
        StageExecutionReceipt(
            run_id="IROF.RUN.GOLDEN.v0_1",
            attempt_id=attempt_id,
            stage_id=stage_id,
            stage_version="0.1",
            status="COMPLETE",
            input_hashes=(),
            output_artifact_ids=(f"IROF.GOLDEN.ARTIFACT.{stage_id}.{scientific_hash[:12]}",),
            metrics={"synthetic_work_units": 1},
        )
        for stage_id in plan.ordered_stage_ids
    )
    return IntegratedRunReceipt(
        run_id="IROF.RUN.GOLDEN.v0_1",
        attempt_id=attempt_id,
        status="COMPLETE",
        stage_receipts=stage_receipts,
        artifact_ids=tuple(item.output_artifact_ids[0] for item in stage_receipts),
        qa_manifest_id="IROF.G10.GOLDEN.QA.v0_1",
        aggregate_metrics={"synthetic_stage_count": len(stage_receipts)},
    )
