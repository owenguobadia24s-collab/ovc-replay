from __future__ import annotations

from decimal import Decimal
from itertools import combinations
from typing import Any, Mapping, Sequence

from .distance import DistanceSpec, compute_distance
from .families import FamilyMethodSpec
from .family_grid_capacity import frozen_hierarchical_configuration_id
from .family_grid_reuse import frozen_medoid_configuration_id, frozen_pam_configuration_id
from .pattern_family_capacity import (
    PatternDistanceSurface,
    PatternHierarchicalStep,
    PatternHierarchicalTrace,
    PatternMedoidStep,
    PatternPamCore,
    all_residual_catalog,
    build_pattern_hierarchical_trace,
    build_pattern_medoid_trace,
    build_pattern_pam_core,
    materialize_pattern_hierarchical_trace,
    materialize_pattern_medoid_trace,
    materialize_pattern_pam_core,
)
from .serialization import logical_sha256
from .wp10_v07_contract import ConfigurationDescriptor, WP10RunnerError

def _gower_fields(record: Mapping[str, Any]) -> tuple[str, ...]:
    raw = record.get("structural_raw")
    if isinstance(raw, Mapping) and raw:
        return tuple(sorted(str(key) for key in raw))
    comparison = record.get("comparison_only")
    if isinstance(comparison, Mapping) and "null_control_token" in comparison:
        return ("null_control_token",)
    raise WP10RunnerError("DISTANCE_BINDING_MISMATCH", "no frozen Gower fields")


def _combined_value(record: Mapping[str, Any], field: str) -> Any:
    for namespace in (
        "structural_raw", "structural_derived", "structural_normalized", "comparison_only"
    ):
        values = record.get(namespace)
        if isinstance(values, Mapping) and field in values:
            return values[field]
    raise WP10RunnerError("DISTANCE_BINDING_MISMATCH", field)


def gower_pattern_surface(records: Sequence[Mapping[str, Any]]) -> PatternDistanceSurface:
    if len(records) < 2:
        raise WP10RunnerError("DISTANCE_BINDING_MISMATCH", "domain requires >=2 records")
    fields = _gower_fields(records[0])
    if any(_gower_fields(record) != fields for record in records):
        raise WP10RunnerError("DISTANCE_BINDING_MISMATCH", "field set changed within domain")
    return PatternDistanceSurface.from_records(
        records, fields=fields, value_getter=_combined_value
    )


