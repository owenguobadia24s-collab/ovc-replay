from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from itertools import combinations
from typing import Any, Sequence

from .families import DistanceMatrix, FamilyError, FamilyMethodSpec, _catalog, _dec, _family
from .families_optimized import PreparedDistanceMatrix, bounded_pam_optimized, medoid_star_optimized
from .serialization import logical_sha256, stable_id


@dataclass(frozen=True)
class MedoidStarTraceStep:
    medoid: str
    covered: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"medoid": self.medoid, "covered": list(self.covered)}


@dataclass(frozen=True)
class MedoidStarTrace:
    radius: str
    population_ids: tuple[str, ...]
    steps: tuple[MedoidStarTraceStep, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": "ovc-srfdi-wp10a-medoid-star-trace/v1",
            "radius": self.radius,
            "population_ids": list(self.population_ids),
            "steps": [step.to_dict() for step in self.steps],
            "scientific_effect": "NONE_CAPACITY_ONLY",
        }
        return {**payload, "logical_hash": logical_sha256(payload)}


def build_medoid_star_trace(matrix: DistanceMatrix, *, radius: str) -> MedoidStarTrace:
    bound = _dec(radius)
    prepared = PreparedDistanceMatrix.from_matrix(matrix)
    adjacency: dict[str, list[tuple[str, Decimal]]] = {
        item: [(item, Decimal("0"))] for item in matrix.ids
    }
    for left, right in combinations(matrix.ids, 2):
        distance = prepared.distance(left, right)
        if distance <= bound:
            adjacency[left].append((right, distance))
            adjacency[right].append((left, distance))
    for item in matrix.ids:
        adjacency[item].sort(key=lambda pair: pair[0])

    active = set(matrix.ids)
    active_counts = {item: len(adjacency[item]) for item in matrix.ids}
    steps: list[MedoidStarTraceStep] = []
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
        if len(covered) < 2:
            break
        steps.append(MedoidStarTraceStep(medoid=medoid, covered=covered))
        active.difference_update(covered)
        for removed in covered:
            for candidate, _ in adjacency[removed]:
                if candidate in active:
                    active_counts[candidate] -= 1
    return MedoidStarTrace(format(bound, "f"), matrix.ids, tuple(steps))


def materialize_medoid_star_trace(
    matrix: DistanceMatrix,
    trace: MedoidStarTrace,
    spec: FamilyMethodSpec,
) -> dict[str, object]:
    if spec.radius is None or _dec(spec.radius) != _dec(trace.radius):
        raise FamilyError("DIST_INVALID_PARAMETER", "medoid trace/spec radius mismatch")
    if trace.population_ids != matrix.ids:
        raise FamilyError("QA_NON_REPRODUCIBLE", "medoid trace population mismatch")
    remaining = set(matrix.ids)
    seed = {
        "method": spec.method_id,
        "configuration": spec.configuration_id,
        "population": list(matrix.ids),
    }
    families: list[dict[str, object]] = []
    for step in trace.steps:
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
    return _catalog(spec, matrix, families, sorted(remaining))


@dataclass(frozen=True)
class BoundedPamCore:
    k: int
    max_assignment_distance: str | None
    max_iterations: int
    population_ids: tuple[str, ...]
    medoids: tuple[str, ...]
    assignments: tuple[tuple[str, tuple[str, ...]], ...]
    residual: tuple[str, ...]

    def assignment_map(self) -> dict[str, list[str]]:
        return {medoid: list(members) for medoid, members in self.assignments}

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": "ovc-srfdi-wp10a-bounded-pam-core/v1",
            "k": self.k,
            "max_assignment_distance": self.max_assignment_distance,
            "max_iterations": self.max_iterations,
            "population_ids": list(self.population_ids),
            "medoids": list(self.medoids),
            "assignments": [
                {"medoid": medoid, "members": list(members)}
                for medoid, members in self.assignments
            ],
            "residual": list(self.residual),
            "scientific_effect": "NONE_CAPACITY_ONLY",
        }
        return {**payload, "logical_hash": logical_sha256(payload)}


