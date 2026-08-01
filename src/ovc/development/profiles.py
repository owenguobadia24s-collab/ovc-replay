"""Strict machine-readable packet profile loading.

Runtime profiles are JSON to keep the shared package dependency-free. Human-readable
YAML registries may reference these profiles but are not silently interpreted here.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from .identity import canonical_sha256, normalize_relative_path


class ProfileError(ValueError):
    """Raised when a packet profile is missing, ambiguous or over-authorised."""


_ALLOWED_AUTHORITY_VALUES = {"ALLOWED", "DENIED", "NONE", "COPY_ONLY"}
_REQUIRED_AUTHORITY_KEYS = {
    "provider_access",
    "release",
    "selector",
    "r2",
    "validation",
    "repository_bot_write",
    "direct_main_write",
    "force_push",
}


@dataclass(frozen=True)
class ProfileInput:
    logical_name: str
    relative_path: str
    identity_policy: str
    required: bool = True


@dataclass(frozen=True)
class ArtifactProfile:
    profile_id: str
    programme_id: str
    packet_id: str
    authority: Mapping[str, str]
    inputs: tuple[ProfileInput, ...]
    test_profile: str
    export_profile: str | None
    profile_hash: str


def _require_string(obj: Mapping[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProfileError(f"{key} must be a non-empty string")
    return value


def parse_profile(obj: Mapping[str, Any]) -> ArtifactProfile:
    if set(obj) - {
        "schema", "profile_id", "programme_id", "packet_id", "authority",
        "inputs", "test_profile", "export_profile",
    }:
        raise ProfileError("unknown top-level profile fields")
    if obj.get("schema") != "ovc-artifact-profile/v1":
        raise ProfileError("unsupported artifact profile schema")

    authority = obj.get("authority")
    if not isinstance(authority, dict):
        raise ProfileError("authority must be an object")
    missing = _REQUIRED_AUTHORITY_KEYS - set(authority)
    if missing:
        raise ProfileError(f"missing authority keys: {sorted(missing)}")
    if set(authority) != _REQUIRED_AUTHORITY_KEYS:
        raise ProfileError("authority contains unknown keys")
    for key, value in authority.items():
        if value not in _ALLOWED_AUTHORITY_VALUES:
            raise ProfileError(f"invalid authority value for {key}: {value}")
    for key in ("provider_access", "release", "selector", "r2", "validation", "repository_bot_write", "direct_main_write", "force_push"):
        if authority[key] != "DENIED":
            raise ProfileError(f"v0.1 shared profiles must deny {key}")

    raw_inputs = obj.get("inputs")
    if not isinstance(raw_inputs, list) or not raw_inputs:
        raise ProfileError("inputs must be a non-empty list")
    inputs: list[ProfileInput] = []
    names: set[str] = set()
    paths: set[str] = set()
    for row in raw_inputs:
        if not isinstance(row, dict):
            raise ProfileError("input entries must be objects")
        if set(row) - {"logical_name", "relative_path", "identity_policy", "required"}:
            raise ProfileError("input contains unknown fields")
        logical_name = _require_string(row, "logical_name")
        relative_path = normalize_relative_path(_require_string(row, "relative_path"))
        identity_policy = _require_string(row, "identity_policy")
        required = row.get("required", True)
        if not isinstance(required, bool):
            raise ProfileError("input required must be boolean")
        if logical_name in names or relative_path in paths:
            raise ProfileError("duplicate logical name or relative path")
        names.add(logical_name)
        paths.add(relative_path)
        inputs.append(ProfileInput(logical_name, relative_path, identity_policy, required))

    profile_id = _require_string(obj, "profile_id")
    programme_id = _require_string(obj, "programme_id")
    packet_id = _require_string(obj, "packet_id")
    test_profile = _require_string(obj, "test_profile")
    export_profile = obj.get("export_profile")
    if export_profile is not None and (not isinstance(export_profile, str) or not export_profile):
        raise ProfileError("export_profile must be null or non-empty string")

    return ArtifactProfile(
        profile_id=profile_id,
        programme_id=programme_id,
        packet_id=packet_id,
        authority=dict(authority),
        inputs=tuple(inputs),
        test_profile=test_profile,
        export_profile=export_profile,
        profile_hash=canonical_sha256(obj, role="ARTIFACT_PROFILE"),
    )


def load_profile(path: Path) -> ArtifactProfile:
    if path.suffix.lower() != ".json":
        raise ProfileError("runtime profiles must use JSON")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileError(f"cannot load profile: {exc}") from exc
    if not isinstance(obj, dict):
        raise ProfileError("profile root must be an object")
    return parse_profile(obj)
