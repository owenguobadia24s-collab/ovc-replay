"""RCCR is a Research Operations research-only, non-authoritative synthesis namespace.

It owns deterministic coverage/capability synthesis mechanics only. It grants no market,
selector, capability activation, scientific promotion, Validation, publication, execution authority,
or agent-write authority. Missing owner evidence or authority must fail closed.
"""

from .core import (
    RCCRAppendOnlyStore,
    RCCRValidationError,
    canonical_json_bytes,
    logical_identity,
    validate_canonical_object,
)
from .source_resolution import (
    DERIVATION_MODES,
    RequirementDependencyIndex,
    RequirementProfileCompiler,
    ResolvedSource,
    SourceResolverService,
    project_currentness,
)

__all__ = [
    "DERIVATION_MODES",
    "RCCRAppendOnlyStore",
    "RCCRValidationError",
    "RequirementDependencyIndex",
    "RequirementProfileCompiler",
    "ResolvedSource",
    "SourceResolverService",
    "canonical_json_bytes",
    "logical_identity",
    "project_currentness",
    "validate_canonical_object",
]
