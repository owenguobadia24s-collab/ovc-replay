from __future__ import annotations

from pathlib import Path

import pytest

from ovc.research_operations.ec1_prelaunch import (
    EC1PrelaunchError,
    EC1PrelaunchInjectedFailure,
    STAGES,
    blinded_heartbeat,
    build_execution_capsule,
    launch_guard,
    probe_environment,
    run_stage_rehearsal,
    validate_artifact_probe,
    validate_shards,
    validate_source_probe,
    verify_repository_prelaunch,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _payloads():
    return {stage: {"stage": stage, "fixture": "NO_SURPRISES", "ordinal": i} for i, stage in enumerate(STAGES)}


def test_repository_court_record_is_prelaunch_closed_while_f0_hold_remains():
    report = verify_repository_prelaunch(REPO_ROOT)
    assert set(report.checks.values()) == {"PASS"}
    assert launch_guard(report, operator_release_present=False) == "BLOCKED_BY_F0_A_HOLD"


def test_exact_stage_rehearsal_crash_resume_matches_clean_run(tmp_path):
    clean = run_stage_rehearsal(_payloads())
    checkpoint = tmp_path / "checkpoint.json"
    with pytest.raises(EC1PrelaunchInjectedFailure):
        run_stage_rehearsal(_payloads(), checkpoint_path=checkpoint, inject_failure_after="PATTERN_LATTICE")
    resumed = run_stage_rehearsal(_payloads(), checkpoint_path=checkpoint)
    assert resumed.resumed_from_checkpoint is True
    assert resumed.terminal_hash == clean.terminal_hash
    assert resumed.stage_hashes == clean.stage_hashes


def test_corrupt_checkpoint_fails_closed(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text('{"schema":"wrong","stage_hashes":{}}\n', encoding="utf-8")
    with pytest.raises(EC1PrelaunchError, match="CORRUPT_CHECKPOINT"):
        run_stage_rehearsal(_payloads(), checkpoint_path=checkpoint)


def test_checkpoint_payload_drift_fails_closed(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    with pytest.raises(EC1PrelaunchInjectedFailure):
        run_stage_rehearsal(_payloads(), checkpoint_path=checkpoint, inject_failure_after="C2E")
    changed = _payloads()
    changed["C2E"] = {"stage": "C2E", "fixture": "DRIFT"}
    with pytest.raises(EC1PrelaunchError, match="CHECKPOINT_STAGE_HASH_MISMATCH"):
        run_stage_rehearsal(changed, checkpoint_path=checkpoint)


def test_blinded_heartbeat_allows_operational_fields_and_rejects_science():
    projection = blinded_heartbeat(
        {
            "run_id": "prelaunch.synthetic.1",
            "stage_id": "PATTERN_LATTICE",
            "eligible_count": 12,
            "processed_count": 12,
            "runtime_seconds": 1.25,
            "peak_rss_bytes": 1024,
            "capacity_state": "WITHIN_ENVELOPE",
            "checkpoint_state": "COMPLETE",
            "qa_state": "PASS",
        }
    )
    assert projection.values["processed_count"] == 12
    with pytest.raises(Exception):
        blinded_heartbeat({"run_id": "x", "pattern_id": "forbidden"})


def test_fault_probes_fail_closed():
    assert validate_source_probe(expected_sha256="a", observed_sha256="a", available=True) == "PASS"
    with pytest.raises(EC1PrelaunchError, match="SOURCE_HASH_MISMATCH"):
        validate_source_probe(expected_sha256="a", observed_sha256="b", available=True)
    with pytest.raises(EC1PrelaunchError, match="SOURCE_FALLBACK_FORBIDDEN"):
        validate_source_probe(expected_sha256="a", observed_sha256="a", available=True, fallback_requested=True)
    assert validate_artifact_probe(writable=True, durable=True) == "PASS"
    with pytest.raises(EC1PrelaunchError, match="PARTIAL_ARTIFACT_WRITE"):
        validate_artifact_probe(writable=True, durable=True, partial_write_detected=True)


def test_shard_ownership_is_complete_and_unique():
    assert validate_shards(["a", "b", "c"], [["a", "c"], ["b"]]) == "PASS"
    with pytest.raises(EC1PrelaunchError, match="DUPLICATE_SHARD"):
        validate_shards(["a", "b"], [["a"], ["a", "b"]])
    with pytest.raises(EC1PrelaunchError, match="INCOMPLETE_SHARD"):
        validate_shards(["a", "b"], [["a"]])


def test_environment_probe_and_execution_capsule_are_content_addressed(tmp_path):
    report = verify_repository_prelaunch(REPO_ROOT)
    environment = probe_environment(tmp_path, minimum_free_disk_bytes=0)
    capsule = build_execution_capsule(
        report=report,
        environment=environment,
        code_commit="17e448c2598bcbe70cb07c780f82ad6b5d1d0335",
        artifact_root_binding="EC1_EXTERNAL_ARTIFACT_ROOT_PRELAUNCH_BOUND",
        checkpoint_policy_id="EC1.CHECKPOINT.FAIL_CLOSED.v1",
    )
    assert capsule["authority_effect"] == "NONE"
    assert len(capsule["capsule_sha256"]) == 64
