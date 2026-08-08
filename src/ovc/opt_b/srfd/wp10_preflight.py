from __future__ import annotations

from typing import Any, Mapping, Sequence

REQUIRED_STABILITY_METRICS = (
    "CROSS_SENSITIVITY_SURVIVAL_WITH_DENOMINATOR",
    "CROSS_METHOD_CORRESPONDENCE_WITH_DENOMINATOR",
    "CHRONOLOGICAL_STABILITY_WITH_DENOMINATOR",
    "RESIDUAL_RATE_WITH_DENOMINATOR",
    "AMBIGUITY_RATE_WITH_DENOMINATOR",
)


class WP10PreflightError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _effective_stability_source(
    preregistration: Mapping[str, Any],
    base_preregistration: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    if "stability_metrics" in preregistration:
        return preregistration
    supersession = preregistration.get("supersession")
    if isinstance(supersession, Mapping) and supersession.get("supersession_scope") == "SEGMENTATION_EXECUTION_SPECIFICATION_ONLY":
        if base_preregistration is None:
            raise WP10PreflightError(
                "WP10_STABILITY_METRIC_BASE_UNBOUND",
                "v0.3 inherits non-segmentation scientific surfaces but the frozen base preregistration was not supplied",
            )
        return base_preregistration
    raise WP10PreflightError("WP10_STABILITY_METRIC_SET_UNBOUND", "stability_metrics sequence required")


def validate_frozen_stability_metric_rules(
    preregistration: Mapping[str, Any],
    *,
    base_preregistration: Mapping[str, Any] | None = None,
) -> None:
    source = _effective_stability_source(preregistration, base_preregistration)
    metrics = source.get("stability_metrics")
    if isinstance(metrics, (str, bytes, bytearray)) or not isinstance(metrics, Sequence):
        raise WP10PreflightError("WP10_STABILITY_METRIC_SET_UNBOUND", "stability_metrics sequence required")
    if tuple(metrics) != REQUIRED_STABILITY_METRICS:
        raise WP10PreflightError("WP10_STABILITY_METRIC_SET_DRIFT", "exact frozen stability metric set required")

    specs = source.get("stability_metric_specs")
    if not isinstance(specs, Mapping):
        raise WP10PreflightError(
            "WP10_STABILITY_METRIC_RULE_UNBOUND",
            "frozen preregistration names stability metrics but does not bind executable per-metric rule specifications",
        )

    missing = [metric for metric in REQUIRED_STABILITY_METRICS if metric not in specs]
    if missing:
        raise WP10PreflightError("WP10_STABILITY_METRIC_RULE_UNBOUND", "missing specs:" + ",".join(missing))

    for metric in REQUIRED_STABILITY_METRICS:
        spec = specs[metric]
        if not isinstance(spec, Mapping):
            raise WP10PreflightError("WP10_STABILITY_METRIC_RULE_UNBOUND", f"{metric}: mapping required")
        for field in ("numerator_rule", "denominator_rule"):
            if not str(spec.get(field, "")).strip():
                raise WP10PreflightError("WP10_STABILITY_METRIC_RULE_UNBOUND", f"{metric}: missing {field}")
        if metric == "CHRONOLOGICAL_STABILITY_WITH_DENOMINATOR" and not str(spec.get("chronology_partition_rule", "")).strip():
            raise WP10PreflightError("WP10_STABILITY_METRIC_RULE_UNBOUND", f"{metric}: chronology_partition_rule required")
        if metric in {"CROSS_SENSITIVITY_SURVIVAL_WITH_DENOMINATOR", "CROSS_METHOD_CORRESPONDENCE_WITH_DENOMINATOR"} and not str(spec.get("correspondence_rule", "")).strip():
            raise WP10PreflightError("WP10_STABILITY_METRIC_RULE_UNBOUND", f"{metric}: correspondence_rule required")
        if metric == "AMBIGUITY_RATE_WITH_DENOMINATOR" and not str(spec.get("ambiguity_event_rule", "")).strip():
            raise WP10PreflightError("WP10_STABILITY_METRIC_RULE_UNBOUND", f"{metric}: ambiguity_event_rule required")
