"""Owner-local publication route for the exact DIASI selected packet class."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ovc.development.skills.dias_cutover import (
    SELECTED_CLASS,
    SUCCESSOR_WRITER,
    validate_live_registry,
    writer_accepts,
)
from ovc.development.skills.repository_assurance_pilot import (
    is_pilot_receipt_path,
    load_json,
    validate_pilot_policy,
)
from ovc.development.skills.vit_routing import validate_vit_lineage_record
from tools.ci.vit_qualification_store import publish_qualification_envelope


ROUTE_REGISTRY = Path("registries/development/skills/VIT_SELECTED_CLASS_ROUTE_v0_1.json")
PILOT_POLICY = Path("registries/development/skills/REPOSITORY_ASSURANCE_PILOT_POLICY_v0_1.json")


def _load_object(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError(f"VIT_QUALIFICATION_OWNER_OBJECT_REQUIRED:{path}")
    return value


def validate_exact_selected_class(
    *,
    root: Path,
    lineage_record: Mapping[str, Any],
) -> tuple[str, ...]:
    validate_vit_lineage_record(lineage_record)
    pip = lineage_record.get("pip")
    if not isinstance(pip, Mapping):
        raise RuntimeError("VIT_QUALIFICATION_OWNER_PIP_INVALID")
    changes = pip.get("logical_changes")
    if not isinstance(changes, list) or not changes:
        raise RuntimeError("VIT_QUALIFICATION_OWNER_CHANGES_INVALID")
    policy = validate_pilot_policy(load_json(root / PILOT_POLICY))
    paths: list[str] = []
    for change in changes:
        if not isinstance(change, Mapping):
            raise RuntimeError("VIT_QUALIFICATION_OWNER_CHANGE_INVALID")
        op = str(change.get("op", ""))
        path = str(change.get("path", ""))
        if op not in {"ADD", "MODIFY"} or not is_pilot_receipt_path(path, policy):
            raise RuntimeError(f"VIT_QUALIFICATION_OWNER_NOT_EXACT_SELECTED_CLASS:{op}:{path}")
        paths.append(path)
    return tuple(sorted(paths))


def publish_owner_local_qualification(
    *,
    root: Path,
    envelope: Mapping[str, Any],
    lineage_record: Mapping[str, Any],
    packet_class: str,
    replace_head_binding: bool = False,
) -> str:
    if packet_class != SELECTED_CLASS:
        raise RuntimeError("VIT_QUALIFICATION_OWNER_CLASS_INVALID")
    registry = _load_object(root / ROUTE_REGISTRY)
    state = validate_live_registry(registry)
    validate_exact_selected_class(root=root, lineage_record=lineage_record)
    writer_accepts(
        writer=state.qualification_writer,
        generation=state.writer_generation,
        packet_class=packet_class,
    )
    if state.qualification_writer != SUCCESSOR_WRITER:
        raise RuntimeError("VIT_QUALIFICATION_OWNER_WRITER_DRIFT")
    return publish_qualification_envelope(
        envelope,
        replace_head_binding=replace_head_binding,
    )
