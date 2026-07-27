from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import median
from typing import Any, Iterable, Mapping, Sequence

from ovc.research_operations.canonical import canonical_sha256

from .models import AXES, PatternDiscoveryError


DISTANCE_VERSION = "PD.DISTANCE.v0.1"
DOMAIN_WEIGHTS = {
    "state_path": 0.25,
    "transition_sequence": 0.25,
    "interaction": 0.15,
    "cross_scale": 0.15,
    "duration_persistence": 0.10,
    "quality": 0.10,
}


@dataclass(frozen=True)
class DistancePack:
    pack_id: str = DISTANCE_VERSION
    missing_one_penalty: float = 0.75
    missing_different_penalty: float = 1.0
    same_missing_reason_distance: float = 0.0
    numeric_clip: float = 3.0
    complexity_penalty_per_cluster: float = 0.01

    def as_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "domain_weights": DOMAIN_WEIGHTS,
            "missing_one_penalty": self.missing_one_penalty,
            "missing_different_penalty": self.missing_different_penalty,
            "same_missing_reason_distance": self.same_missing_reason_distance,
            "numeric_clip": self.numeric_clip,
            "complexity_penalty_per_cluster": self.complexity_penalty_per_cluster,
        }


@dataclass(frozen=True)
class ScaleStat:
    median: float
    iqr: float


@dataclass(frozen=True)
class ScalePack:
    scale_id: str
    features: Mapping[str, ScaleStat]

    def as_dict(self) -> dict[str, Any]:
        return {
            "scale_id": self.scale_id,
            "features": {
                key: {"median": value.median, "iqr": value.iqr}
                for key, value in sorted(self.features.items())
            },
        }


