"""ASOCS audit-only research operations."""

from .instrumentation import (
    ASOCSInstrumentationError,
    InstrumentationObservation,
    logical_scientific_hash,
    observe_record,
    prove_chain_equivalence,
)
from .population import (
    ASOCSPopulationError,
    MaterializationResult,
    materialize_population,
    render_source_native_svg,
)
from .source import (
    ASOCSSourceGap,
    ASOCSSourceManifest,
    ASOCSSourceQualificationError,
    ClaimClassDecision,
    SourceProvenanceAssessment,
    exact_interface_evaluability_matrix,
    qualify_source,
)

__all__ = [
    "ASOCSInstrumentationError",
    "ASOCSPopulationError",
    "ASOCSSourceGap",
    "ASOCSSourceManifest",
    "ASOCSSourceQualificationError",
    "ClaimClassDecision",
    "InstrumentationObservation",
    "MaterializationResult",
    "SourceProvenanceAssessment",
    "exact_interface_evaluability_matrix",
    "logical_scientific_hash",
    "materialize_population",
    "observe_record",
    "prove_chain_equivalence",
    "qualify_source",
    "render_source_native_svg",
]
