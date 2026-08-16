from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

PROGRAMME_ID = "OVC-DSAI-VIT-v0.3"
CURRENT_POINTER_PATH = "registries/implementation/dsai_vit_v0_3/CURRENT_STATE_POINTER.json"
GENERAL_AUTHORITY_PATH = "registries/authority/DSAI3V_VIT_GENERAL_AUTHORITY_v0_1.json"
DEFAULT_SUBSTRATE_PATH = "registries/authority/DEFAULT_EXECUTION_SUBSTRATE.json"

CURRENT_SOURCE_CLASSES = {
    CURRENT_POINTER_PATH: "PROGRAMME_CURRENT_STATE_POINTER",
    GENERAL_AUTHORITY_PATH: "CURRENT_AUTHORITY_REGISTRY",
    DEFAULT_SUBSTRATE_PATH: "CURRENT_EXECUTION_SUBSTRATE",
}


class VitCurrentStateResolutionError(ValueError):
    """Raised when current VIT state cannot be resolved without historical inference."""


def _load_object(root: Path, relative_path: str) -> dict[str, Any]:
    path = root / relative_path
    if not path.is_file():
        raise VitCurrentStateResolutionError(f"VIT_CURRENT_SOURCE_MISSING:{relative_path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise VitCurrentStateResolutionError(f"VIT_CURRENT_SOURCE_NOT_OBJECT:{relative_path}")
    return value


def classify_vit_status_source(relative_path: str) -> str:
    """Classify whether a source may participate in a *current* VIT status answer."""
    normalized = str(relative_path).replace("\\", "/").lstrip("./")
    if normalized in CURRENT_SOURCE_CLASSES:
        return CURRENT_SOURCE_CLASSES[normalized]
    if normalized.startswith("registries/implementation/dsai_vit_v0_3/OVC_DSAI_VIT_V0_3_STATE_"):
        return "POINTED_CURRENT_STATE_ONLY_IF_REFERENCED_BY_CURRENT_POINTER"
    if normalized.startswith("docs/releases/development-skills-architecture-v0-3-vit/"):
        return "HISTORICAL_EVIDENCE_NOT_CURRENT_STATUS"
    if normalized.startswith("docs/plans/development-skills-v0-3/") or normalized.startswith("docs/design/development-skills-v0-3/"):
        return "HISTORICAL_OR_DESIGN_EVIDENCE_NOT_CURRENT_STATUS"
    return "UNREGISTERED_NOT_CURRENT_STATUS_AUTHORITY"


def _validate_state_filename(value: object) -> str:
    name = str(value or "").strip()
    if not name or "/" in name or "\\" in name or not name.endswith(".json"):
        raise VitCurrentStateResolutionError("VIT_CURRENT_POINTER_TARGET_INVALID")
    return name


def resolve_vit_current_state(repository_root: Path | str) -> dict[str, Any]:
    """Resolve current VIT state strictly from current pointers/authority before any historical evidence."""
    root = Path(repository_root)
    pointer = _load_object(root, CURRENT_POINTER_PATH)
    if pointer.get("programme_id") != PROGRAMME_ID:
        raise VitCurrentStateResolutionError("VIT_CURRENT_POINTER_PROGRAMME_MISMATCH")

    state_name = _validate_state_filename(pointer.get("current_state"))
    state_path = f"registries/implementation/dsai_vit_v0_3/{state_name}"
    state = _load_object(root, state_path)
    if state.get("programme_id") != PROGRAMME_ID:
        raise VitCurrentStateResolutionError("VIT_CURRENT_STATE_PROGRAMME_MISMATCH")

    authority_ref = str(state.get("general_authority") or GENERAL_AUTHORITY_PATH)
    if authority_ref != GENERAL_AUTHORITY_PATH:
        raise VitCurrentStateResolutionError("VIT_CURRENT_GENERAL_AUTHORITY_REF_UNEXPECTED")
    authority = _load_object(root, GENERAL_AUTHORITY_PATH)
    substrate = _load_object(root, DEFAULT_SUBSTRATE_PATH)

    if authority.get("programme_id") != PROGRAMME_ID:
        raise VitCurrentStateResolutionError("VIT_CURRENT_AUTHORITY_PROGRAMME_MISMATCH")
    if substrate.get("source_authority") != GENERAL_AUTHORITY_PATH:
        raise VitCurrentStateResolutionError("VIT_CURRENT_SUBSTRATE_AUTHORITY_REF_MISMATCH")
    if substrate.get("substrate_id") != authority.get("authority_id"):
        raise VitCurrentStateResolutionError("VIT_CURRENT_SUBSTRATE_AUTHORITY_ID_MISMATCH")

    authority_status = str(authority.get("authority_status", "UNKNOWN"))
    substrate_status = str(substrate.get("status", "UNKNOWN"))
    current_authority = state.get("current_authority")
    if not isinstance(current_authority, Mapping):
        raise VitCurrentStateResolutionError("VIT_CURRENT_STATE_AUTHORITY_PLANE_MISSING")

    state_routing_scope = str(current_authority.get("routing_scope", ""))
    authority_routing_scope = str(authority.get("routing_scope", ""))
    if state_routing_scope and authority_routing_scope and state_routing_scope != authority_routing_scope:
        raise VitCurrentStateResolutionError("VIT_CURRENT_ROUTING_SCOPE_MISMATCH")

    live_control = str(current_authority.get("vit_live_physical_main_control", "UNKNOWN"))
    if substrate_status == "ACTIVE" and authority_status != "ACTIVE":
        raise VitCurrentStateResolutionError("VIT_ACTIVE_SUBSTRATE_WITHOUT_ACTIVE_GENERAL_AUTHORITY")
    if authority_status == "ACTIVE" and not live_control.startswith("ACTIVE_"):
        raise VitCurrentStateResolutionError("VIT_ACTIVE_GENERAL_AUTHORITY_STATE_PLANE_MISMATCH")

    return {
        "schema": "ovc-vit-current-state-resolution/v1",
        "programme_id": PROGRAMME_ID,
        "resolution_status": "RESOLVED_CURRENT",
        "programme_status": state.get("status"),
        "qualification_frontier": state.get("qualification_frontier"),
        "current_qualification_stage": state.get("current_qualification_stage"),
        "general_authority_status": authority_status,
        "default_execution_substrate_status": substrate_status,
        "vit_live_physical_main_control": live_control,
        "routing_scope": authority_routing_scope or state_routing_scope,
        "controller": authority.get("controller") or substrate.get("controller"),
        "physical_gateway": authority.get("physical_gateway") or substrate.get("execution_policy", {}).get("physical_gateway"),
        "parallel_physical_merge": authority.get("serialization", {}).get("parallel_physical_merge"),
        "current_sources": [
            {"class": "PROGRAMME_CURRENT_STATE_POINTER", "path": CURRENT_POINTER_PATH},
            {"class": "POINTED_PROGRAMME_STATE", "path": state_path},
            {"class": "CURRENT_AUTHORITY_REGISTRY", "path": GENERAL_AUTHORITY_PATH},
            {"class": "CURRENT_EXECUTION_SUBSTRATE", "path": DEFAULT_SUBSTRATE_PATH},
        ],
        "source_precedence": [
            "PROGRAMME_CURRENT_STATE_POINTER",
            "POINTED_PROGRAMME_STATE",
            "CURRENT_AUTHORITY_REGISTRY",
            "CURRENT_EXECUTION_SUBSTRATE",
        ],
        "historical_source_fallback_allowed": False,
        "historical_status_policy": "HISTORICAL_PLANS_AND_GATE_PACKETS_MAY_BE_SHOWN_AS_HISTORY_BUT_MUST_NOT_CONTROL_CURRENT_STATUS",
    }


def resolve_current_vit_query(repository_root: Path | str) -> dict[str, Any]:
    """Canonical entrypoint for any query whose semantic request is 'current VIT state'."""
    return resolve_vit_current_state(repository_root)
