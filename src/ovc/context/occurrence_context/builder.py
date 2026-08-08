from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .chronology import compute_first_valid_time
from .firewall import assert_no_forbidden_fields
from .models import BuildRequest, OccurrenceAnchorRef
from .serialization import canonical_json, logical_hash, sha256_payload

ALLOWED_ANCHORS = {
    "C2_OBSERVATION",
    "C2E_EPISODE_GENESIS",
    "C2E_EPISODE_SNAPSHOT",
    "C2E_PHASE_SEGMENT",
    "SRI_OCCURRENCE_REPRESENTATION",
    "FDI_OCCURRENCE_ASSIGNMENT",
}
ALIAS_ANCHORS = {"SRI_OCCURRENCE_REPRESENTATION", "FDI_OCCURRENCE_ASSIGNMENT"}
ALLOWED_SIDES = {"BID", "ASK"}
ALLOWED_AUTHORITY_STATES = {"INACTIVE", "SHADOW", "RESEARCH_ONLY", "UNAVAILABLE", "QUARANTINED"}
ALLOWED_AVAILABILITY = {"AVAILABLE", "PARTIAL", "NOT_EVALUABLE", "UNAVAILABLE", "STALE", "CONFLICT", "CENSORED", "QUARANTINED"}


class OccurrenceContextError(ValueError):
    def __init__(self, reason_code: str, message: str | None = None):
        self.reason_code = reason_code
        super().__init__(message or reason_code)


def _structural_identity_anchor(anchor: OccurrenceAnchorRef) -> Mapping[str, Any]:
    if anchor.anchor_kind not in ALIAS_ANCHORS:
        return anchor.to_dict()
    nested = anchor.structural_anchor_ref
    if not isinstance(nested, Mapping):
        raise OccurrenceContextError("OC_ID_ANCHOR_MUTATION", "alias anchor lacks structural_anchor_ref")
    for field in ("anchor_kind", "anchor_id", "anchor_schema_id", "anchor_logical_hash"):
        if not nested.get(field):
            raise OccurrenceContextError("OC_ID_ANCHOR_MUTATION", f"alias structural anchor missing {field}")
    return nested


def build_occurrence_key(anchor: OccurrenceAnchorRef) -> str:
    if anchor.anchor_kind not in ALLOWED_ANCHORS:
        raise OccurrenceContextError("OC_AVAIL_ANCHOR_MISSING", f"unsupported anchor kind {anchor.anchor_kind}")
    structural = _structural_identity_anchor(anchor)
    payload = {
        "anchor_kind": structural["anchor_kind"],
        "anchor_id": structural["anchor_id"],
        "anchor_schema_id": structural["anchor_schema_id"],
        "anchor_logical_hash": structural["anchor_logical_hash"],
    }
    return sha256_payload("OVC.OCCURRENCE", payload)


def _dependency_set_hash(request: BuildRequest) -> str:
    items = [item.to_dict() for item in request.dependency_refs]
    items.sort(key=canonical_json)
    return sha256_payload("OVC.OCCURRENCE_CONTEXT.DEPENDENCIES", items)


def _registry_binding_hash(request: BuildRequest) -> str:
    return sha256_payload("OVC.OCCURRENCE_CONTEXT.REGISTRIES", dict(request.registry_bindings))


