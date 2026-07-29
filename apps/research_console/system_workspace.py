from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Iterable, Mapping

_ALLOWED_ACTIVITY_TYPES = {"ARTIFACT", "BUILD", "GATE", "INCIDENT", "QA", "RELEASE", "RESEARCH", "SHELL"}
_ALLOWED_STATUS = {"PASS", "WARN", "BLOCK", "NOT_EVALUATED", "CENSORED", "EXPECTED_EMPTY"}


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_source_refs(item: Mapping[str, Any]) -> tuple[str, ...]:
    refs = tuple(str(ref) for ref in item.get("source_refs", ()) if str(ref))
    if not refs:
        raise ValueError(f"{item.get('object_id', 'UNKNOWN')}: immutable source_refs required")
    return refs


def build_system_projection(
    *,
    source_commit: str,
    read_model_sha256: str,
    objects: Iterable[Mapping[str, Any]],
    releases: Iterable[Mapping[str, Any]],
    gates: Iterable[Mapping[str, Any]],
    activity: Iterable[Mapping[str, Any]],
    catalogue: Iterable[Mapping[str, Any]] = (),
    configuration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic, replaceable, read-only System workspace projection."""
    if not source_commit or not read_model_sha256:
        raise ValueError("source_commit and read_model_sha256 are required")

    normalized_objects = []
    for raw in objects:
        item = deepcopy(dict(raw))
        item["object_id"] = str(item.get("object_id", ""))
        if not item["object_id"]:
            raise ValueError("object_id required")
        item["source_refs"] = list(_require_source_refs(item))
        normalized_objects.append(item)
    normalized_objects.sort(key=lambda item: item["object_id"])

    normalized_releases = sorted((deepcopy(dict(item)) for item in releases), key=lambda item: str(item.get("release_id", "")))
    normalized_gates = sorted((deepcopy(dict(item)) for item in gates), key=lambda item: str(item.get("gate", "")))
    normalized_catalogue = sorted((deepcopy(dict(item)) for item in catalogue), key=lambda item: str(item.get("artifact_id", "")))

    normalized_activity = []
    for sequence, raw in enumerate(activity):
        item = deepcopy(dict(raw))
        activity_type = str(item.get("type", "")).upper()
        status = str(item.get("status", "NOT_EVALUATED")).upper()
        if activity_type not in _ALLOWED_ACTIVITY_TYPES:
            raise ValueError(f"unregistered activity type: {activity_type}")
        if status not in _ALLOWED_STATUS:
            raise ValueError(f"unregistered activity status: {status}")
        if not item.get("object_id") or not item.get("source_refs"):
            raise ValueError("activity requires object_id and source_refs")
        item["type"] = activity_type
        item["status"] = status
        item["sequence"] = int(item.get("sequence", sequence))
        item["source_refs"] = list(_require_source_refs(item))
        normalized_activity.append(item)
    normalized_activity.sort(key=lambda item: (str(item.get("time", "")), item["sequence"], str(item["object_id"])), reverse=True)

    panels = {
        "OBJECTS_LINEAGE": normalized_objects,
        "DATA_CATALOGUE": normalized_catalogue,
        "RELEASES": normalized_releases,
        "QA_GATES": normalized_gates,
        "CONFIGURATION": deepcopy(dict(configuration or {})),
        "ABOUT_AUTHORITY": {
            "mode": "LOCAL_READ_ONLY",
            "writes": "NONE",
            "deployment": "LOCAL_ONLY_NO_REMOTE_DEPLOY",
        },
    }
    body = {
        "schema": "ovc-research-console-system-projection/v1",
        "source_commit": source_commit,
        "read_model_sha256": read_model_sha256,
        "panels": panels,
        "activity": normalized_activity,
        "writes": "NONE",
    }
    return {**body, "projection_sha256": _canonical_sha256(body)}


def filter_activity(
    projection: Mapping[str, Any], *, activity_type: str | None = None, status: str | None = None
) -> list[dict[str, Any]]:
    rows = [deepcopy(dict(item)) for item in projection.get("activity", ())]
    if activity_type:
        rows = [item for item in rows if item.get("type") == activity_type.upper()]
    if status:
        rows = [item for item in rows if item.get("status") == status.upper()]
    return rows


def unavailable_system_projection(reason: str) -> dict[str, Any]:
    body = {
        "schema": "ovc-research-console-system-projection/v1",
        "availability": "NOT_EVALUATED",
        "reason": str(reason),
        "panels": {},
        "activity": [],
        "writes": "NONE",
    }
    return {**body, "projection_sha256": _canonical_sha256(body)}
