from __future__ import annotations

import hashlib
import json
from typing import Any


class ConsoleProjectionDenied(ValueError):
    """Raised before forbidden Validation content or write-capable data is resolved."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _projection_id(kind: str, payload: dict[str, Any]) -> str:
    return f"RO2-CONSOLE-{kind}-{hashlib.sha256(_canonical(payload)).hexdigest()[:20]}"


def _guard_read_only(payload: dict[str, Any]) -> None:
    forbidden = {"write", "mutation", "git_write", "r2_write", "selector_write", "threshold_write"}
    if forbidden.intersection(payload):
        raise ConsoleProjectionDenied("READ_ONLY_CONSOLE_PROJECTION_REQUIRED")
    if payload.get("role") == "VALIDATION" and any(
        key in payload for key in ("rows", "objects", "paths", "source_object_id", "observation_ids", "accepted")
    ):
        raise ConsoleProjectionDenied("VALIDATION_DENY_BEFORE_PATH_RESOLUTION")


def adapt_workspace(indexes: dict[str, Any]) -> dict[str, Any]:
    _guard_read_only(indexes)
    workspaces = [
        {
            "workspace_id": row["workspace_id"],
            "role": row["role"],
            "release_id": row["release_id"],
            "manifest_sha256": row["manifest_sha256"],
            "instrument": row.get("instrument"),
            "coverage_start": row.get("coverage_start"),
            "coverage_end": row.get("coverage_end"),
            "availability": row.get("availability", "NOT_EVALUABLE"),
            "observation_count": row.get("observation_count", 0),
        }
        for row in indexes.get("workspaces", [])
    ]
    workspaces.sort(key=lambda row: row["workspace_id"])
    validation = indexes.get("validation")
    if validation:
        _guard_read_only(validation)
        validation = {
            "role": "VALIDATION",
            "release_id": validation["release_id"],
            "manifest_sha256": validation["manifest_sha256"],
            "aggregate_record_count": validation.get("aggregate_record_count", 0),
            "validation_consumption": "LOCKED_UNCONSUMED",
            "availability": "METADATA_ONLY",
        }
    payload = {"surface": "WORKSPACE", "workspaces": workspaces, "validation": validation, "writes": "NONE"}
    return {**payload, "projection_id": _projection_id("WORKSPACE", payload)}


def adapt_quality(quality: dict[str, Any]) -> dict[str, Any]:
    _guard_read_only(quality)
    payload = {
        "surface": "QUALITY",
        "status": quality.get("status", "NOT_EVALUABLE"),
        "record_count": quality.get("record_count", 0),
        "duplicate_source_object_ids": sorted(quality.get("duplicate_source_object_ids", [])),
        "missing_required_fields": quality.get("missing_required_fields", []),
        "writes": "NONE",
    }
    return {**payload, "projection_id": _projection_id("QUALITY", payload)}


def adapt_lineage(lineage: dict[str, Any]) -> dict[str, Any]:
    _guard_read_only(lineage)
    payload = {
        "surface": "LINEAGE",
        "status": lineage.get("status", "LINEAGE_INCOMPLETE"),
        "source_object_id": lineage.get("source_object_id"),
        "trace": lineage.get("trace", []),
        "writes": "NONE",
    }
    return {**payload, "projection_id": _projection_id("LINEAGE", payload)}


def adapt_replay(replay: dict[str, Any]) -> dict[str, Any]:
    _guard_read_only(replay)
    payload = {
        "surface": "REPLAY",
        "role": replay["role"],
        "cutoff": replay["cutoff"],
        "accepted_count": replay.get("accepted_count", 0),
        "visible_source_object_ids": sorted(
            row.get("source_object_id") for row in replay.get("accepted", []) if row.get("source_object_id")
        ),
        "hidden_post_cutoff_count": len(replay.get("post_cutoff_rejected", [])),
        "mode": "PROSPECTIVE",
        "writes": "NONE",
    }
    return {**payload, "projection_id": _projection_id("REPLAY", payload)}


def adapt_comparison(comparison: dict[str, Any]) -> dict[str, Any]:
    _guard_read_only(comparison)
    payload = {
        "surface": "COMPARISON",
        "status": comparison.get("status", "COMPARISON_NOT_AVAILABLE"),
        "base_identity": comparison.get("base_identity"),
        "target_identity": comparison.get("target_identity"),
        "dimensions": comparison.get("dimensions", {}),
        "differences": comparison.get("differences", []),
        "comparison_sha256": comparison.get("comparison_sha256"),
        "writes": "NONE",
    }
    return {**payload, "projection_id": _projection_id("COMPARISON", payload)}


def build_research_console_projection(
    *,
    workspace: dict[str, Any],
    quality: dict[str, Any],
    lineage: dict[str, Any],
    replay: dict[str, Any],
    comparison: dict[str, Any],
) -> dict[str, Any]:
    panels = {
        "workspace": adapt_workspace(workspace),
        "quality": adapt_quality(quality),
        "lineage": adapt_lineage(lineage),
        "replay": adapt_replay(replay),
        "comparison": adapt_comparison(comparison),
    }
    payload = {"schema": "ovc-ro2-console-projection/v1", "panels": panels, "read_only": True, "writes": "NONE"}
    return {**payload, "projection_id": _projection_id("RESEARCH", payload)}
