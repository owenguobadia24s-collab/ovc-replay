from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .identity import CBSContractError, seal_object, verify_object

FORBIDDEN_SOURCE_FIELDS = frozenset({"outcome", "validation", "probability", "risk", "exposure", "trade", "execution"})
B0_ACTIONS = ("BIRTH", "CONTINUATION", "PHASE_MUTATION", "RE_PARENT", "CENSOR_GAP", "CENSOR_RELEASE_END")
B0_CLASSES = frozenset({"REFERENCE_BOUNDARY", "NON_BOUNDARY_EVENT", "CENSOR", "SOURCE_GAP"})


def build_input_projection_manifest(
    *, comparator_id: str, profile_id: str, source_schema: str, fields: Sequence[str],
    transforms: Sequence[Mapping[str, Any]], scaling: str, missingness: str, representation: str,
    first_valid_time_field: str, exposure_classification: str,
) -> dict[str, Any]:
    if not fields or len(set(fields)) != len(fields):
        raise CBSContractError("INPUT_PROJECTION_UNFROZEN:DUPLICATE_OR_EMPTY_FIELDS")
    lowered = {part.lower() for field in fields for part in field.split(".")}
    if lowered & FORBIDDEN_SOURCE_FIELDS:
        raise CBSContractError("CBS_INPUT_FIREWALL_VIOLATION")
    return seal_object(
        {
            "schema":"ovc-cbs-comparator-input-projection-manifest/v0.1", "comparator_id":comparator_id,
            "profile_id":profile_id, "source_schema":source_schema, "fields":list(fields),
            "transforms":[dict(item) for item in transforms], "scaling":scaling, "missingness":missingness,
            "representation":representation, "first_valid_time_field":first_valid_time_field,
            "hidden_source_fields":"FORBIDDEN", "exposure_classification":exposure_classification,
        }, id_field="projection_id"
    )


def _get(record: Mapping[str, Any], dotted: str) -> Any:
    value: Any = record
    for part in dotted.split("."):
        if not isinstance(value, Mapping) or part not in value:
            raise CBSContractError(f"INPUT_PROJECTION_UNFROZEN:MISSING:{dotted}")
        value = value[part]
    return value


def project_record(record: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    verify_object(manifest, id_field="projection_id")
    projected = {field: _get(record, field) for field in manifest["fields"]}
    return seal_object(
        {"schema":"ovc-cbs-comparator-input/v0.1", "projection_id":manifest["projection_id"], "values":projected},
        id_field="comparator_input_id",
    )


def build_b0_projection_manifest(*, pack_id: str, pack_sha256: str, action_classes: Mapping[str, str], status: str) -> dict[str, Any]:
    if set(action_classes) != set(B0_ACTIONS) or set(action_classes.values()) - B0_CLASSES:
        raise CBSContractError("INPUT_PROJECTION_UNFROZEN:B0_EVENT_CLASSIFICATION_INCOMPLETE")
    return seal_object(
        {"schema":"ovc-cbs-b0-reference-boundary-projection-manifest/v0.1", "pack_id":pack_id,
         "pack_sha256":pack_sha256, "action_classes":dict(sorted(action_classes.items())), "status":status,
         "censor_is_termination":False, "ground_truth":False}, id_field="b0_projection_id"
    )


def project_b0_events(events: Sequence[Mapping[str, Any]], manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    verify_object(manifest, id_field="b0_projection_id")
    if manifest.get("status") not in {"FROZEN_SYNTHETIC", "FROZEN_DEVELOPMENT"}:
        raise CBSContractError("INPUT_PROJECTION_UNFROZEN:B0")
    classes = manifest["action_classes"]
    output = []
    for event in events:
        action = str(event.get("action", ""))
        if action not in classes:
            raise CBSContractError("C2E_REFERENCE_PACK_UNRESOLVED:UNKNOWN_ACTION")
        output.append({"event_id":event.get("event_id"), "action":action, "classification":classes[action],
                       "effective_time":event.get("effective_time"), "first_valid_time":event.get("first_valid_time")})
    return output
