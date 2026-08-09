from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

CACHE_ENABLED = False
MAX_PAGE_SIZE = 200
MAX_MARKET_POINTS = 5000


@dataclass(frozen=True)
class CanonicalQuery:
    resource: str
    params: tuple[tuple[str, str], ...]

    @classmethod
    def from_mapping(cls, resource: str, params: Mapping[str, Any]) -> "CanonicalQuery":
        normalized = tuple(sorted((str(key), "" if value is None else str(value)) for key, value in params.items()))
        return cls(resource=str(resource), params=normalized)

    def cache_key(self) -> str:
        payload = json.dumps(
            {"resource": self.resource, "params": list(self.params)},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "rcn:q1:" + hashlib.sha256(payload).hexdigest()


def stable_page(items: Iterable[Mapping[str, Any]], *, key: str, cursor: int, limit: int) -> dict[str, Any]:
    if cursor < 0 or limit < 1 or limit > MAX_PAGE_SIZE:
        raise ValueError("PAGE_BOUNDS_INVALID")
    ordered = sorted((dict(item) for item in items), key=lambda item: str(item[key]))
    page = ordered[cursor : cursor + limit]
    next_cursor = cursor + len(page) if cursor + len(page) < len(ordered) else None
    return {"items": page, "next_cursor": next_cursor, "total": len(ordered)}


def bounded_time_window(
    items: Sequence[Mapping[str, Any]], *, start: str | None, end: str | None, limit: int
) -> dict[str, Any]:
    if limit < 1 or limit > MAX_MARKET_POINTS:
        raise ValueError("MARKET_RANGE_LIMIT_INVALID")
    if start is not None and end is not None and start > end:
        raise ValueError("MARKET_RANGE_ORDER_INVALID")
    ordered = sorted((dict(item) for item in items), key=lambda item: str(item["t"]))
    filtered = [
        item for item in ordered
        if (start is None or str(item["t"]) >= start) and (end is None or str(item["t"]) <= end)
    ]
    bounded = filtered[:limit]
    return {"items": bounded, "total": len(filtered), "truncated": len(filtered) > len(bounded)}
