from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ovc.development.identity import canonical_sha256, normalize_relative_path, resolve_under
from ovc.development.skills.vit_core import VitContractError

VIT_MANDATORY = "VIT_MANDATORY"
REGISTERED_EXCEPTION = "REGISTERED_EXCEPTION"
UNLAWFUL = "UNLAWFUL"
ROUTE_CLASSES = frozenset({VIT_MANDATORY, REGISTERED_EXCEPTION, UNLAWFUL})

LINEAGE_SCHEMA = "ovc-vit-routing-lineage/v1"
VIT_CONTROLLER = "DSAI_VIT_PHYSICAL_CONTROLLER"
SIQ_GATEWAY = "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY"


def _is_hex(value: str, length: int) -> bool:
    if not isinstance(value, str) or len(value) != length:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value.lower() == value


def _required_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VitContractError(f"{name} must be an object")
    return value


@dataclass(frozen=True)
class ValidatedVitLineage:
    programme_id: str
    packet_id: str
    pip_id: str
    generation_id: str
    placement_id: str
    route_class: str
    lineage_ref: str | None = None


def validate_vit_lineage_record(record: Mapping[str, Any], *, lineage_ref: str | None = None) -> ValidatedVitLineage:
    if record.get("schema") != LINEAGE_SCHEMA:
        raise VitContractError("VIT_LINEAGE_SCHEMA_INVALID")
    if record.get("status") != "ADMITTED":
        raise VitContractError("VIT_LINEAGE_NOT_ADMITTED")

    programme_id = str(record.get("programme_id", "")).strip()
    packet_id = str(record.get("packet_id", "")).strip()
    route_class = str(record.get("route_class", "")).strip()
    if not programme_id or not packet_id:
        raise VitContractError("VIT_LINEAGE_PACKET_IDENTITY_MISSING")
    if route_class not in {VIT_MANDATORY, REGISTERED_EXCEPTION}:
        raise VitContractError("VIT_LINEAGE_ROUTE_CLASS_INVALID")

    pip = _required_mapping(record.get("pip"), "pip")
    if str(pip.get("programme_id", "")) != programme_id or str(pip.get("packet_id", "")) != packet_id:
        raise VitContractError("VIT_LINEAGE_PIP_PACKET_MISMATCH")
    pip_id = str(record.get("pip_id", ""))
    if not _is_hex(pip_id, 64) or pip_id != canonical_sha256(dict(pip)):
        raise VitContractError("VIT_LINEAGE_PIP_ID_INVALID")

    generation = _required_mapping(record.get("generation"), "generation")
    if str(generation.get("pip_id", "")) != pip_id:
        raise VitContractError("VIT_LINEAGE_GENERATION_PIP_MISMATCH")
    if not _is_hex(str(generation.get("predecessor_tree_sha", "")), 40):
        raise VitContractError("VIT_LINEAGE_PREDECESSOR_TREE_INVALID")
    if not _is_hex(str(generation.get("result_tree_sha", "")), 40):
        raise VitContractError("VIT_LINEAGE_RESULT_TREE_INVALID")
    if not str(generation.get("train_generation_id", "")).strip():
        raise VitContractError("VIT_LINEAGE_TRAIN_GENERATION_MISSING")
    try:
        ordinal = int(generation.get("ordinal", -1))
    except (TypeError, ValueError) as exc:
        raise VitContractError("VIT_LINEAGE_ORDINAL_INVALID") from exc
    if ordinal < 0:
        raise VitContractError("VIT_LINEAGE_ORDINAL_INVALID")
    generation_id = str(record.get("generation_id", ""))
    if not _is_hex(generation_id, 64) or generation_id != canonical_sha256(dict(generation)):
        raise VitContractError("VIT_LINEAGE_GENERATION_ID_INVALID")

    placement = _required_mapping(record.get("placement"), "placement")
    if str(placement.get("generation_id", "")) != generation_id:
        raise VitContractError("VIT_LINEAGE_PLACEMENT_GENERATION_MISMATCH")
    if placement.get("controller") != VIT_CONTROLLER or placement.get("physical_gateway") != SIQ_GATEWAY:
        raise VitContractError("VIT_LINEAGE_ROUTING_OWNER_INVALID")
    if str(placement.get("route_class", "")) != route_class:
        raise VitContractError("VIT_LINEAGE_PLACEMENT_ROUTE_MISMATCH")
    placement_id = str(record.get("placement_id", ""))
    if not _is_hex(placement_id, 64) or placement_id != canonical_sha256(dict(placement)):
        raise VitContractError("VIT_LINEAGE_PLACEMENT_ID_INVALID")

    return ValidatedVitLineage(
        programme_id=programme_id,
        packet_id=packet_id,
        pip_id=pip_id,
        generation_id=generation_id,
        placement_id=placement_id,
        route_class=route_class,
        lineage_ref=lineage_ref,
    )


def load_vit_lineage(root: str | Path, relative_path: str) -> ValidatedVitLineage:
    import json

    normalized = normalize_relative_path(relative_path)
    path = resolve_under(Path(root), normalized)
    if not path.is_file():
        raise VitContractError("VIT_LINEAGE_REF_NOT_FOUND")
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, Mapping):
        raise VitContractError("VIT_LINEAGE_RECORD_INVALID")
    return validate_vit_lineage_record(record, lineage_ref=normalized)


def classify_main_movement(
    *,
    previous_pip_id: str,
    current_pip_id: str,
    dependency_frontier_changed: bool,
    authority_changed: bool,
    packet_local_defect_changed_payload: bool,
) -> Mapping[str, Any]:
    """Classify a lawful main advance without treating placement as payload identity.

    An unrelated base movement with the exact same PIP, dependency frontier and authority
    is placement-only and must not trigger a payload rebuild. Any identity-bearing packet,
    dependency or authority change requires a new payload/review path.
    """
    if not _is_hex(previous_pip_id, 64) or not _is_hex(current_pip_id, 64):
        raise VitContractError("VIT_PIP_ID_INVALID")
    payload_changed = previous_pip_id != current_pip_id or packet_local_defect_changed_payload
    if not payload_changed and not dependency_frontier_changed and not authority_changed:
        return {
            "disposition": "PLACEMENT_RECOMPUTE_ONLY",
            "payload_rebuild_required": False,
            "assurance_renewal_required": True,
        }
    return {
        "disposition": "PAYLOAD_REBUILD_REQUIRED" if payload_changed or dependency_frontier_changed else "AUTHORITY_REVIEW_REQUIRED",
        "payload_rebuild_required": bool(payload_changed or dependency_frontier_changed),
        "assurance_renewal_required": True,
    }
