"""OPT-B Empirical Structural Language common contracts (ESLI-WP1).

Inactive deterministic conformance-only namespace. This package grants no active market
or selector authority, no canonical representation or family promotion, no semantic-promotion,
no Validation consumption, and no probability, risk, exposure, execution authority, or
agent-write authority. It fails closed at the ratified ESL boundary.
"""

from .model import (
    ComparabilityDomain,
    DependencyRef,
    DependencyRole,
    EvidenceFrontier,
    EvidenceState,
    ExecutionProfile,
    GenerationCorrespondence,
    OccurrenceAnchor,
    OccurrencePack,
    StructuralDimension,
    StructuralFacet,
    StructuralOccurrenceRecord,
)
from .soi_compat import (
    SOICompatibilityError,
    SOIFamilyAdapterBinding,
    SOITopologyEntry,
    TOPOLOGY_IDS,
    adapt_family_catalog,
    family_binding_from_mapping,
    invoke_soi_topology,
    topology_registry_from_mapping,
)
from .organisation_evidence import (
    OrganisationEvidenceError,
    apply_organisation_decision_rule_pack,
    assemble_organisation_evidence_set,
    assert_no_stable_organisation_claim_lawful,
    build_correspondence_edge,
    build_disagreement_record,
    build_invariant_evidence_record,
    build_metric_record,
    validate_decision_rule_pack_interface,
)
from .validators import ESLValidationError, validate_occurrence

__all__ = [
    "ComparabilityDomain",
    "DependencyRef",
    "DependencyRole",
    "EvidenceFrontier",
    "EvidenceState",
    "ExecutionProfile",
    "GenerationCorrespondence",
    "OccurrenceAnchor",
    "OccurrencePack",
    "StructuralDimension",
    "StructuralFacet",
    "StructuralOccurrenceRecord",
    "SOICompatibilityError",
    "SOIFamilyAdapterBinding",
    "SOITopologyEntry",
    "TOPOLOGY_IDS",
    "adapt_family_catalog",
    "family_binding_from_mapping",
    "invoke_soi_topology",
    "topology_registry_from_mapping",
    "OrganisationEvidenceError",
    "apply_organisation_decision_rule_pack",
    "assemble_organisation_evidence_set",
    "assert_no_stable_organisation_claim_lawful",
    "build_correspondence_edge",
    "build_disagreement_record",
    "build_invariant_evidence_record",
    "build_metric_record",
    "validate_decision_rule_pack_interface",
    "ESLValidationError",
    "validate_occurrence",
]
