"""SRFD shadow-only benchmark research package.

This namespace has no active market selector, canonical representation or family
authority, Validation authority, semantic-promotion authority, or execution authority.
It is fixture/local evidence infrastructure only until separately governed gates pass.
"""
from .serialization import canonical_json_bytes, logical_sha256, stable_id
from .schema import SRFDValidationError, validate_document, VALID_OBJECT_TYPES

__all__ = [
    "canonical_json_bytes",
    "logical_sha256",
    "stable_id",
    "SRFDValidationError",
    "validate_document",
    "VALID_OBJECT_TYPES",
]
