"""Cheap read-only programme-state/current-pointer consistency preflight.

This check is intentionally narrow: it catches stale or contradictory mutable
CURRENT_STATE_POINTER projections before expensive exact-head assurance. It does
not infer authority, repair state, or reinterpret historical programme records.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .identity import canonical_sha256

_POINTER_SCHEMA = "ovc-programme-current-state-pointer/v1"


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def _result(pointer: Path, *, status: str, reason: str, **extra: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "pointer": pointer.as_posix(),
        "status": status,
        "reason": reason,
    }
    row.update(extra)
    return row


def check_pointer(pointer_path: Path, *, repository_root: Path) -> list[dict[str, Any]]:
    """Validate one canonical programme pointer against its referenced state."""
    relative_pointer = pointer_path.relative_to(repository_root)
    try:
        pointer = _load_object(pointer_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return [_result(relative_pointer, status="BLOCK", reason="POINTER_INVALID_JSON", detail=str(exc))]

    if pointer.get("schema") != _POINTER_SCHEMA:
        return [_result(relative_pointer, status="PASS", reason="NON_CANONICAL_POINTER_SCHEMA_SKIPPED")]

    current_state = pointer.get("current_state")
    if not isinstance(current_state, str) or not current_state.strip():
        return [_result(relative_pointer, status="BLOCK", reason="CURRENT_STATE_MISSING")]

    state_ref = Path(current_state)
    if state_ref.is_absolute() or ".." in state_ref.parts:
        return [_result(relative_pointer, status="BLOCK", reason="CURRENT_STATE_PATH_UNSAFE", current_state=current_state)]

    state_path = (pointer_path.parent / state_ref).resolve()
    root = repository_root.resolve()
    try:
        state_path.relative_to(root)
    except ValueError:
        return [_result(relative_pointer, status="BLOCK", reason="CURRENT_STATE_PATH_ESCAPES_REPOSITORY", current_state=current_state)]

    if not state_path.is_file():
        return [_result(relative_pointer, status="BLOCK", reason="CURRENT_STATE_NOT_FOUND", current_state=current_state)]

    try:
        state = _load_object(state_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return [_result(relative_pointer, status="BLOCK", reason="CURRENT_STATE_INVALID_JSON", current_state=current_state, detail=str(exc))]

    checks: list[dict[str, Any]] = []
    field_pairs = (
        ("programme_id", "programme_id"),
        ("status", "status"),
        ("current_packet", "packet_id"),
        ("current_gate", "gate_id"),
        ("next_packet", "next_packet"),
    )
    for pointer_field, state_field in field_pairs:
        if pointer_field not in pointer or state_field not in state:
            continue
        if pointer[pointer_field] != state[state_field]:
            checks.append(_result(
                relative_pointer,
                status="BLOCK",
                reason="POINTER_STATE_FIELD_MISMATCH",
                pointer_field=pointer_field,
                state_field=state_field,
                pointer_value=pointer[pointer_field],
                state_value=state[state_field],
                current_state=current_state,
            ))

    completed = state.get("completed_packets")
    packet_id = state.get("packet_id")
    if state.get("status") == "COMPLETED" and isinstance(completed, list) and isinstance(packet_id, str):
        if packet_id not in completed:
            checks.append(_result(
                relative_pointer,
                status="BLOCK",
                reason="COMPLETED_PACKET_MISSING_FROM_COMPLETED_PACKETS",
                packet_id=packet_id,
                current_state=current_state,
            ))

    next_packet = state.get("next_packet")
    if isinstance(completed, list) and isinstance(next_packet, str) and next_packet in completed:
        checks.append(_result(
            relative_pointer,
            status="BLOCK",
            reason="NEXT_PACKET_ALREADY_COMPLETED",
            next_packet=next_packet,
            current_state=current_state,
        ))

    if not checks:
        checks.append(_result(
            relative_pointer,
            status="PASS",
            reason="POINTER_STATE_CONSISTENT",
            current_state=current_state,
            programme_id=pointer.get("programme_id"),
            packet_id=state.get("packet_id"),
            next_packet=state.get("next_packet"),
        ))
    return checks


def _aggregate(checks: Iterable[dict[str, Any]]) -> str:
    return "BLOCK" if any(row["status"] == "BLOCK" for row in checks) else "PASS"


def run_programme_state_preflight(repository_root: Path, *, scan_root: Path | None = None) -> dict[str, Any]:
    """Scan canonical CURRENT_STATE_POINTER files and emit a deterministic receipt."""
    repository_root = repository_root.resolve()
    scan_root = (scan_root or repository_root / "registries").resolve()
    try:
        scan_root.relative_to(repository_root)
    except ValueError as exc:
        raise ValueError("scan_root must be inside repository_root") from exc

    pointers = sorted(scan_root.rglob("CURRENT_STATE_POINTER.json")) if scan_root.exists() else []
    checks: list[dict[str, Any]] = []
    for pointer in pointers:
        checks.extend(check_pointer(pointer, repository_root=repository_root))

    status = _aggregate(checks)
    logical = {
        "schema": "ovc-programme-state-pointer-preflight/v1",
        "status": status,
        "repository_root": ".",
        "scan_root": scan_root.relative_to(repository_root).as_posix(),
        "pointer_count": len(pointers),
        "blocking_count": sum(row["status"] == "BLOCK" for row in checks),
        "checks": checks,
        "authority": {
            "read_only": True,
            "writes_performed": False,
            "authority_effect": "NONE",
        },
    }
    return {**logical, "receipt_id": canonical_sha256(logical, role="PROGRAMME_STATE_POINTER_PREFLIGHT")}
