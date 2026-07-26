from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

_ALLOWED_SCHEMAS = {"ovc-ro2-console-research-projection/v1"}
_FORBIDDEN_KEYS = {"path", "local_path", "remote_key", "rows", "objects", "observations", "write", "writes_requested"}


def load_ro2_projection(path: str | Path | None = None) -> dict[str, Any]:
    """Load an accepted RO2-G3 projection for local read-only Console presentation.

    Missing or malformed state fails closed. Validation is metadata-only and any
    content-bearing or write-capable payload is rejected before presentation.
    """
    source = Path(path or os.environ.get("OVC_RO2_CONSOLE_PROJECTION", "var/research_operations/console/ro2_research_projection.json"))
    unavailable = {
        "availability": "NOT_EVALUATED",
        "reason": "RO2_PROJECTION_UNAVAILABLE",
        "authority": "READ_ONLY_PRESENTATION",
        "writes": "NONE",
    }
    if not source.is_file():
        return unavailable
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {**unavailable, "reason": "RO2_PROJECTION_INVALID_JSON"}
    if payload.get("schema") not in _ALLOWED_SCHEMAS:
        return {**unavailable, "reason": "RO2_PROJECTION_SCHEMA_DENIED"}
    if any(key in payload for key in _FORBIDDEN_KEYS):
        return {**unavailable, "reason": "RO2_PROJECTION_CAPABILITY_DENIED"}
    if payload.get("writes") not in (None, "NONE"):
        return {**unavailable, "reason": "RO2_PROJECTION_WRITE_DENIED"}
    role = str(payload.get("role", ""))
    if role == "VALIDATION":
        allowed = {
            "schema", "projection_id", "role", "release_id", "manifest_sha256",
            "aggregate_record_count", "validation_consumption", "availability",
            "authority", "writes",
        }
        if set(payload) - allowed:
            return {**unavailable, "reason": "VALIDATION_CONTENT_DENIED_BEFORE_PRESENTATION"}
        if payload.get("validation_consumption") != "LOCKED_UNCONSUMED":
            return {**unavailable, "reason": "VALIDATION_BOUNDARY_INVALID"}
    elif role not in {"DISCOVERY", "DEVELOPMENT"}:
        return {**unavailable, "reason": "RO2_PROJECTION_ROLE_DENIED"}
    return {
        **payload,
        "availability": payload.get("availability", "AVAILABLE"),
        "authority": "ACCEPTED_LOCAL_READ_ONLY_PRESENTATION",
        "writes": "NONE",
    }


def projection_identity(projection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "projection_id": projection.get("projection_id", "NOT_EVALUATED"),
        "role": projection.get("role", "NOT_EVALUATED"),
        "release_id": projection.get("release_id", "NOT_EVALUATED"),
        "manifest_sha256": projection.get("manifest_sha256", "NOT_EVALUATED"),
        "availability": projection.get("availability", "NOT_EVALUATED"),
        "authority": projection.get("authority", "READ_ONLY_PRESENTATION"),
        "writes": "NONE",
    }
