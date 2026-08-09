from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .errors import AuthorityDenied, ContractError, SourceConflict

_FORBIDDEN_WRITE_KEYS = {
    "activate", "delete", "git_write", "mutation", "patch", "promote",
    "release_write", "r2_write", "selector_write", "threshold_write", "write",
}


def require_read_only(value: Any) -> None:
    if isinstance(value, Mapping):
        for raw_key, item in value.items():
            key = str(raw_key).strip().lower()
            if key == "writes" and item != "NONE":
                raise AuthorityDenied("WRITE_CAPABILITY_DENIED")
            if key == "read_only" and item is not True:
                raise AuthorityDenied("READ_ONLY_REQUIRED")
            if key in _FORBIDDEN_WRITE_KEYS or key.endswith("_write") or key.endswith("_mutation"):
                raise AuthorityDenied(f"WRITE_CAPABILITY_DENIED:{key}")
            require_read_only(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            require_read_only(item)


def require_current_identity(context: Mapping[str, Any]) -> str:
    represented = str(context.get("represented_commit") or context.get("source_commit") or "")
    source = str(context.get("source_commit") or represented)
    if len(represented) < 7 or len(source) < 7:
        raise ContractError("SOURCE_COMMIT_IDENTITY_INVALID")
    if represented != source:
        raise SourceConflict("SOURCE_IDENTITY_CONFLICT")
    return source


def deny_validation(context: Mapping[str, Any]) -> None:
    if str(context.get("role", "")).upper() == "VALIDATION":
        raise AuthorityDenied("VALIDATION_DENIED_BEFORE_OBJECT_RESOLUTION")
