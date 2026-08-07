from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import heapq
from itertools import combinations
from typing import Mapping

from .families import (
    DistanceMatrix,
    FamilyError,
    FamilyMethodSpec,
    _catalog,
    _dec,
    _family,
    pair_key,
)


@dataclass(frozen=True)
class PreparedDistanceMatrix:
    """Exact Decimal distance surface parsed once for capacity-equivalent execution."""

    ids: tuple[str, ...]
    values: Mapping[str, Decimal]

    @classmethod
    def from_matrix(cls, matrix: DistanceMatrix) -> "PreparedDistanceMatrix":
        return cls(matrix.ids, {key: _dec(value) for key, value in matrix.values.items()})

    def distance(self, left: str, right: str) -> Decimal:
        if left == right:
            return Decimal("0")
        try:
            return self.values[pair_key(left, right)]
        except KeyError as exc:
            raise FamilyError("COMP_REQUIRED_DIMENSION_MISSING", f"missing distance {left},{right}") from exc


def _seed(spec: FamilyMethodSpec, matrix: DistanceMatrix) -> dict[str, object]:
    return {
        "method": spec.method_id,
        "configuration": spec.configuration_id,
        "population": list(matrix.ids),
    }


def medoid_star_optimized(matrix: DistanceMatrix, spec: FamilyMethodSpec) -> dict[str, object]:
    """Reference-equivalent medoid-star with exact radius adjacency.

    Coverage totals are re-summed in canonical record order only for candidates tied on
    maximum support. This avoids subtraction-based Decimal drift while removing repeated
    full-population distance parsing and scans.
    """

    if spec.radius is None:
        raise FamilyError("DIST_INVALID_PARAMETER", "medoid-star radius required")
    radius = _dec(spec.radius)
    prepared = PreparedDistanceMatrix.from_matrix(matrix)
    adjacency: dict[str, list[tuple[str, Decimal]]] = {
        item: [(item, Decimal("0"))] for item in matrix.ids
    }
    for left, right in combinations(matrix.ids, 2):
        distance = prepared.distance(left, right)
        if distance <= radius:
            adjacency[left].append((right, distance))
            adjacency[right].append((left, distance))
    for item in matrix.ids:
        adjacency[item].sort(key=lambda pair: pair[0])

    active = set(matrix.ids)
    active_counts = {item: len(adjacency[item]) for item in matrix.ids}
    families: list[dict[str, object]] = []
    seed = _seed(spec, matrix)

    while active:
        maximum_support = max(active_counts[item] for item in active)
        tied_candidates = [
            item for item in sorted(active) if active_counts[item] == maximum_support
        ]
        scored: list[tuple[Decimal, str, tuple[str, ...]]] = []
        for candidate in tied_candidates:
            covered = tuple(item for item, _ in adjacency[candidate] if item in active)
            total = sum(
                (distance for item, distance in adjacency[candidate] if item in active),
                Decimal("0"),
            )
            scored.append((total, candidate, covered))
        _, medoid, covered = min(scored)
        if len(covered) < spec.minimum_support:
            break
        families.append(
            _family(
                seed,
                covered,
                prototype_type="MEDOID",
                prototype_id=medoid,
                method_id=spec.method_id,
            )
        )
        active.difference_update(covered)
        for removed in covered:
            for candidate, _ in adjacency[removed]:
                if candidate in active:
                    active_counts[candidate] -= 1

    return _catalog(spec, matrix, families, sorted(active))


