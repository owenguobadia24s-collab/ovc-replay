from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module, util
from typing import Any, Mapping, Sequence

from ovc.context.occurrence_context.consumers import validate_consumption_manifest

from .adapters import AdapterEstimate, AdapterExecution, AdapterPreflight, AdapterVerification
from .models import StageInvocation, StageSpec
from .serialization import canonical_json


class CurrentAdapterError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


@dataclass(frozen=True)
class CurrentStageBinding:
    stage_id: str
    source_modules: tuple[str, ...]
    authority_owner: str
    execution_mode: str
    adapter_mode: str = "OPAQUE_OWNER_HANDOFF"


CURRENT_STAGE_BINDINGS: tuple[CurrentStageBinding, ...] = (
    CurrentStageBinding("POPULATION_SOURCE_OPT_A", ("ovc.opt_a.provider_population", "ovc.opt_a.population_integrity", "ovc.opt_a.release_freeze"), "OPT-A / source-release governance", "EXISTING_AUTHORITY_ONLY"),
    CurrentStageBinding("C1", ("ovc.opt_b.c1",), "OPT-B.C1", "EXISTING_AUTHORITY_ONLY"),
    CurrentStageBinding("C2_REVISED", ("ovc.opt_b.c2_vnext",), "OPT-B.C2", "EXISTING_SELECTOR_ONLY"),
    CurrentStageBinding("C2E_V0_2", ("ovc.opt_b.c2e_v2",), "OVC-C2E-CAUSAL-EPISODE-CONFORMANCE-v0.2", "SYNTHETIC_INACTIVE_ONLY"),
    CurrentStageBinding("OCCURRENCE_CONTEXT", ("ovc.context.occurrence_context.consumers",), "OccurrenceContext v0.1", "CONTEXT_ONLY"),
    CurrentStageBinding("SRI_REPRESENTATION", ("ovc.opt_b.sfc.representation",), "SFC / SRI", "SYNTHETIC_INACTIVE_ONLY"),
    CurrentStageBinding("COMPARABILITY_COMPARISON_DISTANCE", ("ovc.opt_b.sfc.comparison",), "SFC + SRFD", "SYNTHETIC_INACTIVE_ONLY"),
    CurrentStageBinding("FDI_C2G_FAMILY", ("ovc.opt_b.sfc.fdi",), "SFC + SRFD", "SYNTHETIC_INACTIVE_ONLY"),
    CurrentStageBinding("FAMILY_EVIDENCE_STREAM", ("ovc.opt_b.sfc.evidence",), "SFC", "SYNTHETIC_INACTIVE_ONLY"),
    CurrentStageBinding("RESEARCH_OPERATIONS", ("ovc.research_operations.qa", "ovc.research_operations.catalogue"), "Research Operations Foundation", "READ_ONLY_EVIDENCE"),
)

BINDING_BY_STAGE = {item.stage_id: item for item in CURRENT_STAGE_BINDINGS}


