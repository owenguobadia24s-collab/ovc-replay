from __future__ import annotations

import pytest

from ovc.research_orchestration.telemetry import (
    REQUIRED_METRIC_IDS,
    MetricValue,
    TelemetryError,
    TelemetryReceipt,
    assert_telemetry_nonsemantic,
    build_telemetry_receipt,
    validate_metric_coverage,
)


def full_values() -> dict[str, tuple[int | float | None, str]]:
    units = {
        "wall_seconds": "seconds", "cpu_seconds": "seconds", "core_seconds": "core_seconds",
        "peak_rss_bytes": "bytes", "worker_count": "workers", "bytes_read": "bytes",
        "bytes_written": "bytes", "persistent_bytes": "bytes", "temporary_bytes": "bytes",
        "object_count": "objects", "pair_count": "pairs", "tile_count": "tiles",
        "configuration_count": "configurations", "throughput_per_second": "work_units_per_second",
        "cache_hit_count": "hits", "cache_miss_count": "misses", "restart_count": "restarts",
    }
    return {metric_id: (0 if metric_id not in {"wall_seconds", "cpu_seconds", "core_seconds", "throughput_per_second"} else 0.0, units[metric_id]) for metric_id in REQUIRED_METRIC_IDS}


def test_full_metric_coverage_passes_with_typed_values() -> None:
    receipt = build_telemetry_receipt(run_id="RUN", stage_id="A", values=full_values())
    validate_metric_coverage(receipt)
    assert set(receipt.metric_by_id()) == set(REQUIRED_METRIC_IDS)
    assert receipt.scientific_effect == "NONE"


def test_unavailable_metric_is_explicit_not_fabricated() -> None:
    values = full_values()
    values["peak_rss_bytes"] = (None, "bytes")
    receipt = build_telemetry_receipt(run_id="RUN", stage_id="A", values=values)
    metric = receipt.metric_by_id()["peak_rss_bytes"]
    assert metric.availability == "UNAVAILABLE"
    assert metric.value is None
    assert metric.reason_code == "NOT_MEASURED"


def test_missing_required_metric_fails() -> None:
    metrics = tuple(MetricValue(metric_id, 0, "unit") for metric_id in sorted(REQUIRED_METRIC_IDS - {"wall_seconds"}))
    receipt = TelemetryReceipt("RUN", "A", metrics)
    with pytest.raises(TelemetryError, match="IROF_TELEMETRY_REQUIRED_METRIC_MISSING"):
        validate_metric_coverage(receipt)


def test_telemetry_measurement_cannot_change_semantic_hash() -> None:
    assert_telemetry_nonsemantic("same-hash", "same-hash")
    with pytest.raises(TelemetryError, match="IROF_TELEMETRY_CHANGED_SEMANTIC_OUTPUT"):
        assert_telemetry_nonsemantic("before", "after")


def test_duplicate_metric_fails_closed() -> None:
    with pytest.raises(TelemetryError, match="IROF_TELEMETRY_DUPLICATE_METRIC"):
        TelemetryReceipt("RUN", "A", (MetricValue("x", 1, "count"), MetricValue("x", 2, "count")))
