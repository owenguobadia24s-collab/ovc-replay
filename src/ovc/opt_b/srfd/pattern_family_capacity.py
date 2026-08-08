from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import heapq
from itertools import combinations
from typing import Any, Mapping, Sequence

from .families import FamilyError, FamilyMethodSpec, _catalog, _dec, _family
from .family_grid_capacity import frozen_hierarchical_configuration_id
from .family_grid_reuse import frozen_medoid_configuration_id, frozen_pam_configuration_id
from .serialization import logical_sha256


@dataclass(frozen=True)
class PatternDistanceSurface:
    """Exact categorical Gower surface compressed by identical value pattern.

    Every record identity remains present. Distances are evaluated exactly on demand from
    its frozen pattern, so no pair is sampled or approximated and an O(n^2) pair map is
    unnecessary.
    """

    ids: tuple[str, ...]
    fields: tuple[str, ...]
    vectors: Mapping[str, tuple[Any, ...]]
    pattern_members: Mapping[tuple[Any, ...], tuple[str, ...]]
    quantum: Decimal = Decimal("0.000000000001")

    @classmethod
    def from_records(
        cls,
        records: Sequence[Mapping[str, Any]],
        *,
        fields: Sequence[str],
        value_getter: Any,
    ) -> "PatternDistanceSurface":
        vectors: dict[str, tuple[Any, ...]] = {}
        grouped: dict[tuple[Any, ...], list[str]] = {}
        for record in records:
            record_id = str(record["representation_id"])
            vector = tuple(value_getter(record, field) for field in fields)
            vectors[record_id] = vector
            grouped.setdefault(vector, []).append(record_id)
        ids = tuple(sorted(vectors))
        pattern_members = {
            pattern: tuple(sorted(members))
            for pattern, members in grouped.items()
        }
        return cls(ids, tuple(fields), vectors, pattern_members)

    @property
    def unique_pattern_count(self) -> int:
        return len(self.pattern_members)

    def pattern_distance(self, left: tuple[Any, ...], right: tuple[Any, ...]) -> Decimal:
        if left == right:
            return Decimal("0")
        mismatches = sum(a != b for a, b in zip(left, right))
        return (Decimal(mismatches) / Decimal(len(self.fields))).quantize(self.quantum)

    def distance(self, left: str, right: str) -> Decimal:
        if left == right:
            return Decimal("0")
        try:
            return self.pattern_distance(self.vectors[left], self.vectors[right])
        except KeyError as exc:
            raise FamilyError("COMP_REQUIRED_DIMENSION_MISSING", f"unknown record {left},{right}") from exc


@dataclass(frozen=True)
class PatternHierarchicalStep:
    left: tuple[str, ...]
    right: tuple[str, ...]
    merged: tuple[str, ...]
    score_sum: str
    score_count: int

    @property
    def score(self) -> Decimal:
        return Decimal(self.score_sum) / Decimal(self.score_count)


@dataclass(frozen=True)
class PatternHierarchicalTrace:
    linkage: str
    population_ids: tuple[str, ...]
    max_radius: str
    steps: tuple[PatternHierarchicalStep, ...]
    initial_clusters: tuple[tuple[str, ...], ...]


