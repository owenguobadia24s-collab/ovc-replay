from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable

from .models import StageInvocation, StageSpec


class AdapterError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


@dataclass(frozen=True)
class AdapterPreflight:
    stage_id: str
    allowed: bool
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class AdapterEstimate:
    stage_id: str
    work_units: int | None = None
    estimated_bytes: int | None = None
    estimator_id: str | None = None


@dataclass(frozen=True)
class AdapterExecution:
    stage_id: str
    output_refs: tuple[str, ...]
    scientific_payload_hash: str | None = None
    checkpoint_ref: str | None = None


@dataclass(frozen=True)
class AdapterVerification:
    stage_id: str
    valid: bool
    reason_codes: tuple[str, ...] = ()


@runtime_checkable
class StageAdapter(Protocol):
    stage_id: str

    def preflight(self, stage_spec: StageSpec, invocation: StageInvocation, envelope: Mapping[str, Any]) -> AdapterPreflight: ...
    def estimate(self, stage_spec: StageSpec, invocation: StageInvocation, envelope: Mapping[str, Any]) -> AdapterEstimate: ...
    def execute(self, stage_spec: StageSpec, invocation: StageInvocation, envelope: Mapping[str, Any]) -> AdapterExecution: ...
    def resume(self, stage_spec: StageSpec, invocation: StageInvocation, envelope: Mapping[str, Any], checkpoint_ref: str) -> AdapterExecution: ...
    def verify(self, stage_spec: StageSpec, invocation: StageInvocation, result: AdapterExecution) -> AdapterVerification: ...


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, StageAdapter] = {}

    def register(self, adapter: StageAdapter) -> None:
        stage_id = str(adapter.stage_id).strip()
        if not stage_id:
            raise AdapterError("IROF_ADAPTER_STAGE_ID_REQUIRED", "adapter.stage_id")
        if stage_id in self._adapters:
            raise AdapterError("IROF_DUPLICATE_ADAPTER", stage_id)
        self._adapters[stage_id] = adapter

    def require(self, stage_id: str) -> StageAdapter:
        try:
            return self._adapters[stage_id]
        except KeyError as exc:
            raise AdapterError("IROF_ADAPTER_NOT_REGISTERED", stage_id) from exc

    def stage_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))


DEFAULT_ENVELOPE_FIELDS = frozenset({
    "run_id", "stage_id", "attempt_id", "worker_id", "physical_path",
    "cache_status", "checkpoint_ref", "telemetry", "execution_status",
})


def scientific_payload_view(payload: Mapping[str, Any], *, envelope_fields: frozenset[str] = DEFAULT_ENVELOPE_FIELDS) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key not in envelope_fields}


def assert_no_scientific_mutation(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    envelope_fields: frozenset[str] = DEFAULT_ENVELOPE_FIELDS,
) -> None:
    if scientific_payload_view(before, envelope_fields=envelope_fields) != scientific_payload_view(after, envelope_fields=envelope_fields):
        raise AdapterError("IROF_WRAPPER_SCIENTIFIC_MUTATION", "adapter changed scientific payload fields")
