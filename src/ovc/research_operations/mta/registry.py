from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

REGISTRY_PATHS = {
    "FLOW_OBJECT": "registries/research_operations/mta/MTA_FLOW_OBJECT_REGISTRY_v0_1.json",
    "METRIC": "registries/research_operations/mta/MTA_METRIC_REGISTRY_v0_1.json",
    "COMPUTABILITY_STATUS": "registries/research_operations/mta/MTA_COMPUTABILITY_STATUS_REGISTRY_v0_1.json",
    "REASON_CODE": "registries/research_operations/mta/MTA_REASON_CODE_REGISTRY_v0_1.json",
    "MARKER_FUNCTION": "registries/research_operations/mta/MTA_MARKER_FUNCTION_REGISTRY_v0_1.json",
}

EXPECTED_COMPUTABILITY = {
    "EVALUATED_FIRED",
    "EVALUATED_NOT_FIRED",
    "NOT_EVALUATED_OUT_OF_SCOPE",
    "NOT_EVALUABLE_SOURCE_MISSING",
    "NOT_EVALUABLE_PARENT_MISSING",
    "NOT_EVALUABLE_AXIS_MISSING",
    "NOT_EVALUABLE_HISTORY_INSUFFICIENT",
    "NOT_EVALUABLE_GAP_OR_RESET",
    "CONFLICT",
    "CENSORED",
    "QUARANTINED",
}

EXPECTED_MARKERS = {
    "BOUNDARY_ZONE_ENTRY",
    "BREACH_ACTIVE",
    "RETURN_INSIDE",
    "COMPRESSION_TO_DISPLACEMENT",
    "LONG_PERSISTENCE",
    "REPEATED_SWITCHING",
    "LOCAL_PARENT_CONFLICT",
    "ALIGNMENT_GAINED",
}

EXPECTED_MARKER_CLASSES = {
    "BOUNDARY_ZONE_ENTRY": "LEVEL_INTERACTION",
    "BREACH_ACTIVE": "LEVEL_INTERACTION",
    "RETURN_INSIDE": "LEVEL_INTERACTION",
    "COMPRESSION_TO_DISPLACEMENT": "STATE_CHANGE",
    "LONG_PERSISTENCE": "PERSISTENCE",
    "REPEATED_SWITCHING": "SEQUENCE_INSTABILITY",
    "LOCAL_PARENT_CONFLICT": "CROSS_SCALE_CONTEXT",
    "ALIGNMENT_GAINED": "CROSS_SCALE_CONTEXT",
}

STATUS_TO_REASON_FAMILY = {
    "NOT_EVALUATED_OUT_OF_SCOPE": {"SCOPE"},
    "NOT_EVALUABLE_SOURCE_MISSING": {"SOURCE"},
    "NOT_EVALUABLE_PARENT_MISSING": {"PARENT"},
    "NOT_EVALUABLE_AXIS_MISSING": {"AXIS"},
    "NOT_EVALUABLE_HISTORY_INSUFFICIENT": {"HISTORY"},
    "NOT_EVALUABLE_GAP_OR_RESET": {"CONTINUITY"},
    "CONFLICT": {"CONFLICT"},
    "CENSORED": {"CENSORING"},
    "QUARANTINED": {"QUARANTINE"},
}


