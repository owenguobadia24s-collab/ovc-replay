from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
import heapq
from itertools import combinations
from typing import Any, Mapping, Sequence

from .families import DistanceMatrix, FamilyError, FamilyMethodSpec, _catalog, _dec, _family
from .families_optimized import PreparedDistanceMatrix, hierarchical_optimized
from .serialization import logical_sha256, stable_id


@dataclass(frozen=True)
class HierarchicalTraceStep:
    left: tuple[str, ...]
    right: tuple[str, ...]
    merged: tuple[str, ...]
    numerator: str
    count: int

    @property
    def exact_score(self) -> Fraction:
        return Fraction(Decimal(self.numerator)) / self.count

    def to_dict(self) -> dict[str, Any]:
        return {
            "left": list(self.left),
            "right": list(self.right),
            "merged": list(self.merged),
            "numerator": self.numerator,
            "count": self.count,
        }


@dataclass(frozen=True)
class HierarchicalTrace:
    linkage: str
    population_ids: tuple[str, ...]
    max_radius: str
    steps: tuple[HierarchicalTraceStep, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": "ovc-srfdi-wp10a-hierarchical-trace/v1",
            "linkage": self.linkage,
            "population_ids": list(self.population_ids),
            "max_radius": self.max_radius,
            "steps": [step.to_dict() for step in self.steps],
            "scientific_effect": "NONE_CAPACITY_ONLY",
        }
        return {**payload, "logical_hash": logical_sha256(payload)}


