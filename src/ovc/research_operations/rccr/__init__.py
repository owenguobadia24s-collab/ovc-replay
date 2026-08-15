"""RCCR is a Research Operations research-only, non-authoritative synthesis namespace.

It owns deterministic coverage/capability synthesis mechanics only. It grants no market,
selector, capability activation, scientific promotion, Validation, publication, execution
authority, or agent-write authority. Missing owner evidence or authority must fail closed.
"""

from .core import (
    RCCRAppendOnlyStore,
    RCCRValidationError,
    canonical_json_bytes,
    logical_identity,
    validate_canonical_object,
)

__all__ = [
    "RCCRAppendOnlyStore",
    "RCCRValidationError",
    "canonical_json_bytes",
    "logical_identity",
    "validate_canonical_object",
]