def _cluster_key(
    left: tuple[str, ...], right: tuple[str, ...]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return (left, right) if left < right else (right, left)


def build_pattern_hierarchical_trace(
    surface: PatternDistanceSurface,
    *,
    linkage: str,
    max_radius: str,
) -> PatternHierarchicalTrace:
    if linkage not in {"complete", "average"}:
        raise FamilyError("DIST_INVALID_PARAMETER", "linkage must be complete/average")
    radius = _dec(max_radius)
    pattern_for_cluster: dict[tuple[str, ...], tuple[Any, ...]] = {
        members: pattern for pattern, members in surface.pattern_members.items()
    }
    active = set(pattern_for_cluster)
    initial_clusters = tuple(sorted(active))
    aggregates: dict[
        tuple[tuple[str, ...], tuple[str, ...]], tuple[Decimal, int]
    ] = {}
    heap: list[
        tuple[Decimal, tuple[str, ...], tuple[str, ...], tuple[str, ...]]
    ] = []

    for left, right in combinations(sorted(active), 2):
        distance = surface.pattern_distance(pattern_for_cluster[left], pattern_for_cluster[right])
        pair_count = len(left) * len(right)
        score_sum = distance * Decimal(pair_count) if linkage == "average" else distance
        score_count = pair_count if linkage == "average" else 1
        aggregates[_cluster_key(left, right)] = (score_sum, score_count)
        merged = tuple(sorted(left + right))
        heapq.heappush(heap, (distance, merged, left, right))

    steps: list[PatternHierarchicalStep] = []
    while len(active) > 1:
        while heap:
            score, merged, left, right = heapq.heappop(heap)
            if left in active and right in active:
                break
        else:
            break
        if score > radius:
            break
        score_sum, score_count = aggregates[_cluster_key(left, right)]
        steps.append(
            PatternHierarchicalStep(
                left=left,
                right=right,
                merged=merged,
                score_sum=format(score_sum, "f"),
                score_count=score_count,
            )
        )
        others = sorted(active - {left, right})
        active.remove(left)
        active.remove(right)
        active.add(merged)
        for other in others:
            left_key = _cluster_key(left, other)
            right_key = _cluster_key(right, other)
            new_key = _cluster_key(merged, other)
            if linkage == "complete":
                left_score = aggregates[left_key][0]
                right_score = aggregates[right_key][0]
                new_sum = max(left_score, right_score)
                new_count = 1
                new_score = new_sum
            else:
                left_sum, left_count = aggregates[left_key]
                right_sum, right_count = aggregates[right_key]
                new_sum = left_sum + right_sum
                new_count = left_count + right_count
                new_score = new_sum / Decimal(new_count)
            aggregates[new_key] = (new_sum, new_count)
            ordered_left, ordered_right = sorted((merged, other))
            heapq.heappush(
                heap,
                (new_score, tuple(sorted(merged + other)), ordered_left, ordered_right),
            )

    return PatternHierarchicalTrace(
        linkage=linkage,
        population_ids=surface.ids,
        max_radius=format(radius, "f"),
        steps=tuple(steps),
        initial_clusters=initial_clusters,
    )


def materialize_pattern_hierarchical_trace(
    surface: PatternDistanceSurface,
    trace: PatternHierarchicalTrace,
    spec: FamilyMethodSpec,
) -> dict[str, object]:
    if spec.radius is None or spec.linkage != trace.linkage:
        raise FamilyError("DIST_INVALID_PARAMETER", "trace/spec mismatch")
    if trace.population_ids != surface.ids:
        raise FamilyError("QA_NON_REPRODUCIBLE", "trace population mismatch")
    radius = _dec(spec.radius)
    if radius > _dec(trace.max_radius):
        raise FamilyError("DIST_INVALID_PARAMETER", "trace radius coverage failure")
    active = set(trace.initial_clusters)
    for step in trace.steps:
        if step.score > radius:
            break
        if step.left not in active or step.right not in active:
            raise FamilyError("QA_NON_REPRODUCIBLE", "trace active cluster mismatch")
        active.remove(step.left)
        active.remove(step.right)
        active.add(step.merged)
    clusters = sorted(active)
    seed = {
        "method": spec.method_id,
        "configuration": spec.configuration_id,
        "population": list(surface.ids),
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
    return _catalog(spec, surface, families, residual)


@dataclass(frozen=True)
class PatternMedoidStep:
    medoid: str
    covered: tuple[str, ...]


def build_pattern_medoid_trace(
    surface: PatternDistanceSurface,
    *,
    radius: str,
) -> tuple[PatternMedoidStep, ...]:
    bound = _dec(radius)
    pattern_members = dict(surface.pattern_members)
    active_patterns = set(pattern_members)
    pattern_distances: dict[tuple[tuple[Any, ...], tuple[Any, ...]], Decimal] = {}

    def pd(left: tuple[Any, ...], right: tuple[Any, ...]) -> Decimal:
        key = (left, right) if repr(left) <= repr(right) else (right, left)
        if key not in pattern_distances:
            pattern_distances[key] = surface.pattern_distance(left, right)
        return pattern_distances[key]

    steps: list[PatternMedoidStep] = []
    while active_patterns:
        scored: list[tuple[int, Decimal, str, tuple[Any, ...], tuple[str, ...]]] = []
        for candidate_pattern in active_patterns:
            covered_patterns = [
                pattern
                for pattern in active_patterns
                if pd(candidate_pattern, pattern) <= bound
            ]
            covered_ids = tuple(
                sorted(
                    item
                    for pattern in covered_patterns
                    for item in pattern_members[pattern]
                )
            )
            total = sum(
                (
                    pd(candidate_pattern, pattern) * Decimal(len(pattern_members[pattern]))
                    for pattern in covered_patterns
                ),
                Decimal("0"),
            )
            candidate_id = min(pattern_members[candidate_pattern])
            scored.append(
                (-len(covered_ids), total, candidate_id, candidate_pattern, covered_ids)
            )
        _, _, medoid, _, covered = min(scored, key=lambda row: (row[0], row[1], row[2]))
        if len(covered) < 2:
            break
        steps.append(PatternMedoidStep(medoid=medoid, covered=covered))
        covered_set = set(covered)
        active_patterns = {
            pattern
            for pattern in active_patterns
            if not covered_set.intersection(pattern_members[pattern])
        }
    return tuple(steps)


def materialize_pattern_medoid_trace(
    surface: PatternDistanceSurface,
    trace: Sequence[PatternMedoidStep],
    spec: FamilyMethodSpec,
) -> dict[str, object]:
    remaining = set(surface.ids)
    seed = {
        "method": spec.method_id,
        "configuration": spec.configuration_id,
        "population": list(surface.ids),
    }
    families: list[dict[str, object]] = []
    for step in trace:
        if len(step.covered) < spec.minimum_support:
            break
        if not set(step.covered).issubset(remaining):
            raise FamilyError("QA_NON_REPRODUCIBLE", "medoid trace coverage mismatch")
        families.append(
            _family(
                seed,
                step.covered,
                prototype_type="MEDOID",
                prototype_id=step.medoid,
                method_id=spec.method_id,
            )
        )
        remaining.difference_update(step.covered)
    return _catalog(spec, surface, families, sorted(remaining))


@dataclass(frozen=True)
class PatternPamCore:
    k: int
    max_assignment_distance: str
    max_iterations: int
    population_ids: tuple[str, ...]
    medoids: tuple[str, ...]
    assignments: tuple[tuple[str, tuple[str, ...]], ...]
    residual: tuple[str, ...]


def build_pattern_pam_core(
    surface: PatternDistanceSurface,
    *,
    k: int,
    max_assignment_distance: str,
    max_iterations: int,
) -> PatternPamCore:
    if k < 1 or k > len(surface.ids):
        raise FamilyError("DIST_INVALID_PARAMETER", "PAM k outside population")
    radius = _dec(max_assignment_distance)
    medoids = list(surface.ids[:k])
    assignments: dict[str, list[str]] = {}
    residual: list[str] = []
    pattern_members = dict(surface.pattern_members)

    for _ in range(max_iterations):
        assignments = {medoid: [] for medoid in medoids}
        residual = []
        for pattern, members in pattern_members.items():
            ranked = sorted(
                (surface.pattern_distance(pattern, surface.vectors[medoid]), medoid)
                for medoid in medoids
            )
            distance, medoid = ranked[0]
            if distance > radius:
                residual.extend(members)
            else:
                assignments[medoid].extend(members)

        updated: list[str] = []
        for medoid in medoids:
            members = sorted(assignments[medoid])
            if not members:
                updated.append(medoid)
                continue
            member_patterns: dict[tuple[Any, ...], list[str]] = {}
            for member in members:
                member_patterns.setdefault(surface.vectors[member], []).append(member)
            scored: list[tuple[Decimal, str]] = []
            for candidate_pattern, candidate_members in member_patterns.items():
                score = sum(
                    (
                        surface.pattern_distance(candidate_pattern, other_pattern)
                        * Decimal(len(other_members))
                        for other_pattern, other_members in member_patterns.items()
                    ),
                    Decimal("0"),
                )
                scored.append((score, min(candidate_members)))
            updated.append(min(scored)[1])
        updated = sorted(set(updated))
        if updated == sorted(medoids):
            break
        while len(updated) < k:
            updated.append(next(item for item in surface.ids if item not in updated))
        medoids = sorted(updated[:k])

    return PatternPamCore(
        k=k,
        max_assignment_distance=max_assignment_distance,
        max_iterations=max_iterations,
        population_ids=surface.ids,
        medoids=tuple(medoids),
        assignments=tuple(
            (medoid, tuple(sorted(assignments.get(medoid, ())))) for medoid in medoids
        ),
        residual=tuple(sorted(residual)),
    )


def materialize_pattern_pam_core(
    surface: PatternDistanceSurface,
    core: PatternPamCore,
    spec: FamilyMethodSpec,
) -> dict[str, object]:
    if (
        spec.k != core.k
        or spec.max_assignment_distance != core.max_assignment_distance
        or spec.max_iterations != core.max_iterations
        or core.population_ids != surface.ids
    ):
        raise FamilyError("QA_NON_REPRODUCIBLE", "PAM core/spec mismatch")
    assignment_map = {medoid: list(members) for medoid, members in core.assignments}
    seed = {
        "method": spec.method_id,
        "configuration": spec.configuration_id,
        "population": list(surface.ids),
    }
    families: list[dict[str, object]] = []
    residual = list(core.residual)
    for medoid in core.medoids:
        members = assignment_map.get(medoid, [])
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
            residual.extend(members)
    return _catalog(spec, surface, families, residual)


def all_residual_catalog(
    surface: PatternDistanceSurface,
    spec: FamilyMethodSpec,
) -> dict[str, object]:
    return _catalog(spec, surface, [], list(surface.ids))


def materialize_pattern_full_grid(
    surface: PatternDistanceSurface,
    *,
    domain_id: str,
    null_control_all_off_diagonal_one: bool = False,
    radii: Sequence[str] = ("0.04", "0.08", "0.16"),
    minimum_supports: Sequence[int] = (2, 4, 8),
    pam_k: Sequence[int] = (2, 4, 8),
    pam_assignment_radii: Sequence[str] = ("0.10", "0.20", "0.40"),
    pam_max_iterations: int = 8,
) -> dict[str, Any]:
    catalogs: dict[str, dict[str, object]] = {}

    if null_control_all_off_diagonal_one:
        for linkage, method_id in (("complete", "COMPLETE_LINKAGE"), ("average", "AVERAGE_LINKAGE")):
            for radius in radii:
                for support in minimum_supports:
                    config = frozen_hierarchical_configuration_id(
                        domain_id=domain_id,
                        linkage=linkage,
                        radius=radius,
                        minimum_support=support,
                    )
                    catalogs[config] = all_residual_catalog(
                        surface,
                        FamilyMethodSpec(
                            method_id,
                            config,
                            radius=radius,
                            minimum_support=support,
                            linkage=linkage,
                        ),
                    )
        for radius in radii:
            for support in minimum_supports:
                config = frozen_medoid_configuration_id(
                    domain_id=domain_id,
                    radius=radius,
                    minimum_support=support,
                )
                catalogs[config] = all_residual_catalog(
                    surface,
                    FamilyMethodSpec(
                        "GREEDY_LEXICOGRAPHIC_MEDOID_STAR",
                        config,
                        radius=radius,
                        minimum_support=support,
                    ),
                )
        for k in pam_k:
            for assignment_radius in pam_assignment_radii:
                for support in minimum_supports:
                    config = frozen_pam_configuration_id(
                        domain_id=domain_id,
                        k=k,
                        max_assignment_distance=assignment_radius,
                        max_iterations=pam_max_iterations,
                        minimum_support=support,
                    )
                    catalogs[config] = all_residual_catalog(
                        surface,
                        FamilyMethodSpec(
                            "BOUNDED_PAM",
                            config,
                            k=k,
                            minimum_support=support,
                            max_assignment_distance=assignment_radius,
                            max_iterations=pam_max_iterations,
                        ),
                    )
    else:
        for linkage, method_id in (("complete", "COMPLETE_LINKAGE"), ("average", "AVERAGE_LINKAGE")):
            trace = build_pattern_hierarchical_trace(
                surface,
                linkage=linkage,
                max_radius=max(radii, key=_dec),
            )
            for radius in radii:
                for support in minimum_supports:
                    config = frozen_hierarchical_configuration_id(
                        domain_id=domain_id,
                        linkage=linkage,
                        radius=radius,
                        minimum_support=support,
                    )
                    spec = FamilyMethodSpec(
                        method_id,
                        config,
                        radius=radius,
                        minimum_support=support,
                        linkage=linkage,
                    )
                    catalogs[config] = materialize_pattern_hierarchical_trace(surface, trace, spec)
        for radius in radii:
            trace = build_pattern_medoid_trace(surface, radius=radius)
            for support in minimum_supports:
                config = frozen_medoid_configuration_id(
                    domain_id=domain_id,
                    radius=radius,
                    minimum_support=support,
                )
                spec = FamilyMethodSpec(
                    "GREEDY_LEXICOGRAPHIC_MEDOID_STAR",
                    config,
                    radius=radius,
                    minimum_support=support,
                )
                catalogs[config] = materialize_pattern_medoid_trace(surface, trace, spec)
        for k in pam_k:
            if k > len(surface.ids):
                raise FamilyError("DIST_INVALID_PARAMETER", "frozen PAM k outside domain")
            for assignment_radius in pam_assignment_radii:
                core = build_pattern_pam_core(
                    surface,
                    k=k,
                    max_assignment_distance=assignment_radius,
                    max_iterations=pam_max_iterations,
                )
                for support in minimum_supports:
                    config = frozen_pam_configuration_id(
                        domain_id=domain_id,
                        k=k,
                        max_assignment_distance=assignment_radius,
                        max_iterations=pam_max_iterations,
                        minimum_support=support,
                    )
                    spec = FamilyMethodSpec(
                        "BOUNDED_PAM",
                        config,
                        k=k,
                        minimum_support=support,
                        max_assignment_distance=assignment_radius,
                        max_iterations=pam_max_iterations,
                    )
                    catalogs[config] = materialize_pattern_pam_core(surface, core, spec)

    if len(catalogs) != 54:
        raise FamilyError("G10A_GRID_MATERIALIZATION_EQUIVALENCE_FAILURE", f"configs={len(catalogs)}")
    hashes = {key: catalogs[key]["logical_hash"] for key in sorted(catalogs)}
    payload = {
        "schema": "ovc-srfdi-wp10a-pattern-full-grid/v1",
        "domain_id": domain_id,
        "population_count": len(surface.ids),
        "unique_pattern_count": surface.unique_pattern_count,
        "configuration_count": len(catalogs),
        "catalog_hashes_sha256": logical_sha256(hashes),
        "null_control_fast_path": bool(null_control_all_off_diagonal_one),
        "scientific_effect": "NONE_CAPACITY_ONLY",
    }
    return {
        **payload,
        "logical_hash": logical_sha256(payload),
        "catalogs": catalogs,
    }
