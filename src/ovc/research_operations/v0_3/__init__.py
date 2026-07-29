"""Research Operations Foundation v0.3 C1 inspection services."""

from .c1_index import (
    AccessDenied,
    IndexContractError,
    build_c1_indexes,
    build_incremental_index_receipt,
    parse_formula_registry,
    validation_metadata_only,
)
from .computability import (
    ComputabilityAccessDenied,
    ComputabilityContractError,
    build_computability_profile,
    build_null_reason_profile,
)
from .formula_diff import (
    AcknowledgementRequired,
    ComparisonContractError,
    build_affected_surface_report,
    build_non_activating_evidence_header,
    compare_formula_versions,
    compare_release_outputs,
    comparison_preflight,
    create_comparison_acknowledgement,
    validate_comparison_acknowledgement,
)
from .lineage_adapters import (
    DOWNSTREAM_AUTHORITY_BANNER,
    LIVE_ROUTE_STATE,
    ProjectionContractError,
    ProjectionDenied,
    build_c1_console_projection,
    build_c1_fact_projection,
    build_c1_lineage_trace,
    build_downstream_trace_projection,
)
from .metamorphic import (
    MetamorphicContractError,
    contract_oracle,
    load_invariant_registry,
    run_metamorphic_assurance,
)

__all__ = [
    "AccessDenied",
    "AcknowledgementRequired",
    "ComparisonContractError",
    "ComputabilityAccessDenied",
    "ComputabilityContractError",
    "DOWNSTREAM_AUTHORITY_BANNER",
    "IndexContractError",
    "LIVE_ROUTE_STATE",
    "MetamorphicContractError",
    "ProjectionContractError",
    "ProjectionDenied",
    "build_affected_surface_report",
    "build_c1_console_projection",
    "build_c1_fact_projection",
    "build_c1_indexes",
    "build_c1_lineage_trace",
    "build_computability_profile",
    "build_downstream_trace_projection",
    "build_incremental_index_receipt",
    "build_non_activating_evidence_header",
    "build_null_reason_profile",
    "compare_formula_versions",
    "compare_release_outputs",
    "comparison_preflight",
    "contract_oracle",
    "create_comparison_acknowledgement",
    "load_invariant_registry",
    "parse_formula_registry",
    "run_metamorphic_assurance",
    "validate_comparison_acknowledgement",
    "validation_metadata_only",
]
