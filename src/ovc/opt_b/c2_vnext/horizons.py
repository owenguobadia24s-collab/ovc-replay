"""Typed causal horizon, discrepancy and benchmark foundation for C2 vNext.

The module is deterministic and shadow-only.  It operates on the immutable
observation records introduced by C2AR-WP1.  It never activates a selector,
clock, lattice, formula, threshold, release or publication path.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

UTC = timezone.utc

TIME_SEMANTICS = (
    "CALENDAR_DURATION",
    "SOURCE_BAR_COUNT",
    "OBSERVATION_COUNT",
    "SESSION_CLOCK",
    "ORDINAL_SLOT",
)
HORIZON_KINDS = (
    "CURRENT",
    "TRANSITION",
    "TRAILING_COUNT",
    "PAIRED_COMPARISON",
    "CONFIRMATION_DELAY",
    "RUN_LENGTH",
    "AGE",
    "AS_OF_PARENT",
    "EVENT_RELATIVE_VARIABLE",
    "FORWARD_OUTCOME",
)
CAUSAL_CLASSES = (
    "CAUSAL_CURRENT",
    "CAUSAL_BACKWARD",
    "CAUSAL_AS_OF",
    "CAUSAL_EVENT_CLOSED",
    "RETROSPECTIVE_ONLY",
)
CONTINUITY_POLICIES = (
    "SAME_CONTINUITY_SEGMENT",
    "EXPLICIT_RESET_AWARE",
    "NOT_APPLICABLE",
)
MEMBERSHIP_STATUSES = ("COMPUTABLE", "NOT_COMPUTABLE", "BENCHMARK_ONLY")
REASON_CODES = (
    "OK",
    "CURRENT_OBSERVATION_NOT_ELIGIBLE",
    "WARM_UP_INSUFFICIENT",
    "DISCONTINUITY",
    "CLOSURE_BOUNDARY",
    "GAP_OR_RESET",
    "UNKNOWN_BREAK",
    "PARTIAL_WINDOW",
    "ANCHOR_REQUIRED",
    "ANCHOR_NOT_FOUND",
    "ANCHOR_AFTER_AS_OF",
    "ANCHOR_NOT_IN_SEGMENT",
    "CONFIRMATION_DELAY_NOT_MET",
    "PARENT_REQUIRED",
    "PARENT_NOT_AVAILABLE_AS_OF",
    "EVENT_REQUIRED",
    "EVENT_NOT_AVAILABLE_AS_OF",
    "EVENT_NOT_IN_SEGMENT",
    "PREDICATE_REQUIRED",
    "RETROSPECTIVE_ONLY",
    "BENCHMARK_MODE_REQUIRED",
    "CONSUMER_NOT_ALLOWED",
    "CLOCK_MAPPING_REQUIRED",
    "CLOCK_MAPPING_NOT_APPROVED",
    "HISTORY_CAPACITY_INSUFFICIENT",
    "HISTORY_CAPACITY_IS_NOT_HORIZON",
    "UNSUPPORTED_TIME_SEMANTIC",
)
CAUSAL_CONSUMER_CLASSES = {
    "C2_MEASUREMENT",
    "C2_LEVEL",
    "C2_CONTAINER",
    "C2_RELATION",
    "C2_AXIS",
    "C2_PARENT_CONTEXT",
    "C2_TRANSITION",
    "RESEARCH_CAUSAL_READ",
}
RETROSPECTIVE_CONSUMER_CLASSES = {"RESEARCH_BENCHMARK", "FORWARD_OUTCOME_LABEL"}
COUNTED_KINDS = {"TRAILING_COUNT", "CONFIRMATION_DELAY", "FORWARD_OUTCOME"}
PROHIBITED_DEFINITION_KINDS = {"HISTORY_CAPACITY", "CENTERED_WINDOW", "UNIVERSAL_HORIZON"}


class HorizonContractError(ValueError):
    """Raised when typed-horizon or causal-store invariants are violated."""


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise HorizonContractError(marker)


def parse_time(value: str | datetime) -> datetime:
    result = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    _require(result.tzinfo is not None, "TIMEZONE_REQUIRED")
    return result.astimezone(UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(prefix: str, value: Any, length: int = 24) -> str:
    return f"{prefix}.{hashlib.sha256(canonical_bytes(value)).hexdigest()[:length]}"


@dataclass(frozen=True)
class TypedTimeValue:
    """A numeric or ordinal time value with all semantic qualifiers attached."""

    semantic_type: str
    value: int | float | str
    unit: str
    grain: str
    version: str
    source_basis: str
    applicability_scope: tuple[str, ...]

    def __post_init__(self) -> None:
        _require(self.semantic_type in TIME_SEMANTICS, "TIME_SEMANTIC_TYPE")
        _require(not isinstance(self.value, bool), "TIME_VALUE_BOOLEAN")
        _require(bool(str(self.unit).strip()), "TIME_UNIT_REQUIRED")
        _require(bool(str(self.grain).strip()), "TIME_GRAIN_REQUIRED")
        _require(bool(str(self.version).strip()), "TIME_VERSION_REQUIRED")
        _require(bool(str(self.source_basis).strip()), "TIME_SOURCE_BASIS_REQUIRED")
        _require(bool(self.applicability_scope), "TIME_APPLICABILITY_SCOPE_REQUIRED")

    @property
    def typed_value_id(self) -> str:
        return digest("C2.TYPED_TIME", self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_type": self.semantic_type,
            "value": self.value,
            "unit": self.unit,
            "grain": self.grain,
            "version": self.version,
            "source_basis": self.source_basis,
            "applicability_scope": list(self.applicability_scope),
        }


def typed_time_from_mapping(value: Mapping[str, Any]) -> TypedTimeValue:
    """Reject a bare value and require the complete P2-D1 semantic package."""

    _require(isinstance(value, Mapping), "BARE_TIME_VALUE_INVALID")
    required = {
        "semantic_type",
        "value",
        "unit",
        "grain",
        "version",
        "source_basis",
        "applicability_scope",
    }
    _require(required.issubset(value), "INCOMPLETE_TYPED_TIME_VALUE")
    return TypedTimeValue(
        semantic_type=str(value["semantic_type"]),
        value=value["value"],
        unit=str(value["unit"]),
        grain=str(value["grain"]),
        version=str(value["version"]),
        source_basis=str(value["source_basis"]),
        applicability_scope=tuple(str(item) for item in value["applicability_scope"]),
    )


@dataclass(frozen=True)
class HorizonDefinition:
    horizon_id: str
    kind: str
    semantic_type: str
    unit: str
    grain: str
    source_basis: str
    applicability_scope: tuple[str, ...]
    consumer_classes: tuple[str, ...]
    causal_class: str
    continuity_policy: str
    first_valid_rule: str
    version: str
    maturity: str = "SHADOW_EXPERIMENT"
    clock_id: str | None = None
    count: int | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
    template: bool = False
    benchmark_only: bool = False
    canonical: bool = False

    def __post_init__(self) -> None:
        _require(self.kind in HORIZON_KINDS, "HORIZON_KIND")
        _require(self.kind not in PROHIBITED_DEFINITION_KINDS, "PROHIBITED_HORIZON_KIND")
        _require(self.semantic_type in TIME_SEMANTICS, "HORIZON_TIME_SEMANTIC")
        _require(self.causal_class in CAUSAL_CLASSES, "HORIZON_CAUSAL_CLASS")
        _require(self.continuity_policy in CONTINUITY_POLICIES, "HORIZON_CONTINUITY_POLICY")
        _require(self.maturity in {"NORMATIVE_BOUNDARY", "SHADOW_EXPERIMENT", "HISTORICAL_DECLARATION"}, "HORIZON_MATURITY")
        _require(bool(self.unit) and bool(self.grain) and bool(self.source_basis), "HORIZON_TYPED_FIELDS")
        _require(bool(self.applicability_scope), "HORIZON_APPLICABILITY_SCOPE")
        _require(bool(self.version) and bool(self.first_valid_rule), "HORIZON_VERSION_FIRST_VALID")
        _require(not self.canonical, "UNIVERSAL_CANONICAL_HORIZON_DENIED")
        if self.kind in COUNTED_KINDS and self.count is None:
            _require(self.template, "HORIZON_COUNT_REQUIRED")
        if self.count is not None:
            _require(isinstance(self.count, int) and not isinstance(self.count, bool) and self.count > 0, "HORIZON_COUNT")
        if self.kind == "PAIRED_COMPARISON" and not self.template:
            left = self.parameters.get("left_count")
            right = self.parameters.get("right_count")
            _require(isinstance(left, int) and left > 0, "PAIRED_LEFT_COUNT")
            _require(isinstance(right, int) and right > 0, "PAIRED_RIGHT_COUNT")
        if self.kind == "TRANSITION":
            _require(self.semantic_type in {"OBSERVATION_COUNT", "ORDINAL_SLOT"}, "TRANSITION_TIME_SEMANTIC")
        if self.kind in {"TRAILING_COUNT", "PAIRED_COMPARISON", "CONFIRMATION_DELAY", "RUN_LENGTH"}:
            _require(self.causal_class == "CAUSAL_BACKWARD", "BACKWARD_HORIZON_CLASS")
        if self.kind == "AS_OF_PARENT":
            _require(self.causal_class == "CAUSAL_AS_OF", "AS_OF_PARENT_CLASS")
        if self.kind == "EVENT_RELATIVE_VARIABLE":
            _require(self.causal_class == "CAUSAL_EVENT_CLOSED", "EVENT_RELATIVE_CLASS")
        if self.kind == "FORWARD_OUTCOME":
            _require(self.causal_class == "RETROSPECTIVE_ONLY", "FORWARD_OUTCOME_CLASS")
            _require(self.benchmark_only, "FORWARD_OUTCOME_BENCHMARK_ONLY")
            _require(not set(self.consumer_classes) & CAUSAL_CONSUMER_CLASSES, "FORWARD_OUTCOME_CAUSAL_CONSUMER")
        if self.causal_class == "RETROSPECTIVE_ONLY":
            _require(self.benchmark_only, "RETROSPECTIVE_BENCHMARK_ONLY")
        if self.clock_id is None:
            _require(self.semantic_type != "SESSION_CLOCK", "SESSION_CLOCK_ID_REQUIRED")

    def to_dict(self) -> dict[str, Any]:
        return {
            "horizon_id": self.horizon_id,
            "kind": self.kind,
            "semantic_type": self.semantic_type,
            "unit": self.unit,
            "grain": self.grain,
            "source_basis": self.source_basis,
            "applicability_scope": list(self.applicability_scope),
            "consumer_classes": list(self.consumer_classes),
            "causal_class": self.causal_class,
            "continuity_policy": self.continuity_policy,
            "first_valid_rule": self.first_valid_rule,
            "version": self.version,
            "maturity": self.maturity,
            "clock_id": self.clock_id,
            "count": self.count,
            "parameters": copy.deepcopy(dict(self.parameters)),
            "template": self.template,
            "benchmark_only": self.benchmark_only,
            "canonical": self.canonical,
        }

    @property
    def definition_sha256(self) -> str:
        return hashlib.sha256(canonical_bytes(self.to_dict())).hexdigest()


def horizon_from_mapping(value: Mapping[str, Any]) -> HorizonDefinition:
    required = {
        "horizon_id", "kind", "semantic_type", "unit", "grain", "source_basis",
        "applicability_scope", "consumer_classes", "causal_class",
        "continuity_policy", "first_valid_rule", "version",
    }
    _require(required.issubset(value), "HORIZON_DEFINITION_INCOMPLETE")
    return HorizonDefinition(
        horizon_id=str(value["horizon_id"]),
        kind=str(value["kind"]),
        semantic_type=str(value["semantic_type"]),
        unit=str(value["unit"]),
        grain=str(value["grain"]),
        source_basis=str(value["source_basis"]),
        applicability_scope=tuple(str(item) for item in value["applicability_scope"]),
        consumer_classes=tuple(str(item) for item in value["consumer_classes"]),
        causal_class=str(value["causal_class"]),
        continuity_policy=str(value["continuity_policy"]),
        first_valid_rule=str(value["first_valid_rule"]),
        version=str(value["version"]),
        maturity=str(value.get("maturity", "SHADOW_EXPERIMENT")),
        clock_id=str(value["clock_id"]) if value.get("clock_id") is not None else None,
        count=value.get("count"),
        parameters=copy.deepcopy(dict(value.get("parameters", {}))),
        template=bool(value.get("template", False)),
        benchmark_only=bool(value.get("benchmark_only", False)),
        canonical=bool(value.get("canonical", False)),
    )


@dataclass(frozen=True)
class CrossClockMapping:
    mapping_id: str
    source_horizon_id: str
    target_horizon_id: str
    relation_basis: str
    status: str
    source_ref: str
    automatic_equivalence: bool = False

    def __post_init__(self) -> None:
        _require(self.relation_basis in {"ELAPSED_DURATION", "STRUCTURAL_DEPTH", "CLOCK_RELATIVE_POPULATION"}, "CROSS_CLOCK_RELATION_BASIS")
        _require(self.status in {"UNRESOLVED", "REGISTERED_SHADOW", "APPROVED_NORMATIVE"}, "CROSS_CLOCK_STATUS")
        _require(not self.automatic_equivalence, "AUTOMATIC_CROSS_CLOCK_EQUIVALENCE_DENIED")
        _require(bool(self.source_ref), "CROSS_CLOCK_SOURCE_REF")


def require_cross_clock_mapping(
    source_horizon_id: str,
    target_horizon_id: str,
    mappings: Sequence[CrossClockMapping],
    *,
    allow_shadow: bool = False,
) -> CrossClockMapping:
    matches = [
        item for item in mappings
        if item.source_horizon_id == source_horizon_id and item.target_horizon_id == target_horizon_id
    ]
    _require(len(matches) == 1, "CLOCK_MAPPING_REQUIRED")
    mapping = matches[0]
    if mapping.status != "APPROVED_NORMATIVE":
        _require(allow_shadow and mapping.status == "REGISTERED_SHADOW", "CLOCK_MAPPING_NOT_APPROVED")
    return mapping


def default_horizon_templates() -> tuple[HorizonDefinition, ...]:
    common = {
        "unit": "OBSERVATION",
        "grain": "C2_OBSERVATION",
        "source_basis": "C2AR-WP2_TYPED_HORIZON_REGISTRY",
        "applicability_scope": ("GBPUSD", "BID", "ASK"),
        "version": "vnext-r1",
        "maturity": "SHADOW_EXPERIMENT",
        "canonical": False,
    }
    return (
        HorizonDefinition("HORIZON.CURRENT.template", "CURRENT", "OBSERVATION_COUNT", consumer_classes=("C2_MEASUREMENT",), causal_class="CAUSAL_CURRENT", continuity_policy="EXPLICIT_RESET_AWARE", first_valid_rule="CURRENT_OBSERVATION_FIRST_VALID", **common),
        HorizonDefinition("HORIZON.TRANSITION.template", "TRANSITION", "OBSERVATION_COUNT", consumer_classes=("C2_TRANSITION",), causal_class="CAUSAL_BACKWARD", continuity_policy="SAME_CONTINUITY_SEGMENT", first_valid_rule="CURRENT_OBSERVATION_FIRST_VALID", **common),
        HorizonDefinition("HORIZON.TRAILING_COUNT.template", "TRAILING_COUNT", "OBSERVATION_COUNT", consumer_classes=("C2_MEASUREMENT",), causal_class="CAUSAL_BACKWARD", continuity_policy="SAME_CONTINUITY_SEGMENT", first_valid_rule="CURRENT_OBSERVATION_FIRST_VALID", template=True, **common),
        HorizonDefinition("HORIZON.PAIRED_COMPARISON.template", "PAIRED_COMPARISON", "OBSERVATION_COUNT", consumer_classes=("C2_MEASUREMENT",), causal_class="CAUSAL_BACKWARD", continuity_policy="SAME_CONTINUITY_SEGMENT", first_valid_rule="CURRENT_OBSERVATION_FIRST_VALID", template=True, **common),
        HorizonDefinition("HORIZON.CONFIRMATION_DELAY.template", "CONFIRMATION_DELAY", "OBSERVATION_COUNT", consumer_classes=("C2_LEVEL", "C2_CONTAINER"), causal_class="CAUSAL_BACKWARD", continuity_policy="SAME_CONTINUITY_SEGMENT", first_valid_rule="CONFIRMING_OBSERVATION_FIRST_VALID", template=True, **common),
        HorizonDefinition("HORIZON.RUN_LENGTH.template", "RUN_LENGTH", "OBSERVATION_COUNT", consumer_classes=("C2_MEASUREMENT",), causal_class="CAUSAL_BACKWARD", continuity_policy="SAME_CONTINUITY_SEGMENT", first_valid_rule="CURRENT_OBSERVATION_FIRST_VALID", template=True, **common),
        HorizonDefinition("HORIZON.AGE.template", "AGE", "OBSERVATION_COUNT", consumer_classes=("C2_LEVEL", "C2_CONTAINER", "C2_PARENT_CONTEXT"), causal_class="CAUSAL_AS_OF", continuity_policy="EXPLICIT_RESET_AWARE", first_valid_rule="CURRENT_OBSERVATION_FIRST_VALID", template=True, **common),
        HorizonDefinition("HORIZON.AS_OF_PARENT.template", "AS_OF_PARENT", "OBSERVATION_COUNT", consumer_classes=("C2_PARENT_CONTEXT",), causal_class="CAUSAL_AS_OF", continuity_policy="NOT_APPLICABLE", first_valid_rule="CURRENT_OBSERVATION_FIRST_VALID", template=True, **common),
        HorizonDefinition("HORIZON.EVENT_RELATIVE_VARIABLE.template", "EVENT_RELATIVE_VARIABLE", "OBSERVATION_COUNT", consumer_classes=("C2_LEVEL", "C2_CONTAINER", "RESEARCH_CAUSAL_READ"), causal_class="CAUSAL_EVENT_CLOSED", continuity_policy="SAME_CONTINUITY_SEGMENT", first_valid_rule="CURRENT_OR_CLOSING_EVENT_FIRST_VALID", template=True, **common),
        HorizonDefinition("HORIZON.FORWARD_OUTCOME.template", "FORWARD_OUTCOME", "OBSERVATION_COUNT", consumer_classes=("RESEARCH_BENCHMARK", "FORWARD_OUTCOME_LABEL"), causal_class="RETROSPECTIVE_ONLY", continuity_policy="SAME_CONTINUITY_SEGMENT", first_valid_rule="LAST_FORWARD_OBSERVATION_FIRST_VALID", template=True, benchmark_only=True, **common),
    )


def _observation_time(item: Mapping[str, Any]) -> datetime:
    return parse_time(str(item["first_valid_time"]))


def _eligible(item: Mapping[str, Any]) -> bool:
    return bool(item.get("projection_eligibility", {}).get("eligible", False))


def _group(observations: Sequence[Mapping[str, Any]], current: Mapping[str, Any]) -> list[dict[str, Any]]:
    items = [
        copy.deepcopy(dict(item)) for item in observations
        if item.get("instrument") == current.get("instrument") and item.get("side") == current.get("side")
    ]
    items.sort(key=lambda item: (_observation_time(item), str(item["observation_id"])))
    _require(len({str(item["observation_id"]) for item in items}) == len(items), "DUPLICATE_OBSERVATION_ID")
    return items


def _find_current(observations: Sequence[Mapping[str, Any]], observation_id: str) -> dict[str, Any]:
    matches = [copy.deepcopy(dict(item)) for item in observations if item.get("observation_id") == observation_id]
    _require(len(matches) == 1, "AS_OF_OBSERVATION_NOT_FOUND")
    return matches[0]


def _reason_for_segment_break(items: Sequence[Mapping[str, Any]]) -> str:
    statuses = {str(item.get("continuity", {}).get("status")) for item in items}
    if "CLOSURE_BOUNDARY" in statuses:
        return "CLOSURE_BOUNDARY"
    if "UNKNOWN_BREAK" in statuses:
        return "UNKNOWN_BREAK"
    if statuses & {"GAP_RESET", "PARTITION_BOUNDARY"}:
        return "GAP_OR_RESET"
    return "DISCONTINUITY"


def _tail_same_segment(items: Sequence[Mapping[str, Any]], index: int, count: int) -> tuple[list[dict[str, Any]] | None, str]:
    if index + 1 < count:
        return None, "WARM_UP_INSUFFICIENT"
    selected = [copy.deepcopy(dict(item)) for item in items[index - count + 1:index + 1]]
    if not all(_eligible(item) for item in selected):
        return None, _reason_for_segment_break(selected)
    segments = {item.get("continuity", {}).get("segment_id") for item in selected}
    if len(segments) != 1 or None in segments:
        return None, _reason_for_segment_break(selected)
    for left, right in zip(selected, selected[1:]):
        if str(left["interval_end"]) != str(right["interval_start"]):
            return None, "DISCONTINUITY"
    return selected, "OK"


def _not_computable(definition: HorizonDefinition, current: Mapping[str, Any], reason: str, metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    _require(reason in REASON_CODES, "UNKNOWN_REASON_CODE")
    body = {
        "horizon_id": definition.horizon_id,
        "definition_sha256": definition.definition_sha256,
        "kind": definition.kind,
        "as_of_observation_id": current["observation_id"],
        "as_of_first_valid_time": current["first_valid_time"],
        "status": "NOT_COMPUTABLE",
        "reason": reason,
        "member_observation_ids": [],
        "member_first_valid_times": [],
        "segment_id": current.get("continuity", {}).get("segment_id"),
        "causal_store_eligible": False,
        "benchmark_only": definition.benchmark_only,
        "metadata": copy.deepcopy(dict(metadata or {})),
        "authority": "SHADOW_ONLY",
    }
    return {"membership_id": digest("C2.HORIZON.MEMBERSHIP", body), **body}


def _membership(
    definition: HorizonDefinition,
    current: Mapping[str, Any],
    members: Sequence[Mapping[str, Any]],
    *,
    status: str = "COMPUTABLE",
    reason: str = "OK",
    metadata: Mapping[str, Any] | None = None,
    available_at: str | None = None,
) -> dict[str, Any]:
    _require(status in MEMBERSHIP_STATUSES, "MEMBERSHIP_STATUS")
    _require(reason in REASON_CODES, "UNKNOWN_REASON_CODE")
    member_ids = [str(item["observation_id"]) for item in members]
    member_times = [str(item["first_valid_time"]) for item in members]
    body = {
        "horizon_id": definition.horizon_id,
        "definition_sha256": definition.definition_sha256,
        "kind": definition.kind,
        "as_of_observation_id": current["observation_id"],
        "as_of_first_valid_time": current["first_valid_time"],
        "available_at": available_at or current["first_valid_time"],
        "status": status,
        "reason": reason,
        "member_observation_ids": member_ids,
        "member_first_valid_times": member_times,
        "segment_id": current.get("continuity", {}).get("segment_id"),
        "causal_store_eligible": status == "COMPUTABLE" and not definition.benchmark_only,
        "benchmark_only": definition.benchmark_only,
        "metadata": copy.deepcopy(dict(metadata or {})),
        "authority": "SHADOW_ONLY",
    }
    return {"membership_id": digest("C2.HORIZON.MEMBERSHIP", body), **body}


def _guard_consumer(definition: HorizonDefinition, consumer_class: str, benchmark_mode: bool) -> None:
    allowed = set(definition.consumer_classes)
    _require(consumer_class in allowed, "CONSUMER_NOT_ALLOWED")
    if consumer_class in CAUSAL_CONSUMER_CLASSES:
        _require(definition.causal_class != "RETROSPECTIVE_ONLY", "RETROSPECTIVE_ONLY")
        _require(not definition.benchmark_only, "RETROSPECTIVE_ONLY")
    if definition.kind == "FORWARD_OUTCOME":
        _require(benchmark_mode, "BENCHMARK_MODE_REQUIRED")
        _require(consumer_class in RETROSPECTIVE_CONSUMER_CLASSES, "CONSUMER_NOT_ALLOWED")


def evaluate_horizon(
    definition: HorizonDefinition,
    observations: Sequence[Mapping[str, Any]],
    *,
    as_of_observation_id: str,
    consumer_class: str,
    benchmark_mode: bool = False,
    anchor_observation_id: str | None = None,
    parent: Mapping[str, Any] | None = None,
    event: Mapping[str, Any] | None = None,
    predicates: Mapping[str, bool] | None = None,
    history_capacity: int | None = None,
) -> dict[str, Any]:
    """Evaluate one typed horizon without selecting any canonical numeric profile."""

    _require(not definition.template, "HORIZON_TEMPLATE_NOT_EXECUTABLE")
    _guard_consumer(definition, consumer_class, benchmark_mode)
    current = _find_current(observations, as_of_observation_id)
    items = _group(observations, current)
    index = next(i for i, item in enumerate(items) if item["observation_id"] == as_of_observation_id)
    current_time = _observation_time(current)
    if history_capacity is not None:
        _require(isinstance(history_capacity, int) and history_capacity >= 0, "HISTORY_CAPACITY")
        required = definition.count
        if definition.kind == "PAIRED_COMPARISON":
            required = int(definition.parameters["left_count"]) + int(definition.parameters["right_count"])
        if required is not None and history_capacity < required:
            return _not_computable(definition, current, "HISTORY_CAPACITY_INSUFFICIENT", {
                "history_capacity": history_capacity,
                "required_members": required,
                "history_capacity_is_horizon": False,
            })

    if definition.kind == "CURRENT":
        if not _eligible(current):
            return _not_computable(definition, current, "CURRENT_OBSERVATION_NOT_ELIGIBLE")
        return _membership(definition, current, [current])

    if definition.kind == "TRANSITION":
        selected, reason = _tail_same_segment(items, index, 2)
        if selected is None:
            return _not_computable(definition, current, reason)
        return _membership(definition, current, selected, metadata={"previous_observation_id": selected[0]["observation_id"], "current_observation_id": selected[1]["observation_id"]})

    if definition.kind == "TRAILING_COUNT":
        selected, reason = _tail_same_segment(items, index, int(definition.count))
        if selected is None:
            return _not_computable(definition, current, reason, {"requested_count": definition.count})
        return _membership(definition, current, selected, metadata={"requested_count": definition.count})

    if definition.kind == "PAIRED_COMPARISON":
        left_count = int(definition.parameters["left_count"])
        right_count = int(definition.parameters["right_count"])
        selected, reason = _tail_same_segment(items, index, left_count + right_count)
        if selected is None:
            return _not_computable(definition, current, reason, {"left_count": left_count, "right_count": right_count})
        left = selected[:left_count]
        right = selected[left_count:]
        return _membership(definition, current, selected, metadata={
            "left_observation_ids": [item["observation_id"] for item in left],
            "right_observation_ids": [item["observation_id"] for item in right],
            "left_count": left_count,
            "right_count": right_count,
        })

    if definition.kind == "CONFIRMATION_DELAY":
        if anchor_observation_id is None:
            return _not_computable(definition, current, "ANCHOR_REQUIRED")
        anchors = [i for i, item in enumerate(items) if item["observation_id"] == anchor_observation_id]
        if not anchors:
            return _not_computable(definition, current, "ANCHOR_NOT_FOUND")
        anchor_index = anchors[0]
        if anchor_index > index:
            return _not_computable(definition, current, "ANCHOR_AFTER_AS_OF")
        selected = items[anchor_index:index + 1]
        if not all(_eligible(item) for item in selected) or len({item.get("continuity", {}).get("segment_id") for item in selected}) != 1:
            return _not_computable(definition, current, "ANCHOR_NOT_IN_SEGMENT")
        observed_delay = index - anchor_index
        if observed_delay < int(definition.count):
            return _not_computable(definition, current, "CONFIRMATION_DELAY_NOT_MET", {"observed_delay": observed_delay, "required_delay": definition.count})
        return _membership(definition, current, selected, metadata={"anchor_observation_id": anchor_observation_id, "observed_delay": observed_delay, "required_delay": definition.count})

    if definition.kind == "RUN_LENGTH":
        if predicates is None:
            return _not_computable(definition, current, "PREDICATE_REQUIRED")
        if not _eligible(current):
            return _not_computable(definition, current, "CURRENT_OBSERVATION_NOT_ELIGIBLE")
        segment_id = current.get("continuity", {}).get("segment_id")
        run: list[dict[str, Any]] = []
        cursor = index
        while cursor >= 0:
            item = items[cursor]
            if not _eligible(item) or item.get("continuity", {}).get("segment_id") != segment_id:
                break
            if not bool(predicates.get(str(item["observation_id"]), False)):
                break
            run.append(item)
            cursor -= 1
        run.reverse()
        return _membership(definition, current, run, metadata={"run_length": len(run), "typed_time": TypedTimeValue("OBSERVATION_COUNT", len(run), "OBSERVATION", definition.grain, definition.version, definition.source_basis, definition.applicability_scope).to_dict()})

    if definition.kind == "AGE":
        if anchor_observation_id is None:
            return _not_computable(definition, current, "ANCHOR_REQUIRED")
        anchors = [i for i, item in enumerate(items) if item["observation_id"] == anchor_observation_id]
        if not anchors:
            return _not_computable(definition, current, "ANCHOR_NOT_FOUND")
        anchor_index = anchors[0]
        if anchor_index > index:
            return _not_computable(definition, current, "ANCHOR_AFTER_AS_OF")
        anchor = items[anchor_index]
        if definition.semantic_type == "OBSERVATION_COUNT":
            value: int | float = index - anchor_index
            unit = "OBSERVATION"
        elif definition.semantic_type == "CALENDAR_DURATION":
            seconds = (current_time - _observation_time(anchor)).total_seconds()
            requested_unit = definition.unit.upper()
            divisors = {"SECOND": 1.0, "MINUTE": 60.0, "HOUR": 3600.0, "DAY": 86400.0}
            _require(requested_unit in divisors, "UNSUPPORTED_TIME_SEMANTIC")
            value = seconds / divisors[requested_unit]
            unit = requested_unit
        else:
            return _not_computable(definition, current, "UNSUPPORTED_TIME_SEMANTIC")
        typed = TypedTimeValue(definition.semantic_type, value, unit, definition.grain, definition.version, definition.source_basis, definition.applicability_scope)
        return _membership(definition, current, [anchor, current] if anchor_index != index else [current], metadata={"anchor_observation_id": anchor_observation_id, "age": typed.to_dict()})

    if definition.kind == "AS_OF_PARENT":
        if parent is None:
            return _not_computable(definition, current, "PARENT_REQUIRED")
        parent_first_valid = parse_time(str(parent["first_valid_time"]))
        if parent_first_valid > current_time:
            return _not_computable(definition, current, "PARENT_NOT_AVAILABLE_AS_OF", {"parent_id": parent.get("parent_id"), "parent_first_valid_time": iso(parent_first_valid)})
        return _membership(definition, current, [current], metadata={"parent_id": parent.get("parent_id"), "parent_first_valid_time": iso(parent_first_valid), "parent_age_seconds": (current_time - parent_first_valid).total_seconds()})

    if definition.kind == "EVENT_RELATIVE_VARIABLE":
        if event is None:
            return _not_computable(definition, current, "EVENT_REQUIRED")
        event_first_valid = parse_time(str(event["first_valid_time"]))
        if event_first_valid > current_time:
            return _not_computable(definition, current, "EVENT_NOT_AVAILABLE_AS_OF", {"event_id": event.get("event_id")})
        start_id = event.get("start_observation_id")
        if not isinstance(start_id, str):
            return _not_computable(definition, current, "ANCHOR_REQUIRED")
        starts = [i for i, item in enumerate(items) if item["observation_id"] == start_id]
        if not starts or starts[0] > index:
            return _not_computable(definition, current, "EVENT_NOT_IN_SEGMENT")
        selected = items[starts[0]:index + 1]
        if not all(_eligible(item) for item in selected) or len({item.get("continuity", {}).get("segment_id") for item in selected}) != 1:
            return _not_computable(definition, current, "EVENT_NOT_IN_SEGMENT")
        closing_time = event.get("end_first_valid_time")
        if closing_time is not None and parse_time(str(closing_time)) > current_time:
            return _not_computable(definition, current, "EVENT_NOT_AVAILABLE_AS_OF")
        return _membership(definition, current, selected, metadata={"event_id": event.get("event_id"), "event_first_valid_time": iso(event_first_valid), "event_closed_as_of": closing_time is None or parse_time(str(closing_time)) <= current_time})

    if definition.kind == "FORWARD_OUTCOME":
        count = int(definition.count)
        future = items[index + 1:index + 1 + count]
        if len(future) < count:
            return _not_computable(definition, current, "PARTIAL_WINDOW", {"requested_count": count, "available_count": len(future)})
        if not all(_eligible(item) for item in future):
            return _not_computable(definition, current, _reason_for_segment_break(future))
        segment_id = current.get("continuity", {}).get("segment_id")
        if segment_id is None or any(item.get("continuity", {}).get("segment_id") != segment_id for item in future):
            return _not_computable(definition, current, "DISCONTINUITY")
        return _membership(definition, current, future, status="BENCHMARK_ONLY", reason="RETROSPECTIVE_ONLY", metadata={"requested_count": count, "label_start": future[0]["first_valid_time"], "label_end": future[-1]["first_valid_time"]}, available_at=future[-1]["first_valid_time"])

    raise HorizonContractError("HORIZON_KIND_NOT_IMPLEMENTED")


def assert_causal_store_record(record: Mapping[str, Any]) -> None:
    """Technical leakage guard for any record proposed for a causal store."""

    _require(record.get("status") == "COMPUTABLE", "CAUSAL_STORE_REQUIRES_COMPUTABLE")
    _require(record.get("causal_store_eligible") is True, "CAUSAL_STORE_RETROSPECTIVE_RECORD")
    _require(record.get("benchmark_only") is False, "CAUSAL_STORE_BENCHMARK_RECORD")
    as_of = parse_time(str(record["as_of_first_valid_time"]))
    available_at = parse_time(str(record.get("available_at", record["as_of_first_valid_time"])))
    _require(available_at <= as_of, "CAUSAL_STORE_FUTURE_AVAILABILITY")
    for member_time in record.get("member_first_valid_times", []):
        _require(parse_time(str(member_time)) <= as_of, "CAUSAL_STORE_FUTURE_MEMBER")
    prohibited = {"forward_outcome", "future_value", "outcome_label"}
    _require(not prohibited.intersection(record), "CAUSAL_STORE_PROHIBITED_FIELD")


def build_benchmark_envelope(
    membership: Mapping[str, Any],
    *,
    source_population_id: str,
    method_id: str,
    comparator_id: str,
) -> dict[str, Any]:
    _require(membership.get("status") == "BENCHMARK_ONLY", "BENCHMARK_MEMBERSHIP_REQUIRED")
    _require(membership.get("benchmark_only") is True, "BENCHMARK_ONLY_REQUIRED")
    body = {
        "schema": "c2_horizon_benchmark_envelope/vnext-r1",
        "membership_id": membership["membership_id"],
        "source_population_id": source_population_id,
        "method_id": method_id,
        "comparator_id": comparator_id,
        "as_of_first_valid_time": membership["as_of_first_valid_time"],
        "available_at": membership["available_at"],
        "label_member_observation_ids": list(membership["member_observation_ids"]),
        "causal_store_eligible": False,
        "benchmark_only": True,
        "authority": "RESEARCH_RETROSPECTIVE_ONLY",
    }
    return {"benchmark_envelope_id": digest("C2.HORIZON.BENCHMARK", body), **body}


def build_discrepancy_record(
    *,
    domain: str,
    declared: Mapping[str, Any],
    implemented: Mapping[str, Any],
    redesign_candidate: Mapping[str, Any],
    source_refs: Sequence[str],
) -> dict[str, Any]:
    _require(domain in {"MOTION", "ORGANISATION"}, "DISCREPANCY_DOMAIN")
    _require(bool(source_refs), "DISCREPANCY_SOURCE_REFS")
    body = {
        "domain": domain,
        "legacy_declared": copy.deepcopy(dict(declared)),
        "legacy_implemented": copy.deepcopy(dict(implemented)),
        "redesign_candidate": copy.deepcopy(dict(redesign_candidate)),
        "source_refs": list(source_refs),
        "automatic_reconciliation": False,
        "canonical_numeric_selection": False,
        "authority": "EVIDENCE_ONLY",
    }
    body["reproduction_sha256"] = hashlib.sha256(canonical_bytes(body)).hexdigest()
    return {"discrepancy_id": digest("C2.HORIZON.DISCREPANCY", body), **body}


def validate_history_capacity_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
    _require("capacity" in value, "HISTORY_CAPACITY_REQUIRED")
    capacity = value["capacity"]
    _require(isinstance(capacity, int) and not isinstance(capacity, bool) and capacity >= 0, "HISTORY_CAPACITY")
    _require(value.get("is_measurement_horizon") is False, "HISTORY_CAPACITY_IS_NOT_HORIZON")
    _require(value.get("selection_effect") == "NONE", "HISTORY_CAPACITY_SELECTION_EFFECT")
    return copy.deepcopy(dict(value))


def compact_membership_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    reasons: dict[str, int] = {}
    for record in records:
        status = str(record["status"])
        reason = str(record["reason"])
        statuses[status] = statuses.get(status, 0) + 1
        reasons[reason] = reasons.get(reason, 0) + 1
    body = {
        "record_count": len(records),
        "status_counts": dict(sorted(statuses.items())),
        "reason_counts": dict(sorted(reasons.items())),
        "causal_store_eligible_count": sum(1 for item in records if item.get("causal_store_eligible") is True),
        "benchmark_only_count": sum(1 for item in records if item.get("benchmark_only") is True),
    }
    return {**body, "summary_sha256": hashlib.sha256(canonical_bytes(body)).hexdigest()}
