"""Inactive read-only observability implementation for OVC System Atlas.

The namespace creates no active observability reliance or source admission. It
creates no write route, Validation access, scientific semantics, publication,
or execution authority. Every derived graph and projection fails closed at
those boundaries.
"""

from .canonical import canonical_json_bytes, canonical_sha256, graph_logical_hash, logical_id
from .core import AtlasContractError, build_system_graph, validate_system_graph

__all__ = [
    "AtlasContractError",
    "build_system_graph",
    "canonical_json_bytes",
    "canonical_sha256",
    "graph_logical_hash",
    "logical_id",
    "validate_system_graph",
]
