from __future__ import annotations

import json
from pathlib import Path

from ovc.research_orchestration.cache import SemanticArtifactCache, assert_cached_recompute_equivalent
from ovc.research_orchestration.checkpoint import assert_fresh_resume_equivalent, build_resume_plan
from ovc.research_orchestration.evidence import classify_scientific_result
from ovc.research_orchestration.golden import (
    build_golden_plan,
    golden_run_receipt,
    golden_stage_completions,
    run_golden_scientific_chain,
)
from ovc.research_orchestration.models import ArtifactRef, SemanticCacheKey

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / "fixtures/research_orchestration/golden_v0_1/golden_full_chain.json"


def fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_fresh_repeated_resumed_and_alternate_order_scientific_identity_match() -> None:
    data = fixture()
    episode_ids = [item["episode_id"] for item in data["episodes"]]
    fresh = run_golden_scientific_chain(data)
    repeated = run_golden_scientific_chain(data)
    alternate = run_golden_scientific_chain(
        data,
        episode_order=tuple(reversed(episode_ids)),
        reverse_source_objects=True,
    )
    resumed_hash = fresh["logical_hash"]
    assert fresh["logical_hash"] == repeated["logical_hash"] == alternate["logical_hash"]
    assert_fresh_resume_equivalent(fresh["logical_hash"], repeated["logical_hash"], resumed_hash)


def test_complete_checkpoint_set_reuses_every_stage_without_scientific_change() -> None:
    result = run_golden_scientific_chain(fixture())
    plan = build_golden_plan()
    completions = golden_stage_completions(plan, result["logical_hash"], attempt_id="ATTEMPT.1")
    resume = build_resume_plan(
        plan=plan,
        semantic_run_id="IROF.RUN.GOLDEN.v0_1",
        completions=completions,
        expected_stage_spec_hashes=dict(plan.stage_spec_hashes),
        observed_content_hashes={item.stage_id: item.content_hash for item in completions},
        new_attempt_id="ATTEMPT.2",
    )
    assert resume.rerun_stage_ids == ()
    assert resume.reusable_completed_stage_ids == plan.ordered_stage_ids
    assert resume.restart_count == 1


def test_corrupt_checkpoint_reruns_only_owner_stage_and_descendants() -> None:
    result = run_golden_scientific_chain(fixture())
    plan = build_golden_plan()
    completions = golden_stage_completions(plan, result["logical_hash"], attempt_id="ATTEMPT.1")
    observed = {item.stage_id: item.content_hash for item in completions}
    observed["SRI_REPRESENTATION"] = "CORRUPTED"
    resume = build_resume_plan(
        plan=plan,
        semantic_run_id="IROF.RUN.GOLDEN.v0_1",
        completions=completions,
        expected_stage_spec_hashes=dict(plan.stage_spec_hashes),
        observed_content_hashes=observed,
        new_attempt_id="ATTEMPT.2",
    )
    assert resume.quarantined_stage_ids == ("SRI_REPRESENTATION",)
    assert "SRI_REPRESENTATION" in resume.rerun_stage_ids
    assert "COMPARABILITY_COMPARISON_DISTANCE" in resume.rerun_stage_ids
    assert "FDI_C2G_FAMILY" in resume.rerun_stage_ids
    assert "FAMILY_EVIDENCE_STREAM" in resume.rerun_stage_ids
    assert "RESEARCH_OPERATIONS" in resume.rerun_stage_ids
    assert "OCCURRENCE_CONTEXT" in resume.reusable_completed_stage_ids
    assert "IROF_CHECKPOINT_CONTENT_CORRUPTION" in resume.reason_codes


def test_semantic_cache_reuses_exact_artifact_and_quarantines_corruption() -> None:
    result = run_golden_scientific_chain(fixture())
    key = SemanticCacheKey(
        stage_id="FDI_C2G_FAMILY",
        stage_version="0.1",
        parent_semantic_hashes=(result["representations"][0]["logical_hash"], result["representations"][1]["logical_hash"]),
        contract_identity="IROF.GOLDEN.FDI.CONTRACT",
        schema_identity="IROF.GOLDEN.FDI.SCHEMA",
        implementation_identity="IROF.GOLDEN.FDI.IMPLEMENTATION",
        pack_bindings={"family_method": "IROF.GOLDEN.FDI.STAR.v0_1"},
        population_hash=result["population"]["logical_hash"],
        comparability_identity="IROF.GOLDEN.COMPARABILITY.v0_1",
    )
    artifact = ArtifactRef(
        artifact_id="IROF.GOLDEN.FAMILY.CATALOG",
        logical_hash=result["catalog"]["logical_hash"],
        artifact_type="FAMILY_CATALOG",
        owner_stage_id="FDI_C2G_FAMILY",
        owner_run_id="IROF.RUN.GOLDEN.v0_1",
        lifecycle_state="COMPLETE",
        content_sha256=result["catalog"]["logical_hash"],
        semantic_cache_key=key.key,
        schema_identity="IROF.GOLDEN.FDI.SCHEMA",
    )
    cache = SemanticArtifactCache()
    cache.register(key, artifact)
    hit = cache.lookup(key, observed_content_sha256=artifact.content_sha256, bytes_avoided=1024, work_units_avoided=3)
    assert hit.status == "HIT"
    assert hit.artifact == artifact
    assert hit.bytes_avoided == 1024
    assert hit.work_units_avoided == 3
    assert_cached_recompute_equivalent(artifact, artifact)

    corrupt = cache.lookup(key, observed_content_sha256="CORRUPTED")
    assert corrupt.status == "MISS"
    assert corrupt.reason_codes == ("IROF_CACHE_PAYLOAD_CORRUPTION",)
    assert key.key in cache.quarantined
    after_quarantine = cache.lookup(key)
    assert after_quarantine.status == "MISS"
    assert after_quarantine.reason_codes == ("IROF_CACHE_KEY_QUARANTINED",)


def test_attempt_and_worker_order_are_operational_not_scientific_identity() -> None:
    result = run_golden_scientific_chain(fixture())
    plan = build_golden_plan()
    first = golden_run_receipt(plan, result["logical_hash"], attempt_id="ATTEMPT.1")
    second = golden_run_receipt(plan, result["logical_hash"], attempt_id="ATTEMPT.2")
    assert first.logical_hash == second.logical_hash
    assert first.attempt_id != second.attempt_id


def test_scientific_zero_family_is_successful_result_not_execution_incident() -> None:
    result = run_golden_scientific_chain(fixture())
    assert result["zero_family_evidence_stream"]["status"] == "NO_STABLE_FAMILY"
    assert classify_scientific_result("NO_STABLE_FAMILY") == "SCIENTIFIC_RESULT_NOT_INCIDENT"
