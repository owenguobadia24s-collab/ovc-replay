"""C2S-SPTO inactive repository-conformance machinery.

This namespace is research-only and non-authoritative.  It grants no
real-source access, market/selector activation, candidate freeze, semantic
promotion, Validation consumption, canonical publication, probability, risk,
exposure, trading, execution, or agent-write authority.  Every boundary fails
closed.
"""

from .source_binding import (
    C2OwnerStreamBinding,
    FactorisedSourceBindingManifest,
    SPTOBindingError,
    adapt_owner_snapshot,
    build_c2_owner_stream_binding,
    build_factorised_source_binding_manifest,
    resolve_owner_read_surface,
)

__all__ = [
    "C2OwnerStreamBinding",
    "FactorisedSourceBindingManifest",
    "SPTOBindingError",
    "adapt_owner_snapshot",
    "build_c2_owner_stream_binding",
    "build_factorised_source_binding_manifest",
    "resolve_owner_read_surface",
]
