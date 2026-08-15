from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping

from .canonical import canonical_bytes
from .projection import SNAPSHOT_SCHEMA


class IntegrationReadError(ValueError):
    pass


def _hash(payload: Any) -> str:
    return sha256(canonical_bytes(payload)).hexdigest()


def _snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    value = deepcopy(dict(snapshot))
    if value.get("schema") != SNAPSHOT_SCHEMA:
        raise IntegrationReadError("C2P_READ_MODEL_SNAPSHOT_SCHEMA_INVALID")
    required = {
        "snapshot_id",
        "object_assertion_id",
        "event_frontier_hash",
        "event_frontier_sequence",
        "lifecycle_state",
        "observability_state",
        "evaluation_state",
        "market_effective_start",
        "first_valid_time",
        "evaluation_cutoff",
    }
    missing = sorted(required - value.keys())
    if missing:
        raise IntegrationReadError(f"C2P_READ_MODEL_SNAPSHOT_FIELD_MISSING:{missing[0]}")
    return value


def _base_reference(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    value = _snapshot(snapshot)
    return {
        "object_assertion_id": value["object_assertion_id"],
        "snapshot_id": value["snapshot_id"],
        "event_frontier_hash": value["event_frontier_hash"],
        "event_frontier_sequence": value["event_frontier_sequence"],
        "lifecycle_state": value["lifecycle_state"],
        "observability_state": value["observability_state"],
        "evaluation_state": value["evaluation_state"],
        "market_effective_start": value["market_effective_start"],
        "market_effective_end": value.get("market_effective_end"),
        "first_valid_time": value["first_valid_time"],
        "evaluation_cutoff": value["evaluation_cutoff"],
    }


def build_esl_optional_reference(
    snapshot: Mapping[str, Any] | None,
    *,
    availability_state: str,
    reason_code: str | None = None,
) -> dict[str, Any]:
    allowed = {"AVAILABLE", "NOT_AVAILABLE", "NOT_EVALUABLE", "AMBIGUOUS", "CONFLICT", "QUARANTINED"}
    if availability_state not in allowed:
        raise IntegrationReadError("C2P_ESL_INTEROP_STATE_INVALID")
    if availability_state == "AVAILABLE":
        if snapshot is None:
            raise IntegrationReadError("C2P_ESL_AVAILABLE_REQUIRES_ASSERTION")
        reference = _base_reference(snapshot)
    else:
        if snapshot is not None:
            raise IntegrationReadError("C2P_ESL_ABSENCE_CANNOT_CARRY_ASSERTION")
        reference = None
    body = {
        "schema": "c2p-esl-optional-reference/v0.1",
        "availability_state": availability_state,
        "object_assertion_reference": reference,
        "reason_code": reason_code,
        "authority_effect": "NONE",
        "base_structural_occurrence_remains_lawful": True,
        "persistence_synthesized": False,
    }
    return {"reference_id": _hash(body), **body}


def build_c25_reference(
    snapshot: Mapping[str, Any],
    *,
    event_definition_id: str,
    dependency_manifest_id: str,
    dependency_declared: bool,
) -> dict[str, Any]:
    if not dependency_declared:
        raise IntegrationReadError("C2P_C25_DEPENDENCY_NOT_DECLARED")
    reference = _base_reference(snapshot)
    if reference["evaluation_state"] != "AVAILABLE":
        raise IntegrationReadError("C2P_C25_REFERENCE_NOT_AVAILABLE")
    body = {
        "schema": "c2p-c25-read-reference/v0.2",
        "event_definition_id": event_definition_id,
        "dependency_manifest_id": dependency_manifest_id,
        "dependency_declared": True,
        "reference": reference,
        "tracklet_reference": None,
        "authority_effect": "NONE",
        "identity_owner": "C2P",
        "auto_retarget": False,
        "persistence_inference": False,
    }
    return {"reference_id": _hash(body), **body}


def build_c3_entity_temporal_reference(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    reference = _base_reference(snapshot)
    body = {
        "schema": "c2p-c3-entity-temporal-reference/v0.2",
        "entity_ref": {
            "namespace": "C2P",
            "object_type": "C2PObjectAssertion",
            "logical_id": reference["object_assertion_id"],
            "snapshot_id": reference["snapshot_id"],
        },
        "lifecycle_fact": reference["lifecycle_state"],
        "effective_interval": {
            "start": reference["market_effective_start"],
            "end": reference["market_effective_end"],
        },
        "knowledge_chronology": {
            "first_valid_time": reference["first_valid_time"],
            "evaluation_cutoff": reference["evaluation_cutoff"],
        },
        "source_frontier": {
            "event_frontier_hash": reference["event_frontier_hash"],
            "event_frontier_sequence": reference["event_frontier_sequence"],
        },
        "authority_effect": "NONE",
        "upstream_owner": "C2P",
        "persistence_inference": False,
        "identity_repair": False,
        "auto_retarget": False,
    }
    return {"reference_id": _hash(body), **body}


def build_research_operations_view(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    reference = _base_reference(snapshot)
    body = {
        "schema": "c2p-research-operations-read-view/v0.1",
        "record_class": "DERIVED_READ_ONLY_EVIDENCE_VIEW",
        "reference": reference,
        "state_axes": {
            "lifecycle": reference["lifecycle_state"],
            "observability": reference["observability_state"],
            "evaluation": reference["evaluation_state"],
        },
        "authority_effect": "NONE",
        "durable_research_write_performed": False,
        "source_owned": True,
    }
    return {"view_id": _hash(body), **body}


def build_console_read_model(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    value = _snapshot(snapshot)
    reference = _base_reference(value)
    body = {
        "schema": "c2p-console-read-model/v0.1",
        "object_assertion_id": reference["object_assertion_id"],
        "snapshot_id": reference["snapshot_id"],
        "frontier": {
            "hash": reference["event_frontier_hash"],
            "sequence": reference["event_frontier_sequence"],
        },
        "state_axes": {
            "lifecycle": reference["lifecycle_state"],
            "observability": reference["observability_state"],
            "evaluation": reference["evaluation_state"],
        },
        "chronology": {
            "effective_start": reference["market_effective_start"],
            "effective_end": reference["market_effective_end"],
            "first_valid_time": reference["first_valid_time"],
            "evaluation_cutoff": reference["evaluation_cutoff"],
        },
        "geometry": deepcopy(value.get("geometry", {})),
        "state_payload": deepcopy(value.get("state_payload", {})),
        "authority_effect": "NONE",
        "read_only": True,
        "write_capabilities": [],
    }
    return {"read_model_id": _hash(body), **body}
