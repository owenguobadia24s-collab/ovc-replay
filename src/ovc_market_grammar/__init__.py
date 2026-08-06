"""Inactive, noncanonical market-grammar research components."""

from .predicate_domains import (
    ComponentClass,
    ComponentStats,
    ExclusivityRule,
    PredicateDomain,
    classify_component,
    infer_domain,
    migrate_legacy_component,
    validate_exclusivity_rule,
    validate_predicate_domain,
)

__all__ = [
    "ComponentClass",
    "ComponentStats",
    "ExclusivityRule",
    "PredicateDomain",
    "classify_component",
    "infer_domain",
    "migrate_legacy_component",
    "validate_exclusivity_rule",
    "validate_predicate_domain",
]