class RegistryValidationError(ValueError):
    """Raised when the frozen MTA registry bundle is inconsistent."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RegistryValidationError(f"REGISTRY_NOT_OBJECT:{path}")
    return value


def load_registry_bundle(root: Path) -> dict[str, dict[str, Any]]:
    bundle: dict[str, dict[str, Any]] = {}
    for kind, relative in REGISTRY_PATHS.items():
        path = root / relative
        if not path.is_file():
            raise RegistryValidationError(f"REGISTRY_MISSING:{relative}")
        bundle[kind] = _load_object(path)
    return bundle


def _entries(registry: Mapping[str, Any], expected_kind: str) -> list[dict[str, Any]]:
    entries = registry.get("entries")
    if not isinstance(entries, list) or not entries:
        raise RegistryValidationError(f"REGISTRY_ENTRIES_INVALID:{expected_kind}")
    result: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise RegistryValidationError(f"REGISTRY_ENTRY_NOT_OBJECT:{expected_kind}:{index}")
        if entry.get("registry_kind") != expected_kind:
            raise RegistryValidationError(f"REGISTRY_KIND_MISMATCH:{expected_kind}:{index}")
        result.append(entry)
    return result


def _validate_common(entries: list[dict[str, Any]], kind: str) -> None:
    ids: set[str] = set()
    names: set[str] = set()
    for entry in entries:
        entry_id = entry.get("registry_entry_id")
        name = entry.get("name")
        if not isinstance(entry_id, str) or not entry_id:
            raise RegistryValidationError(f"ENTRY_ID_INVALID:{kind}")
        if entry_id in ids:
            raise RegistryValidationError(f"DUPLICATE_ENTRY_ID:{entry_id}")
        ids.add(entry_id)
        if not isinstance(name, str) or not name:
            raise RegistryValidationError(f"ENTRY_NAME_INVALID:{entry_id}")
        if name in names:
            raise RegistryValidationError(f"DUPLICATE_ENTRY_NAME:{name}")
        names.add(name)
        if entry.get("status") not in {
            "ACTIVE_AUDIT", "REFERENCE_ONLY", "DEFERRED", "PROHIBITED", "SUPERSEDED"
        }:
            raise RegistryValidationError(f"ENTRY_STATUS_INVALID:{entry_id}")
        authority = entry.get("authority")
        if not isinstance(authority, dict):
            raise RegistryValidationError(f"AUTHORITY_MISSING:{entry_id}")
        if authority.get("semantic_promotion") != "DENIED":
            raise RegistryValidationError(f"SEMANTIC_PROMOTION_NOT_DENIED:{entry_id}")
        if authority.get("selector_or_release_mutation") != "DENIED":
            raise RegistryValidationError(f"SELECTOR_RELEASE_MUTATION_NOT_DENIED:{entry_id}")
        lineage = entry.get("source_lineage")
        if not isinstance(lineage, list) or not lineage:
            raise RegistryValidationError(f"SOURCE_LINEAGE_MISSING:{entry_id}")
        for source in lineage:
            if not isinstance(source, dict) or not source.get("path") or not source.get("role"):
                raise RegistryValidationError(f"SOURCE_LINEAGE_INVALID:{entry_id}")


def _validate_flow(entries: list[dict[str, Any]]) -> None:
    names = {entry["name"] for entry in entries}
    required = {
        "OPT-A sealed source interval",
        "OPT-B.C1 atomic fact",
        "OPT-B.C2 parallel state",
        "MTA marker attempt",
        "MTA occurrence",
        "MTA overlap cluster",
        "RO4 sequence window",
        "OPT-B.C2E episode",
        "OPT-B.C2.5 event",
        "OPT-B.C3 structural meaning",
    }
    missing = sorted(required - names)
    if missing:
        raise RegistryValidationError(f"FLOW_OBJECTS_MISSING:{','.join(missing)}")
    by_id = {entry["registry_entry_id"]: entry for entry in entries}
    for suffix in ("OPT_B_C2E.v1", "OPT_B_C2_5.v1", "OPT_B_C3.v1"):
        entry = next((item for key, item in by_id.items() if key.endswith(suffix)), None)
        if entry is None or entry["status"] not in {"DEFERRED", "PROHIBITED"}:
            raise RegistryValidationError(f"DEFERRED_AUTHORITY_NOT_CLOSED:{suffix}")


def _validate_metrics(entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        unit = entry.get("unit")
        numerator = entry.get("numerator")
        denominator = entry.get("denominator")
        zero = entry.get("zero_denominator")
        if not isinstance(numerator, str) or not numerator:
            raise RegistryValidationError(f"METRIC_NUMERATOR_MISSING:{entry['name']}")
        if unit == "COUNT":
            if zero != "ZERO":
                raise RegistryValidationError(f"COUNT_ZERO_POLICY_INVALID:{entry['name']}")
        else:
            if not isinstance(denominator, str) or not denominator or denominator == "not applicable":
                raise RegistryValidationError(f"METRIC_DENOMINATOR_MISSING:{entry['name']}")
            if zero != "NOT_EVALUABLE":
                raise RegistryValidationError(f"RATE_ZERO_POLICY_INVALID:{entry['name']}")


def _validate_computability(entries: list[dict[str, Any]]) -> None:
    names = {entry["name"] for entry in entries}
    if names != EXPECTED_COMPUTABILITY:
        missing = sorted(EXPECTED_COMPUTABILITY - names)
        extra = sorted(names - EXPECTED_COMPUTABILITY)
        raise RegistryValidationError(f"COMPUTABILITY_VOCABULARY_MISMATCH:missing={missing}:extra={extra}")
    for entry in entries:
        expected = STATUS_TO_REASON_FAMILY.get(entry["name"])
        if expected is None:
            if entry.get("reason_family") is not None:
                raise RegistryValidationError(f"EVALUATED_STATUS_HAS_REASON_FAMILY:{entry['name']}")
        elif entry.get("reason_family") not in expected:
            raise RegistryValidationError(f"COMPUTABILITY_REASON_FAMILY_MISMATCH:{entry['name']}")


def _validate_reasons(entries: list[dict[str, Any]]) -> None:
    families = {entry.get("reason_family") for entry in entries}
    required = {"SOURCE", "PARENT", "AXIS", "HISTORY", "CONTINUITY", "CONFLICT", "CENSORING", "QUARANTINE", "SCOPE"}
    missing = sorted(required - families)
    if missing:
        raise RegistryValidationError(f"REASON_FAMILIES_MISSING:{','.join(missing)}")


def _validate_markers(entries: list[dict[str, Any]]) -> None:
    names = {entry["name"] for entry in entries}
    if names != EXPECTED_MARKERS:
        missing = sorted(EXPECTED_MARKERS - names)
        extra = sorted(names - EXPECTED_MARKERS)
        raise RegistryValidationError(f"MARKER_SET_MISMATCH:missing={missing}:extra={extra}")
    for entry in entries:
        expected_class = EXPECTED_MARKER_CLASSES[entry["name"]]
        if entry.get("functional_class") != expected_class:
            raise RegistryValidationError(f"MARKER_CLASS_MISMATCH:{entry['name']}")
        if not isinstance(entry.get("required_history_bars"), int) or entry["required_history_bars"] < 2:
            raise RegistryValidationError(f"MARKER_HISTORY_INVALID:{entry['name']}")
        if entry["name"] in {"LOCAL_PARENT_CONFLICT", "ALIGNMENT_GAINED"}:
            if entry.get("requires_parent") is not True:
                raise RegistryValidationError(f"PARENT_REQUIREMENT_MISSING:{entry['name']}")
        elif entry.get("requires_parent") is not False:
            raise RegistryValidationError(f"UNDECLARED_PARENT_REQUIREMENT:{entry['name']}")


def validate_registry_bundle(bundle: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    missing = sorted(set(REGISTRY_PATHS) - set(bundle))
    if missing:
        raise RegistryValidationError(f"REGISTRY_KINDS_MISSING:{','.join(missing)}")
    validated: dict[str, list[dict[str, Any]]] = {}
    for kind in REGISTRY_PATHS:
        entries = _entries(bundle[kind], kind)
        _validate_common(entries, kind)
        validated[kind] = entries
    _validate_flow(validated["FLOW_OBJECT"])
    _validate_metrics(validated["METRIC"])
    _validate_computability(validated["COMPUTABILITY_STATUS"])
    _validate_reasons(validated["REASON_CODE"])
    _validate_markers(validated["MARKER_FUNCTION"])

    all_ids = [entry["registry_entry_id"] for entries in validated.values() for entry in entries]
    if len(all_ids) != len(set(all_ids)):
        raise RegistryValidationError("DUPLICATE_ID_ACROSS_REGISTRIES")

    return {
        "status": "PASS",
        "registry_versions": {kind: str(bundle[kind].get("version")) for kind in REGISTRY_PATHS},
        "entry_counts": {kind: len(validated[kind]) for kind in REGISTRY_PATHS},
        "logical_sha256": canonical_sha256({kind: bundle[kind] for kind in sorted(REGISTRY_PATHS)}),
        "authority_delta": "AUDIT_CLASSIFICATION_ONLY",
    }


def _reason_index(bundle: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    return {
        entry["name"]: entry["reason_family"]
        for entry in _entries(bundle["REASON_CODE"], "REASON_CODE")
    }


def classify_attempt(
    bundle: Mapping[str, Mapping[str, Any]],
    *,
    status: str,
    reason_code: str | None,
) -> dict[str, Any]:
    if status not in EXPECTED_COMPUTABILITY:
        raise RegistryValidationError(f"UNKNOWN_COMPUTABILITY_STATUS:{status}")
    if status in {"EVALUATED_FIRED", "EVALUATED_NOT_FIRED"}:
        if reason_code is not None:
            raise RegistryValidationError(f"EVALUATED_ATTEMPT_HAS_REASON:{status}:{reason_code}")
        return {"status": status, "reason_code": None, "reason_family": None}
    if reason_code is None:
        raise RegistryValidationError(f"NON_EVALUATED_ATTEMPT_MISSING_REASON:{status}")
    reasons = _reason_index(bundle)
    if reason_code not in reasons:
        raise RegistryValidationError(f"UNKNOWN_REASON_CODE:{reason_code}")
    family = reasons[reason_code]
    expected = STATUS_TO_REASON_FAMILY[status]
    if family not in expected:
        raise RegistryValidationError(f"STATUS_REASON_MISMATCH:{status}:{reason_code}:{family}")
    return {"status": status, "reason_code": reason_code, "reason_family": family}


def validate_amendment(amendment: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "amendment_id",
        "created_at",
        "materiality",
        "prior_registry_version",
        "new_registry_version",
        "changes",
        "rationale",
        "evidence_refs",
        "affected_packets",
        "rerun_required",
        "operator_acknowledgement_required",
        "status",
    }
    missing = sorted(required - set(amendment))
    if missing:
        raise RegistryValidationError(f"AMENDMENT_FIELDS_MISSING:{','.join(missing)}")
    if amendment["prior_registry_version"] == amendment["new_registry_version"]:
        raise RegistryValidationError("AMENDMENT_REUSES_REGISTRY_VERSION")
    changes = amendment["changes"]
    if not isinstance(changes, list) or not changes:
        raise RegistryValidationError("AMENDMENT_CHANGES_EMPTY")
    if not isinstance(amendment["evidence_refs"], list) or not amendment["evidence_refs"]:
        raise RegistryValidationError("AMENDMENT_EVIDENCE_EMPTY")
    material = amendment["materiality"] == "MATERIAL_MEANING_OR_ROUTING"
    if material:
        if amendment["operator_acknowledgement_required"] is not True:
            raise RegistryValidationError("MATERIAL_AMENDMENT_WITHOUT_OPERATOR_ACK")
        if amendment["rerun_required"] is not True:
            raise RegistryValidationError("MATERIAL_AMENDMENT_WITHOUT_RERUN")
        if amendment["status"] not in {"ACKNOWLEDGEMENT_REQUIRED", "APPROVED_FOR_RERUN", "COMPLETED", "REJECTED"}:
            raise RegistryValidationError("MATERIAL_AMENDMENT_STATUS_INVALID")
    return {
        "status": "PASS",
        "amendment_id": amendment["amendment_id"],
        "material": material,
        "logical_sha256": canonical_sha256(dict(amendment)),
    }
