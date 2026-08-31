"""Historical C2-CSM reference conformance helpers.

This package owns no current C2 semantics or authority.
"""

from .source_census import (
    LOAD_BEARING_SEMANTICS,
    classify_source_completeness,
    validate_no_derived_semantic_promotion,
)

__all__ = [
    "LOAD_BEARING_SEMANTICS",
    "classify_source_completeness",
    "validate_no_derived_semantic_promotion",
]
