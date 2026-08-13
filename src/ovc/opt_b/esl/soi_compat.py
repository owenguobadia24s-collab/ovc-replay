from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ovc.opt_b.sfc.serialization import logical_hash as sfc_logical_hash

from .canonical import sha256_canonical


class SOICompatibilityError(ValueError):
    """Raised when a requested SOI view cannot be formed lawfully."""


TOPOLOGY_IDS = (
    "FAMILY",
    "HIERARCHY",
    "OVERLAP",
    "GRAPH",
    "CONTINUUM",
    "COMPOSITION",
)
TOPOLOGY_MATURITIES = frozenset({"INTERFACE_ONLY", "EXECUTABLE_INACTIVE"})
FAMILY_EVIDENCE_STATUSES = frozenset(
    {
        "FAMILY_EVIDENCE_PRESENT",
        "METHOD_DEPENDENT_STRUCTURE_ONLY",
        "NO_STABLE_FAMILY",
        "NOT_EVALUABLE",
        "UNRESOLVED",
        "QUARANTINED",
    }
)
ASSIGNMENT_STATUSES = frozenset(
    {
        "MEMBER",
        "RESIDUAL",
        "NOISE",
        "SINGLETON",
        "AMBIGUOUS",
        "NOT_COMPARABLE",
        "NOT_EVALUABLE",
        "QUARANTINED",
    }
)

_FAMILY_ADAPTER_ID = "ESLI.SOI.FAMILY.FDI_COMPAT.v0.1"
_FAMILY_SOURCE_PROGRAMME = "OVC-SFC-v0.1"
_FAMILY_SOURCE_RESULT_TYPE = "SFC.FamilyCatalog.v0.1"
_REQUIRED_CATALOG_FIELDS = frozenset(
    {
        "family_catalog_id",
        "source_population_id",
        "representation_pack_id",
        "comparison_spec_id",
        "family_method_id",
        "configuration_id",
        "families",
        "assignment_records",
        "residual_ids",
        "noise_ids",
        "singleton_ids",
        "denominator_eligible",
        "denominator_assigned",
        "denominator_residual_noise",
        "evidence_status",
        "first_valid_time",
        "evaluation_cutoff",
        "authority_state",
        "logical_hash",
    }
)
_REQUIRED_FAMILY_FIELDS = frozenset(
    {
        "family_id",
        "family_catalog_id",
        "member_ids",
        "support_count",
        "prototype_descriptor",
        "within_family_evidence",
        "dispersion_evidence",
        "exemplar_ids",
        "counterexample_ids",
        "first_valid_time",
        "evaluation_cutoff",
        "authority_state",
        "logical_hash",
    }
)
_REQUIRED_ASSIGNMENT_FIELDS = frozenset(
    {
        "occurrence_id",
        "catalog_id",
        "status",
        "family_ids",
        "reason_codes",
        "first_valid_time",
        "evaluation_cutoff",
        "logical_hash",
    }
)
_PROHIBITED_KEYS = frozenset(
    {
        "future_return",
        "expected_return",
        "mfe",
        "mae",
        "outcome",
        "outcomes",
        "validation_label",
        "validation_result",
        "forecast",
        "probability",
        "risk",
        "exposure",
        "trade",
        "trading",
        "execution",
        "setup_eligibility",
        "semantic_term",
        "semantic_label",
        "mechanism",
        "cause",
        "causal_claim",
        "intent",
        "admitted_active",
        "canonical_family",
        "production_selector",
    }
)


