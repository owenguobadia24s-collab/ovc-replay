from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from .distance import DOMAIN_WEIGHTS, DistancePack, build_scale_pack, composite_distance
from .models import C2Snapshot, ChronologyError, PatternDiscoveryError, parse_utc
from .windows import CandidateWindowManager


_HISTORY_REQUIREMENTS = {
    "LONG_PERSISTENCE": {"minimum_records": 4, "history_kind": "PRE_TRIGGER_C2_STATE_HISTORY"},
    "REPEATED_SWITCHING": {"minimum_records": 6, "history_kind": "PRE_TRIGGER_C2_STATE_HISTORY"},
}


def _timeline_row(source: Mapping[str, Any]) -> dict[str, Any]:
    item = dict(source)
    state_id = item.get("c2_state_id")
    first_valid_time = item.get("first_valid_time")
    if not isinstance(state_id, str) or not state_id:
        raise PatternDiscoveryError("candidate timeline row requires c2_state_id")
    if not isinstance(first_valid_time, str) or not first_valid_time:
        raise ChronologyError("candidate timeline row requires first_valid_time")
    parse_utc(first_valid_time)
    return item


def chronological_timeline(timeline: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return an immutable read-only timeline projection in first-valid order.

    The projection fails closed on duplicate C2 identities or invalid timestamps. It
    does not change candidate identity, source bytes, trigger identity or release
    authority.
    """

    rows = [_timeline_row(item) for item in timeline]
    ids = [str(item["c2_state_id"]) for item in rows]
    if len(ids) != len(set(ids)):
        raise PatternDiscoveryError("candidate timeline contains duplicate C2 state IDs")
    return sorted(rows, key=lambda item: (parse_utc(str(item["first_valid_time"])), str(item["c2_state_id"])))


def timeline_is_chronological(timeline: Iterable[Mapping[str, Any]]) -> bool:
    rows = [_timeline_row(item) for item in timeline]
    ordered_ids = [str(item["c2_state_id"]) for item in chronological_timeline(rows)]
    return ordered_ids == [str(item["c2_state_id"]) for item in rows]


def align_source_ids_to_timeline(
    source_c2_record_ids: Iterable[str],
    timeline: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Align source IDs to the chronology of an exact candidate timeline."""

    source_ids = [str(item) for item in source_c2_record_ids]
    if len(source_ids) != len(set(source_ids)):
        raise PatternDiscoveryError("candidate source C2 IDs contain duplicates")
    ordered = chronological_timeline(timeline)
    ordered_ids = [str(item["c2_state_id"]) for item in ordered]
    if set(source_ids) != set(ordered_ids):
        raise PatternDiscoveryError("candidate timeline and source C2 IDs do not reconcile")
    return ordered_ids


def project_candidate_chronology(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Build a chronology-safe candidate projection without rewriting evidence."""

    timeline_source = candidate.get("timeline", ())
    if not isinstance(timeline_source, (list, tuple)):
        raise PatternDiscoveryError("candidate timeline must be a sequence")
    original = [_timeline_row(item) for item in timeline_source]
    ordered = chronological_timeline(original)
    source_ids = list(candidate.get("source_c2_record_ids", ()))
    ordered_ids = align_source_ids_to_timeline(source_ids, ordered) if ordered else [str(item) for item in source_ids]
    return {
        "timeline": ordered,
        "source_c2_record_ids": ordered_ids,
        "original_is_chronological": [row["c2_state_id"] for row in original]
        == [row["c2_state_id"] for row in ordered],
        "ordering_rule": "FIRST_VALID_TIME_THEN_C2_STATE_ID",
        "mutation": "NONE_READ_ONLY_PROJECTION_ONLY",
    }


def trigger_history_requirement(primary_trigger_reason: str | None) -> dict[str, Any]:
    reason = str(primary_trigger_reason or "")
    requirement = _HISTORY_REQUIREMENTS.get(reason)
    if requirement is None:
        return {
            "required": False,
            "trigger_reason": reason,
            "minimum_records": 0,
            "history_kind": "NOT_APPLICABLE",
        }
    return {"required": True, "trigger_reason": reason, **requirement}


def recompute_structural_comparison(
    fingerprint: Mapping[str, Any],
    medoid: Mapping[str, Any],
    cluster_version: Mapping[str, Any],
    partition_fingerprints: Sequence[Mapping[str, Any]],
    *,
    distance_pack: DistancePack = DistancePack(),
) -> dict[str, Any]:
    """Recompute an exact frozen candidate-to-medoid comparison.

    This function exposes component distances and the frozen machine decision. It
    does not select a new medoid, change clustering or create semantic authority.
    """

    fingerprint_id = str(fingerprint.get("fingerprint_id") or "")
    medoid_id = str(medoid.get("fingerprint_id") or "")
    if not fingerprint_id or not medoid_id:
        raise PatternDiscoveryError("structural comparison requires exact fingerprint identities")
    assignments = cluster_version.get("assignments", {})
    if assignments.get(fingerprint_id) != medoid_id:
        raise PatternDiscoveryError("fingerprint is not assigned to the supplied medoid")
    population = [dict(item) for item in partition_fingerprints]
    if {str(item.get("fingerprint_id")) for item in population} != {
        str(item.get("fingerprint_id")) for item in partition_fingerprints
    }:
        raise PatternDiscoveryError("duplicate partition fingerprint identities")
    scale_pack = build_scale_pack(population)
    recorded_scale_id = str(cluster_version.get("scale_pack_id") or "")
    if recorded_scale_id and scale_pack.scale_id != recorded_scale_id:
        raise PatternDiscoveryError("recomputed scale pack does not match the frozen cluster version")
    result = composite_distance(
        fingerprint,
        medoid,
        scale_pack=scale_pack,
        distance_pack=distance_pack,
    )
    recorded_distance = cluster_version.get("distances", {}).get(fingerprint_id)
    if recorded_distance is None:
        raise PatternDiscoveryError("cluster version does not expose the recorded assignment distance")
    if abs(float(recorded_distance) - float(result["distance"])) > 1e-12:
        raise PatternDiscoveryError("recomputed distance does not match the frozen cluster version")
    cluster = next(
        (
            dict(item)
            for item in cluster_version.get("clusters", ())
            if str(item.get("medoid_id")) == medoid_id
        ),
        None,
    )
    if cluster is None:
        raise PatternDiscoveryError("assigned medoid has no exact cluster row")
    threshold = float(cluster.get("outlier_threshold_p90", 0.0))
    recomputed_outlier = float(result["distance"]) > threshold
    recorded_outlier = fingerprint_id in set(str(item) for item in cluster.get("outlier_ids", ()))
    if recomputed_outlier != recorded_outlier:
        raise PatternDiscoveryError("recomputed outlier decision does not match the frozen cluster row")
    return {
        "fingerprint_id": fingerprint_id,
        "assigned_medoid_id": medoid_id,
        "recorded_total_distance": float(recorded_distance),
        "recomputed_total_distance": result["distance"],
        "raw_domain_distances": result["domains"],
        "domain_weights": dict(DOMAIN_WEIGHTS),
        "weighted_domain_contributions": {
            name: round(float(result["domains"][name]) * float(DOMAIN_WEIGHTS[name]), 12)
            for name in sorted(DOMAIN_WEIGHTS)
        },
        "distance_pack_id": result["distance_pack_id"],
        "scale_pack_id": result["scale_pack_id"],
        "scale_features": scale_pack.as_dict()["features"],
        "outlier_threshold_p90": threshold,
        "recorded_outlier": recorded_outlier,
        "recomputed_outlier": recomputed_outlier,
        "authority": "READ_ONLY_STRUCTURAL_ASSURANCE_NO_CLUSTER_OR_SEMANTIC_CHANGE",
    }


class ChronologySafeCandidateWindowManager(CandidateWindowManager):
    """Corrective materializer preserving source IDs in first-valid chronology."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._first_valid_by_state_id: dict[str, str] = {}

    def _remember(self, snapshot_record: Mapping[str, Any] | C2Snapshot) -> C2Snapshot:
        snapshot = snapshot_record if isinstance(snapshot_record, C2Snapshot) else C2Snapshot.from_mapping(snapshot_record)
        self._first_valid_by_state_id[snapshot.c2_state_id] = snapshot.first_valid_time
        return snapshot

    def _correct_internal_order(self, window_id: str) -> dict[str, Any]:
        runtime = self._require(window_id)
        ids = [str(item) for item in runtime.public.get("source_c2_record_ids", ())]
        missing = [item for item in ids if item not in self._first_valid_by_state_id]
        if missing:
            raise ChronologyError(f"candidate source chronology unavailable for IDs: {missing}")
        runtime.public["source_c2_record_ids"] = sorted(
            dict.fromkeys(ids),
            key=lambda item: (parse_utc(self._first_valid_by_state_id[item]), item),
        )
        return self.get(window_id)

    def open_from_trigger(
        self,
        snapshot_record: Mapping[str, Any] | C2Snapshot,
        trigger_event: Mapping[str, Any],
        *,
        trigger_family: str,
        open_window_epoch: str | None = None,
        control_class: str = "NONE",
    ) -> dict[str, Any]:
        snapshot = self._remember(snapshot_record)
        window = super().open_from_trigger(
            snapshot,
            trigger_event,
            trigger_family=trigger_family,
            open_window_epoch=open_window_epoch,
            control_class=control_class,
        )
        return self._correct_internal_order(str(window["window_id"]))

    def accumulate(
        self,
        window_id: str,
        snapshot_record: Mapping[str, Any] | C2Snapshot,
    ) -> dict[str, Any]:
        snapshot = self._remember(snapshot_record)
        result = super().accumulate(window_id, snapshot)
        return self._correct_internal_order(str(result["window_id"]))
