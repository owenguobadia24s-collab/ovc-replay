from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from apps.research_console.ro4_projection_source import (
    RO4ProjectionSourceError,
    load_disabled_projection,
)

ROUTE_ID = "RESEARCH.C2_SEQUENCE_EVIDENCE"
ROUTE_STATE = "ENABLED_LOCAL_READ_ONLY"
AUTHORITY = "LOCAL_READ_ONLY_C2_SEQUENCE_EVIDENCE_PRESENTATION"
DECISION_ID = "RC-G5.OPERATOR.PASS.20260801T084900Z"
AUTHORITY_PATH = "registries/research_console/RC_G5_C2_SEQUENCE_EVIDENCE_AUTHORITY_v0_1.json"


class RO4ActiveProjectionError(ValueError):
    pass


def _repo_root(root: str | Path | None = None) -> Path:
    return Path(root) if root is not None else Path(__file__).resolve().parents[2]


def _git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    try:
        digest = hashlib.sha1(usedforsecurity=False)
    except TypeError:  # pragma: no cover
        digest = hashlib.sha1()
    digest.update(header)
    digest.update(content)
    return digest.hexdigest()


def _load_authority(
    *,
    root: str | Path | None = None,
    authority_path: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(root)
    path = Path(authority_path) if authority_path is not None else repo / AUTHORITY_PATH
    try:
        authority = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RO4ActiveProjectionError("RC_G5_AUTHORITY_REGISTRY_UNAVAILABLE") from exc

    if authority.get("status") != "ENABLED_LOCAL_READ_ONLY" or authority.get("enabled") is not True:
        raise RO4ActiveProjectionError("RC_G5_ROUTE_NOT_ACTIVATED")
    if authority.get("operator_decision_id") != DECISION_ID:
        raise RO4ActiveProjectionError("RC_G5_OPERATOR_DECISION_BINDING_FAILURE")
    if authority.get("route_id") != ROUTE_ID or authority.get("current_route_state") != ROUTE_STATE:
        raise RO4ActiveProjectionError("RC_G5_ROUTE_IDENTITY_FAILURE")
    if authority.get("writes") != "NONE" or authority.get("annotation_actions") != "NONE":
        raise RO4ActiveProjectionError("RC_G5_WRITE_AUTHORITY_DENIED")
    if authority.get("remote_deployment") != "DENIED":
        raise RO4ActiveProjectionError("RC_G5_REMOTE_DEPLOYMENT_DENIED")
    if authority.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise RO4ActiveProjectionError("RC_G5_VALIDATION_LOCK_REQUIRED")

    bindings = (
        authority["approved_projection_schema"],
        authority["approved_adapter"],
        authority["approved_local_source"],
        authority["approved_projection_registry"],
        authority["assurance_fixture"],
    )
    for binding in bindings:
        relative = str(binding["path"])
        source = repo / relative
        try:
            raw = source.read_bytes()
        except OSError as exc:
            raise RO4ActiveProjectionError(f"RC_G5_APPROVED_BINDING_UNAVAILABLE:{relative}") from exc
        if _git_blob_sha(raw) != binding.get("git_blob_sha"):
            raise RO4ActiveProjectionError(f"RC_G5_APPROVED_BINDING_HASH_FAILURE:{relative}")
    return authority


def _empty(reason: str, authority: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "ovc-research-console-rc-g5-live-c2-sequence/v1",
        "route_id": ROUTE_ID,
        "route_state": ROUTE_STATE,
        "route_enabled": True,
        "availability": "NOT_EVALUATED",
        "reason": reason,
        "authority": AUTHORITY,
        "authority_banners": list(authority["permanent_banners"]),
        "source_commit": "NOT_EVALUATED",
        "source_projection_id": "NOT_EVALUATED",
        "source_logical_hash": "NOT_EVALUATED",
        "source_release_refs": [],
        "panels": [],
        "read_only": True,
        "writes": "NONE",
        "annotation_actions": "NONE",
        "validation_consumption": "LOCKED_UNCONSUMED",
        "c2_authority": "UNCHANGED",
        "pattern_discovery_authority": "UNCHANGED",
        "remote_deployment": "DENIED",
        "operator_decision_id": DECISION_ID,
    }


def load_active_projection(
    path: str | Path | None = None,
    *,
    schema_root: str | Path | None = None,
    authority_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load one exact approved RO4 projection under RC-G5 local read-only authority."""

    root = _repo_root(schema_root)
    authority = _load_authority(root=root, authority_path=authority_path)
    source_path = Path(path) if path is not None else Path(os.environ.get("OVC_RO4_PROJECTION", "var/research_operations/ro4/current_projection.json"))
    if not source_path.is_file():
        return _empty("RO4_PROJECTION_UNAVAILABLE", authority)
    try:
        projection = load_disabled_projection(source_path, schema_root=root)
    except (RO4ProjectionSourceError, ValueError) as exc:
        return _empty(str(exc), authority)

    return {
        "schema": "ovc-research-console-rc-g5-live-c2-sequence/v1",
        "route_id": ROUTE_ID,
        "route_state": ROUTE_STATE,
        "route_enabled": True,
        "availability": "AVAILABLE",
        "reason": "NONE",
        "authority": AUTHORITY,
        "authority_banners": list(authority["permanent_banners"]),
        "source_commit": projection["source_commit"],
        "source_projection_id": projection["projection_id"],
        "source_logical_hash": projection["logical_hash"],
        "source_release_refs": [dict(item) for item in projection["source_release_refs"]],
        "panels": [dict(item) for item in projection["panels"]],
        "read_only": True,
        "writes": "NONE",
        "annotation_actions": "NONE",
        "validation_consumption": "LOCKED_UNCONSUMED",
        "c2_authority": "UNCHANGED",
        "pattern_discovery_authority": "UNCHANGED",
        "remote_deployment": "DENIED",
        "operator_decision_id": DECISION_ID,
    }


def projection_identity(projection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "route_id": projection.get("route_id", ROUTE_ID),
        "route_state": projection.get("route_state", ROUTE_STATE),
        "availability": projection.get("availability", "NOT_EVALUATED"),
        "authority": projection.get("authority", AUTHORITY),
        "source_commit": projection.get("source_commit", "NOT_EVALUATED"),
        "source_projection_id": projection.get("source_projection_id", "NOT_EVALUATED"),
        "writes": "NONE",
        "validation_consumption": "LOCKED_UNCONSUMED",
    }


def route_registration() -> dict[str, Any]:
    return {
        "route_id": ROUTE_ID,
        "route_state": ROUTE_STATE,
        "local_only": True,
        "writes": "NONE",
        "annotation_actions": "NONE",
        "remote_deployment": "DENIED",
        "operator_decision_id": DECISION_ID,
    }
