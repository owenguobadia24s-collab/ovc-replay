from __future__ import annotations


class ConsoleBoundaryError(ValueError):
    """Typed application-boundary failure. Presentation layers translate it."""

    reason_code = "CONSOLE_BOUNDARY_ERROR"


class AuthorityDenied(ConsoleBoundaryError):
    reason_code = "AUTHORITY_DENIED"


class SourceGap(ConsoleBoundaryError):
    reason_code = "UPSTREAM_READ_MODEL_GAP"


class SourceConflict(ConsoleBoundaryError):
    reason_code = "SOURCE_IDENTITY_CONFLICT"


class ContractError(ConsoleBoundaryError):
    reason_code = "SOURCE_CONTRACT_ERROR"