def verify_gower_equivalence(
    records: Sequence[Mapping[str, Any]], surface: PatternDistanceSurface, *, sample_pairs: int = 64
) -> dict[str, Any]:
    by_id = {str(record["representation_id"]): record for record in records}
    fields = _gower_fields(records[0])
    spec = DistanceSpec("SRFDI-WP10-GOWER-CHECK", "GOWER_MIXED", fields)
    pairs = list(combinations(surface.ids, 2))
    if len(pairs) > sample_pairs:
        stride = max(1, len(pairs) // sample_pairs)
        pairs = pairs[::stride][:sample_pairs]
    for left, right in pairs:
        expected = compute_distance(by_id[left], by_id[right], spec)
        actual = surface.distance(left, right)
        if Decimal(str(expected["distance"])) != actual:
            raise WP10RunnerError(
                "G10A_DISTANCE_EQUIVALENCE_FAILURE",
                f"{left}|{right}:{expected['distance']}!={format(actual, 'f')}",
            )
    payload = {"checked_pairs": len(pairs), "fields": list(fields), "result": "PASS"}
    return {**payload, "logical_hash": logical_sha256(payload)}


def _is_exact_null_control(surface: PatternDistanceSurface) -> bool:
    return (
        surface.fields == ("null_control_token",)
        and surface.unique_pattern_count == len(surface.ids)
        and all(
            surface.distance(left, right) == Decimal("1.000000000000")
            for left, right in zip(surface.ids, surface.ids[1:])
        )
    )


def frozen_configuration_plan(domain_id: str) -> tuple[ConfigurationDescriptor, ...]:
    output: list[ConfigurationDescriptor] = []
    for linkage, method_id in (("complete", "COMPLETE_LINKAGE"), ("average", "AVERAGE_LINKAGE")):
        for radius in ("0.04", "0.08", "0.16"):
            for support in (2, 4, 8):
                output.append(
                    ConfigurationDescriptor(
                        frozen_hierarchical_configuration_id(
                            domain_id=domain_id,
                            linkage=linkage,
                            radius=radius,
                            minimum_support=support,
                        ),
                        method_id,
                        support,
                        "HIERARCHICAL",
                        linkage=linkage,
                        radius=radius,
                    )
                )
    for radius in ("0.04", "0.08", "0.16"):
        for support in (2, 4, 8):
            output.append(
                ConfigurationDescriptor(
                    frozen_medoid_configuration_id(
                        domain_id=domain_id, radius=radius, minimum_support=support
                    ),
                    "GREEDY_LEXICOGRAPHIC_MEDOID_STAR",
                    support,
                    "MEDOID_STAR",
                    radius=radius,
                )
            )
    for k in (2, 4, 8):
        for assignment_radius in ("0.10", "0.20", "0.40"):
            for support in (2, 4, 8):
                output.append(
                    ConfigurationDescriptor(
                        frozen_pam_configuration_id(
                            domain_id=domain_id,
                            k=k,
                            max_assignment_distance=assignment_radius,
                            max_iterations=8,
                            minimum_support=support,
                        ),
                        "BOUNDED_PAM",
                        support,
                        "PAM",
                        k=k,
                        max_assignment_distance=assignment_radius,
                        max_iterations=8,
                    )
                )
    if len(output) != 54:
        raise WP10RunnerError("FROZEN_GRID_INCOMPLETE", f"domain={domain_id}")
    return tuple(sorted(output, key=lambda item: item.configuration_id))


def _hierarchical_trace_dict(trace: PatternHierarchicalTrace) -> dict[str, Any]:
    return {
        "linkage": trace.linkage,
        "population_ids": list(trace.population_ids),
        "max_radius": trace.max_radius,
        "initial_clusters": [list(cluster) for cluster in trace.initial_clusters],
        "steps": [
            {
                "left": list(step.left),
                "right": list(step.right),
                "merged": list(step.merged),
                "score_sum": step.score_sum,
                "score_count": step.score_count,
            }
            for step in trace.steps
        ],
    }


def _hierarchical_trace_from_dict(value: Mapping[str, Any]) -> PatternHierarchicalTrace:
    return PatternHierarchicalTrace(
        linkage=str(value["linkage"]),
        population_ids=tuple(str(item) for item in value["population_ids"]),
        max_radius=str(value["max_radius"]),
        initial_clusters=tuple(tuple(str(item) for item in cluster) for cluster in value["initial_clusters"]),
        steps=tuple(
            PatternHierarchicalStep(
                left=tuple(str(item) for item in step["left"]),
                right=tuple(str(item) for item in step["right"]),
                merged=tuple(str(item) for item in step["merged"]),
                score_sum=str(step["score_sum"]),
                score_count=int(step["score_count"]),
            )
            for step in value["steps"]
        ),
    )


def _pam_core_dict(core: PatternPamCore) -> dict[str, Any]:
    return {
        "k": core.k,
        "max_assignment_distance": core.max_assignment_distance,
        "max_iterations": core.max_iterations,
        "population_ids": list(core.population_ids),
        "medoids": list(core.medoids),
        "assignments": [
            {"medoid": medoid, "members": list(members)} for medoid, members in core.assignments
        ],
        "residual": list(core.residual),
    }


def _pam_core_from_dict(value: Mapping[str, Any]) -> PatternPamCore:
    return PatternPamCore(
        k=int(value["k"]),
        max_assignment_distance=str(value["max_assignment_distance"]),
        max_iterations=int(value["max_iterations"]),
        population_ids=tuple(str(item) for item in value["population_ids"]),
        medoids=tuple(str(item) for item in value["medoids"]),
        assignments=tuple(
            (str(item["medoid"]), tuple(str(member) for member in item["members"]))
            for item in value["assignments"]
        ),
        residual=tuple(str(item) for item in value["residual"]),
    )


def prepare_domain(records: Sequence[Mapping[str, Any]], domain_id: str) -> dict[str, Any]:
    surface = gower_pattern_surface(records)
    equivalence = verify_gower_equivalence(records, surface)
    null_control = _is_exact_null_control(surface)
    preparation: dict[str, Any] = {
        "hierarchical": {}, "medoid": {}, "pam": {}
    }
    if not null_control:
        for linkage in ("complete", "average"):
            preparation["hierarchical"][linkage] = _hierarchical_trace_dict(
                build_pattern_hierarchical_trace(surface, linkage=linkage, max_radius="0.16")
            )
        for radius in ("0.04", "0.08", "0.16"):
            preparation["medoid"][radius] = [
                {"medoid": step.medoid, "covered": list(step.covered)}
                for step in build_pattern_medoid_trace(surface, radius=radius)
            ]
        for k in (2, 4, 8):
            for radius in ("0.10", "0.20", "0.40"):
                preparation["pam"][f"{k}|{radius}"] = _pam_core_dict(
                    build_pattern_pam_core(
                        surface,
                        k=k,
                        max_assignment_distance=radius,
                        max_iterations=8,
                    )
                )
    first = records[0]
    representation_id = str(first.get("representation_variant_id") or first.get("implementation_class_id"))
    payload = {
        "schema": "ovc-srfdi-wp10-v07-domain-preparation/v1",
        "domain_id": domain_id,
        "population_count": len(surface.ids),
        "pair_count": len(surface.ids) * (len(surface.ids) - 1) // 2,
        "unique_pattern_count": surface.unique_pattern_count,
        "representation_id": representation_id,
        "distance_id": "GOWER_MIXED",
        "null_control_fast_path": null_control,
        "gower_equivalence": equivalence,
        "configuration_plan": [item.to_dict() for item in frozen_configuration_plan(domain_id)],
        "preparation": preparation,
        "authority_effect": "NONE_EXECUTION_ROUTE_ONLY",
    }
    return {**payload, "logical_hash": logical_sha256(payload)}


def materialize_prepared_configuration(
    records: Sequence[Mapping[str, Any]],
    preparation: Mapping[str, Any],
    descriptor: ConfigurationDescriptor,
) -> dict[str, Any]:
    domain_id = str(preparation["domain_id"])
    if descriptor.configuration_id not in {
        str(item["configuration_id"]) for item in preparation["configuration_plan"]
    }:
        raise WP10RunnerError("FROZEN_GRID_INCOMPLETE", descriptor.configuration_id)
    surface = gower_pattern_surface(records)
    if tuple(surface.ids) != tuple(sorted(str(record["representation_id"]) for record in records)):
        raise WP10RunnerError("QA_NON_REPRODUCIBLE", "surface identity drift")
    spec = FamilyMethodSpec(
        descriptor.family_method_id,
        descriptor.configuration_id,
        radius=descriptor.radius,
        minimum_support=descriptor.minimum_support,
        k=descriptor.k,
        max_iterations=(descriptor.max_iterations if descriptor.max_iterations is not None else 20),
        linkage=descriptor.linkage,
        max_assignment_distance=descriptor.max_assignment_distance,
    )
    if bool(preparation["null_control_fast_path"]):
        catalog = all_residual_catalog(surface, spec)
    elif descriptor.kind == "HIERARCHICAL":
        trace = _hierarchical_trace_from_dict(
            preparation["preparation"]["hierarchical"][str(descriptor.linkage)]
        )
        catalog = materialize_pattern_hierarchical_trace(surface, trace, spec)
    elif descriptor.kind == "MEDOID_STAR":
        steps = tuple(
            PatternMedoidStep(
                medoid=str(item["medoid"]),
                covered=tuple(str(value) for value in item["covered"]),
            )
            for item in preparation["preparation"]["medoid"][str(descriptor.radius)]
        )
        catalog = materialize_pattern_medoid_trace(surface, steps, spec)
    elif descriptor.kind == "PAM":
        core = _pam_core_from_dict(
            preparation["preparation"]["pam"][f"{descriptor.k}|{descriptor.max_assignment_distance}"]
        )
        catalog = materialize_pattern_pam_core(surface, core, spec)
    else:
        raise WP10RunnerError("FROZEN_GRID_INCOMPLETE", f"unknown kind:{descriptor.kind}")
    if str(catalog.get("configuration_id")) != descriptor.configuration_id:
        raise WP10RunnerError("QA_NON_REPRODUCIBLE", "catalog configuration drift")
    payload = {
        "schema": "ovc-srfdi-wp10-v07-family-configuration/v1",
        "domain_id": domain_id,
        "configuration": descriptor.to_dict(),
        "catalog": catalog,
        "authority_effect": "NONE_EXECUTION_ROUTE_ONLY",
    }
    return {**payload, "logical_hash": logical_sha256(payload)}