def _validate_request(request: BuildRequest) -> None:
    if request.source_context.get("instrument_id") != "GBPUSD":
        raise OccurrenceContextError("OC_AUTH_NEW_INSTRUMENT_DENIED")
    if request.source_context.get("price_side") not in ALLOWED_SIDES:
        raise OccurrenceContextError("OC_AUTH_NEW_SIDE_DENIED")
    if request.research_role == "VALIDATION_METADATA_ONLY":
        raise OccurrenceContextError("OC_AUTH_VALIDATION_ACCESS_DENIED")
    if request.research_role not in {"DISCOVERY", "DEVELOPMENT"}:
        raise OccurrenceContextError("OC_DEP_FORBIDDEN_FIELD", "unsupported research role")
    if request.authority_state not in ALLOWED_AUTHORITY_STATES:
        raise OccurrenceContextError("OC_DEP_FORBIDDEN_FIELD", "activating authority state denied")
    if request.availability_status not in ALLOWED_AVAILABILITY:
        raise OccurrenceContextError("OC_DEP_FORBIDDEN_FIELD", "invalid availability state")
    if request.episode_relative_context is not None and not request.anchor_ref.anchor_kind.startswith("C2E_"):
        raise OccurrenceContextError("OC_C2E_REQUIRED_FOR_ELAPSED_DURATION")
    assert_no_forbidden_fields({
        "source_context": request.source_context,
        "calendar_context": request.calendar_context,
        "session_context": request.session_context,
        "clock_scale_context": request.clock_scale_context,
        "parent_context_refs": request.parent_context_refs,
        "market_condition_context": request.market_condition_context,
        "episode_relative_context": request.episode_relative_context,
        "auxiliary_refs": request.auxiliary_refs,
        "lineage": request.lineage,
    })


def build_context(request: BuildRequest) -> dict[str, Any]:
    _validate_request(request)
    anchor = request.anchor_ref.to_dict()
    occurrence_key = build_occurrence_key(request.anchor_ref)
    dependency_times = [item.first_valid_time for item in request.dependency_refs]
    first_valid_time = compute_first_valid_time(
        request.anchor_ref.anchor_first_valid_time,
        dependency_times,
        request.registry_first_valid_times,
        request.confirmation_time,
    )
    dependency_set_hash = _dependency_set_hash(request)
    registry_binding_hash = _registry_binding_hash(request)
    identity_payload = {
        "schema_version": "0.1",
        "context_pack_id": request.context_pack_id,
        "context_pack_version": request.context_pack_version,
        "occurrence_key": occurrence_key,
        "anchor_ref": anchor,
        "context_role_map_id": request.context_role_map_id,
        "dependency_set_hash": dependency_set_hash,
        "registry_binding_hash": registry_binding_hash,
        "first_valid_time": first_valid_time,
    }
    context_id = sha256_payload("OVC.OCCURRENCE_CONTEXT", identity_payload)
    record: dict[str, Any] = {
        "schema": "occurrence_context/v0_1",
        "schema_version": "0.1",
        "occurrence_context_id": context_id,
        "occurrence_key": occurrence_key,
        "context_pack_id": request.context_pack_id,
        "context_pack_version": request.context_pack_version,
        "anchor_ref": deepcopy(anchor),
        "source_context": deepcopy(dict(request.source_context)),
        "research_role": request.research_role,
        "occurrence_interval": deepcopy(dict(request.occurrence_interval)),
        "calendar_context": deepcopy(dict(request.calendar_context)),
        "session_context": deepcopy(dict(request.session_context)),
        "clock_scale_context": deepcopy(dict(request.clock_scale_context)),
        "parent_context_refs": deepcopy(list(request.parent_context_refs)),
        "market_condition_context": deepcopy(dict(request.market_condition_context)) if request.market_condition_context is not None else None,
        "episode_relative_context": deepcopy(dict(request.episode_relative_context)) if request.episode_relative_context is not None else None,
        "auxiliary_refs": deepcopy(list(request.auxiliary_refs)),
        "context_role_map_id": request.context_role_map_id,
        "dependency_refs": [deepcopy(item.to_dict()) for item in request.dependency_refs],
        "first_valid_time": first_valid_time,
        "availability": {"status": request.availability_status},
        "reason_codes": sorted(set(request.reason_codes)),
        "authority_state": request.authority_state,
        "lineage": {**deepcopy(dict(request.lineage)), "dependency_set_hash": dependency_set_hash, "registry_binding_hash": registry_binding_hash},
    }
    assert_no_forbidden_fields(record)
    record["logical_hash"] = logical_hash(record)
    return record
