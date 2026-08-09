from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


class TelemetryError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


METRIC_AVAILABILITY = frozenset({"AVAILABLE", "UNAVAILABLE", "NOT_APPLICABLE"})


@dataclass(frozen=True)
class MetricValue:
    metric_id: str
    value: int | float | None
    unit: str
    availability: str = "AVAILABLE"
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if not self.metric_id.strip() or not self.unit.strip():
            raise TelemetryError("IROF_TELEMETRY_METRIC_FIELD_REQUIRED", self.metric_id)
        if self.availability not in METRIC_AVAILABILITY:
            raise TelemetryError("IROF_TELEMETRY_AVAILABILITY_INVALID", self.availability)
        if self.availability == "AVAILABLE" and self.value is None:
            raise TelemetryError("IROF_TELEMETRY_AVAILABLE_VALUE_REQUIRED", self.metric_id)
        if self.availability != "AVAILABLE" and self.value is not None:
            raise TelemetryError("IROF_TELEMETRY_UNAVAILABLE_VALUE_FORBIDDEN", self.metric_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "value": self.value,
            "unit": self.unit,
            "availability": self.availability,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class TelemetryReceipt:
    run_id: str
    stage_id: str
    metrics: tuple[MetricValue, ...]
    warnings: tuple[str, ...] = ()
    capacity_status: str = "COMPLETE"
    scientific_effect: str = "NONE"

    def __post_init__(self) -> None:
        if self.scientific_effect != "NONE":
            raise TelemetryError("IROF_TELEMETRY_SCIENTIFIC_EFFECT_FORBIDDEN", self.stage_id)
        ids = tuple(item.metric_id for item in self.metrics)
        if len(ids) != len(set(ids)):
            raise TelemetryError("IROF_TELEMETRY_DUPLICATE_METRIC", self.stage_id)

    def metric_by_id(self) -> Mapping[str, MetricValue]:
        return {item.metric_id: item for item in self.metrics}

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "stage_id": self.stage_id,
            "metrics": [item.to_dict() for item in sorted(self.metrics, key=lambda x: x.metric_id)],
            "warnings": list(self.warnings),
            "capacity_status": self.capacity_status,
            "scientific_effect": self.scientific_effect,
        }


REQUIRED_METRIC_IDS = frozenset({
    "wall_seconds",
    "cpu_seconds",
    "core_seconds",
    "peak_rss_bytes",
    "worker_count",
    "bytes_read",
    "bytes_written",
    "persistent_bytes",
    "temporary_bytes",
    "object_count",
    "pair_count",
    "tile_count",
    "configuration_count",
    "throughput_per_second",
    "cache_hit_count",
    "cache_miss_count",
    "restart_count",
})


def validate_metric_coverage(receipt: TelemetryReceipt, required_metric_ids: Iterable[str] = REQUIRED_METRIC_IDS) -> None:
    present = set(receipt.metric_by_id())
    missing = set(required_metric_ids) - present
    if missing:
        raise TelemetryError("IROF_TELEMETRY_REQUIRED_METRIC_MISSING", ",".join(sorted(missing)))


def metric(metric_id: str, value: int | float | None, unit: str, *, reason_code: str | None = None) -> MetricValue:
    if value is None:
        return MetricValue(metric_id, None, unit, availability="UNAVAILABLE", reason_code=reason_code or "NOT_MEASURED")
    return MetricValue(metric_id, value, unit)


def build_telemetry_receipt(
    *,
    run_id: str,
    stage_id: str,
    values: Mapping[str, tuple[int | float | None, str]],
    warnings: Iterable[str] = (),
    capacity_status: str = "COMPLETE",
) -> TelemetryReceipt:
    metrics = tuple(metric(metric_id, value, unit) for metric_id, (value, unit) in values.items())
    receipt = TelemetryReceipt(run_id, stage_id, metrics, tuple(sorted(set(warnings))), capacity_status)
    validate_metric_coverage(receipt)
    return receipt


def assert_telemetry_nonsemantic(before_logical_hash: str, after_logical_hash: str) -> None:
    if before_logical_hash != after_logical_hash:
        raise TelemetryError("IROF_TELEMETRY_CHANGED_SEMANTIC_OUTPUT", before_logical_hash)
