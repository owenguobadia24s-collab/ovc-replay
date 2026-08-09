from __future__ import annotations

import pytest

from ovc.research_orchestration.cache import CacheError, SemanticArtifactCache, assert_cached_recompute_equivalent
from ovc.research_orchestration.models import ArtifactRef, SemanticCacheKey


def key(*, parent="parent-a", pack="pack-a", code="code-a") -> SemanticCacheKey:
    return SemanticCacheKey(
        stage_id="SRI_REPRESENTATION",
        stage_version="0.1",
        parent_semantic_hashes=(parent,),
        contract_identity="contract:sri",
        schema_identity="schema:sri",
        implementation_identity="impl:sri",
        pack_bindings={"representation_pack": pack},
        population_hash="population",
        chronology_identity="chrono",
        comparability_identity="domain",
        context_role_identity="METADATA_ONLY",
        code_identity=code,
    )


def artifact(cache_key: str, *, state="COMPLETE", logical="logical-a", content="content-a", location="/one") -> ArtifactRef:
    return ArtifactRef(
        artifact_id="ART.SRI.1",
        logical_hash=logical,
        artifact_type="REPRESENTATION_POPULATION",
        owner_stage_id="SRI_REPRESENTATION",
        owner_run_id="RUN.1",
        lifecycle_state=state,
        content_sha256=content,
        semantic_cache_key=cache_key,
        schema_identity="schema:sri",
        locations=({"kind": "LOCAL", "value": location},),
    )


def test_exact_hit_reports_only_deterministically_supplied_avoidance() -> None:
    cache = SemanticArtifactCache()
    k = key()
    a = artifact(k.key)
    cache.register(k, a)
    result = cache.lookup(k, observed_content_sha256="content-a", bytes_avoided=100, work_units_avoided=7)
    assert result.status == "HIT"
    assert result.artifact == a
    assert result.bytes_avoided == 100
    assert result.work_units_avoided == 7


def test_semantic_field_change_is_miss() -> None:
    cache = SemanticArtifactCache()
    original = key(pack="pack-a")
    cache.register(original, artifact(original.key))
    changed = key(pack="pack-b")
    result = cache.lookup(changed)
    assert result.status == "MISS"
    assert result.reason_codes == ("IROF_CACHE_KEY_NOT_FOUND",)


def test_parent_hash_change_is_miss() -> None:
    cache = SemanticArtifactCache()
    original = key(parent="parent-a")
    cache.register(original, artifact(original.key))
    result = cache.lookup(key(parent="parent-b"))
    assert result.status == "MISS"


def test_physical_path_relocation_preserves_hit() -> None:
    cache = SemanticArtifactCache()
    k = key()
    first = artifact(k.key, location="/host-a/cache")
    moved = artifact(k.key, location="/host-b/cache")
    cache.register(k, first)
    cache.register(k, moved)
    result = cache.lookup(k, observed_content_sha256="content-a")
    assert result.status == "HIT"
    assert result.artifact is not None
    assert result.artifact.locations[0]["value"] == "/host-b/cache"
    assert k.key == key().key


def test_corrupt_payload_is_quarantined_and_never_reused() -> None:
    cache = SemanticArtifactCache()
    k = key()
    cache.register(k, artifact(k.key))
    first = cache.lookup(k, observed_content_sha256="corrupt")
    assert first.status == "MISS"
    assert first.reason_codes == ("IROF_CACHE_PAYLOAD_CORRUPTION",)
    assert cache.quarantined[k.key] == "IROF_CACHE_PAYLOAD_CORRUPTION"
    second = cache.lookup(k, observed_content_sha256="content-a")
    assert second.status == "MISS"
    assert second.reason_codes == ("IROF_CACHE_KEY_QUARANTINED",)


@pytest.mark.parametrize("state", ["SUPERSEDED", "QUARANTINED", "STAGING"])
def test_non_complete_artifact_is_never_reused(state: str) -> None:
    cache = SemanticArtifactCache()
    k = key()
    cache.register(k, artifact(k.key, state=state))
    result = cache.lookup(k)
    assert result.status == "MISS"
    assert result.reason_codes == ("IROF_CACHE_ARTIFACT_LIFECYCLE_NOT_REUSABLE",)


def test_cache_counters_and_location_do_not_change_scientific_hash() -> None:
    cache = SemanticArtifactCache()
    k = key()
    a = artifact(k.key)
    before = a.logical_hash
    cache.register(k, a)
    cache.lookup(k)
    cache.lookup(key(pack="other"))
    assert a.logical_hash == before
    assert cache.hits == 1
    assert cache.misses == 1


def test_cached_and_recomputed_outputs_must_be_semantically_equal() -> None:
    k = key()
    cached = artifact(k.key, location="/cached")
    recomputed = artifact(k.key, location="/fresh")
    assert_cached_recompute_equivalent(cached, recomputed)
    drifted = artifact(k.key, logical="different", content="different")
    with pytest.raises(CacheError, match="IROF_CACHE_RECOMPUTE_SEMANTIC_DRIFT"):
        assert_cached_recompute_equivalent(cached, drifted)


def test_duplicate_key_with_different_semantics_quarantines() -> None:
    cache = SemanticArtifactCache()
    k = key()
    cache.register(k, artifact(k.key))
    with pytest.raises(CacheError, match="IROF_CACHE_DUPLICATE_KEY_SEMANTIC_CONFLICT"):
        cache.register(k, artifact(k.key, logical="different"))
    assert k.key in cache.quarantined