def build_bounded_pam_core(
    matrix: DistanceMatrix,
    *,
    k: int,
    max_assignment_distance: str | None,
    max_iterations: int,
) -> BoundedPamCore:
    if k < 1 or k > len(matrix.ids) or max_iterations < 1:
        raise FamilyError("DIST_INVALID_PARAMETER", "invalid PAM capacity core parameters")
    prepared = PreparedDistanceMatrix.from_matrix(matrix)
    medoids = list(matrix.ids[:k])
    radius = _dec(max_assignment_distance) if max_assignment_distance is not None else None
    assignments: dict[str, list[str]] = {}
    residual: list[str] = []
    for _ in range(max_iterations):
        assignments = {medoid: [] for medoid in medoids}
        residual = []
        for item in matrix.ids:
            distance, medoid = min(
                (prepared.distance(item, candidate), candidate) for candidate in medoids
            )
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
        while len(updated) < k:
            updated.append(next(item for item in matrix.ids if item not in updated))
        medoids = sorted(updated[:k])
    return BoundedPamCore(
        k=k,
        max_assignment_distance=max_assignment_distance,
        max_iterations=max_iterations,
        population_ids=matrix.ids,
        medoids=tuple(medoids),
        assignments=tuple(
            (medoid, tuple(assignments.get(medoid, ()))) for medoid in medoids
        ),
        residual=tuple(residual),
    )


def materialize_bounded_pam_core(
    matrix: DistanceMatrix,
    core: BoundedPamCore,
    spec: FamilyMethodSpec,
) -> dict[str, object]:
    if (
        spec.k != core.k
        or spec.max_assignment_distance != core.max_assignment_distance
        or spec.max_iterations != core.max_iterations
        or core.population_ids != matrix.ids
    ):
        raise FamilyError("QA_NON_REPRODUCIBLE", "PAM core/spec mismatch")
    assignments = core.assignment_map()
    seed = {
        "method": spec.method_id,
        "configuration": spec.configuration_id,
        "population": list(matrix.ids),
    }
    families: list[dict[str, object]] = []
    residual = list(core.residual)
    for medoid in core.medoids:
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
            residual.extend(members)
    return _catalog(spec, matrix, families, residual)


def frozen_medoid_configuration_id(
    *, domain_id: str, radius: str, minimum_support: int
) -> str:
    return stable_id(
        "SRFD.WP10A.CONFIG.",
        {
            "domain_id": domain_id,
            "method_id": "GREEDY_LEXICOGRAPHIC_MEDOID_STAR",
            "radius": str(radius),
            "minimum_support": int(minimum_support),
        },
    )


def frozen_pam_configuration_id(
    *,
    domain_id: str,
    k: int,
    max_assignment_distance: str,
    max_iterations: int,
    minimum_support: int,
) -> str:
    return stable_id(
        "SRFD.WP10A.CONFIG.",
        {
            "domain_id": domain_id,
            "method_id": "BOUNDED_PAM",
            "k": int(k),
            "max_assignment_distance": str(max_assignment_distance),
            "max_iterations": int(max_iterations),
            "minimum_support": int(minimum_support),
        },
    )


def verify_reuse_against_independent_optimized(
    matrix: DistanceMatrix,
    *,
    domain_id: str,
    radii: Sequence[str] = ("0.04", "0.08", "0.16"),
    minimum_supports: Sequence[int] = (2, 4, 8),
    pam_k: Sequence[int] = (2, 4, 8),
    pam_assignment_radii: Sequence[str] = ("0.10", "0.20", "0.40"),
    pam_max_iterations: int = 8,
) -> dict[str, Any]:
    checked = 0
    for radius in radii:
        trace = build_medoid_star_trace(matrix, radius=radius)
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
            if medoid_star_optimized(matrix, spec) != materialize_medoid_star_trace(matrix, trace, spec):
                raise FamilyError("G10A_GRID_MATERIALIZATION_EQUIVALENCE_FAILURE", config)
            checked += 1
    for k in pam_k:
        if k > len(matrix.ids):
            continue
        for radius in pam_assignment_radii:
            core = build_bounded_pam_core(
                matrix,
                k=k,
                max_assignment_distance=radius,
                max_iterations=pam_max_iterations,
            )
            for support in minimum_supports:
                config = frozen_pam_configuration_id(
                    domain_id=domain_id,
                    k=k,
                    max_assignment_distance=radius,
                    max_iterations=pam_max_iterations,
                    minimum_support=support,
                )
                spec = FamilyMethodSpec(
                    "BOUNDED_PAM",
                    config,
                    k=k,
                    minimum_support=support,
                    max_assignment_distance=radius,
                    max_iterations=pam_max_iterations,
                )
                if bounded_pam_optimized(matrix, spec) != materialize_bounded_pam_core(matrix, core, spec):
                    raise FamilyError("G10A_GRID_MATERIALIZATION_EQUIVALENCE_FAILURE", config)
                checked += 1
    payload = {
        "schema": "ovc-srfdi-wp10a-reuse-equivalence/v1",
        "domain_id": domain_id,
        "checked_configuration_count": checked,
        "result": "PASS",
        "scientific_effect": "NONE_CAPACITY_ONLY",
    }
    return {**payload, "logical_hash": logical_sha256(payload)}