class CurrentStageAdapter:
    """Semantics-neutral handoff adapter for already-owned stage contracts.

    It validates that pinned current modules exist and relays owner output references. It does
    not reconstruct, normalize or repair the owner payload.
    """

    def __init__(self, binding: CurrentStageBinding) -> None:
        self.binding = binding
        self.stage_id = binding.stage_id

    def preflight(self, stage_spec: StageSpec, invocation: StageInvocation, envelope: Mapping[str, Any]) -> AdapterPreflight:
        reasons: list[str] = []
        if stage_spec.stage_id != self.stage_id or invocation.stage_id != self.stage_id:
            reasons.append("IROF_CURRENT_ADAPTER_STAGE_ID_MISMATCH")
        for module in self.binding.source_modules:
            if util.find_spec(module) is None:
                reasons.append("IROF_CURRENT_SOURCE_MODULE_MISSING")
        population_mode = str(envelope.get("population_mode", "SYNTHETIC_FIXTURE"))
        if self.binding.execution_mode == "SYNTHETIC_INACTIVE_ONLY" and population_mode not in {"SYNTHETIC_FIXTURE", "GENERATED_FIXTURE", "NON_EVIDENTIARY_REPLAY"}:
            reasons.append("IROF_CURRENT_ADAPTER_REAL_EXECUTION_NOT_AUTHORISED")
        if self.stage_id == "OCCURRENCE_CONTEXT" and envelope.get("context_role") == "REPRESENTATION_INPUT":
            reasons.append("IROF_OCCURRENCE_CONTEXT_REPRESENTATION_INPUT_NOT_AUTHORISED")
        return AdapterPreflight(self.stage_id, not reasons, tuple(sorted(set(reasons))))

    def estimate(self, stage_spec: StageSpec, invocation: StageInvocation, envelope: Mapping[str, Any]) -> AdapterEstimate:
        return AdapterEstimate(self.stage_id, work_units=None, estimated_bytes=None, estimator_id="OWNER_STAGE_ESTIMATOR_ONLY")

    def execute(self, stage_spec: StageSpec, invocation: StageInvocation, envelope: Mapping[str, Any]) -> AdapterExecution:
        preflight = self.preflight(stage_spec, invocation, envelope)
        if not preflight.allowed:
            raise CurrentAdapterError(preflight.reason_codes[0], self.stage_id)
        refs = tuple(str(item) for item in envelope.get("owner_output_refs", ()))
        if not refs:
            raise CurrentAdapterError("IROF_OWNER_OUTPUT_REFERENCE_REQUIRED", self.stage_id)
        return AdapterExecution(self.stage_id, refs, scientific_payload_hash=envelope.get("owner_scientific_payload_hash"), checkpoint_ref=envelope.get("checkpoint_ref"))

    def resume(self, stage_spec: StageSpec, invocation: StageInvocation, envelope: Mapping[str, Any], checkpoint_ref: str) -> AdapterExecution:
        merged = dict(envelope)
        merged["checkpoint_ref"] = checkpoint_ref
        return self.execute(stage_spec, invocation, merged)

    def verify(self, stage_spec: StageSpec, invocation: StageInvocation, result: AdapterExecution) -> AdapterVerification:
        reasons = []
        if result.stage_id != self.stage_id:
            reasons.append("IROF_CURRENT_ADAPTER_STAGE_ID_MISMATCH")
        if not result.output_refs:
            reasons.append("IROF_OWNER_OUTPUT_REFERENCE_REQUIRED")
        return AdapterVerification(self.stage_id, not reasons, tuple(reasons))


def verify_current_source_bindings() -> tuple[str, ...]:
    missing: list[str] = []
    for binding in CURRENT_STAGE_BINDINGS:
        for module in binding.source_modules:
            if util.find_spec(module) is None:
                missing.append(f"{binding.stage_id}:{module}")
    if missing:
        raise CurrentAdapterError("IROF_CURRENT_SOURCE_MODULE_MISSING", ",".join(sorted(missing)))
    return tuple(item.stage_id for item in CURRENT_STAGE_BINDINGS)


def invoke_owner_callable(module_name: str, callable_name: str, /, *args: Any, **kwargs: Any) -> Any:
    module = import_module(module_name)
    callable_obj = getattr(module, callable_name, None)
    if not callable(callable_obj):
        raise CurrentAdapterError("IROF_OWNER_CALLABLE_NOT_FOUND", f"{module_name}:{callable_name}")
    return callable_obj(*args, **kwargs)


def assert_exact_owner_output(reference: Any, candidate: Any) -> None:
    if canonical_json(reference) != canonical_json(candidate):
        raise CurrentAdapterError("IROF_CURRENT_ADAPTER_SCIENTIFIC_OUTPUT_DRIFT", "owner output changed")


def validate_occurrence_context_adapter_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return validate_consumption_manifest(manifest)
    except Exception as exc:
        message = str(exc)
        if "REPRESENTATION_INPUT" in message or "OC_ROLE_REPRESENTATION_INPUT_UNAUTHORIZED" in message:
            raise CurrentAdapterError("IROF_OCCURRENCE_CONTEXT_REPRESENTATION_INPUT_NOT_AUTHORISED", message) from exc
        raise


def adapter_for_stage(stage_id: str) -> CurrentStageAdapter:
    try:
        return CurrentStageAdapter(BINDING_BY_STAGE[stage_id])
    except KeyError as exc:
        raise CurrentAdapterError("IROF_CURRENT_STAGE_NOT_REGISTERED", stage_id) from exc


def mcarb_adapter_available() -> bool:
    # MCARB remains a separately governed extension point and is not part of the current IROF executable graph.
    return False
