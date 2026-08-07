from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from itertools import combinations
from typing import Any, Iterable, Mapping, Sequence

from .serialization import logical_sha256, stable_id


class FamilyError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _dec(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise FamilyError("DIST_NONFINITE_RESULT", f"invalid distance {value}") from exc
    if not result.is_finite() or result < 0:
        raise FamilyError("DIST_NONFINITE_RESULT", "distance must be finite and non-negative")
    return result


def pair_key(left: str, right: str) -> str:
    if left == right:
        return f"{left}|{right}"
    a, b = sorted((left, right))
    return f"{a}|{b}"


@dataclass(frozen=True)
class DistanceMatrix:
    ids: tuple[str, ...]
    values: Mapping[str, str]

    @classmethod
    def from_pairs(cls, ids: Iterable[str], pairs: Mapping[str, Any]) -> "DistanceMatrix":
        ordered = tuple(sorted(set(str(value) for value in ids)))
        values = {str(key): str(_dec(value)) for key, value in pairs.items()}
        for left, right in combinations(ordered, 2):
            if pair_key(left, right) not in values:
                raise FamilyError("COMP_REQUIRED_DIMENSION_MISSING", f"missing distance {left},{right}")
        return cls(ordered, dict(sorted(values.items())))

    def distance(self, left: str, right: str) -> Decimal:
        if left == right:
            return Decimal("0")
        try:
            return _dec(self.values[pair_key(left, right)])
        except KeyError as exc:
            raise FamilyError("COMP_REQUIRED_DIMENSION_MISSING", f"missing distance {left},{right}") from exc


@dataclass(frozen=True)
class FamilyMethodSpec:
    method_id: str
    configuration_id: str
    radius: str | None = None
    minimum_support: int = 2
    k: int | None = None
    max_iterations: int = 20
    linkage: str | None = None
    max_assignment_distance: str | None = None

    def __post_init__(self) -> None:
        if self.minimum_support < 2:
            raise FamilyError("DIST_INVALID_PARAMETER", "minimum_support must be at least 2")
        if self.max_iterations < 1:
            raise FamilyError("DIST_INVALID_PARAMETER", "max_iterations must be positive")


def _family(catalog_seed: Mapping[str, Any], members: Sequence[str], *, prototype_type: str, prototype_id: str | None, method_id: str) -> dict[str, Any]:
    member_ids = tuple(sorted(members))
    payload = {
        "catalog_seed": dict(catalog_seed), "member_ids": list(member_ids),
        "prototype_descriptor": {"type": prototype_type, "record_id": prototype_id},
        "method_id": method_id, "authority_state": "FIXTURE_ONLY",
    }
    return {**payload, "family_id": stable_id("SRFD.FAM.", payload)}


def _catalog(method: FamilyMethodSpec, matrix: DistanceMatrix, families: Sequence[Mapping[str, Any]], residual_ids: Sequence[str], *, noise_ids: Sequence[str] = ()) -> dict[str, Any]:
    seed = {"method_id":method.method_id,"configuration_id":method.configuration_id,"population_ids":list(matrix.ids)}
    payload = {
        "method_id": method.method_id,
        "configuration_id": method.configuration_id,
        "families": sorted([dict(item) for item in families], key=lambda item: item["family_id"]),
        "residual_ids": sorted(set(residual_ids)),
        "noise_ids": sorted(set(noise_ids)),
        "singleton_ids": sorted({item for item in residual_ids if item not in noise_ids}),
        "full_assignment_target": False,
        "authority_state": "FIXTURE_ONLY",
    }
    status = "NO_STABLE_FAMILY" if not payload["families"] else "FAMILY_EVIDENCE_PRESENT"
    payload["evidence_status"] = status
    return {**payload,"family_catalog_id":stable_id("SRFD.CATALOG.",{**seed,"method_config":method.__dict__}),"logical_hash":logical_sha256(payload)}


def medoid_star(matrix: DistanceMatrix, spec: FamilyMethodSpec) -> dict[str, Any]:
    if spec.radius is None:
        raise FamilyError("DIST_INVALID_PARAMETER", "medoid-star radius required")
    radius = _dec(spec.radius)
    remaining = set(matrix.ids)
    families: list[dict[str, Any]] = []
    seed = {"method":spec.method_id,"configuration":spec.configuration_id,"population":list(matrix.ids)}
    while remaining:
        scored: list[tuple[int, Decimal, str, tuple[str, ...]]] = []
        for candidate in sorted(remaining):
            covered = tuple(sorted(item for item in remaining if matrix.distance(candidate, item) <= radius))
            total = sum((matrix.distance(candidate, item) for item in covered), Decimal("0"))
            scored.append((-len(covered), total, candidate, covered))
        _, _, medoid, covered = min(scored)
        if len(covered) < spec.minimum_support:
            break
        families.append(_family(seed, covered, prototype_type="MEDOID", prototype_id=medoid, method_id=spec.method_id))
        remaining.difference_update(covered)
    return _catalog(spec, matrix, families, sorted(remaining))


def hierarchical(matrix: DistanceMatrix, spec: FamilyMethodSpec) -> dict[str, Any]:
    if spec.radius is None or spec.linkage not in {"complete", "average"}:
        raise FamilyError("DIST_INVALID_PARAMETER", "hierarchical radius and complete/average linkage required")
    radius = _dec(spec.radius)
    clusters: list[tuple[str, ...]] = [(item,) for item in matrix.ids]
    def cluster_distance(left: Sequence[str], right: Sequence[str]) -> Decimal:
        distances = [matrix.distance(a, b) for a in left for b in right]
        if spec.linkage == "complete":
            return max(distances)
        return sum(distances, Decimal("0")) / Decimal(len(distances))
    while len(clusters) > 1:
        candidates: list[tuple[Decimal, tuple[str, ...], int, int]] = []
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                merged = tuple(sorted(clusters[i] + clusters[j]))
                candidates.append((cluster_distance(clusters[i],clusters[j]),merged,i,j))
        distance, merged, i, j = min(candidates, key=lambda value:(value[0],value[1]))
        if distance > radius:
            break
        clusters = [cluster for index,cluster in enumerate(clusters) if index not in {i,j}] + [merged]
        clusters.sort()
    seed = {"method":spec.method_id,"configuration":spec.configuration_id,"population":list(matrix.ids)}
    families = [_family(seed, cluster, prototype_type="EXEMPLAR_SET", prototype_id=None, method_id=spec.method_id) for cluster in clusters if len(cluster) >= spec.minimum_support]
    residual = [item for cluster in clusters if len(cluster) < spec.minimum_support for item in cluster]
    return _catalog(spec,matrix,families,residual)


def bounded_pam(matrix: DistanceMatrix, spec: FamilyMethodSpec) -> dict[str, Any]:
    if spec.k is None or spec.k < 1 or spec.k > len(matrix.ids):
        raise FamilyError("DIST_INVALID_PARAMETER", "PAM k outside population")
    medoids = list(matrix.ids[:spec.k])
    radius = _dec(spec.max_assignment_distance) if spec.max_assignment_distance is not None else None
    assignments: dict[str, list[str]] = {}
    residual: list[str] = []
    for _ in range(spec.max_iterations):
        assignments = {medoid: [] for medoid in medoids}; residual = []
        for item in matrix.ids:
            ranked = sorted((matrix.distance(item,medoid),medoid) for medoid in medoids)
            distance, medoid = ranked[0]
            if radius is not None and distance > radius:
                residual.append(item)
            else:
                assignments[medoid].append(item)
        updated: list[str] = []
        for medoid in medoids:
            members = assignments[medoid]
            if not members:
                updated.append(medoid); continue
            scored = [(sum((matrix.distance(candidate,item) for item in members),Decimal("0")),candidate) for candidate in members]
            updated.append(min(scored)[1])
        updated = sorted(set(updated))
        if updated == sorted(medoids):
            break
        while len(updated) < spec.k:
            updated.append(next(item for item in matrix.ids if item not in updated))
        medoids = sorted(updated[:spec.k])
    seed = {"method":spec.method_id,"configuration":spec.configuration_id,"population":list(matrix.ids)}
    families: list[dict[str, Any]] = []
    small_cluster_residual: list[str] = []
    for medoid in medoids:
        members = assignments.get(medoid,[])
        if len(members) >= spec.minimum_support:
            families.append(_family(seed,members,prototype_type="MEDOID",prototype_id=medoid,method_id=spec.method_id))
        else:
            small_cluster_residual.extend(members)
    residual.extend(small_cluster_residual)
    return _catalog(spec,matrix,families,residual)


def family_assignments(catalog: Mapping[str, Any]) -> list[dict[str, Any]]:
    assignments: list[dict[str, Any]] = []
    for family in catalog.get("families", []):
        for member in family["member_ids"]:
            assignments.append({"record_id":member,"status":"MEMBER","family_id":family["family_id"],"authority_state":"FIXTURE_ONLY"})
    for member in catalog.get("residual_ids", []):
        assignments.append({"record_id":member,"status":"RESIDUAL","family_id":None,"reason_code":"FAM_ALL_RESIDUAL" if not catalog.get("families") else "FAM_RESIDUAL","authority_state":"FIXTURE_ONLY"})
    for member in catalog.get("noise_ids", []):
        assignments.append({"record_id":member,"status":"NOISE","family_id":None,"reason_code":"FAM_NOISE","authority_state":"FIXTURE_ONLY"})
    return sorted(assignments,key=lambda item:(item["record_id"],item["status"]))


def sequence_native_wrapper(matrix: DistanceMatrix, spec: FamilyMethodSpec, *, adapter: str) -> dict[str, Any]:
    if adapter == "MEDOID_STAR":
        return medoid_star(matrix,spec)
    if adapter == "PAM":
        return bounded_pam(matrix,spec)
    raise FamilyError("DIST_INVALID_PARAMETER", "unsupported sequence-native wrapper")
