"""Typed predicate domains, exclusivity proof and component classification.

This module is intentionally inactive and noncanonical. It provides deterministic
research computation for MG-WP1 only; it does not activate a grammar, family,
selector, rule or semantic interpretation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence


class PredicateDomain(str, Enum):
    STRUCTURAL = "STRUCTURAL"
    TEMPORAL = "TEMPORAL"
    OBJECT_BINDING = "OBJECT_BINDING"
    CONTEXT = "CONTEXT"
    COMPUTABILITY = "COMPUTABILITY"
    PROVENANCE = "PROVENANCE"


class ComponentClass(str, Enum):
    INVARIANT = "INVARIANT"
    COMMON = "COMMON"
    NORMAL_VARIATION = "NORMAL_VARIATION"
    HIGH_CARDINALITY_VARIATION = "HIGH_CARDINALITY_VARIATION"
    MISSINGNESS_VARIATION = "MISSINGNESS_VARIATION"
    LOGICAL_CONFLICT = "LOGICAL_CONFLICT"
    OPTIONAL = "OPTIONAL"
    RARE = "RARE"


_ALLOWED_OBJECT_SCOPES = frozenset(
    {"STATE_RECORD", "RELATION_RECORD", "EPISODE_RECORD", "PARSE_NODE"}
)
_PROVENANCE_EXACT = frozenset(
    {
        "source_release_id",
        "manifest_id",
        "record_id",
        "content_sha256",
        "provider_name",
        "source_object_id",
        "run_id",
        "commit_sha",
    }
)
_COMPUTABILITY_EXACT = frozenset(
    {
        "missingness",
        "computability_status",
        "quality_status",
        "not_evaluable_reason",
        "censoring_status",
    }
)
_TEMPORAL_EXACT = frozenset(
    {
        "first_valid_time",
        "duration",
        "duration_bars",
        "ordinal",
        "sequence_index",
        "start_time",
        "end_time",
        "closed_time",
    }
)
_OBJECT_BINDING_EXACT = frozenset(
    {
        "object_id",
        "parent_record_id",
        "parent_record_ids",
        "relation_id",
        "episode_id",
        "level_id",
        "container_id",
    }
)
_CONTEXT_EXACT = frozenset(
    {
        "clock_id",
        "instrument_id",
        "session_id",
        "context_clock_id",
        "parent_clock_id",
        "market_day_id",
    }
)


def _normalise_key(feature_key: str) -> str:
    key = feature_key.strip().lower()
    if not key:
        raise ValueError("feature_key must be non-empty")
    return key


def infer_domain(feature_key: str) -> PredicateDomain:
    """Infer the only lawful default domain for a named field."""

    key = _normalise_key(feature_key)
    leaf = key.rsplit(".", 1)[-1]
    if (
        leaf in _PROVENANCE_EXACT
        or leaf.startswith(("source_", "provider_", "manifest_"))
        or leaf.endswith(("_sha256", "_hash", "_record_id"))
    ):
        return PredicateDomain.PROVENANCE
    if leaf in _COMPUTABILITY_EXACT or leaf.startswith("missing_"):
        return PredicateDomain.COMPUTABILITY
    if leaf in _TEMPORAL_EXACT or leaf.endswith(("_time", "_duration")):
        return PredicateDomain.TEMPORAL
    if leaf in _OBJECT_BINDING_EXACT or leaf.endswith(("_object_id", "_episode_id")):
        return PredicateDomain.OBJECT_BINDING
    if leaf in _CONTEXT_EXACT or leaf.endswith("_clock_id"):
        return PredicateDomain.CONTEXT
    return PredicateDomain.STRUCTURAL


def validate_predicate_domain(
    feature_key: str,
    requested_domain: PredicateDomain | str,
) -> PredicateDomain:
    """Validate a declared domain and block provenance contamination."""

    domain = PredicateDomain(requested_domain)
    inferred = infer_domain(feature_key)
    if domain is PredicateDomain.STRUCTURAL and inferred is not PredicateDomain.STRUCTURAL:
        raise ValueError(
            f"{feature_key!r} is reserved for {inferred.value} and cannot be STRUCTURAL"
        )
    return domain


@dataclass(frozen=True)
class ComponentStats:
    feature_key: str
    domain: PredicateDomain
    object_scope: str
    clock_id: str
    first_valid_time: str
    total_eligible: int
    missing_count: int
    value_counts: Mapping[str, int]

    def __post_init__(self) -> None:
        object.__setattr__(self, "domain", PredicateDomain(self.domain))
        object.__setattr__(self, "feature_key", _normalise_key(self.feature_key))
        object.__setattr__(self, "object_scope", self.object_scope.strip().upper())
        object.__setattr__(self, "clock_id", self.clock_id.strip())
        object.__setattr__(self, "first_valid_time", self.first_valid_time.strip())
        frozen_counts = MappingProxyType(
            dict(sorted((str(key), int(value)) for key, value in self.value_counts.items()))
        )
        object.__setattr__(self, "value_counts", frozen_counts)
        self.validate()

    @property
    def present_count(self) -> int:
        return sum(self.value_counts.values())

    @property
    def absent_count(self) -> int:
        return self.total_eligible - self.missing_count - self.present_count

    @property
    def distinct_count(self) -> int:
        return sum(1 for value in self.value_counts.values() if value > 0)

    @property
    def present_ratio(self) -> float:
        return 0.0 if self.total_eligible == 0 else self.present_count / self.total_eligible

    @property
    def positive_values(self) -> tuple[str, ...]:
        return tuple(key for key, count in self.value_counts.items() if count > 0)

    def validate(self) -> None:
        validate_predicate_domain(self.feature_key, self.domain)
        if self.object_scope not in _ALLOWED_OBJECT_SCOPES:
            raise ValueError(f"unsupported object_scope: {self.object_scope}")
        if not self.clock_id:
            raise ValueError("clock_id must be non-empty")
        if not self.first_valid_time:
            raise ValueError("first_valid_time must be non-empty")
        if self.total_eligible < 0 or self.missing_count < 0:
            raise ValueError("counts must be non-negative")
        if any(count < 0 for count in self.value_counts.values()):
            raise ValueError("value counts must be non-negative")
        if self.present_count + self.missing_count > self.total_eligible:
            raise ValueError("present + missing exceeds total_eligible")


@dataclass(frozen=True)
class ExclusivityRule:
    rule_id: str
    feature_key: str
    domain: PredicateDomain
    object_scope: str
    clock_scope: str
    time_scope: str
    mutually_exclusive_values: tuple[str, ...]
    registry_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", self.rule_id.strip())
        object.__setattr__(self, "feature_key", _normalise_key(self.feature_key))
        object.__setattr__(self, "domain", PredicateDomain(self.domain))
        object.__setattr__(self, "object_scope", self.object_scope.strip().upper())
        object.__setattr__(self, "clock_scope", self.clock_scope.strip().upper())
        object.__setattr__(self, "time_scope", self.time_scope.strip().upper())
        values = tuple(sorted({str(value).strip() for value in self.mutually_exclusive_values}))
        object.__setattr__(self, "mutually_exclusive_values", values)
        object.__setattr__(self, "registry_version", self.registry_version.strip())
        validate_exclusivity_rule(self)


def validate_exclusivity_rule(rule: ExclusivityRule) -> ExclusivityRule:
    if not rule.rule_id or not rule.registry_version:
        raise ValueError("rule_id and registry_version are required")
    validate_predicate_domain(rule.feature_key, rule.domain)
    if rule.domain in {PredicateDomain.PROVENANCE, PredicateDomain.COMPUTABILITY}:
        raise ValueError("provenance/computability fields cannot prove logical conflict")
    if rule.object_scope not in _ALLOWED_OBJECT_SCOPES:
        raise ValueError(f"unsupported object_scope: {rule.object_scope}")
    if rule.clock_scope != "SAME_CLOCK":
        raise ValueError("clock_scope must be SAME_CLOCK")
    if rule.time_scope != "EXACT_FIRST_VALID_TIME":
        raise ValueError("time_scope must be EXACT_FIRST_VALID_TIME")
    if any("*" in value for value in (rule.rule_id, rule.feature_key, rule.object_scope)):
        raise ValueError("wildcards are forbidden in exclusivity scope")
    if len(rule.mutually_exclusive_values) < 2:
        raise ValueError("at least two mutually exclusive values are required")
    if any(not value for value in rule.mutually_exclusive_values):
        raise ValueError("exclusive values must be non-empty")
    return rule


def _matching_exclusivity_rule(
    stats: ComponentStats,
    rules: Iterable[ExclusivityRule],
) -> ExclusivityRule | None:
    observed = set(stats.positive_values)
    if len(observed) < 2:
        return None
    for rule in sorted(rules, key=lambda item: item.rule_id):
        validate_exclusivity_rule(rule)
        if (
            rule.feature_key == stats.feature_key
            and rule.domain is stats.domain
            and rule.object_scope == stats.object_scope
            and observed.issubset(set(rule.mutually_exclusive_values))
        ):
            return rule
    return None


def classify_component(
    stats: ComponentStats,
    exclusivity_rules: Sequence[ExclusivityRule] = (),
) -> ComponentClass:
    """Classify a component without conflating frequency and contradiction."""

    stats.validate()
    if (
        stats.total_eligible > 0
        and stats.present_count == stats.total_eligible
        and stats.missing_count == 0
        and stats.distinct_count == 1
    ):
        return ComponentClass.INVARIANT
    if _matching_exclusivity_rule(stats, exclusivity_rules) is not None:
        return ComponentClass.LOGICAL_CONFLICT
    if stats.missing_count > 0 and stats.present_count > 0:
        return ComponentClass.MISSINGNESS_VARIATION
    if stats.distinct_count >= 8 or (
        stats.present_count >= 8
        and stats.distinct_count / max(stats.present_count, 1) >= 0.5
    ):
        return ComponentClass.HIGH_CARDINALITY_VARIATION
    if stats.distinct_count > 1:
        return ComponentClass.NORMAL_VARIATION
    if stats.present_ratio >= 0.7:
        return ComponentClass.COMMON
    if stats.present_ratio >= 0.2:
        return ComponentClass.OPTIONAL
    return ComponentClass.RARE


def migrate_legacy_component(
    legacy_class: str,
    stats: ComponentStats,
    exclusivity_rules: Sequence[ExclusivityRule] = (),
) -> dict[str, object]:
    """Reclassify a legacy component; legacy CONTRADICTORY has no direct map."""

    new_class = classify_component(stats, exclusivity_rules)
    structural_eligible = stats.domain in {
        PredicateDomain.STRUCTURAL,
        PredicateDomain.TEMPORAL,
        PredicateDomain.OBJECT_BINDING,
        PredicateDomain.CONTEXT,
    }
    return {
        "legacy_class": legacy_class.strip().upper(),
        "new_class": new_class.value,
        "domain": stats.domain.value,
        "structural_eligible": structural_eligible,
        "reason": (
            "EXACT_EXCLUSIVITY_PROOF"
            if new_class is ComponentClass.LOGICAL_CONFLICT
            else "RECOMPUTED_WITH_TYPED_COMPONENT_CLASSIFIER"
        ),
    }
