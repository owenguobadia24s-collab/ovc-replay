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
from .resolver import (
    AtlasResolverError,
    relationship_resolution_state,
    resolve_current_vit_projection,
    resolve_reference_candidates,
)
from .generation import (
    AtlasGenerationError,
    GenerationBundle,
    build_incremental_generation,
    build_reference_generation,
    derive_source_currentness_proofs,
    generation_equivalence_receipt,
    load_generation_bundle,
    materialize_generation,
    publish_current_generation,
    retention_inventory,
    verify_generation_bundle,
)
from .store import AtlasGraphStoreError, GraphStore
from .query import (
    AtlasQueryError,
    AtlasQueryIndex,
    QUERY_FAMILIES,
    execute_optimized_query,
    execute_reference_query,
    query_equivalence_receipt,
)
from .qualification import (
    AtlasQualificationError,
    build_exact_git_shadow_graph,
    build_qualification_report,
    evaluate_operational_budget,
    evaluate_retention_budget,
    measure_operational_profile,
    prove_exact_current_publication_shadow,
    scan_retention_inventory,
    validate_live_shadow_binding,
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
    "AtlasResolverError",
    "relationship_resolution_state",
    "resolve_current_vit_projection",
    "resolve_reference_candidates",
    "validate_system_graph",
    "AtlasGenerationError",
    "GenerationBundle",
    "build_incremental_generation",
    "build_reference_generation",
    "derive_source_currentness_proofs",
    "generation_equivalence_receipt",
    "load_generation_bundle",
    "materialize_generation",
    "publish_current_generation",
    "retention_inventory",
    "verify_generation_bundle",
    "AtlasGraphStoreError",
    "GraphStore",
    "AtlasQueryError",
    "AtlasQueryIndex",
    "QUERY_FAMILIES",
    "execute_optimized_query",
    "execute_reference_query",
    "query_equivalence_receipt",
    "AtlasQualificationError",
    "build_exact_git_shadow_graph",
    "build_qualification_report",
    "evaluate_operational_budget",
    "evaluate_retention_budget",
    "measure_operational_profile",
    "prove_exact_current_publication_shadow",
    "scan_retention_inventory",
    "validate_live_shadow_binding",
]
