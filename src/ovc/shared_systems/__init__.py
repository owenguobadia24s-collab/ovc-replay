"""OVC Shared Systems v0.1 inactive/reference implementation only.

This package exposes Stage-0 deterministic bootstrap/reference machinery. It does not activate a Shared Systems runtime,
replace or restrict any current consumer path, create a new source/provider/research role, grant scientific or semantic
promotion, consume Validation, publish canon/R2, or grant probability, risk, exposure, execution, or agent-write authority.
Missing authority fails closed.
"""

from .stage0 import (
    BOOTSTRAP_NODES,
    NORMATIVE_EDGES,
    SharedSystemsStage0Error,
    build_stage0_proof,
    canonical_json_bytes,
    logical_hash,
    stage1_ready,
    verify_binding_registry,
)

__all__ = [
    "BOOTSTRAP_NODES",
    "NORMATIVE_EDGES",
    "SharedSystemsStage0Error",
    "build_stage0_proof",
    "canonical_json_bytes",
    "logical_hash",
    "stage1_ready",
    "verify_binding_registry",
]
