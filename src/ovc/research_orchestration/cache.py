from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .models import ArtifactRef, SemanticCacheKey


class CacheError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


@dataclass(frozen=True)
class CacheRecord:
    cache_key: str
    artifact: ArtifactRef
    parent_semantic_hashes: tuple[str, ...]
    content_sha256: str | None


@dataclass(frozen=True)
class CacheLookupReceipt:
    cache_key: str
    status: str
    reason_codes: tuple[str, ...]
    artifact: ArtifactRef | None = None
    bytes_avoided: int | None = None
    work_units_avoided: int | None = None
    hit_count: int = 0
    miss_count: int = 0


class SemanticArtifactCache:
    """In-memory semantic index contract used by IROF adapters.

    Physical persistence is adapter-owned. This class freezes lookup/reuse semantics:
    exact semantic key only, COMPLETE lifecycle only, verified content only, and
    quarantine-on-corruption. Counters and physical locations never enter key identity.
    """

    def __init__(self) -> None:
        self._entries: dict[str, CacheRecord] = {}
        self._quarantine: dict[str, str] = {}
        self.hits = 0
        self.misses = 0

    def register(self, key: SemanticCacheKey, artifact: ArtifactRef) -> None:
        if artifact.semantic_cache_key != key.key:
            raise CacheError("IROF_CACHE_ARTIFACT_KEY_MISMATCH", artifact.artifact_id)
        if artifact.owner_stage_id != key.stage_id:
            raise CacheError("IROF_CACHE_OWNER_STAGE_MISMATCH", artifact.artifact_id)
        record = CacheRecord(
            cache_key=key.key,
            artifact=artifact,
            parent_semantic_hashes=tuple(sorted(key.parent_semantic_hashes)),
            content_sha256=artifact.content_sha256,
        )
        existing = self._entries.get(key.key)
        if existing is not None:
            same_semantics = (
                existing.artifact.logical_hash == artifact.logical_hash
                and existing.artifact.artifact_type == artifact.artifact_type
                and existing.artifact.schema_identity == artifact.schema_identity
                and existing.content_sha256 == artifact.content_sha256
            )
            if not same_semantics:
                self._quarantine[key.key] = "IROF_CACHE_DUPLICATE_KEY_SEMANTIC_CONFLICT"
                self._entries.pop(key.key, None)
                raise CacheError("IROF_CACHE_DUPLICATE_KEY_SEMANTIC_CONFLICT", key.key)
        self._entries[key.key] = record

    def lookup(
        self,
        key: SemanticCacheKey,
        *,
        observed_content_sha256: str | None = None,
        bytes_avoided: int | None = None,
        work_units_avoided: int | None = None,
    ) -> CacheLookupReceipt:
        if key.key in self._quarantine:
            self.misses += 1
            return self._receipt(key.key, "MISS", ("IROF_CACHE_KEY_QUARANTINED",))
        record = self._entries.get(key.key)
        if record is None:
            self.misses += 1
            return self._receipt(key.key, "MISS", ("IROF_CACHE_KEY_NOT_FOUND",))
        artifact = record.artifact
        if artifact.lifecycle_state != "COMPLETE":
            self.misses += 1
            return self._receipt(key.key, "MISS", ("IROF_CACHE_ARTIFACT_LIFECYCLE_NOT_REUSABLE",))
        if artifact.semantic_cache_key != key.key:
            self._quarantine_record(key.key, "IROF_CACHE_INDEX_KEY_CORRUPTION")
            self.misses += 1
            return self._receipt(key.key, "MISS", ("IROF_CACHE_INDEX_KEY_CORRUPTION",))
        if record.parent_semantic_hashes != tuple(sorted(key.parent_semantic_hashes)):
            self.misses += 1
            return self._receipt(key.key, "MISS", ("IROF_CACHE_PARENT_HASH_MISMATCH",))
        if observed_content_sha256 is not None and record.content_sha256 is not None and observed_content_sha256 != record.content_sha256:
            self._quarantine_record(key.key, "IROF_CACHE_PAYLOAD_CORRUPTION")
            self.misses += 1
            return self._receipt(key.key, "MISS", ("IROF_CACHE_PAYLOAD_CORRUPTION",))
        self.hits += 1
        measurable_bytes = bytes_avoided if bytes_avoided is not None and bytes_avoided >= 0 else None
        measurable_work = work_units_avoided if work_units_avoided is not None and work_units_avoided >= 0 else None
        return self._receipt(
            key.key,
            "HIT",
            (),
            artifact=artifact,
            bytes_avoided=measurable_bytes,
            work_units_avoided=measurable_work,
        )

    def quarantine(self, key: str, reason_code: str) -> None:
        if not reason_code:
            raise CacheError("IROF_CACHE_QUARANTINE_REASON_REQUIRED", key)
        self._quarantine_record(key, reason_code)

    def _quarantine_record(self, key: str, reason_code: str) -> None:
        self._entries.pop(key, None)
        self._quarantine[key] = reason_code

    def _receipt(
        self,
        key: str,
        status: str,
        reasons: tuple[str, ...],
        *,
        artifact: ArtifactRef | None = None,
        bytes_avoided: int | None = None,
        work_units_avoided: int | None = None,
    ) -> CacheLookupReceipt:
        return CacheLookupReceipt(
            cache_key=key,
            status=status,
            reason_codes=reasons,
            artifact=artifact,
            bytes_avoided=bytes_avoided,
            work_units_avoided=work_units_avoided,
            hit_count=self.hits,
            miss_count=self.misses,
        )

    @property
    def quarantined(self) -> Mapping[str, str]:
        return dict(self._quarantine)


def assert_cached_recompute_equivalent(cached: ArtifactRef, recomputed: ArtifactRef) -> None:
    fields = (
        "logical_hash",
        "artifact_type",
        "owner_stage_id",
        "schema_identity",
        "authority_classification",
    )
    for field in fields:
        if getattr(cached, field) != getattr(recomputed, field):
            raise CacheError("IROF_CACHE_RECOMPUTE_SEMANTIC_DRIFT", field)
    if cached.content_sha256 is not None and recomputed.content_sha256 is not None and cached.content_sha256 != recomputed.content_sha256:
        raise CacheError("IROF_CACHE_RECOMPUTE_CONTENT_DRIFT", cached.artifact_id)