@dataclass(frozen=True)
class SOITopologyEntry:
    topology_id: str
    maturity: str
    adapter_id: str | None
    source_programme_id: str | None
    source_result_type: str | None
    reason_code: str | None
    authority_state: str = "INACTIVE_CONFORMANCE_ONLY"

    def __post_init__(self) -> None:
        if self.topology_id not in TOPOLOGY_IDS:
            raise SOICompatibilityError("SOI_TOPOLOGY_UNKNOWN:" + self.topology_id)
        if self.maturity not in TOPOLOGY_MATURITIES:
            raise SOICompatibilityError("SOI_TOPOLOGY_MATURITY_INVALID:" + self.topology_id)
        if self.authority_state != "INACTIVE_CONFORMANCE_ONLY":
            raise SOICompatibilityError("SOI_TOPOLOGY_AUTHORITY_NOT_INACTIVE:" + self.topology_id)
        if self.maturity == "EXECUTABLE_INACTIVE":
            if self.topology_id != "FAMILY":
                raise SOICompatibilityError("SOI_EXECUTABLE_TOPOLOGY_NOT_AUTHORISED:" + self.topology_id)
            if self.adapter_id != _FAMILY_ADAPTER_ID:
                raise SOICompatibilityError("SOI_FAMILY_ADAPTER_ID_INVALID")
            if self.source_programme_id != _FAMILY_SOURCE_PROGRAMME:
                raise SOICompatibilityError("SOI_FAMILY_SOURCE_PROGRAMME_INVALID")
            if self.source_result_type != _FAMILY_SOURCE_RESULT_TYPE:
                raise SOICompatibilityError("SOI_FAMILY_SOURCE_RESULT_TYPE_INVALID")
            if self.reason_code is not None:
                raise SOICompatibilityError("SOI_EXECUTABLE_TOPOLOGY_REASON_CODE_FORBIDDEN")
        else:
            if self.adapter_id is not None or self.source_programme_id is not None or self.source_result_type is not None:
                raise SOICompatibilityError("SOI_INTERFACE_ONLY_ADAPTER_MUST_BE_ABSENT:" + self.topology_id)
            if self.reason_code != "SOI_ADAPTER_NOT_MATERIALIZED":
                raise SOICompatibilityError("SOI_INTERFACE_ONLY_REASON_REQUIRED:" + self.topology_id)


@dataclass(frozen=True)
class SOIFamilyAdapterBinding:
    adapter_id: str
    topology_id: str
    source_programme_id: str
    source_programme_disposition: str
    source_result_type: str
    source_schema: str
    source_implementation: str
    output_schema: str
    authority_state: str

    def __post_init__(self) -> None:
        if self.adapter_id != _FAMILY_ADAPTER_ID:
            raise SOICompatibilityError("SOI_FAMILY_ADAPTER_ID_INVALID")
        if self.topology_id != "FAMILY":
            raise SOICompatibilityError("SOI_FAMILY_TOPOLOGY_BINDING_INVALID")
        if self.source_programme_id != _FAMILY_SOURCE_PROGRAMME:
            raise SOICompatibilityError("SOI_FAMILY_SOURCE_PROGRAMME_INVALID")
        if self.source_programme_disposition != "COMPLETED_PRESERVED":
            raise SOICompatibilityError("SOI_FAMILY_SOURCE_NOT_COMPLETED_PRESERVED")
        if self.source_result_type != _FAMILY_SOURCE_RESULT_TYPE:
            raise SOICompatibilityError("SOI_FAMILY_SOURCE_RESULT_TYPE_INVALID")
        if not self.source_schema or not self.source_implementation or not self.output_schema:
            raise SOICompatibilityError("SOI_FAMILY_SOURCE_BINDING_INCOMPLETE")
        if self.authority_state != "INACTIVE_CONFORMANCE_ONLY":
            raise SOICompatibilityError("SOI_FAMILY_ADAPTER_AUTHORITY_NOT_INACTIVE")


def _copy_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _copy_json(child) for key, child in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_copy_json(child) for child in value]
    return copy.deepcopy(value)


