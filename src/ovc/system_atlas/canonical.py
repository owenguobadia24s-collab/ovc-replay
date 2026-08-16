from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Mapping


class CanonicalizationError(ValueError):
    """Raised when a value cannot enter the Atlas logical identity domain."""


_IDENTITY_ARRAYS = {
    "entities": "entity_id",
    "relationships": "relationship_id",
    "assertions": "assertion_id",
    "evidence_references": "evidence_id",
    "conflicts": "conflict_id",
}

_SET_LIKE_ARRAYS = {
    "aliases",
    "competing_assertion_ids",
    "evidence_refs",
    "permitted_source_classes",
    "required_dimensions",
}


def _normalize(value: Any, *, key: str | None = None) -> Any:
    if isinstance(value, float):
        raise CanonicalizationError("floating-point values are outside the Atlas canonical identity domain")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(item_key): _normalize(item_value, key=str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, (list, tuple)):
        rows = [_normalize(item) for item in value]
        if key in _SET_LIKE_ARRAYS:
            encoded = {json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False): item for item in rows}
            return [encoded[item_key] for item_key in sorted(encoded)]
        return rows
    raise CanonicalizationError(f"unsupported canonical value type: {type(value).__name__}")


def canonicalize_graph(graph: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _normalize(deepcopy(dict(graph)))
    for array_name, identity_key in _IDENTITY_ARRAYS.items():
        rows = normalized.get(array_name)
        if isinstance(rows, list):
            normalized[array_name] = sorted(rows, key=lambda row: str(row.get(identity_key, "")))
    return normalized


def canonical_json_bytes(value: Any, *, trailing_newline: bool = False) -> bytes:
    normalized = _normalize(value)
    text = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    if trailing_newline:
        text += "\n"
    return text.encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def logical_id(namespace: str, value: Any) -> str:
    if not namespace or ":" in namespace:
        raise CanonicalizationError("logical ID namespace must be non-empty and contain no colon")
    return f"atlas:{namespace}:{canonical_sha256(value)}"


def graph_logical_hash(graph: Mapping[str, Any]) -> str:
    payload = canonicalize_graph(graph)
    payload.pop("graph_logical_hash", None)
    return canonical_sha256(payload)
