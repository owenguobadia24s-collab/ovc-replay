"""SHSI-WP9 inactive ESL shadow-consumer mappings and comparisons."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping

from .envelopes import EvidenceEntry, EvidenceFrontier


class ESLShadowError(ValueError):
    """A fail-closed ESL shadow-consumer contract violation."""


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value or "latest" in value.casefold():
        raise ESLShadowError(f"{field.upper()}_EXACT_REF_REQUIRED")
    return value


def _refs(values: tuple[str, ...], field: str) -> None:
    if not values or any(not isinstance(value, str) or not value for value in values):
        raise ESLShadowError(f"{field.upper()}_REQUIRED")
    if len(values) != len(set(values)):
        raise ESLShadowError(f"{field.upper()}_DUPLICATE")


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ESLShadowError("NON_CANONICAL_ESL_SHADOW_VALUE") from exc


def _logical_id(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class ESLSharedSystemsConsumptionManifest:
    manifest_id: str
    consumer_programme_id: str
    consumer_generation: str
    current_state_ref: str
    current_state_blob_sha: str
    shared_release_id: str
    surfaces: tuple[str, ...]
    c3_activation_state: str
    current_binding_changed: bool = False
    status: str = "SHADOW_ONLY"
    writes_performed: tuple[str, ...] = ()
    source_expansion: tuple[str, ...] = ()
    semantic_promotions: tuple[str, ...] = ()
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in (
            "manifest_id", "consumer_programme_id", "consumer_generation",
            "current_state_ref", "shared_release_id",
        ):
            _text(getattr(self, field), field)
        if self.consumer_programme_id != "OVC-OPTB-ESL-CONFORMANCE-v0.1":
            raise ESLShadowError("NON_ESL_CONSUMER_FORBIDDEN")
        if len(self.current_state_blob_sha) != 40:
            raise ESLShadowError("ESL_CURRENT_STATE_BLOB_INVALID")
        _refs(self.surfaces, "surfaces")
        if set(self.surfaces) != ESL_SURFACES:
            raise ESLShadowError("ESL_SURFACE_COVERAGE_INCOMPLETE")
        if self.c3_activation_state != "NONE":
            raise ESLShadowError("C3_ACTIVATION_FORBIDDEN")
        if (
            self.current_binding_changed or self.status != "SHADOW_ONLY"
            or self.writes_performed or self.source_expansion or self.semantic_promotions
        ):
            raise ESLShadowError("ESL_WRITE_BINDING_SOURCE_OR_PROMOTION_FORBIDDEN")
        if self.authority_effect != "NONE":
            raise ESLShadowError("ESL_CONSUMPTION_AUTHORITY_EFFECT_FORBIDDEN")


ESL_SURFACES = frozenset({"PROFILE", "EVIDENCE_FRONTIER", "LINEAGE", "INTERFACE", "READ_MODEL"})


@dataclass(frozen=True)
class ESLShadowSurfaceBinding:
    binding_id: str
    surface: str
    source_ref: str
    target_contract_ref: str
    field_mapping: tuple[tuple[str, str], ...] = (("$", "source_record"),)
    declared_loss_fields: tuple[str, ...] = ()
    semantic_inventions: tuple[str, ...] = ()
    active: bool = False
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in ("binding_id", "source_ref", "target_contract_ref"):
            _text(getattr(self, field), field)
        if self.surface not in ESL_SURFACES:
            raise ESLShadowError("ESL_SURFACE_UNKNOWN")
        if self.field_mapping != (("$", "source_record"),):
            raise ESLShadowError("ESL_NON_IDENTITY_MAPPING_FORBIDDEN")
        if self.declared_loss_fields:
            raise ESLShadowError("ESL_UNNECESSARY_LOSS_FORBIDDEN")
        if self.semantic_inventions:
            raise ESLShadowError("ESL_SEMANTIC_FABRICATION")
        if self.active:
            raise ESLShadowError("ESL_ADAPTER_ACTIVATION_FORBIDDEN")
        if self.authority_effect != "NONE":
            raise ESLShadowError("ESL_ADAPTER_AUTHORITY_EFFECT_FORBIDDEN")


def adapt_esl_surface(
    binding: ESLShadowSurfaceBinding, source_record: Mapping[str, Any]
) -> dict[str, Any]:
    source = dict(source_record)
    payload = {
        "binding_id": binding.binding_id,
        "surface": binding.surface,
        "source_record": source,
        "source_logical_sha256": _logical_id(source),
        "declared_loss_fields": [],
        "status": "SHADOW_ONLY",
        "authority_effect": "NONE",
    }
    return {"schema": "ovc-shsi-esl-shadow-surface/v0.1", **payload, "logical_id": _logical_id(payload)}


def unwrap_esl_surface(
    binding: ESLShadowSurfaceBinding, wrapped: Mapping[str, Any]
) -> dict[str, Any]:
    if wrapped.get("binding_id") != binding.binding_id or wrapped.get("status") != "SHADOW_ONLY":
        raise ESLShadowError("ESL_SHADOW_WRAPPER_BINDING_MISMATCH")
    source = wrapped.get("source_record")
    if not isinstance(source, Mapping) or _logical_id(source) != wrapped.get("source_logical_sha256"):
        raise ESLShadowError("ESL_SHADOW_SOURCE_IDENTITY_MISMATCH")
    return dict(source)


@dataclass(frozen=True)
class ESLEvidenceFrontierMapping:
    mapping_id: str
    shared_frontier: EvidenceFrontier
    dependency_roles: tuple[tuple[str, str], ...]
    required_missing_refs: tuple[str, ...]
    optional_missing_refs: tuple[str, ...]
    declared_loss_fields: tuple[str, ...]
    base_structural_status: str
    status: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        expected = "NOT_EVALUABLE" if self.required_missing_refs else "READY"
        if self.status != expected:
            raise ESLShadowError("ESL_FRONTIER_MAPPING_STATUS_INCONSISTENT")
        if self.optional_missing_refs and not self.required_missing_refs:
            if self.base_structural_status != "LAWFUL_BASE_PRESERVED":
                raise ESLShadowError("OPTIONAL_MISSING_POISONED_BASE")
        if self.declared_loss_fields:
            raise ESLShadowError("ESL_FRONTIER_MAPPING_LOSS_FORBIDDEN")
        if self.authority_effect != "NONE":
            raise ESLShadowError("ESL_FRONTIER_MAPPING_AUTHORITY_EFFECT_FORBIDDEN")


def map_esl_evidence_frontier(
    mapping_id: str, occurrence: Mapping[str, Any]
) -> ESLEvidenceFrontierMapping:
    raw_frontier = occurrence.get("evidence_frontier")
    raw_dependencies = occurrence.get("dependency_refs")
    if not isinstance(raw_frontier, Mapping) or not isinstance(raw_dependencies, list):
        raise ESLShadowError("ESL_FRONTIER_SOURCE_INVALID")
    dependencies: dict[str, Mapping[str, Any]] = {}
    for row in raw_dependencies:
        if not isinstance(row, Mapping) or not isinstance(row.get("ref_id"), str):
            raise ESLShadowError("ESL_DEPENDENCY_INVALID")
        if row["ref_id"] in dependencies:
            raise ESLShadowError("ESL_DEPENDENCY_AMBIGUOUS")
        dependencies[row["ref_id"]] = row
    roles = tuple(sorted((ref, str(row.get("role", ""))) for ref, row in dependencies.items()))
    required_missing = tuple(sorted(
        ref for ref, row in dependencies.items()
        if row.get("role") in {"REQUIRED", "CONDITIONAL_REQUIRED"}
        and row.get("evidence_state") != "AVAILABLE"
    ))
    optional_missing = tuple(sorted(
        ref for ref, row in dependencies.items()
        if row.get("role") not in {"REQUIRED", "CONDITIONAL_REQUIRED"}
        and row.get("evidence_state") != "AVAILABLE"
    ))
    entries = []
    for ref, row in sorted(dependencies.items()):
        if row.get("evidence_state") != "AVAILABLE":
            continue
        if not row.get("first_valid_time") or not row.get("generation_id"):
            raise ESLShadowError(f"ESL_AVAILABLE_DEPENDENCY_INCOMPLETE:{ref}")
        entries.append(EvidenceEntry(ref, ref, row["first_valid_time"], row["generation_id"]))
    latest = raw_frontier.get("latest_required_fvt")
    available_required = {
        ref for ref, row in dependencies.items()
        if row.get("role") in {"REQUIRED", "CONDITIONAL_REQUIRED"}
        and row.get("evidence_state") == "AVAILABLE"
    }
    if not available_required:
        latest = None
    missing = tuple(sorted((*required_missing, *optional_missing)))
    reasons = tuple(
        code for condition, code in (
            (bool(required_missing), "REQUIRED_DEPENDENCY_MISSING"),
            (bool(optional_missing), "OPTIONAL_DEPENDENCY_MISSING"),
        ) if condition
    )
    frontier = EvidenceFrontier(
        f"{mapping_id}.FRONTIER", "ovc-shsi-esl-frontier/v0.1", "ESL",
        str(raw_frontier.get("evaluation_cutoff", "")), f"{mapping_id}.DEPENDENCIES",
        tuple(entries), missing, latest,
        tuple(sorted(str(value) for value in raw_frontier.get("source_generation_ids", ()))),
        reasons, raw_frontier.get("comparability_domain_id"),
    )
    return ESLEvidenceFrontierMapping(
        mapping_id, frontier, roles, required_missing, optional_missing, (),
        "NOT_EVALUABLE" if required_missing else "LAWFUL_BASE_PRESERVED",
        "NOT_EVALUABLE" if required_missing else "READY",
    )


@dataclass(frozen=True)
class ESLReferenceComparison:
    comparison_id: str
    source_ref: str
    reference_logical_sha256: str
    shadow_logical_sha256: str
    status: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        expected = "PASS" if self.reference_logical_sha256 == self.shadow_logical_sha256 else "BLOCK"
        if self.status != expected:
            raise ESLShadowError("ESL_REFERENCE_STATUS_INCONSISTENT")
        if self.authority_effect != "NONE":
            raise ESLShadowError("ESL_REFERENCE_AUTHORITY_EFFECT_FORBIDDEN")


def compare_esl_reference(
    comparison_id: str, source_ref: str,
    reference: Mapping[str, Any], shadow: Mapping[str, Any],
) -> ESLReferenceComparison:
    reference_id, shadow_id = _logical_id(reference), _logical_id(shadow)
    return ESLReferenceComparison(
        comparison_id, source_ref, reference_id, shadow_id,
        "PASS" if reference_id == shadow_id else "BLOCK",
    )


@dataclass(frozen=True)
class ESLAdapterComplexityLedger:
    ledger_id: str
    binding_refs: tuple[str, ...]
    active_adapter_count: int
    adapter_code_surface_lines: int
    adapter_mapping_count: int
    artifact_byte_delta: int
    status: str
    exceeded_dimensions: tuple[str, ...]
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        if self.status != ("PASS" if not self.exceeded_dimensions else "BLOCK"):
            raise ESLShadowError("ESL_ADAPTER_BUDGET_STATUS_INCONSISTENT")
        if self.authority_effect != "NONE":
            raise ESLShadowError("ESL_ADAPTER_LEDGER_AUTHORITY_EFFECT_FORBIDDEN")


def evaluate_esl_adapter_complexity(
    ledger_id: str, bindings: Iterable[ESLShadowSurfaceBinding], *,
    budget: Mapping[str, Any], code_surface_lines: int, artifact_byte_delta: int,
) -> ESLAdapterComplexityLedger:
    rows = tuple(bindings)
    if set(row.surface for row in rows) != ESL_SURFACES:
        raise ESLShadowError("ESL_SURFACE_COVERAGE_INCOMPLETE")
    caps = {row[0]: float(row[1]) for row in budget.get("numeric_caps", ())}
    observed = {
        "ACTIVE_ADAPTER_COUNT": sum(int(row.active) for row in rows),
        "ADAPTER_CODE_SURFACE_LINES": code_surface_lines,
        "ADAPTER_MAPPING_COUNT": max(len(row.field_mapping) for row in rows),
        "ARTIFACT_BYTE_DELTA_BYTES": artifact_byte_delta,
    }
    missing = sorted(set(observed) - set(caps))
    if missing:
        raise ESLShadowError(f"PILOT_BUDGET_CAP_MISSING:{','.join(missing)}")
    exceeded = tuple(sorted(key for key, value in observed.items() if value > caps[key]))
    return ESLAdapterComplexityLedger(
        ledger_id, tuple(sorted(row.binding_id for row in rows)),
        observed["ACTIVE_ADAPTER_COUNT"], code_surface_lines,
        observed["ADAPTER_MAPPING_COUNT"], artifact_byte_delta,
        "BLOCK" if exceeded else "PASS", exceeded,
    )
