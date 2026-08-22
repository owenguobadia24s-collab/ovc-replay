"""SHSI-WP7 zero-write DSAI shadow-consumer wrappers and comparisons."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping


class DSAIShadowError(ValueError):
    """A fail-closed DSAI shadow-consumer contract violation."""


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value or "latest" in value.casefold():
        raise DSAIShadowError(f"{field.upper()}_EXACT_REF_REQUIRED")
    return value


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DSAIShadowError("NON_CANONICAL_DSAI_SHADOW_VALUE") from exc


def _logical_id(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class DSAISharedSystemsConsumptionManifest:
    manifest_id: str
    consumer_programme_id: str
    consumer_generation: str
    shared_service_id: str
    shared_release_id: str
    capability_ids: tuple[str, ...]
    current_state_path: str
    current_state_blob_sha: str
    status: str = "SHADOW_ONLY"
    current_binding_changed: bool = False
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in (
            "manifest_id", "consumer_programme_id", "consumer_generation",
            "shared_service_id", "shared_release_id", "current_state_path",
        ):
            _text(getattr(self, field), field)
        if self.consumer_programme_id != "OVC-DSAI-v0.1":
            raise DSAIShadowError("NON_DSAI_CONSUMER_FORBIDDEN")
        if not self.capability_ids or len(self.capability_ids) != len(set(self.capability_ids)):
            raise DSAIShadowError("DSAI_CAPABILITY_SET_INVALID")
        if len(self.current_state_blob_sha) != 40:
            raise DSAIShadowError("DSAI_CURRENT_STATE_BLOB_INVALID")
        if self.status != "SHADOW_ONLY" or self.current_binding_changed:
            raise DSAIShadowError("DSAI_CURRENT_BINDING_CHANGE_FORBIDDEN")
        if self.authority_effect != "NONE":
            raise DSAIShadowError("DSAI_CONSUMPTION_AUTHORITY_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class DSAIShadowExecutionContext:
    context_id: str
    consumption_manifest_ref: str
    shared_resolution_manifest_ref: str
    dsai_current_state_ref: str
    source_blob_refs: tuple[str, ...]
    status: str = "SHADOW_ONLY"
    writes_performed: tuple[str, ...] = ()
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in (
            "context_id", "consumption_manifest_ref", "shared_resolution_manifest_ref",
            "dsai_current_state_ref",
        ):
            _text(getattr(self, field), field)
        if not self.source_blob_refs or any(len(item) != 40 for item in self.source_blob_refs):
            raise DSAIShadowError("DSAI_SHADOW_SOURCE_BLOBS_INVALID")
        if self.status != "SHADOW_ONLY" or self.writes_performed:
            raise DSAIShadowError("DSAI_SHADOW_WRITE_OR_ACTIVATION_FORBIDDEN")
        if self.authority_effect != "NONE":
            raise DSAIShadowError("DSAI_SHADOW_CONTEXT_AUTHORITY_EFFECT_FORBIDDEN")


DSAI_SURFACES = frozenset({"ENVIRONMENT", "RUN", "ASSURANCE", "RECEIPT", "CURRENTNESS"})


@dataclass(frozen=True)
class DSAISurfaceAdapterBinding:
    binding_id: str
    surface: str
    source_schema: str
    target_contract_ref: str
    field_mapping: tuple[tuple[str, str], ...] = (("$", "source_record"),)
    semantic_inventions: tuple[str, ...] = ()
    active: bool = False
    status: str = "SHADOW_ONLY"
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in ("binding_id", "source_schema", "target_contract_ref"):
            _text(getattr(self, field), field)
        if self.surface not in DSAI_SURFACES:
            raise DSAIShadowError("DSAI_ADAPTER_SURFACE_UNKNOWN")
        if self.field_mapping != (("$", "source_record"),):
            raise DSAIShadowError("DSAI_ADAPTER_NON_IDENTITY_MAPPING_FORBIDDEN")
        if self.semantic_inventions:
            raise DSAIShadowError("DSAI_ADAPTER_SEMANTIC_FABRICATION")
        if self.active or self.status != "SHADOW_ONLY":
            raise DSAIShadowError("DSAI_ADAPTER_ACTIVATION_FORBIDDEN")
        if self.authority_effect != "NONE":
            raise DSAIShadowError("DSAI_ADAPTER_AUTHORITY_EFFECT_FORBIDDEN")


def adapt_dsai_surface(
    binding: DSAISurfaceAdapterBinding, source_record: Mapping[str, Any]
) -> dict[str, Any]:
    if source_record.get("schema") != binding.source_schema:
        raise DSAIShadowError("DSAI_ADAPTER_SOURCE_SCHEMA_MISMATCH")
    source = dict(source_record)
    payload = {
        "binding_id": binding.binding_id,
        "surface": binding.surface,
        "source_schema": binding.source_schema,
        "target_contract_ref": binding.target_contract_ref,
        "source_record": source,
        "source_logical_sha256": _logical_id(source),
        "status": "SHADOW_ONLY",
        "writes_performed": [],
        "authority_effect": "NONE",
    }
    return {"schema": "ovc-shsi-dsai-shadow-surface/v0.1", **payload, "logical_id": _logical_id(payload)}


def unwrap_dsai_surface(binding: DSAISurfaceAdapterBinding, wrapped: Mapping[str, Any]) -> dict[str, Any]:
    if wrapped.get("binding_id") != binding.binding_id or wrapped.get("status") != "SHADOW_ONLY":
        raise DSAIShadowError("DSAI_SHADOW_WRAPPER_BINDING_MISMATCH")
    source = wrapped.get("source_record")
    if not isinstance(source, Mapping) or _logical_id(source) != wrapped.get("source_logical_sha256"):
        raise DSAIShadowError("DSAI_SHADOW_SOURCE_IDENTITY_MISMATCH")
    return dict(source)


def _resolve_path(value: Mapping[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise DSAIShadowError(f"MANDATORY_SEMANTIC_PATH_MISSING:{path}")
        current = current[part]
    return current


@dataclass(frozen=True)
class DSAIDualRunComparison:
    comparison_id: str
    source_ref: str
    reference_logical_sha256: str
    shadow_logical_sha256: str
    mandatory_semantic_paths: tuple[str, ...]
    divergent_paths: tuple[str, ...]
    expected_divergence_paths: tuple[str, ...]
    status: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        if set(self.expected_divergence_paths) & set(self.mandatory_semantic_paths):
            raise DSAIShadowError("EXPECTED_MANDATORY_DIVERGENCE_FORBIDDEN")
        expected_status = "PASS" if not self.divergent_paths else "BLOCK"
        if self.status != expected_status:
            raise DSAIShadowError("DSAI_DUAL_RUN_STATUS_INCONSISTENT")
        if self.authority_effect != "NONE":
            raise DSAIShadowError("DSAI_DUAL_RUN_AUTHORITY_EFFECT_FORBIDDEN")


def compare_dsai_dual_run(
    comparison_id: str,
    source_ref: str,
    reference: Mapping[str, Any],
    shadow: Mapping[str, Any],
    *,
    mandatory_semantic_paths: Iterable[str],
    expected_divergence_paths: Iterable[str] = (),
) -> DSAIDualRunComparison:
    mandatory = tuple(sorted(set(mandatory_semantic_paths)))
    expected = tuple(sorted(set(expected_divergence_paths)))
    divergent = tuple(
        path for path in mandatory if _resolve_path(reference, path) != _resolve_path(shadow, path)
    )
    return DSAIDualRunComparison(
        comparison_id, source_ref, _logical_id(reference), _logical_id(shadow),
        mandatory, divergent, expected, "PASS" if not divergent else "BLOCK",
    )


@dataclass(frozen=True)
class DSAISecurityRefusalParity:
    parity_id: str
    action: str
    dsai_decision: str
    shared_decision: str
    dsai_metadata_revealed: bool
    shared_metadata_revealed: bool
    status: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        expected = "PASS" if (
            self.dsai_decision == self.shared_decision
            and self.dsai_decision == "DENY"
            and not self.dsai_metadata_revealed
            and not self.shared_metadata_revealed
        ) else "BLOCK"
        if self.status != expected:
            raise DSAIShadowError("DSAI_SECURITY_PARITY_STATUS_INCONSISTENT")
        if self.authority_effect != "NONE":
            raise DSAIShadowError("DSAI_SECURITY_PARITY_AUTHORITY_EFFECT_FORBIDDEN")


def compare_security_refusal(
    parity_id: str,
    action: str,
    *,
    dsai_decision: Mapping[str, Any],
    shared_decision: object,
) -> DSAISecurityRefusalParity:
    shared_status = str(getattr(shared_decision, "status", ""))
    shared_revealed = bool(getattr(shared_decision, "metadata_revealed", True))
    dsai_status = str(dsai_decision.get("decision", ""))
    dsai_revealed = bool(dsai_decision.get("metadata_revealed", False))
    passed = dsai_status == shared_status == "DENY" and not dsai_revealed and not shared_revealed
    return DSAISecurityRefusalParity(
        parity_id, action, dsai_status, shared_status, dsai_revealed, shared_revealed,
        "PASS" if passed else "BLOCK",
    )


@dataclass(frozen=True)
class DSAIAdapterComplexityLedger:
    ledger_id: str
    binding_refs: tuple[str, ...]
    surface_coverage: tuple[str, ...]
    active_adapter_count: int
    max_adapter_code_surface_lines: int
    max_adapter_mapping_count: int
    artifact_byte_delta: int
    maintenance_time_seconds: int
    adapter_incident_contribution_count: int
    budget_cap_refs: tuple[str, ...]
    status: str
    exceeded_dimensions: tuple[str, ...]
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        if set(self.surface_coverage) != DSAI_SURFACES:
            raise DSAIShadowError("DSAI_ADAPTER_SURFACE_COVERAGE_INCOMPLETE")
        expected = "PASS" if not self.exceeded_dimensions else "BLOCK"
        if self.status != expected:
            raise DSAIShadowError("DSAI_ADAPTER_BUDGET_STATUS_INCONSISTENT")
        if self.authority_effect != "NONE":
            raise DSAIShadowError("DSAI_ADAPTER_LEDGER_AUTHORITY_EFFECT_FORBIDDEN")


def evaluate_adapter_complexity(
    ledger_id: str,
    bindings: Iterable[DSAISurfaceAdapterBinding],
    *,
    budget: Mapping[str, Any],
    code_surface_lines: int,
    artifact_byte_delta: int,
    maintenance_time_seconds: int = 0,
    incident_contribution_count: int = 0,
) -> DSAIAdapterComplexityLedger:
    rows = tuple(bindings)
    if len({item.binding_id for item in rows}) != len(rows):
        raise DSAIShadowError("DSAI_ADAPTER_BINDING_AMBIGUOUS")
    caps = {item[0]: float(item[1]) for item in budget.get("numeric_caps", ())}
    observed = {
        "ACTIVE_ADAPTER_COUNT": sum(1 for item in rows if item.active),
        "ADAPTER_CODE_SURFACE_LINES": code_surface_lines,
        "ADAPTER_MAPPING_COUNT": max((len(item.field_mapping) for item in rows), default=0),
        "ARTIFACT_BYTE_DELTA_BYTES": artifact_byte_delta,
        "MAINTENANCE_TIME_SECONDS": maintenance_time_seconds,
        "ADAPTER_INCIDENT_CONTRIBUTION_COUNT": incident_contribution_count,
    }
    missing = sorted(set(observed) - set(caps))
    if missing:
        raise DSAIShadowError(f"PILOT_BUDGET_CAP_MISSING:{','.join(missing)}")
    exceeded = tuple(sorted(key for key, value in observed.items() if value > caps[key]))
    return DSAIAdapterComplexityLedger(
        ledger_id,
        tuple(sorted(item.binding_id for item in rows)),
        tuple(sorted(item.surface for item in rows)),
        observed["ACTIVE_ADAPTER_COUNT"],
        code_surface_lines,
        observed["ADAPTER_MAPPING_COUNT"],
        artifact_byte_delta,
        maintenance_time_seconds,
        incident_contribution_count,
        tuple(sorted(caps)),
        "PASS" if not exceeded else "BLOCK",
        exceeded,
    )
