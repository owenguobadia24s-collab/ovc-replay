"""EC1 Post-Recurrence Scientific Challenge (PRSC) Research Operations namespace.

Research-only, non-authoritative challenge machinery. This package grants no market
or selector authority, no candidate-freeze or activation authority, no Validation or
publication authority, and no probability/risk/exposure/execution authority or
agent-write authority. Real-source PRSC challenge remains separately gated; missing
authority fails closed.
"""
from .contracts import (
    CHALLENGE_DIMENSIONS,
    PRSCContractError,
    adapt_ec1_record,
    build_protocol_generation,
    semantic_id,
)
from .dependence import (
    DependenceGraphView,
    adapt_evidence_dependence_graph,
    build_candidate_dependence_profile,
    build_inference_block_manifest,
    leave_one_component_out,
)
from .reference import (
    build_negative_space_controls,
    build_reference_method_pack,
    dependency_preserving_block_resample,
    hac_ordered_secondary,
    validate_reference_preservation,
)
from .representation import (
    build_candidate_invariant_core,
    build_invariance_contract,
    build_population_crosswalk,
    build_representation_challenge_pack,
    directional_correspondence,
)
from .temporal import (
    build_context_challenge_pack,
    build_temporal_challenge_pack,
    build_temporal_context_stability_matrix,
    build_temporal_support_profile,
    leave_one_block_out_support,
    within_discovery_forward_support,
)

__all__ = [
    "CHALLENGE_DIMENSIONS", "PRSCContractError", "adapt_ec1_record",
    "build_protocol_generation", "semantic_id", "DependenceGraphView",
    "adapt_evidence_dependence_graph", "build_candidate_dependence_profile",
    "build_inference_block_manifest", "leave_one_component_out",
    "build_negative_space_controls", "build_reference_method_pack",
    "dependency_preserving_block_resample", "hac_ordered_secondary",
    "validate_reference_preservation", "build_candidate_invariant_core",
    "build_invariance_contract", "build_population_crosswalk",
    "build_representation_challenge_pack", "directional_correspondence",
    "build_context_challenge_pack", "build_temporal_challenge_pack",
    "build_temporal_context_stability_matrix", "build_temporal_support_profile",
    "leave_one_block_out_support", "within_discovery_forward_support",
]
