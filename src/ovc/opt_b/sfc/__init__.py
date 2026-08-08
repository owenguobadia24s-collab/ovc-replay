"""OVC SFC v0.1 conformance namespace.

This package is intentionally capability-only. It wraps finalized C2E producer
artifacts and existing SRFD backends without selecting scientific methods,
family catalogues, selectors, publication routes or exposure semantics.
"""

from .serialization import canonical_json_bytes, logical_hash, assert_allowed_keys

__all__ = ["canonical_json_bytes", "logical_hash", "assert_allowed_keys"]
