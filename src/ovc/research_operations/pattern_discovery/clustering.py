from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from math import floor, sqrt
from typing import Any, Iterable, Mapping, Sequence

from ovc.research_operations.canonical import canonical_sha256

from .distance import DistancePack, ScalePack, build_scale_pack, composite_distance
from .fingerprints import FINGERPRINT_VERSION, partition_key
from .models import PatternDiscoveryError


ALGORITHM_VERSION = "PD.PAM.v0.1"
MAX_ACTIVE_PARTITION = 500
ALLOWED_MACHINE_STATUSES = {"PROVISIONAL", "RECURRING", "REVIEW_REQUIRED", "RESTRICTED", "REJECTED", "SUPERSEDED"}


def _validate(fingerprints: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted((dict(item) for item in fingerprints), key=lambda item: str(item.get("fingerprint_id")))
    ids = [str(item.get("fingerprint_id") or "") for item in ordered]
    if any(not item for item in ids):
        raise PatternDiscoveryError("every fingerprint requires fingerprint_id")
    if len(ids) != len(set(ids)):
        raise PatternDiscoveryError("duplicate fingerprint IDs fail closed")
    versions = {str(item.get("fingerprint_version")) for item in ordered}
    if len(versions) > 1:
        raise PatternDiscoveryError("mixed fingerprint versions fail closed")
    for item in ordered:
        if item.get("record_type") != "PatternFingerprint":
            raise PatternDiscoveryError("clustering input must be PatternFingerprint")
        partition_key(item)
    return ordered


def eligible_clustering_population(fingerprints: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for source in fingerprints:
        item = dict(source)
        reasons: list[str] = []
        status = str(item.get("candidate_status") or item.get("status") or "READY_FOR_REVIEW")
        if status in {"INVALID", "QUARANTINED"}:
            reasons.append("INVALID_OR_QUARANTINED")
        if item.get("source_lineage_status") not in {None, "RESOLVED"}:
            reasons.append("UNRESOLVED_LINEAGE")
        if item.get("fingerprint_status") == "FAILED":
            reasons.append("FINGERPRINT_FAILED")
        mode = str(item.get("operation_mode") or "LIVE_PROSPECTIVE")
        if mode in {"TIME_GATED_REPLAY", "NON_EVIDENTIARY_REPLAY"} and item.get("prospective_count_requested"):
            reasons.append("NON_PROSPECTIVE_MODE")
        serialized_keys = {str(key).lower() for key in item.keys()}
        if serialized_keys & {"return", "returns", "mfe", "mae", "outcome", "probability", "trade_direction"}:
            reasons.append("PROHIBITED_OUTCOME_FEATURE")
        if reasons:
            excluded.append({"fingerprint_id": item.get("fingerprint_id"), "reasons": sorted(reasons)})
        else:
            included.append(item)
    return {"included": included, "excluded": excluded}


def _matrix(
    fingerprints: Sequence[Mapping[str, Any]],
    *,
    scale_pack: ScalePack,
    distance_pack: DistancePack,
) -> dict[tuple[str, str], float]:
    result: dict[tuple[str, str], float] = {}
    for left_index, left in enumerate(fingerprints):
        left_id = str(left["fingerprint_id"])
        result[(left_id, left_id)] = 0.0
        for right in fingerprints[left_index + 1 :]:
            right_id = str(right["fingerprint_id"])
            value = composite_distance(left, right, scale_pack=scale_pack, distance_pack=distance_pack)["distance"]
            result[(left_id, right_id)] = value
            result[(right_id, left_id)] = value
    return result


def _assign(ids: Sequence[str], medoids: Sequence[str], matrix: Mapping[tuple[str, str], float]) -> tuple[dict[str, str], dict[str, float], float]:
    assignments: dict[str, str] = {}
    distances: dict[str, float] = {}
    for item in ids:
        ranked = sorted((matrix[(item, medoid)], medoid) for medoid in medoids)
        distance, medoid = ranked[0]
        assignments[item] = medoid
        distances[item] = distance
    return assignments, distances, sum(distances.values())


def deterministic_pam(
    fingerprints: Sequence[Mapping[str, Any]],
    *,
    k: int,
    scale_pack: ScalePack | None = None,
    distance_pack: DistancePack = DistancePack(),
) -> dict[str, Any]:
    ordered = _validate(fingerprints)
    if not ordered:
        raise PatternDiscoveryError("PAM requires fingerprints")
    if k < 1 or k > len(ordered):
        raise ValueError("k must be between one and population size")
    scale = scale_pack or build_scale_pack(ordered)
    ids = [str(item["fingerprint_id"]) for item in ordered]
    matrix = _matrix(ordered, scale_pack=scale, distance_pack=distance_pack)

    first = min(ids, key=lambda candidate: (sum(matrix[(item, candidate)] for item in ids), candidate))
    medoids = [first]
    while len(medoids) < k:
        best_candidate = None
        best_cost = None
        best_set: tuple[str, ...] | None = None
        for candidate in ids:
            if candidate in medoids:
                continue
            candidate_set = tuple(sorted(medoids + [candidate]))
            _, _, cost = _assign(ids, candidate_set, matrix)
            key = (round(cost, 12), candidate_set)
            if best_cost is None or key < (best_cost, best_set):
                best_candidate = candidate
                best_cost = key[0]
                best_set = candidate_set
        if best_candidate is None:
            break
        medoids = list(best_set or sorted(medoids + [best_candidate]))

    while True:
        current_assignments, current_distances, current_cost = _assign(ids, medoids, matrix)
        best_medoids = tuple(sorted(medoids))
        best_cost = round(current_cost, 12)
        for medoid in tuple(medoids):
            for candidate in ids:
                if candidate in medoids:
                    continue
                proposed = tuple(sorted((set(medoids) - {medoid}) | {candidate}))
                _, _, cost = _assign(ids, proposed, matrix)
                rounded = round(cost, 12)
                if rounded < best_cost - 1e-12 or (abs(rounded - best_cost) <= 1e-12 and proposed < best_medoids):
                    best_cost = rounded
                    best_medoids = proposed
        if best_medoids == tuple(sorted(medoids)):
            assignments, distances, total_cost = current_assignments, current_distances, current_cost
            break
        medoids = list(best_medoids)

    return {
        "k": k,
        "medoid_ids": sorted(medoids),
        "assignments": assignments,
        "distances": {key: round(value, 12) for key, value in sorted(distances.items())},
        "total_within_cluster_distance": round(total_cost, 12),
        "matrix": matrix,
        "scale_pack": scale,
        "distance_pack": distance_pack,
    }


def _silhouette(assignments: Mapping[str, str], matrix: Mapping[tuple[str, str], float]) -> float:
    members: dict[str, list[str]] = defaultdict(list)
    for item, medoid in assignments.items():
        members[medoid].append(item)
    if len(members) <= 1:
        return 0.0
    scores: list[float] = []
    for item, own_medoid in assignments.items():
        own = [other for other in members[own_medoid] if other != item]
        if not own:
            scores.append(0.0)
            continue
        a = sum(matrix[(item, other)] for other in own) / len(own)
        alternatives = []
        for medoid, cluster_members in members.items():
            if medoid == own_medoid:
                continue
            alternatives.append(sum(matrix[(item, other)] for other in cluster_members) / len(cluster_members))
        b = min(alternatives)
        denominator = max(a, b)
        scores.append(0.0 if denominator == 0 else (b - a) / denominator)
    return sum(scores) / len(scores)


def _p90(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(int(round(0.9 * (len(ordered) - 1))), len(ordered) - 1)
    return ordered[index]


def build_partition_cluster_version(
    fingerprints: Sequence[Mapping[str, Any]],
    *,
    previous_cluster_version: Mapping[str, Any] | None = None,
    distance_pack: DistancePack = DistancePack(),
    capacity: int = MAX_ACTIVE_PARTITION,
) -> dict[str, Any]:
    ordered = _validate(fingerprints)
    if not ordered:
        raise PatternDiscoveryError("cluster build requires input")
    keys = {partition_key(item) for item in ordered}
    if len(keys) != 1:
        raise PatternDiscoveryError("different structural partitions cannot share a PAM build")
    partition = next(iter(keys))
    input_hash = canonical_sha256(sorted(str(item["fingerprint_id"]) for item in ordered))
    common = {
        "record_type": "ClusterVersion",
        "algorithm_version": ALGORITHM_VERSION,
        "fingerprint_version": str(ordered[0].get("fingerprint_version") or FINGERPRINT_VERSION),
        "distance_pack_id": distance_pack.pack_id,
        "partition": list(partition),
        "input_candidate_set_hash": input_hash,
        "input_count": len(ordered),
        "previous_cluster_version_id": previous_cluster_version.get("cluster_version_id") if previous_cluster_version else None,
    }
    if len(ordered) > capacity:
        payload = {**common, "build_status": "CLUSTER_BUILD_CAPACITY_BLOCK", "capacity": capacity}
        return {"cluster_version_id": f"PDCV-{canonical_sha256(payload)[:32]}", **payload}
    if len(ordered) < 5:
        payload = {
            **common,
            "build_status": "UNASSIGNED_SMALL_SAMPLE",
            "members": sorted(str(item["fingerprint_id"]) for item in ordered),
            "clusters": [],
        }
        return {"cluster_version_id": f"PDCV-{canonical_sha256(payload)[:32]}", **payload}

    scale_pack = build_scale_pack(ordered)
    max_k = min(8, floor(sqrt(len(ordered))))
    candidates: list[dict[str, Any]] = []
    for k in range(1, max_k + 1):
        result = deterministic_pam(ordered, k=k, scale_pack=scale_pack, distance_pack=distance_pack)
        silhouette = _silhouette(result["assignments"], result["matrix"])
        penalized = silhouette - (distance_pack.complexity_penalty_per_cluster * k)
        candidates.append({**result, "silhouette": round(silhouette, 12), "penalized_silhouette": round(penalized, 12)})
    selected = sorted(
        candidates,
        key=lambda item: (
            -item["penalized_silhouette"],
            item["k"],
            item["total_within_cluster_distance"],
            tuple(item["medoid_ids"]),
        ),
    )[0]

    cluster_rows: list[dict[str, Any]] = []
    for medoid in selected["medoid_ids"]:
        members = sorted(item for item, assigned in selected["assignments"].items() if assigned == medoid)
        member_distances = [selected["distances"][item] for item in members]
        dispersion = 0.0 if not member_distances else sum(member_distances) / len(member_distances)
        threshold = _p90(member_distances)
        cluster_payload = {
            "medoid_id": medoid,
            "member_ids": members,
            "member_count": len(members),
            "dispersion": round(dispersion, 12),
            "outlier_threshold_p90": round(threshold, 12),
            "outlier_ids": sorted(item for item in members if selected["distances"][item] > threshold),
            "status": "RECURRING" if len(members) >= 5 else "PROVISIONAL",
        }
        if cluster_payload["status"] not in ALLOWED_MACHINE_STATUSES:
            raise PatternDiscoveryError("invalid machine cluster status")
        cluster_rows.append({"cluster_id": f"PDCL-{canonical_sha256(cluster_payload)[:24]}", **cluster_payload})

    payload = {
        **common,
        "build_status": "PASS",
        "scale_pack_id": scale_pack.scale_id,
        "selected_k": selected["k"],
        "silhouette": selected["silhouette"],
        "penalized_silhouette": selected["penalized_silhouette"],
        "total_within_cluster_distance": selected["total_within_cluster_distance"],
        "medoid_ids": selected["medoid_ids"],
        "assignments": selected["assignments"],
        "distances": selected["distances"],
        "clusters": sorted(cluster_rows, key=lambda item: item["cluster_id"]),
    }
    return {"cluster_version_id": f"PDCV-{canonical_sha256(payload)[:32]}", **payload}


def build_cluster_versions(fingerprints: Iterable[Mapping[str, Any]], *, capacity: int = MAX_ACTIVE_PARTITION) -> list[dict[str, Any]]:
    population = eligible_clustering_population(fingerprints)
    ordered = _validate(population["included"])
    partitions: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for item in ordered:
        partitions[partition_key(item)].append(item)
    return [
        build_partition_cluster_version(partitions[key], capacity=capacity)
        for key in sorted(partitions)
    ]


def map_cluster_lineage(previous: Mapping[str, Any], current: Mapping[str, Any]) -> list[dict[str, Any]]:
    previous_clusters = {item["cluster_id"]: set(item.get("member_ids", ())) for item in previous.get("clusters", ())}
    current_clusters = {item["cluster_id"]: set(item.get("member_ids", ())) for item in current.get("clusters", ())}
    links: list[dict[str, Any]] = []
    for previous_id, previous_members in sorted(previous_clusters.items()):
        overlaps = []
        for current_id, current_members in sorted(current_clusters.items()):
            intersection = len(previous_members & current_members)
            if intersection:
                overlaps.append((current_id, intersection))
        if not overlaps:
            links.append({"previous_cluster_id": previous_id, "current_cluster_ids": [], "relation": "DISSOLVED"})
        elif len(overlaps) == 1:
            current_id = overlaps[0][0]
            relation = "RETAINED" if previous_members == current_clusters[current_id] else "MATCHED_CHANGED"
            links.append({"previous_cluster_id": previous_id, "current_cluster_ids": [current_id], "relation": relation})
        else:
            links.append({"previous_cluster_id": previous_id, "current_cluster_ids": [item[0] for item in overlaps], "relation": "SPLIT"})
    for current_id, current_members in sorted(current_clusters.items()):
        sources = [previous_id for previous_id, members in previous_clusters.items() if members & current_members]
        if not sources:
            links.append({"previous_cluster_ids": [], "current_cluster_id": current_id, "relation": "UNMATCHED"})
        elif len(sources) > 1:
            links.append({"previous_cluster_ids": sorted(sources), "current_cluster_id": current_id, "relation": "MERGED"})
    return links
