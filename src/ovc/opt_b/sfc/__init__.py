"""OVC SFC v0.1 conformance namespace.

This package is inactive, shadow-only conformance capability. It wraps finalized
C2E producer artifacts and existing SRFD backends without selecting scientific
methods, family catalogues or production representations. It grants no active market
or production authority, no selector authority, no canonical representation/family
standing, no Validation access, no semantic-promotion authority, no publication,
and no probability, risk, exposure or execution authority.
"""

from .serialization import canonical_json_bytes, logical_hash, assert_allowed_keys

__all__ = ["canonical_json_bytes", "logical_hash", "assert_allowed_keys"]
