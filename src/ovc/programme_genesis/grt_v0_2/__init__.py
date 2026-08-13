"""GRT v0.2 repository-conformance implementation package.

The package remains non-enforcing until separately reserved GRT2-G2.5/G3
operator decisions. WP0 exposes read-only exact-source reconciliation; WP1
materializes the inactive Repository Constitution candidate and finite
bootstrap validation surface. WP2 adds finding/baseline/debt mechanics.
"""

from .wp0 import (
    B0_SOURCE_COMMIT,
    B0_SOURCE_TREE,
    B0_TOPOLOGY_SHA256,
    B0_WARNING_COUNT,
    WP0ReconciliationError,
)
from .wp0_evidence import reconcile, write_reconciliation_outputs
from .bootstrap import (
    DIALECT,
    PROFILE_ID,
    VALIDATOR_RELEASE,
    BootstrapValidationError,
)
from .constitution import (
    CONSTITUTION_ID,
    CONSTITUTION_STATUS,
    build_registry_bundle,
    validate_committed_bundle,
)
from .serialization import (
    SERIALIZATION_ID,
    CanonicalJSONError,
    canonical_json_v1_bytes,
    canonical_json_v1_text,
    canonical_sha256,
)

__all__ = [
    "B0_SOURCE_COMMIT",
    "B0_SOURCE_TREE",
    "B0_TOPOLOGY_SHA256",
    "B0_WARNING_COUNT",
    "WP0ReconciliationError",
    "reconcile",
    "write_reconciliation_outputs",
    "DIALECT",
    "PROFILE_ID",
    "VALIDATOR_RELEASE",
    "BootstrapValidationError",
    "CONSTITUTION_ID",
    "CONSTITUTION_STATUS",
    "build_registry_bundle",
    "validate_committed_bundle",
    "SERIALIZATION_ID",
    "CanonicalJSONError",
    "canonical_json_v1_bytes",
    "canonical_json_v1_text",
    "canonical_sha256",
]
