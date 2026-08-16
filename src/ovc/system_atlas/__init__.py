"""Inactive read-only observability implementation for OVC System Atlas.

The namespace creates no active observability reliance or source admission. It
creates no write route, Validation access, scientific semantics, publication,
or execution authority. Every derived graph and projection fails closed at
those boundaries.
"""

from .canonical import canonical_json_bytes, canonical_sha256, graph_logical_hash, logical_id
from .core import AtlasContractError, build_system_graph, validate_system_graph
from .grt_adapter import AtlasGRTAdapterError, adapt_grt_topology, scan_grt_exact_tree
from .governed_extractors import AtlasGovernedExtractorError, extract_governed_sources
from .architecture import (
    AtlasArchitectureManifestError,
    architecture_manifest_observations,
    manifest_currentness_record,
    validate_architecture_manifest,
)

__all__ = [
    "AtlasContractError",
    "AtlasGRTAdapterError",
    "adapt_grt_topology",
    "build_system_graph",
    "canonical_json_bytes",
    "canonical_sha256",
    "graph_logical_hash",
    "logical_id",
    "scan_grt_exact_tree",
    "AtlasGovernedExtractorError",
    "extract_governed_sources",
    "AtlasArchitectureManifestError",
    "architecture_manifest_observations",
    "manifest_currentness_record",
    "validate_architecture_manifest",
    "validate_system_graph",
]
