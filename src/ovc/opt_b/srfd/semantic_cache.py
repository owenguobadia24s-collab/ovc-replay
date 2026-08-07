from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .serialization import logical_sha256, stable_id


CACHE_SCOPES = frozenset({"PAIR_LOCAL_REUSABLE", "POPULATION_SCOPED", "CHRONOLOGY_SCOPED"})


class SemanticCacheError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def semantic_cache_key(scope: str, identity: Mapping[str, Any]) -> str:
    if scope not in CACHE_SCOPES:
        raise SemanticCacheError("G8R_CACHE_INVALID_SCOPE", scope)
    return stable_id("SRFD.CACHE.V2.", {"scope": scope, "identity": dict(identity)})


@dataclass(frozen=True)
class CacheEntry:
    scope: str
    identity: Mapping[str, Any]
    payload: Mapping[str, Any]
    payload_hash: str


class SemanticCache:
    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}
        self._quarantine: dict[str, str] = {}
        self.hits = 0
        self.misses = 0

    def put(self, scope: str, identity: Mapping[str, Any], payload: Mapping[str, Any]) -> str:
        key = semantic_cache_key(scope, identity)
        value = dict(payload)
        self._entries[key] = CacheEntry(scope, dict(identity), value, logical_sha256(value))
        return key

    def get(self, scope: str, identity: Mapping[str, Any]) -> dict[str, Any] | None:
        key = semantic_cache_key(scope, identity)
        entry = self._entries.get(key)
        if entry is None:
            self.misses += 1
            return None
        if entry.scope != scope or dict(entry.identity) != dict(identity) or logical_sha256(entry.payload) != entry.payload_hash:
            self._entries.pop(key, None)
            self._quarantine[key] = "QA_CACHE_CORRUPTION"
            self.misses += 1
            return None
        self.hits += 1
        return dict(entry.payload)

    def corrupt_for_fixture(self, key: str) -> None:
        entry = self._entries.get(key)
        if entry is not None:
            self._entries[key] = CacheEntry(entry.scope, entry.identity, {**entry.payload, "fixture_corruption": True}, entry.payload_hash)

    @property
    def quarantined(self) -> Mapping[str, str]:
        return dict(self._quarantine)

    @property
    def hit_ratio(self) -> float:
        denominator = self.hits + self.misses
        return self.hits / denominator if denominator else 0.0


@dataclass(frozen=True)
class TileCompletion:
    tile_id: str
    content_hash: str
    status: str
    attempt_id: str


class TileCompletionLedger:
    def __init__(self) -> None:
        self._complete: dict[str, TileCompletion] = {}
        self._attempts: dict[str, list[str]] = {}
        self._quarantine: dict[str, str] = {}

    def register_complete(self, tile_id: str, *, content_hash: str, attempt_id: str) -> None:
        existing = self._complete.get(tile_id)
        if existing is not None and existing.content_hash != content_hash:
            self._quarantine[tile_id] = "G8R_RESTART_COMPLETE_HASH_CONFLICT"
            raise SemanticCacheError("G8R_RESTART_COMPLETE_HASH_CONFLICT", tile_id)
        self._complete[tile_id] = TileCompletion(tile_id, content_hash, "COMPLETE", attempt_id)
        self._attempts.setdefault(tile_id, []).append(attempt_id)

    def should_compute(self, tile_id: str, *, expected_hash: str | None = None) -> bool:
        existing = self._complete.get(tile_id)
        if existing is None:
            return True
        if expected_hash is not None and existing.content_hash != expected_hash:
            self._quarantine[tile_id] = "QA_CACHE_CORRUPTION"
            return True
        return False

    def attempts(self, tile_id: str) -> tuple[str, ...]:
        return tuple(self._attempts.get(tile_id, ()))

    @property
    def quarantined(self) -> Mapping[str, str]:
        return dict(self._quarantine)
