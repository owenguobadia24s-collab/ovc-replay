from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

_ALLOWED_CONTENT_ROLES = {"DISCOVERY", "DEVELOPMENT"}
_VALIDATION_ROLE = "VALIDATION"


class AccessDenied(ValueError):
    """Raised before any forbidden source path or content is resolved."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _workspace_id(release: dict[str, Any]) -> str:
    seed = {
        "role": release["role"],
        "release_id": release["release_id"],
        "manifest_sha256": release["manifest_sha256"],
        "instrument": release.get("instrument"),
        "coverage_start": release.get("coverage_start"),
        "coverage_end": release.get("coverage_end"),
    }
    return f"RO2-WS-{_digest(seed)[:16]}"


def _observation_id(release_id: str, row: dict[str, Any]) -> str:
    if row.get("observation_id"):
        return str(row["observation_id"])
    seed = {
        "release_id": release_id,
        "source_object_id": row["source_object_id"],
        "clock": row["clock"],
        "side": row["side"],
        "first_valid_at": row["first_valid_at"],
    }
    return f"RO2-OBS-{_digest(seed)[:24]}"


def _family_id(role: str, release_id: str, row: dict[str, Any], instrument: str) -> str:
    seed = {
        "role": role,
        "release_id": release_id,
        "instrument": instrument,
        "clock": row["clock"],
        "side": row["side"],
        "schema_version": row.get("schema_version", "UNKNOWN"),
    }
    return f"RO2-FAM-{_digest(seed)[:20]}"


def validation_metadata_only(metadata: dict[str, Any]) -> dict[str, Any]:
    if metadata.get("role") != _VALIDATION_ROLE:
        raise ValueError("metadata role must be VALIDATION")
    if any(key in metadata for key in ("path", "local_path", "remote_key", "observations", "rows", "objects")):
        raise AccessDenied("Validation denied before path resolution")
    return {
        "role": _VALIDATION_ROLE,
        "release_id": metadata["release_id"],
        "manifest_sha256": metadata["manifest_sha256"],
        "coverage_start": metadata.get("coverage_start"),
        "coverage_end": metadata.get("coverage_end"),
        "aggregate_record_count": int(metadata.get("aggregate_record_count", 0)),
        "validation_consumption": "LOCKED_UNCONSUMED",
        "availability": "METADATA_ONLY",
    }


def build_indexes(releases: Iterable[dict[str, Any]], validation_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    workspaces: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    families: dict[str, dict[str, Any]] = {}
    seen: dict[str, bytes] = {}

    for release in releases:
        role = str(release.get("role", ""))
        if role not in _ALLOWED_CONTENT_ROLES:
            raise AccessDenied(f"content resolution denied for role {role or 'UNKNOWN'}")
        required = ("release_id", "manifest_sha256", "instrument", "observations")
        missing = [field for field in required if field not in release]
        if missing:
            raise ValueError(f"release missing required fields: {missing}")

        workspace_id = _workspace_id(release)
        release_rows = list(release["observations"])
        workspace = {
            "workspace_id": workspace_id,
            "role": role,
            "release_id": release["release_id"],
            "manifest_sha256": release["manifest_sha256"],
            "instrument": release["instrument"],
            "coverage_start": release.get("coverage_start"),
            "coverage_end": release.get("coverage_end"),
            "availability": "AVAILABLE",
            "observation_count": len(release_rows),
        }
        workspaces.append(workspace)

        for row in release_rows:
            for field in ("source_object_id", "clock", "side", "first_valid_at"):
                if not row.get(field):
                    raise ValueError(f"observation missing {field}")
            observation_id = _observation_id(release["release_id"], row)
            record = {
                "observation_id": observation_id,
                "workspace_id": workspace_id,
                "role": role,
                "release_id": release["release_id"],
                "source_object_id": row["source_object_id"],
                "instrument": release["instrument"],
                "clock": row["clock"],
                "side": row["side"],
                "first_valid_at": row["first_valid_at"],
                "schema_version": row.get("schema_version", "UNKNOWN"),
                "source_hash": row.get("source_hash"),
            }
            encoded = _canonical(record)
            if observation_id in seen and seen[observation_id] != encoded:
                raise ValueError(f"conflicting duplicate observation_id: {observation_id}")
            seen[observation_id] = encoded
            observations.append(record)

            family_id = _family_id(role, release["release_id"], row, release["instrument"])
            family = families.setdefault(family_id, {
                "family_id": family_id,
                "role": role,
                "release_id": release["release_id"],
                "instrument": release["instrument"],
                "clock": row["clock"],
                "side": row["side"],
                "schema_version": row.get("schema_version", "UNKNOWN"),
                "observation_ids": [],
            })
            family["observation_ids"].append(observation_id)

    workspaces.sort(key=lambda item: item["workspace_id"])
    observations.sort(key=lambda item: item["observation_id"])
    family_records = sorted(families.values(), key=lambda item: item["family_id"])
    for family in family_records:
        family["observation_ids"].sort()

    validation = validation_metadata_only(validation_metadata) if validation_metadata else None
    logical = {"workspaces": workspaces, "observations": observations, "families": family_records, "validation": validation}
    return {**logical, "logical_index_hash": _digest(logical)}
