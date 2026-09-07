"""C2S-SPTO conformance machinery.

The package is inactive repository qualification infrastructure.  It grants no
real-source, candidate-generation, semantic, Validation, or publication
authority.
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