def _pair_key(
    left: tuple[str, ...], right: tuple[str, ...]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return (left, right) if left < right else (right, left)


def _fraction(value: Decimal, count: int = 1) -> Fraction:
    return Fraction(value) / count


def build_hierarchical_trace(
    matrix: DistanceMatrix,
    *,
    linkage: str,
    max_radius: str,
) -> HierarchicalTrace:
    """Build one exact agglomeration trace reusable across frozen radii/supports.

    Average linkage stores exact Decimal base-distance sums plus integer pair counts and
    orders candidates with exact rational cross-multiplication through ``Fraction``.
    Complete linkage stores the exact maximum base distance. The trace stops only after
    the first candidate strictly outside ``max_radius``.
    """

    if linkage not in {"complete", "average"}:
        raise FamilyError("DIST_INVALID_PARAMETER", "trace linkage must be complete/average")
    radius = _dec(max_radius)
    radius_fraction = Fraction(radius)
    prepared = PreparedDistanceMatrix.from_matrix(matrix)
    active: set[tuple[str, ...]] = {(item,) for item in matrix.ids}
    aggregates: dict[
        tuple[tuple[str, ...], tuple[str, ...]], tuple[Decimal, int]
    ] = {}
    heap: list[
        tuple[Fraction, tuple[str, ...], tuple[str, ...], tuple[str, ...]]
    ] = []

    singleton_clusters = sorted(active)
    for left, right in combinations(singleton_clusters, 2):
        distance = prepared.distance(left[0], right[0])
        key = _pair_key(left, right)
        aggregates[key] = (distance, 1)
        merged = tuple(sorted(left + right))
        heapq.heappush(heap, (Fraction(distance), merged, left, right))

    steps: list[HierarchicalTraceStep] = []
    while len(active) > 1:
        while heap:
            score, merged, left, right = heapq.heappop(heap)
            if left in active and right in active:
                break
        else:
            break
        if score > radius_fraction:
            break

        score_sum, score_count = aggregates[_pair_key(left, right)]
        steps.append(
            HierarchicalTraceStep(
                left=left,
                right=right,
                merged=merged,
                numerator=format(score_sum, "f"),
                count=score_count,
            )
        )
        others = sorted(active - {left, right})
        active.remove(left)
        active.remove(right)
        active.add(merged)

        for other in others:
            left_key = _pair_key(left, other)
            right_key = _pair_key(right, other)
            new_key = _pair_key(merged, other)
            if linkage == "complete":
                left_distance = _fraction(*aggregates[left_key])
                right_distance = _fraction(*aggregates[right_key])
                if left_distance >= right_distance:
                    new_sum, new_count = aggregates[left_key]
                else:
                    new_sum, new_count = aggregates[right_key]
                new_score = max(left_distance, right_distance)
            else:
                left_sum, left_count = aggregates[left_key]
                right_sum, right_count = aggregates[right_key]
                new_sum = left_sum + right_sum
                new_count = left_count + right_count
                new_score = _fraction(new_sum, new_count)
            aggregates[new_key] = (new_sum, new_count)
            union = tuple(sorted(merged + other))
            ordered_left, ordered_right = sorted((merged, other))
            heapq.heappush(
                heap,
                (new_score, union, ordered_left, ordered_right),
            )

    return HierarchicalTrace(
        linkage=linkage,
        population_ids=matrix.ids,
        max_radius=format(radius, "f"),
        steps=tuple(steps),
    )


def materialize_hierarchical_trace(
    matrix: DistanceMatrix,
    trace: HierarchicalTrace,
    spec: FamilyMethodSpec,
) -> dict[str, object]:
    if spec.radius is None or spec.linkage != trace.linkage:
        raise FamilyError("DIST_INVALID_PARAMETER", "trace/spec linkage or radius mismatch")
    if trace.population_ids != matrix.ids:
        raise FamilyError("QA_NON_REPRODUCIBLE", "trace population does not match matrix")
    radius = Fraction(_dec(spec.radius))
    if radius > Fraction(_dec(trace.max_radius)):
        raise FamilyError("DIST_INVALID_PARAMETER", "trace max radius does not cover spec")

    active: set[tuple[str, ...]] = {(item,) for item in matrix.ids}
    for step in trace.steps:
        if step.exact_score > radius:
            break
        if step.left not in active or step.right not in active:
            raise FamilyError("QA_NON_REPRODUCIBLE", "trace active-cluster mismatch")
        active.remove(step.left)
        active.remove(step.right)
        active.add(step.merged)

    clusters = sorted(active)
    seed = {
        "method": spec.method_id,
        "configuration": spec.configuration_id,
        "population": list(matrix.ids),
    }
    families = [
        _family(
            seed,
            cluster,
            prototype_type="EXEMPLAR_SET",
            prototype_id=None,
            method_id=spec.method_id,
        )
        for cluster in clusters
        if len(cluster) >= spec.minimum_support
    ]
    residual = [
        item
        for cluster in clusters
        if len(cluster) < spec.minimum_support
        for item in cluster
    ]
    return _catalog(spec, matrix, families, residual)


def frozen_hierarchical_configuration_id(
    *,
    domain_id: str,
    linkage: str,
    radius: str,
    minimum_support: int,
) -> str:
    method_id = "COMPLETE_LINKAGE" if linkage == "complete" else "AVERAGE_LINKAGE"
    return stable_id(
        "SRFD.WP10A.CONFIG.",
        {
            "domain_id": domain_id,
            "method_id": method_id,
            "radius": str(radius),
            "minimum_support": int(minimum_support),
        },
    )


def materialize_frozen_hierarchical_grid(
    matrix: DistanceMatrix,
    *,
    domain_id: str,
    radii: Sequence[str] = ("0.04", "0.08", "0.16"),
    minimum_supports: Sequence[int] = (2, 4, 8),
) -> dict[str, Any]:
    catalogs: dict[str, dict[str, object]] = {}
    traces: dict[str, HierarchicalTrace] = {}
    for linkage, method_id in (
        ("complete", "COMPLETE_LINKAGE"),
        ("average", "AVERAGE_LINKAGE"),
    ):
        trace = build_hierarchical_trace(
            matrix,
            linkage=linkage,
            max_radius=max(radii, key=_dec),
        )
        traces[linkage] = trace
        for radius in radii:
            for support in minimum_supports:
                configuration_id = frozen_hierarchical_configuration_id(
                    domain_id=domain_id,
                    linkage=linkage,
                    radius=radius,
                    minimum_support=support,
                )
                spec = FamilyMethodSpec(
                    method_id,
                    configuration_id,
                    radius=radius,
                    minimum_support=int(support),
                    linkage=linkage,
                )
                catalogs[configuration_id] = materialize_hierarchical_trace(
                    matrix,
                    trace,
                    spec,
                )
    payload = {
        "schema": "ovc-srfdi-wp10a-hierarchical-grid/v1",
        "domain_id": domain_id,
        "population_count": len(matrix.ids),
        "configuration_count": len(catalogs),
        "configuration_ids": sorted(catalogs),
        "catalog_logical_hashes": {
            key: catalogs[key]["logical_hash"] for key in sorted(catalogs)
        },
        "trace_hashes": {
            linkage: traces[linkage].to_dict()["logical_hash"]
            for linkage in sorted(traces)
        },
        "scientific_effect": "NONE_CAPACITY_ONLY",
    }
    return {
        **payload,
        "logical_hash": logical_sha256(payload),
        "catalogs": catalogs,
        "traces": traces,
    }


def verify_hierarchical_grid_against_independent_optimized(
    matrix: DistanceMatrix,
    *,
    domain_id: str,
    radii: Sequence[str] = ("0.04", "0.08", "0.16"),
    minimum_supports: Sequence[int] = (2, 4, 8),
) -> dict[str, Any]:
    materialized = materialize_frozen_hierarchical_grid(
        matrix,
        domain_id=domain_id,
        radii=radii,
        minimum_supports=minimum_supports,
    )
    checked = 0
    for linkage, method_id in (
        ("complete", "COMPLETE_LINKAGE"),
        ("average", "AVERAGE_LINKAGE"),
    ):
        for radius in radii:
            for support in minimum_supports:
                configuration_id = frozen_hierarchical_configuration_id(
                    domain_id=domain_id,
                    linkage=linkage,
                    radius=radius,
                    minimum_support=support,
                )
                spec = FamilyMethodSpec(
                    method_id,
                    configuration_id,
                    radius=radius,
                    minimum_support=int(support),
                    linkage=linkage,
                )
                expected = hierarchical_optimized(matrix, spec)
                actual = materialized["catalogs"][configuration_id]
                if expected != actual:
                    raise FamilyError(
                        "G10A_GRID_MATERIALIZATION_EQUIVALENCE_FAILURE",
                        configuration_id,
                    )
                checked += 1
    payload = {
        "schema": "ovc-srfdi-wp10a-grid-equivalence/v1",
        "domain_id": domain_id,
        "checked_configuration_count": checked,
        "result": "PASS",
        "scientific_effect": "NONE_CAPACITY_ONLY",
    }
    return {**payload, "logical_hash": logical_sha256(payload)}
