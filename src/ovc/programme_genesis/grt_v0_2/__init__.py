"""GRT v0.2 repository-conformance implementation package.

The package remains non-enforcing until separately reserved GRT2-G2.5/G3
operator decisions.  WP0 exposes read-only exact-source reconciliation only.
"""

from .wp0 import (
    B0_SOURCE_COMMIT,
    B0_SOURCE_TREE,
    B0_TOPOLOGY_SHA256,
    B0_WARNING_COUNT,
    WP0ReconciliationError,
    reconcile,
    write_reconciliation_outputs,
)

__all__ = [
    "B0_SOURCE_COMMIT",
    "B0_SOURCE_TREE",
    "B0_TOPOLOGY_SHA256",
    "B0_WARNING_COUNT",
    "WP0ReconciliationError",
    "reconcile",
    "write_reconciliation_outputs",
]
