"""Deterministic materialisation of ratified OVC plan/work-packet records.

This module does not parse or interpret DOCX prose.  It accepts an already reviewed
plan transcription, binds it to an exact source identity, validates the packet/gate
graph fail-closed, and emits objects consumable by the existing DSAI orchestrator.
It never resolves Skill releases or grants authority.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable, Mapping, Sequence

from ovc.development.identity import canonical_sha256
from ovc.development.skills.orchestration import build_packet_graph_snapshot


AUTO_GATE_CLASSES = {"AUTO_EXECUTABLE", "AUTO_RATIFIABLE"}
OPERATOR_GATE_CLASSES = {"OPERATOR_REQUIRED", "OPERATOR_RESERVED"}
GATE_CLASSES = AUTO_GATE_CLASSES | OPERATOR_GATE_CLASSES
PACKET_STATES = {
    "PLANNED",
    "READY",
    "RUNNING",
    "IMPLEMENTED",
    "QA_REVIEW",
    "GATE_READY",
    "APPROVED",
    "BLOCKED",
    "QUARANTINED",
    "SUPERSEDED",
    "COMPLETED",
}
REQUIRED_CAPABILITY_FIELDS = {
    "capability_id",
    "version_range",
    "required_tier",
    "mandatory",
    "reason",
}
REQUIRED_PACKET_FIELDS = {
    "packet_id",
    "title",
    "status",
    "objective",
    "prerequisites",
    "required_artifacts",
    "capability_requirements",
    "tests",
    "acceptance_conditions",
    "outputs",
    "rollback",
    "authority_required",
    "authority_delta",
    "gate_ids",
    "next_packet",
}
REQUIRED_GATE_FIELDS = {
    "gate_id",
    "title",
    "gate_class",
    "acceptance_conditions",
    "authority_delta",
    "rollback",
}
RESERVED_AUTHORITY_TOKENS = {
    "SELECTOR",
    "ACTIVE_DISCOVERY",
    "ACTIVE_DEVELOPMENT",
    "ACTIVE_VALIDATION",
    "SEMANTIC_PROMOTION",
    "THRESHOLD_PROMOTION",
    "MODEL_PROMOTION",
    "FAMILY_PROMOTION",
    "CANDIDATE_PROMOTION",
    "THEORY_PROMOTION",
    "CANONICAL_PUBLICATION",
    "R2_PUBLICATION",
    "NEW_IMMUTABLE_RELEASE",
    "REAL_PROVIDER_INTAKE",
    "AUTHORITATIVE_RELEASE_FREEZE",
    "RETIRE_ACTIVE_AUTHORITY",
    "DESTRUCTIVE_ACTION",
    "HISTORY_REWRITE",
    "FORCE_PUSH",
    "DEFERRED_CAPABILITY_ACTIVATION",
    "SCOPE_EXPANSION",
    "NEW_INSTRUMENT",
    "NEW_MARKET",
    "NEW_CLOCK",
    "NEW_SIDE",
    "UNDECLARED_DEPENDENCY",
    "FROZEN_CONTRACT_CHANGE",
    "AGENT_WRITE_AUTHORITY",
    "PROBABILITY_AUTHORITY",
    "RISK_AUTHORITY",
    "EXPOSURE_AUTHORITY",
    "E_H_AUTHORITY",
    "EXECUTION_AUTHORITY",
    "SKILL_TRUSTED_PROMOTION",
    "TOOL_BROKER_ACTIVATION",
    "ORCH_1_ASSISTED_WRITES",
    "ORCH_2_AUTOMATIC_INTEGRATION",
    "VALIDATION_ACCESS",
    "CANONICAL_OR_R2_PUBLICATION",
    "PROBABILITY_RISK_EXPOSURE_EXECUTION",
}


class PlanMaterialisationError(ValueError):
    """Fail-closed plan/packet materialisation error."""


def _non_empty(value: Any, *, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise PlanMaterialisationError(f"{field} is required")
    return text


def _string_list(value: Any, *, field: str, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, (list, tuple)):
        raise PlanMaterialisationError(f"{field} must be a list")
    values = [str(item).strip() for item in value]
    if any(not item for item in values):
        raise PlanMaterialisationError(f"{field} contains an empty value")
    if not allow_empty and not values:
        raise PlanMaterialisationError(f"{field} must not be empty")
    if len(values) != len(set(values)):
        raise PlanMaterialisationError(f"{field} contains duplicate values")
    return values


def _content_sha256(content: bytes | str) -> str:
    payload = content if isinstance(content, bytes) else content.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _reserved_tokens(
    authority_delta: str,
    declared_tokens: Sequence[str] = (),
) -> list[str]:
    declared = {str(value).strip().upper() for value in declared_tokens if str(value).strip()}
    inferred = {token for token in RESERVED_AUTHORITY_TOKENS if token in authority_delta.upper()}
    return sorted(declared | inferred)


def build_plan_source_ref(
    *,
    plan_id: str,
    plan_version: str,
    source_ref: str,
    source_sha256: str,
) -> dict[str, Any]:
    source_hash = _non_empty(source_sha256, field="source_sha256").lower()
    if re.fullmatch(r"[0-9a-f]{64}", source_hash) is None:
        raise PlanMaterialisationError("source_sha256 must be a lowercase SHA-256 hex digest")
    logical = {
        "plan_id": _non_empty(plan_id, field="plan_id"),
        "plan_version": _non_empty(plan_version, field="plan_version"),
        "source_ref": _non_empty(source_ref, field="source_ref"),
        "source_sha256": source_hash,
    }
    return {
        "schema": "ovc-dsai-plan-source-ref/v1",
        **logical,
        "source_ref_id": canonical_sha256(logical, role="DSAI_PLAN_SOURCE_REF"),
        "authority_effect": "NONE",
    }


def _validate_plan_source_ref(plan_source_ref: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema",
        "plan_id",
        "plan_version",
        "source_ref",
        "source_sha256",
        "source_ref_id",
        "authority_effect",
    }
    missing = sorted(required - set(plan_source_ref))
    if missing:
        raise PlanMaterialisationError(f"plan source ref missing fields {missing}")
    if plan_source_ref.get("schema") != "ovc-dsai-plan-source-ref/v1":
        raise PlanMaterialisationError("unsupported plan source ref schema")
    if plan_source_ref.get("authority_effect") != "NONE":
        raise PlanMaterialisationError("plan source ref cannot grant authority")
    rebuilt = build_plan_source_ref(
        plan_id=str(plan_source_ref.get("plan_id", "")),
        plan_version=str(plan_source_ref.get("plan_version", "")),
        source_ref=str(plan_source_ref.get("source_ref", "")),
        source_sha256=str(plan_source_ref.get("source_sha256", "")),
    )
    if dict(plan_source_ref) != rebuilt:
        raise PlanMaterialisationError("plan source ref identity/content mismatch")
    return rebuilt


def verify_plan_source(
    plan_source_ref: Mapping[str, Any],
    source_content: bytes | str,
) -> str:
    source = _validate_plan_source_ref(plan_source_ref)
    observed = _content_sha256(source_content)
    if observed != source["source_sha256"]:
        raise PlanMaterialisationError(
            f"source hash mismatch: expected {source['source_sha256']}, observed {observed}"
        )
    return observed


def verify_materialisation_freshness(
    *,
    receipt: Mapping[str, Any],
    plan_source_ref: Mapping[str, Any],
    current_source_sha256: str,
) -> None:
    source = _validate_plan_source_ref(plan_source_ref)
    current = _non_empty(current_source_sha256, field="current_source_sha256").lower()
    if re.fullmatch(r"[0-9a-f]{64}", current) is None:
        raise PlanMaterialisationError("current_source_sha256 must be a SHA-256 hex digest")
    expected_ref = receipt.get("plan_source_ref_id")
    expected_hash = receipt.get("source_sha256")
    if expected_ref != source["source_ref_id"] or expected_hash != source["source_sha256"]:
        raise PlanMaterialisationError("receipt/source binding mismatch")
    if current != source["source_sha256"]:
        raise PlanMaterialisationError("governing plan source changed after materialisation")


def capability_ids_from_registry(
    capability_registry: Mapping[str, Any],
) -> set[str]:
    if capability_registry.get("schema") != "ovc-dsai-capability-registry/v1":
        raise PlanMaterialisationError("unsupported capability registry schema")
    if capability_registry.get("projection_only") is not True:
        raise PlanMaterialisationError("capability registry must be projection-only")
    if capability_registry.get("authority_effect") != "NONE":
        raise PlanMaterialisationError("capability registry cannot grant authority")
    entries = capability_registry.get("entries")
    if not isinstance(entries, list) or not entries:
        raise PlanMaterialisationError("capability registry entries are required")
    capability_ids = [
        _non_empty(row.get("capability_id"), field="capability_registry.capability_id")
        for row in entries
        if isinstance(row, Mapping)
    ]
    if len(capability_ids) != len(entries):
        raise PlanMaterialisationError("capability registry entries must be objects")
    if len(capability_ids) != len(set(capability_ids)):
        raise PlanMaterialisationError("capability registry contains duplicate ids")
    return set(capability_ids)


def build_capability_requirement(
    *,
    capability_id: str,
    version_range: str,
    required_tier: str,
    mandatory: bool,
    reason: str,
) -> dict[str, Any]:
    if not isinstance(mandatory, bool):
        raise PlanMaterialisationError("mandatory must be boolean")
    return {
        "schema": "ovc-dsai-capability-requirement/v1",
        "capability_id": _non_empty(capability_id, field="capability_id"),
        "version_range": _non_empty(version_range, field="version_range"),
        "required_tier": _non_empty(required_tier, field="required_tier").upper(),
        "mandatory": mandatory,
        "reason": _non_empty(reason, field="reason"),
        "authority_effect": "NONE",
    }


def _normalize_requirement(
    raw: Mapping[str, Any],
    *,
    known_capability_ids: set[str],
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise PlanMaterialisationError("capability requirement must be an object")
    missing = sorted(REQUIRED_CAPABILITY_FIELDS - set(raw))
    if missing:
        raise PlanMaterialisationError(f"capability requirement missing fields {missing}")
    requirement = build_capability_requirement(
        capability_id=str(raw.get("capability_id", "")),
        version_range=str(raw.get("version_range", "")),
        required_tier=str(raw.get("required_tier", "")),
        mandatory=raw.get("mandatory"),
        reason=str(raw.get("reason", "")),
    )
    if requirement["mandatory"] and requirement["capability_id"] not in known_capability_ids:
        raise PlanMaterialisationError(
            f"unknown mandatory capability {requirement['capability_id']}"
        )
    return requirement


def _normalize_gate(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise PlanMaterialisationError("gate must be an object")
    missing = sorted(REQUIRED_GATE_FIELDS - set(raw))
    if missing:
        raise PlanMaterialisationError(f"missing gate fields {missing}")
    gate_class = _non_empty(raw.get("gate_class"), field="gate_class").upper()
    if gate_class not in GATE_CLASSES:
        raise PlanMaterialisationError(f"unsupported gate class {gate_class}")
    acceptance = _string_list(
        raw.get("acceptance_conditions"),
        field="gate.acceptance_conditions",
        allow_empty=False,
    )
    authority_delta = _non_empty(raw.get("authority_delta"), field="gate.authority_delta")
    reserved = _reserved_tokens(authority_delta, raw.get("reserved_authority_tokens", []))
    if reserved and gate_class in AUTO_GATE_CLASSES:
        raise PlanMaterialisationError(
            f"gate {_non_empty(raw.get('gate_id'), field='gate_id')} cannot be auto-ratifiable with reserved authority {reserved}"
        )
    gate = {
        "schema": "ovc-dsai-packet-gate-manifest/v1",
        "gate_id": _non_empty(raw.get("gate_id"), field="gate_id"),
        "title": _non_empty(raw.get("title"), field="gate.title"),
        "gate_class": gate_class,
        "acceptance_conditions": acceptance,
        "authority_delta": authority_delta,
        "reserved_authority_tokens": reserved,
        "rollback": _non_empty(raw.get("rollback"), field="gate.rollback"),
        "authority_effect": "NONE",
    }
    if raw.get("pass_permits") is not None:
        gate["pass_permits"] = _string_list(raw["pass_permits"], field="gate.pass_permits")
    if raw.get("pass_does_not_permit") is not None:
        gate["pass_does_not_permit"] = _string_list(
            raw["pass_does_not_permit"], field="gate.pass_does_not_permit"
        )
    return gate


def _normalize_packet(
    raw: Mapping[str, Any],
    *,
    known_capability_ids: set[str],
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise PlanMaterialisationError("packet must be an object")
    missing = sorted(REQUIRED_PACKET_FIELDS - set(raw))
    if missing:
        raise PlanMaterialisationError(f"missing packet fields {missing}")
    packet_id = _non_empty(raw.get("packet_id"), field="packet_id")
    status = _non_empty(raw.get("status"), field=f"{packet_id}.status").upper()
    if status not in PACKET_STATES:
        raise PlanMaterialisationError(f"{packet_id}: unsupported packet status {status}")
    raw_requirements = raw.get("capability_requirements")
    if not isinstance(raw_requirements, (list, tuple)) or not raw_requirements:
        raise PlanMaterialisationError(f"{packet_id}: capability_requirements must not be empty")
    requirements = [
        _normalize_requirement(requirement, known_capability_ids=known_capability_ids)
        for requirement in raw_requirements
    ]
    capability_keys = [(row["capability_id"], row["version_range"], row["required_tier"]) for row in requirements]
    if len(capability_keys) != len(set(capability_keys)):
        raise PlanMaterialisationError(f"{packet_id}: duplicate capability requirement")
    requirements.sort(key=lambda row: (row["capability_id"], row["version_range"], row["required_tier"]))
    packet = {
        "schema": "ovc-dsai-packet-manifest/v1",
        "packet_id": packet_id,
        "title": _non_empty(raw.get("title"), field=f"{packet_id}.title"),
        "status": status,
        "objective": _non_empty(raw.get("objective"), field=f"{packet_id}.objective"),
        "packet_class": _non_empty(raw.get("packet_class", "IMPLEMENTATION"), field=f"{packet_id}.packet_class").upper(),
        "prerequisites": sorted(_string_list(raw.get("prerequisites"), field=f"{packet_id}.prerequisites")),
        "required_artifacts": _string_list(raw.get("required_artifacts"), field=f"{packet_id}.required_artifacts", allow_empty=False),
        "capability_requirements": requirements,
        "tests": _string_list(raw.get("tests"), field=f"{packet_id}.tests", allow_empty=False),
        "acceptance_conditions": _string_list(raw.get("acceptance_conditions"), field=f"{packet_id}.acceptance_conditions", allow_empty=False),
        "outputs": _string_list(raw.get("outputs"), field=f"{packet_id}.outputs", allow_empty=False),
        "rollback": _non_empty(raw.get("rollback"), field=f"{packet_id}.rollback"),
        "authority_required": _non_empty(raw.get("authority_required"), field=f"{packet_id}.authority_required"),
        "authority_delta": _non_empty(raw.get("authority_delta"), field=f"{packet_id}.authority_delta"),
        "reserved_authority_tokens": _reserved_tokens(
            str(raw.get("authority_delta", "")), raw.get("reserved_authority_tokens", [])
        ),
        "gate_ids": sorted(_string_list(raw.get("gate_ids"), field=f"{packet_id}.gate_ids", allow_empty=False)),
        "next_packet": None if raw.get("next_packet") is None else _non_empty(raw.get("next_packet"), field=f"{packet_id}.next_packet"),
        "authority_effect": "NONE",
    }
    optional_lists = {
        "external_prerequisites",
        "inputs",
        "implementation_actions",
        "qa_requirements",
    }
    for field in optional_lists:
        if raw.get(field) is not None:
            packet[field] = _string_list(raw[field], field=f"{packet_id}.{field}")
    for field in ("allowed", "state_transition"):
        if raw.get(field) is not None:
            packet[field] = _non_empty(raw[field], field=f"{packet_id}.{field}")
    return packet


def _topological_order(packets: Sequence[Mapping[str, Any]]) -> list[str]:
    packet_ids = {str(packet["packet_id"]) for packet in packets}
    prerequisites: dict[str, set[str]] = {}
    dependents: dict[str, set[str]] = {packet_id: set() for packet_id in packet_ids}
    for packet in packets:
        packet_id = str(packet["packet_id"])
        deps = {str(value) for value in packet.get("prerequisites", [])}
        if packet_id in deps:
            raise PlanMaterialisationError(f"{packet_id}: self prerequisite")
        unknown = sorted(deps - packet_ids)
        if unknown:
            raise PlanMaterialisationError(
                f"{packet_id}: unknown internal prerequisites {unknown}"
            )
        prerequisites[packet_id] = deps
        for dep in deps:
            dependents[dep].add(packet_id)
    ready = sorted(packet_id for packet_id, deps in prerequisites.items() if not deps)
    order: list[str] = []
    remaining = {packet_id: set(deps) for packet_id, deps in prerequisites.items()}
    while ready:
        packet_id = ready.pop(0)
        order.append(packet_id)
        for dependent in sorted(dependents[packet_id]):
            remaining[dependent].discard(packet_id)
            if not remaining[dependent] and dependent not in order and dependent not in ready:
                ready.append(dependent)
                ready.sort()
    if len(order) != len(packet_ids):
        cyclic = sorted(packet_ids - set(order))
        raise PlanMaterialisationError(f"packet prerequisite cycle detected {cyclic}")
    return order


def _validate_successors(packets: Sequence[Mapping[str, Any]]) -> None:
    by_id = {str(packet["packet_id"]): packet for packet in packets}
    for packet in packets:
        packet_id = str(packet["packet_id"])
        successor = packet.get("next_packet")
        if successor is None:
            continue
        if successor not in by_id:
            raise PlanMaterialisationError(f"{packet_id}: unknown next_packet {successor}")
        if packet_id not in set(by_id[successor].get("prerequisites", [])):
            raise PlanMaterialisationError(
                f"{packet_id}: next_packet {successor} is inconsistent with successor prerequisites"
            )


def _validate_packet_authority(
    packets: Sequence[Mapping[str, Any]],
    gates: Sequence[Mapping[str, Any]],
) -> None:
    gates_by_id = {str(gate["gate_id"]): gate for gate in gates}
    for packet in packets:
        packet_id = str(packet["packet_id"])
        selected = [gates_by_id[gate_id] for gate_id in packet.get("gate_ids", []) if gate_id in gates_by_id]
        reserved = list(packet.get("reserved_authority_tokens", []))
        authority_required = str(packet.get("authority_required", "")).upper()
        operator_required = bool(reserved) or "OPERATOR" in authority_required
        if operator_required and not any(gate["gate_class"] in OPERATOR_GATE_CLASSES for gate in selected):
            raise PlanMaterialisationError(
                f"{packet_id}: reserved authority requires an operator gate"
            )
        if reserved and any(gate["gate_class"] in AUTO_GATE_CLASSES for gate in selected):
            raise PlanMaterialisationError(
                f"{packet_id}: reserved authority {reserved} cannot be hidden under an auto gate"
            )


def materialise_programme(
    *,
    programme_id: str,
    baseline_main: str,
    plan_source_ref: Mapping[str, Any],
    packets: Sequence[Mapping[str, Any]],
    gates: Sequence[Mapping[str, Any]],
    known_capability_ids: Iterable[str],
    source_content: bytes | str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    source = _validate_plan_source_ref(plan_source_ref)
    if source_content is not None:
        verify_plan_source(source, source_content)

    known_capabilities = {
        _non_empty(value, field="known_capability_id") for value in known_capability_ids
    }
    if not known_capabilities:
        raise PlanMaterialisationError("known_capability_ids must not be empty")

    normalized_gates = [_normalize_gate(raw) for raw in gates]
    gate_ids = [str(gate["gate_id"]) for gate in normalized_gates]
    if not gate_ids:
        raise PlanMaterialisationError("at least one gate must be materialised")
    if len(gate_ids) != len(set(gate_ids)):
        raise PlanMaterialisationError("duplicate gate identity")

    normalized_packets = [
        _normalize_packet(raw, known_capability_ids=known_capabilities)
        for raw in packets
    ]
    packet_ids = [str(packet["packet_id"]) for packet in normalized_packets]
    if not packet_ids:
        raise PlanMaterialisationError("at least one packet must be materialised")
    if len(packet_ids) != len(set(packet_ids)):
        raise PlanMaterialisationError("duplicate packet identity")

    known_gates = set(gate_ids)
    for packet in normalized_packets:
        unknown_gates = sorted(set(packet["gate_ids"]) - known_gates)
        if unknown_gates:
            raise PlanMaterialisationError(
                f"{packet['packet_id']}: unknown gate references {unknown_gates}"
            )

    order = _topological_order(normalized_packets)
    _validate_successors(normalized_packets)
    _validate_packet_authority(normalized_packets, normalized_gates)
    normalized_packets.sort(key=lambda row: row["packet_id"])
    normalized_gates.sort(key=lambda row: row["gate_id"])

    logical = {
        "programme_id": _non_empty(programme_id, field="programme_id"),
        "plan_id": source["plan_id"],
        "plan_version": source["plan_version"],
        "plan_source_ref": source,
        "packets": normalized_packets,
        "gates": normalized_gates,
        "topological_order": order,
    }
    manifest = {
        "schema": "ovc-dsai-programme-manifest/v1",
        **logical,
        "programme_manifest_id": canonical_sha256(
            logical, role="DSAI_PROGRAMME_MANIFEST"
        ),
        "authority_effect": "NONE",
    }

    gates_by_id = {gate["gate_id"]: gate for gate in normalized_gates}
    graph_packets = []
    for packet in normalized_packets:
        selected = [gates_by_id[gate_id] for gate_id in packet["gate_ids"]]
        graph_gate_class = (
            "OPERATOR_REQUIRED"
            if any(gate["gate_class"] in OPERATOR_GATE_CLASSES for gate in selected)
            else "AUTO_EXECUTABLE"
        )
        graph_packets.append(
            {
                "packet_id": packet["packet_id"],
                "prerequisites": packet["prerequisites"],
                "required_capabilities": [
                    requirement["capability_id"]
                    for requirement in packet["capability_requirements"]
                    if requirement["mandatory"]
                ],
                "gate_class": graph_gate_class,
                "authority_delta": packet["authority_delta"],
                "packet_class": packet["packet_class"],
            }
        )
    graph = build_packet_graph_snapshot(
        programme_id=manifest["programme_id"],
        baseline_main=_non_empty(baseline_main, field="baseline_main"),
        packets=graph_packets,
    )

    receipt_logical = {
        "programme_manifest_id": manifest["programme_manifest_id"],
        "plan_source_ref_id": source["source_ref_id"],
        "source_sha256": source["source_sha256"],
        "source_verified": source_content is not None,
        "packet_graph_id": graph["record_id"],
        "packet_graph_hash": graph["graph_hash"],
        "packet_count": len(normalized_packets),
        "gate_count": len(normalized_gates),
        "topological_order": order,
        "validation_status": "PASS",
    }
    receipt = {
        "schema": "ovc-dsai-plan-packet-materialisation-receipt/v1",
        **receipt_logical,
        "materialisation_receipt_id": canonical_sha256(
            receipt_logical, role="DSAI_PLAN_PACKET_MATERIALISATION_RECEIPT"
        ),
        "authority_effect": "NONE",
    }
    return manifest, graph, receipt