def _percentile(values: Sequence[float], p: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * p
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def build_scale_pack(fingerprints: Sequence[Mapping[str, Any]], *, scale_id: str = "PD.SCALE.v0.1") -> ScalePack:
    feature_names = ("duration_records", "transition_count", "switch_count", "max_persistence")
    features: dict[str, ScaleStat] = {}
    for feature in feature_names:
        values = [float(item["duration_persistence"][feature]) for item in fingerprints if item.get("duration_persistence", {}).get(feature) is not None]
        if not values:
            features[feature] = ScaleStat(0.0, 1.0)
            continue
        q1 = _percentile(values, 0.25)
        q3 = _percentile(values, 0.75)
        iqr = q3 - q1
        features[feature] = ScaleStat(float(median(values)), iqr if iqr > 0 else 1.0)
    payload = {"scale_id": scale_id, "features": {k: {"median": v.median, "iqr": v.iqr} for k, v in sorted(features.items())}}
    return ScalePack(scale_id=f"{scale_id}-{canonical_sha256(payload)[:12]}", features=features)


def normalized_levenshtein(left: Sequence[str], right: Sequence[str]) -> float:
    if not left and not right:
        return 0.0
    if not left or not right:
        return 1.0
    previous = list(range(len(right) + 1))
    for i, left_value in enumerate(left, start=1):
        current = [i]
        for j, right_value in enumerate(right, start=1):
            substitution = previous[j - 1] + (0 if left_value == right_value else 1)
            current.append(min(current[-1] + 1, previous[j] + 1, substitution))
        previous = current
    return previous[-1] / max(len(left), len(right))


def jaccard_distance(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set and not right_set:
        return 0.0
    return 1.0 - len(left_set & right_set) / len(left_set | right_set)


def _categorical_distance(left: Any, right: Any, pack: DistancePack) -> float:
    left_missing = left is None or str(left).startswith("NOT_EVALUABLE")
    right_missing = right is None or str(right).startswith("NOT_EVALUABLE")
    if left_missing and right_missing:
        return pack.same_missing_reason_distance if left == right else pack.missing_different_penalty
    if left_missing or right_missing:
        return pack.missing_one_penalty
    return 0.0 if left == right else 1.0


def _mapping_categorical_distance(left: Mapping[str, Any], right: Mapping[str, Any], pack: DistancePack) -> float:
    keys = sorted(set(left) | set(right))
    if not keys:
        return 0.0
    return sum(_categorical_distance(left.get(key), right.get(key), pack) for key in keys) / len(keys)


def _occupancy_distance(left: Mapping[str, Mapping[str, float]], right: Mapping[str, Mapping[str, float]]) -> float:
    axis_distances: list[float] = []
    for axis in AXES:
        left_axis = left.get(axis, {})
        right_axis = right.get(axis, {})
        keys = set(left_axis) | set(right_axis)
        if not keys:
            axis_distances.append(0.0)
            continue
        axis_distances.append(sum(abs(float(left_axis.get(key, 0.0)) - float(right_axis.get(key, 0.0))) for key in keys) / 2.0)
    return sum(axis_distances) / len(axis_distances)


def _state_path_distance(left: Mapping[str, Any], right: Mapping[str, Any], pack: DistancePack) -> float:
    initial = _mapping_categorical_distance(left.get("initial", {}), right.get("initial", {}), pack)
    terminal = _mapping_categorical_distance(left.get("terminal", {}), right.get("terminal", {}), pack)
    occupancy = _occupancy_distance(left.get("occupancy", {}), right.get("occupancy", {}))
    return (0.4 * initial) + (0.3 * terminal) + (0.3 * occupancy)


def _numeric_distance(left: float | None, right: float | None, stat: ScaleStat, pack: DistancePack) -> float:
    if left is None and right is None:
        return pack.same_missing_reason_distance
    if left is None or right is None:
        return pack.missing_one_penalty
    raw = abs(float(left) - float(right)) / max(stat.iqr, 1e-12)
    return min(raw, pack.numeric_clip) / pack.numeric_clip


def _duration_distance(left: Mapping[str, Any], right: Mapping[str, Any], scale_pack: ScalePack, pack: DistancePack) -> float:
    keys = sorted(scale_pack.features)
    if not keys:
        return 0.0
    return sum(_numeric_distance(left.get(key), right.get(key), scale_pack.features[key], pack) for key in keys) / len(keys)


def _quality_distance(left: Mapping[str, Any], right: Mapping[str, Any], pack: DistancePack) -> float:
    categorical = (
        _categorical_distance(left.get("closure_reason"), right.get("closure_reason"), pack)
        + _categorical_distance(left.get("censored"), right.get("censored"), pack)
    ) / 2.0
    numeric_keys = ("not_evaluable_fraction", "conflict_fraction", "stale_fraction")
    numeric = sum(abs(float(left.get(key, 0.0)) - float(right.get(key, 0.0))) for key in numeric_keys) / len(numeric_keys)
    return (0.5 * categorical) + (0.5 * min(numeric, 1.0))


def composite_distance(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    scale_pack: ScalePack,
    distance_pack: DistancePack = DistancePack(),
) -> dict[str, Any]:
    if left.get("fingerprint_version") != right.get("fingerprint_version"):
        raise PatternDiscoveryError("mixed fingerprint versions fail closed")
    domains = {
        "state_path": _state_path_distance(left.get("state_path", {}), right.get("state_path", {}), distance_pack),
        "transition_sequence": normalized_levenshtein(left.get("transition_sequence", []), right.get("transition_sequence", [])),
        "interaction": jaccard_distance(left.get("interaction_events", []), right.get("interaction_events", [])),
        "cross_scale": _mapping_categorical_distance(left.get("cross_scale", {}), right.get("cross_scale", {}), distance_pack),
        "duration_persistence": _duration_distance(left.get("duration_persistence", {}), right.get("duration_persistence", {}), scale_pack, distance_pack),
        "quality": _quality_distance(left.get("quality", {}), right.get("quality", {}), distance_pack),
    }
    total = sum(DOMAIN_WEIGHTS[name] * value for name, value in domains.items())
    if not isfinite(total):
        raise PatternDiscoveryError("non-finite composite distance")
    return {
        "distance": round(total, 12),
        "domains": {key: round(value, 12) for key, value in domains.items()},
        "distance_pack_id": distance_pack.pack_id,
        "scale_pack_id": scale_pack.scale_id,
    }
