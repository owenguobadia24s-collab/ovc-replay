"""CBS research-only, synthetic/conformance implementation.

This namespace is non-authoritative: it grants no real-source Development,
market or selector authority, C2E boundary-pack selection/replacement or
activation authority, Validation consumption, canonical publication,
probability, risk, exposure, trading, execution, or agent-write authority.
Missing owner source/authority or a reserved gate fails closed.
"""

from .identity import CBSContractError, canonical_bytes, canonical_id, seal_object, verify_object

__all__ = ["CBSContractError", "canonical_bytes", "canonical_id", "seal_object", "verify_object"]
