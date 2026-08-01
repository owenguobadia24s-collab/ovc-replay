"""Universal read-only artifact preflight.

The preflight validates profile authority, exact input identity, compact schema
markers and destination collision state. It performs no writes and grants no
publication, selector, provider, Validation or repository-bot authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable

from .artifacts import ArtifactRef, verify_artifact
from .identity import canonical_sha256, normalize_relative_path, resolve_under
from .profiles import ArtifactProfile


@dataclass(frozen=True)
class DestinationCheck:
    logical_name: str
    relative_path: str
    policy: str = "ABSENT_OR_EMPTY"

    def __post_init__(self) -> None:
        if not self.logical_name:
            raise ValueError("destination logical_name is required")
        normalize_relative_path(self.relative_path)
        if self.policy not in {"ABSENT", "ABSENT_OR_EMPTY"}:
            raise ValueError("unsupported destination policy")


@dataclass(frozen=True)
class PreflightRequest:
    profile: ArtifactProfile
    input_refs: tuple[ArtifactRef, ...]
    destinations: tuple[DestinationCheck, ...] = ()

    def __post_init__(self) -> None:
        logical_names = [ref.logical_name for ref in self.input_refs]
        if len(logical_names) != len(set(logical_names)):
            raise ValueError("duplicate input_ref logical names")
        destination_names = [row.logical_name for row in self.destinations]
        if len(destination_names) != len(set(destination_names)):
            raise ValueError("duplicate destination logical names")

    @property
    def request_id(self) -> str:
        payload = {
            "profile_id": self.profile.profile_id,
            "profile_hash": self.profile.profile_hash,
            "input_refs": [ref.to_dict() for ref in sorted(self.input_refs, key=lambda ref: ref.logical_name)],
            "destinations": [asdict(row) for row in sorted(self.destinations, key=lambda row: row.logical_name)],
        }
        return canonical_sha256(payload, role="PREFLIGHT_REQUEST")


def _check_json_schema_marker(path: Path, ref: ArtifactRef) -> dict[str, Any] | None:
    if ref.schema_id is None or ref.media_type != "application/json":
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"check": "SCHEMA_MARKER", "status": "BLOCK", "reason": "INVALID_JSON", "detail": str(exc)}
    if not isinstance(value, dict):
        return {"check": "SCHEMA_MARKER", "status": "BLOCK", "reason": "JSON_ROOT_NOT_OBJECT"}
    actual = value.get("schema")
    if actual != ref.schema_id:
        return {
            "check": "SCHEMA_MARKER",
            "status": "BLOCK",
            "reason": "SCHEMA_ID_MISMATCH",
            "expected": ref.schema_id,
            "actual": actual,
        }
    return {"check": "SCHEMA_MARKER", "status": "PASS", "reason": "SCHEMA_ID_MATCH", "schema_id": actual}


def _destination_result(root: Path, check: DestinationCheck) -> dict[str, Any]:
    path = resolve_under(root, check.relative_path)
    if not path.exists():
        return {"check": "DESTINATION", "logical_name": check.logical_name, "status": "PASS", "reason": "ABSENT"}
    if path.is_symlink():
        return {"check": "DESTINATION", "logical_name": check.logical_name, "status": "BLOCK", "reason": "SYMLINK_PROHIBITED"}
    if check.policy == "ABSENT":
        return {"check": "DESTINATION", "logical_name": check.logical_name, "status": "BLOCK", "reason": "DESTINATION_EXISTS"}
    if not path.is_dir():
        return {"check": "DESTINATION", "logical_name": check.logical_name, "status": "BLOCK", "reason": "DESTINATION_NOT_DIRECTORY"}
    try:
        next(path.iterdir())
    except StopIteration:
        return {"check": "DESTINATION", "logical_name": check.logical_name, "status": "PASS", "reason": "EMPTY_DIRECTORY"}
    return {"check": "DESTINATION", "logical_name": check.logical_name, "status": "BLOCK", "reason": "DESTINATION_COLLISION"}


def _aggregate_status(checks: Iterable[dict[str, Any]]) -> str:
    statuses = {row["status"] for row in checks}
    if "QUARANTINE" in statuses:
        return "QUARANTINE"
    if "BLOCK" in statuses:
        return "BLOCK"
    if "NOT_EVALUABLE" in statuses:
        return "NOT_EVALUABLE"
    if "WARN" in statuses:
        return "WARN"
    return "PASS"


def run_preflight(input_root: Path, destination_root: Path, request: PreflightRequest) -> dict[str, Any]:
    """Run a deterministic read-only preflight and return a compact receipt."""
    profile_inputs = {row.logical_name: row for row in request.profile.inputs}
    refs = {row.logical_name: row for row in request.input_refs}
    checks: list[dict[str, Any]] = []

    expected = set(profile_inputs)
    supplied = set(refs)
    for logical_name in sorted(expected - supplied):
        row = profile_inputs[logical_name]
        checks.append({
            "check": "INPUT_PROFILE",
            "logical_name": logical_name,
            "status": "BLOCK" if row.required else "WARN",
            "reason": "REQUIRED_REF_MISSING" if row.required else "OPTIONAL_REF_MISSING",
        })
    for logical_name in sorted(supplied - expected):
        checks.append({"check": "INPUT_PROFILE", "logical_name": logical_name, "status": "BLOCK", "reason": "UNDECLARED_INPUT_REF"})

    for logical_name in sorted(expected & supplied):
        profile_input = profile_inputs[logical_name]
        ref = refs[logical_name]
        if profile_input.relative_path != ref.relative_path:
            checks.append({
                "check": "INPUT_PROFILE",
                "logical_name": logical_name,
                "status": "BLOCK",
                "reason": "PATH_MISMATCH",
                "expected": profile_input.relative_path,
                "actual": ref.relative_path,
            })
            continue
        if profile_input.identity_policy != ref.identity_policy:
            checks.append({
                "check": "INPUT_PROFILE",
                "logical_name": logical_name,
                "status": "BLOCK",
                "reason": "IDENTITY_POLICY_MISMATCH",
                "expected": profile_input.identity_policy,
                "actual": ref.identity_policy,
            })
            continue
        exact = verify_artifact(input_root, ref)
        exact.update({"check": "EXACT_ARTIFACT", "logical_name": logical_name})
        checks.append(exact)
        if exact["status"] == "PASS":
            marker = _check_json_schema_marker(resolve_under(input_root, ref.relative_path), ref)
            if marker is not None:
                marker["logical_name"] = logical_name
                checks.append(marker)

    for destination in sorted(request.destinations, key=lambda row: row.logical_name):
        checks.append(_destination_result(destination_root, destination))

    checks = sorted(checks, key=lambda row: (row.get("logical_name", ""), row["check"], row.get("reason", "")))
    status = _aggregate_status(checks)
    logical_payload = {
        "request_id": request.request_id,
        "profile_id": request.profile.profile_id,
        "profile_hash": request.profile.profile_hash,
        "status": status,
        "checks": checks,
        "authority": {
            "read_only": True,
            "writes_performed": False,
            "repository_bot_write": "DENIED",
            "release": "DENIED",
            "selector": "DENIED",
            "r2": "DENIED",
            "validation": "DENIED",
        },
    }
    return {**logical_payload, "preflight_receipt_id": canonical_sha256(logical_payload, role="PREFLIGHT_RECEIPT")}
