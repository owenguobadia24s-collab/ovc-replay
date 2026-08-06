"""Shadow-only market-grammar research namespace.

This package has no active market or selector authority, no canonical grammar,
no Validation or semantic-promotion authority, and no probability, risk,
exposure or execution authority.
"""

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