def _scan_prohibited(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if key_text.lower() in _PROHIBITED_KEYS:
                raise SOICompatibilityError(f"SOI_FORBIDDEN_FIELD:{path}.{key_text}")
            _scan_prohibited(child, f"{path}.{key_text}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _scan_prohibited(child, f"{path}[{index}]")


def _assert_exact_fields(record: Mapping[str, Any], expected: frozenset[str], code: str) -> None:
    actual = set(record)
    if actual != expected:
        missing = ",".join(sorted(expected - actual))
        extra = ",".join(sorted(actual - expected))
        raise SOICompatibilityError(f"{code}:missing={missing}:extra={extra}")


def _assert_source_hash(record: Mapping[str, Any], code: str) -> None:
    expected_hash = str(record.get("logical_hash") or "")
    if not expected_hash:
        raise SOICompatibilityError(code + ":LOGICAL_HASH_REQUIRED")
    payload = dict(record)
    payload.pop("logical_hash", None)
    if sfc_logical_hash(payload) != expected_hash:
        raise SOICompatibilityError(code + ":LOGICAL_HASH_MISMATCH")


def topology_registry_from_mapping(registry: Mapping[str, Any]) -> dict[str, SOITopologyEntry]:
    raw = _copy_json(registry)
    if not isinstance(raw, Mapping):
        raise SOICompatibilityError("SOI_TOPOLOGY_REGISTRY_OBJECT_REQUIRED")
    if raw.get("authority_effect") != "NONE":
        raise SOICompatibilityError("SOI_TOPOLOGY_REGISTRY_AUTHORITY_EFFECT_FORBIDDEN")
    if raw.get("canonical_topology") != "NONE":
        raise SOICompatibilityError("SOI_CANONICAL_TOPOLOGY_FORBIDDEN")
    if raw.get("topology_activation") != "NONE":
        raise SOICompatibilityError("SOI_TOPOLOGY_ACTIVATION_FORBIDDEN")
    if raw.get("scientific_selection") != "NONE":
        raise SOICompatibilityError("SOI_SCIENTIFIC_SELECTION_FORBIDDEN")
    rows = raw.get("entries")
    if not isinstance(rows, list):
        raise SOICompatibilityError("SOI_TOPOLOGY_REGISTRY_ENTRIES_REQUIRED")

    entries: dict[str, SOITopologyEntry] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise SOICompatibilityError("SOI_TOPOLOGY_REGISTRY_ROW_OBJECT_REQUIRED")
        entry = SOITopologyEntry(
            topology_id=str(row.get("topology_id") or ""),
            maturity=str(row.get("maturity") or ""),
            adapter_id=row.get("adapter_id"),
            source_programme_id=row.get("source_programme_id"),
            source_result_type=row.get("source_result_type"),
            reason_code=row.get("reason_code"),
            authority_state=str(row.get("authority_state") or ""),
        )
        if entry.topology_id in entries:
            raise SOICompatibilityError("SOI_TOPOLOGY_DUPLICATE:" + entry.topology_id)
        entries[entry.topology_id] = entry
    if set(entries) != set(TOPOLOGY_IDS):
        raise SOICompatibilityError("SOI_TOPOLOGY_REGISTRY_INCOMPLETE")
    return entries


def family_binding_from_mapping(manifest: Mapping[str, Any]) -> SOIFamilyAdapterBinding:
    raw = _copy_json(manifest)
    if not isinstance(raw, Mapping):
        raise SOICompatibilityError("SOI_FAMILY_MANIFEST_OBJECT_REQUIRED")
    authority = raw.get("authority")
    if not isinstance(authority, Mapping):
        raise SOICompatibilityError("SOI_FAMILY_MANIFEST_AUTHORITY_REQUIRED")
    if authority.get("authority_effect") != "NONE":
        raise SOICompatibilityError("SOI_FAMILY_MANIFEST_AUTHORITY_EFFECT_FORBIDDEN")
    for field in (
        "topology_activation",
        "family_promotion",
        "method_selection",
        "scientific_support_disposition",
        "semantic_promotion",
        "publication",
    ):
        if authority.get(field) != "NONE":
            raise SOICompatibilityError("SOI_FAMILY_MANIFEST_RESERVED_AUTHORITY_FORBIDDEN:" + field)
    if authority.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise SOICompatibilityError("SOI_FAMILY_MANIFEST_VALIDATION_BOUNDARY_INVALID")
    return SOIFamilyAdapterBinding(
        adapter_id=str(raw.get("adapter_id") or ""),
        topology_id=str(raw.get("topology_id") or ""),
        source_programme_id=str(raw.get("source_programme_id") or ""),
        source_programme_disposition=str(raw.get("source_programme_disposition") or ""),
        source_result_type=str(raw.get("source_result_type") or ""),
        source_schema=str(raw.get("source_schema") or ""),
        source_implementation=str(raw.get("source_implementation") or ""),
        output_schema=str(raw.get("output_schema") or ""),
        authority_state=str(raw.get("authority_state") or ""),
    )


def _normalise_family_record(record: Mapping[str, Any], catalog_id: str) -> dict[str, Any]:
    row = _copy_json(record)
    if not isinstance(row, Mapping):
        raise SOICompatibilityError("SOI_FAMILY_RECORD_OBJECT_REQUIRED")
    _assert_exact_fields(row, _REQUIRED_FAMILY_FIELDS, "SOI_FAMILY_RECORD_SCHEMA_INVALID")
    _assert_source_hash(row, "SOI_FAMILY_RECORD")
    if row["family_catalog_id"] != catalog_id:
        raise SOICompatibilityError("SOI_FAMILY_RECORD_CATALOG_MISMATCH")
    if row["authority_state"] != "INACTIVE_CONFORMANCE_ONLY":
        raise SOICompatibilityError("SOI_FAMILY_RECORD_AUTHORITY_NOT_INACTIVE")
    member_ids = [str(value) for value in row["member_ids"]]
    if len(member_ids) != len(set(member_ids)):
        raise SOICompatibilityError("SOI_FAMILY_MEMBER_DUPLICATE")
    if int(row["support_count"]) != len(member_ids):
        raise SOICompatibilityError("SOI_FAMILY_SUPPORT_COUNT_MISMATCH")
    row["member_ids"] = sorted(member_ids)
    row["exemplar_ids"] = sorted(str(value) for value in row["exemplar_ids"])
    row["counterexample_ids"] = sorted(str(value) for value in row["counterexample_ids"])
    return dict(row)


def _normalise_assignment(record: Mapping[str, Any], catalog_id: str, valid_family_ids: set[str]) -> dict[str, Any]:
    row = _copy_json(record)
    if not isinstance(row, Mapping):
        raise SOICompatibilityError("SOI_ASSIGNMENT_OBJECT_REQUIRED")
    _assert_exact_fields(row, _REQUIRED_ASSIGNMENT_FIELDS, "SOI_ASSIGNMENT_SCHEMA_INVALID")
    _assert_source_hash(row, "SOI_ASSIGNMENT")
    if row["catalog_id"] != catalog_id:
        raise SOICompatibilityError("SOI_ASSIGNMENT_CATALOG_MISMATCH")
    status = str(row["status"])
    if status not in ASSIGNMENT_STATUSES:
        raise SOICompatibilityError("SOI_ASSIGNMENT_STATUS_INVALID:" + status)
    family_ids = sorted(set(str(value) for value in row["family_ids"]))
    if any(family_id not in valid_family_ids for family_id in family_ids):
        raise SOICompatibilityError("SOI_ASSIGNMENT_UNKNOWN_FAMILY")
    if status == "MEMBER" and len(family_ids) != 1:
        raise SOICompatibilityError("SOI_MEMBER_REQUIRES_ONE_FAMILY")
    if status == "AMBIGUOUS" and len(family_ids) < 2:
        raise SOICompatibilityError("SOI_AMBIGUOUS_REQUIRES_MULTIPLE_FAMILIES")
    if status not in {"MEMBER", "AMBIGUOUS"} and family_ids:
        raise SOICompatibilityError("SOI_NONMEMBER_FAMILY_IDS_FORBIDDEN")
    row["family_ids"] = family_ids
    row["reason_codes"] = sorted(set(str(value) for value in row["reason_codes"]))
    return dict(row)


def adapt_family_catalog(
    catalog: Mapping[str, Any],
    *,
    adapter_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Project one exact preserved SFC FamilyCatalog into an inactive SOI.FAMILY view.

    This function performs no clustering, family discovery, thresholding, representation
    selection, method selection, scientific support decision or semantic admission.
    """
    binding = family_binding_from_mapping(adapter_manifest)
    source = _copy_json(catalog)
    if not isinstance(source, Mapping):
        raise SOICompatibilityError("SOI_FAMILY_CATALOG_OBJECT_REQUIRED")
    _scan_prohibited(source)
    _assert_exact_fields(source, _REQUIRED_CATALOG_FIELDS, "SOI_FAMILY_CATALOG_SCHEMA_INVALID")
    _assert_source_hash(source, "SOI_FAMILY_CATALOG")
    if source["authority_state"] != "INACTIVE_CONFORMANCE_ONLY":
        raise SOICompatibilityError("SOI_FAMILY_CATALOG_AUTHORITY_NOT_INACTIVE")
    evidence_status = str(source["evidence_status"])
    if evidence_status not in FAMILY_EVIDENCE_STATUSES:
        raise SOICompatibilityError("SOI_FAMILY_EVIDENCE_STATUS_INVALID:" + evidence_status)

    catalog_id = str(source["family_catalog_id"])
    if not catalog_id:
        raise SOICompatibilityError("SOI_FAMILY_CATALOG_ID_REQUIRED")
    if not str(source["source_population_id"]):
        raise SOICompatibilityError("SOI_SOURCE_POPULATION_ID_REQUIRED")
    if not str(source["representation_pack_id"]) or not str(source["comparison_spec_id"]):
        raise SOICompatibilityError("SOI_REPRESENTATION_COMPARISON_BINDING_REQUIRED")
    if not str(source["family_method_id"]) or not str(source["configuration_id"]):
        raise SOICompatibilityError("SOI_SOURCE_METHOD_BINDING_REQUIRED")
    if not str(source["first_valid_time"]) or not str(source["evaluation_cutoff"]):
        raise SOICompatibilityError("SOI_CHRONOLOGY_REQUIRED")

    families_raw = source["families"]
    assignments_raw = source["assignment_records"]
    if not isinstance(families_raw, list) or not isinstance(assignments_raw, list):
        raise SOICompatibilityError("SOI_FAMILY_CATALOG_COLLECTIONS_REQUIRED")
    families = sorted(
        (_normalise_family_record(record, catalog_id) for record in families_raw),
        key=lambda row: row["family_id"],
    )
    valid_family_ids = {str(row["family_id"]) for row in families}
    assignments = sorted(
        (_normalise_assignment(record, catalog_id, valid_family_ids) for record in assignments_raw),
        key=lambda row: row["occurrence_id"],
    )
    assignment_ids = [str(row["occurrence_id"]) for row in assignments]
    if len(assignment_ids) != len(set(assignment_ids)):
        raise SOICompatibilityError("SOI_ASSIGNMENT_OCCURRENCE_DUPLICATE")

    denominators = {
        "eligible": int(source["denominator_eligible"]),
        "assigned": int(source["denominator_assigned"]),
        "residual_noise_singleton": int(source["denominator_residual_noise"]),
    }
    if any(value < 0 for value in denominators.values()):
        raise SOICompatibilityError("SOI_NEGATIVE_DENOMINATOR")
    if denominators["assigned"] > denominators["eligible"]:
        raise SOICompatibilityError("SOI_ASSIGNED_DENOMINATOR_EXCEEDS_ELIGIBLE")
    if denominators["residual_noise_singleton"] > denominators["eligible"]:
        raise SOICompatibilityError("SOI_RESIDUAL_DENOMINATOR_EXCEEDS_ELIGIBLE")

    residual_ids = sorted(set(str(value) for value in source["residual_ids"]))
    noise_ids = sorted(set(str(value) for value in source["noise_ids"]))
    singleton_ids = sorted(set(str(value) for value in source["singleton_ids"]))
    if not set(noise_ids).issubset(residual_ids) or not set(singleton_ids).issubset(residual_ids):
        raise SOICompatibilityError("SOI_RESIDUAL_SUBSET_INVARIANT_FAILED")

    if evidence_status == "NO_STABLE_FAMILY" and families:
        raise SOICompatibilityError("SOI_NO_STABLE_FAMILY_WITH_FAMILIES")
    if evidence_status == "FAMILY_EVIDENCE_PRESENT" and not families:
        raise SOICompatibilityError("SOI_FAMILY_EVIDENCE_PRESENT_WITHOUT_FAMILIES")

    payload = {
        "schema": "ovc-esl-soi-view-result/v1",
        "topology": {
            "topology_id": "FAMILY",
            "maturity": "EXECUTABLE_INACTIVE",
            "adapter_id": binding.adapter_id,
        },
        "method": {
            "adapter_method_id": binding.adapter_id,
            "source_family_method_id": str(source["family_method_id"]),
            "source_configuration_id": str(source["configuration_id"]),
            "source_comparison_spec_id": str(source["comparison_spec_id"]),
            "topology_id": "FAMILY",
            "method_topology_separation": "EXPLICIT",
            "scientific_selection": "NONE",
        },
        "source_binding": {
            "source_programme_id": binding.source_programme_id,
            "source_programme_disposition": binding.source_programme_disposition,
            "source_result_type": binding.source_result_type,
            "source_result_id": catalog_id,
            "source_logical_hash": str(source["logical_hash"]),
            "source_population_id": str(source["source_population_id"]),
            "representation_pack_id": str(source["representation_pack_id"]),
            "comparison_spec_id": str(source["comparison_spec_id"]),
        },
        "topology_result": {
            "evidence_status": evidence_status,
            "families": families,
            "assignments": assignments,
            "residual_ids": residual_ids,
            "noise_ids": noise_ids,
            "singleton_ids": singleton_ids,
            "denominators": denominators,
        },
        "chronology": {
            "first_valid_time": str(source["first_valid_time"]),
            "evaluation_cutoff": str(source["evaluation_cutoff"]),
        },
        "epistemic_boundary": {
            "result_class": "RAW_ORGANISATION_VIEW_RESULT",
            "scientific_support_disposition": "NOT_PERFORMED_WP7_OWNED",
            "organisation_evidence_set": "NOT_MATERIALIZED_WP7_OWNED",
            "no_stable_family_scope": (
                "FAMILY_TOPOLOGY_ONLY" if evidence_status == "NO_STABLE_FAMILY" else "NOT_APPLICABLE"
            ),
            "organisation_absence_inference": "FORBIDDEN",
            "family_assignment_is_ontology": "FORBIDDEN",
        },
        "authority": {
            "authority_state": binding.authority_state,
            "authority_effect": "NONE",
            "topology_activation": "NONE",
            "family_promotion": "NONE",
            "method_selection": "NONE",
            "scientific_support_disposition": "NONE",
            "semantic_promotion": "NONE",
            "validation_consumption": "LOCKED_UNCONSUMED",
            "publication": "NONE",
            "probability_risk_exposure_execution": "NONE",
        },
    }
    identity_hash = sha256_canonical(payload)
    return {
        **payload,
        "soi_view_result_id": "soi1:" + identity_hash,
        "logical_hash": identity_hash,
    }


def invoke_soi_topology(
    topology_id: str,
    *,
    topology_registry: Mapping[str, Any],
    adapter_manifest: Mapping[str, Any] | None = None,
    source_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    entries = topology_registry_from_mapping(topology_registry)
    topology = str(topology_id)
    if topology not in entries:
        raise SOICompatibilityError("SOI_TOPOLOGY_UNKNOWN:" + topology)
    entry = entries[topology]
    if entry.maturity == "INTERFACE_ONLY":
        raise SOICompatibilityError("SOI_ADAPTER_NOT_MATERIALIZED:" + topology)
    if topology != "FAMILY":
        raise SOICompatibilityError("SOI_EXECUTABLE_TOPOLOGY_NOT_AUTHORISED:" + topology)
    if adapter_manifest is None or source_result is None:
        raise SOICompatibilityError("SOI_FAMILY_ADAPTER_INPUTS_REQUIRED")
    return adapt_family_catalog(source_result, adapter_manifest=adapter_manifest)