def _cluster_pair_key(
    left: tuple[str, ...], right: tuple[str, ...]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return (left, right) if left < right else (right, left)


def hierarchical_optimized(matrix: DistanceMatrix, spec: FamilyMethodSpec) -> dict[str, object]:
    """Reference-equivalent complete/average linkage with a lazy exact heap.

    Complete linkage uses exact max updates. Average linkage recomputes only distances
    involving the newly merged cluster from the prepared base surface, in the same
    lexicographic cluster/member order used by the reference implementation. Recursive
    averaging of rounded means is intentionally prohibited.
    """

    if spec.radius is None or spec.linkage not in {"complete", "average"}:
        raise FamilyError(
            "DIST_INVALID_PARAMETER",
            "hierarchical radius and complete/average linkage required",
        )
    radius = _dec(spec.radius)
    prepared = PreparedDistanceMatrix.from_matrix(matrix)
    active: set[tuple[str, ...]] = {(item,) for item in matrix.ids}
    distances: dict[
        tuple[tuple[str, ...], tuple[str, ...]], Decimal
    ] = {}
    heap: list[
        tuple[Decimal, tuple[str, ...], tuple[str, ...], tuple[str, ...]]
    ] = []

    for left, right in combinations(sorted(active), 2):
        distance = prepared.distance(left[0], right[0])
        distances[_cluster_pair_key(left, right)] = distance
        merged = tuple(sorted(left + right))
        heapq.heappush(heap, (distance, merged, left, right))

    while len(active) > 1:
        while heap:
            distance, merged, left, right = heapq.heappop(heap)
            if left in active and right in active:
                break
        else:
            break
        if distance > radius:
            break

        others = sorted(active - {left, right})
        active.remove(left)
        active.remove(right)
        active.add(merged)

        for other in others:
            ordered_left, ordered_right = sorted((merged, other))
            if spec.linkage == "complete":
                new_distance = max(
                    distances[_cluster_pair_key(left, other)],
                    distances[_cluster_pair_key(right, other)],
                )
            else:
                base_distances = [
                    prepared.distance(left_member, right_member)
                    for left_member in ordered_left
                    for right_member in ordered_right
                ]
                new_distance = sum(base_distances, Decimal("0")) / Decimal(
                    len(base_distances)
                )
            distances[_cluster_pair_key(merged, other)] = new_distance
            union = tuple(sorted(merged + other))
            heapq.heappush(
                heap,
                (new_distance, union, ordered_left, ordered_right),
            )

    clusters = sorted(active)
    seed = _seed(spec, matrix)
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


def bounded_pam_optimized(matrix: DistanceMatrix, spec: FamilyMethodSpec) -> dict[str, object]:
    """Reference-equivalent bounded PAM with a once-parsed exact distance surface."""

    if spec.k is None or spec.k < 1 or spec.k > len(matrix.ids):
        raise FamilyError("DIST_INVALID_PARAMETER", "PAM k outside population")
    prepared = PreparedDistanceMatrix.from_matrix(matrix)
    medoids = list(matrix.ids[: spec.k])
    radius = (
        _dec(spec.max_assignment_distance)
        if spec.max_assignment_distance is not None
        else None
    )
    assignments: dict[str, list[str]] = {}
    residual: list[str] = []

    for _ in range(spec.max_iterations):
        assignments = {medoid: [] for medoid in medoids}
        residual = []
        for item in matrix.ids:
            ranked = sorted(
                (prepared.distance(item, medoid), medoid) for medoid in medoids
            )
            distance, medoid = ranked[0]
            if radius is not None and distance > radius:
                residual.append(item)
            else:
                assignments[medoid].append(item)

        updated: list[str] = []
        for medoid in medoids:
            members = assignments[medoid]
            if not members:
                updated.append(medoid)
                continue
            scored = [
                (
                    sum(
                        (prepared.distance(candidate, item) for item in members),
                        Decimal("0"),
                    ),
                    candidate,
                )
                for candidate in members
            ]
            updated.append(min(scored)[1])
        updated = sorted(set(updated))
        if updated == sorted(medoids):
            break
        while len(updated) < spec.k:
            updated.append(next(item for item in matrix.ids if item not in updated))
        medoids = sorted(updated[: spec.k])

    seed = _seed(spec, matrix)
    families: list[dict[str, object]] = []
    small_cluster_residual: list[str] = []
    for medoid in medoids:
        members = assignments.get(medoid, [])
        if len(members) >= spec.minimum_support:
            families.append(
                _family(
                    seed,
                    members,
                    prototype_type="MEDOID",
                    prototype_id=medoid,
                    method_id=spec.method_id,
                )
            )
        else:
            small_cluster_residual.extend(members)
    residual.extend(small_cluster_residual)
    return _catalog(spec, matrix, families, residual)
