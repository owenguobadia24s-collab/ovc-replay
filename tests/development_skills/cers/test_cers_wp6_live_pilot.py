from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.development.skills.cers.live import (
    EXECUTOR_ID,
    EXPECTED_WORK_ID,
    PACKET_CLASS,
    PACKET_ID,
    PROGRAMME_ID,
    LivePilotCoordinator,
    LivePilotViolation,
    validate_background_assurance_witness,
)
from ovc.development.skills.cers.model import DispatchIdentity, WorkerOwnership, canonical_id

ROOT = Path(__file__).resolve().parents[3]
FREEZE_PATH = "docs/releases/development-skills-v0-3/cers-conformance/wp6/CERS_WP6_LIVE_PILOT_FREEZE_v0_1.json"
AUTH_PATH = "registries/development/skills/cers/CERS_LIVE_DISPATCH_AUTHORITY_v0_1.json"
REGISTRY_PATH = "registries/development/skills/cers/CERS_ACTION_SIDE_EFFECT_REGISTRY_v0_2.json"
RUN_PATH = "docs/releases/development-skills-v0-3/cers-conformance/wp6/CERS_WP6_LIVE_PILOT_RUN_v0_1.json"
FIRST_WRITE = "src/ovc/development/skills/cers/live.py"


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def coordinator() -> LivePilotCoordinator:
    return LivePilotCoordinator(load(AUTH_PATH), load(FREEZE_PATH))


def work_manifest():
    return {
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "packet_class": PACKET_CLASS,
        "semantic_owner": "CERS",
        "action": "WRITE_FILE",
        "write_paths": [
            "registries/development/skills/cers/CERS_ACTION_SIDE_EFFECT_REGISTRY_v0_2.json",
            "src/ovc/development/skills/cers/live.py",
            "tests/development_skills/cers/test_cers_wp6_live_pilot.py",
            "docs/releases/development-skills-v0-3/cers-conformance/wp6/CERS_WP6_LIVE_PILOT_RUN_v0_1.json",
        ],
    }


def identity(generation: int = 1, *, work_id: str | None = None) -> DispatchIdentity:
    return DispatchIdentity(PROGRAMME_ID, PACKET_ID, "WRITE_FILE", work_id or canonical_id(work_manifest()), EXECUTOR_ID, generation)


def witness():
    run = load(RUN_PATH)
    background = run["background_assurance"]
    return {
        "repository": background["repository"],
        "observed_head": background["head_sha"],
        "caller_absent": run["caller_absent_at_start"],
        "workflows": [{"name": background["workflow"], "run_id": background["run_id"], "run_number": background["run_number"], "status": "in_progress"}],
    }


def test_exact_operator_authority_and_preexecution_freeze_are_required():
    c = coordinator()
    assert c.branch == "pilot/cers-wp6-live-20260818"
    assert c.freeze["status"] == "FROZEN_PRE_EXECUTION"
    assert c.freeze["freeze_revision"] == 5
    assert c.authority["approved"] is True and c.authority["effective"] is True
    assert EXPECTED_WORK_ID == "92fe5a075ffd852ec28903005d64f053f79ebdc93a94e7851c4ae9b507746403"
    bad = dict(c.authority); bad["effective"] = False
    with pytest.raises(LivePilotViolation, match="LIVE_DISPATCH_AUTHORITY_INACTIVE"):
        LivePilotCoordinator(bad, c.freeze)


def test_exact_live_actions_allow_only_frozen_packet_branch_scope():
    c = coordinator()
    assert c.authorize_action(action="WRITE_FILE", branch=c.branch, semantic_owner="CERS", path=FIRST_WRITE)["decision"] == "ALLOW"
    assert c.authorize_action(action="GIT_COMMIT", branch=c.branch, semantic_owner="CERS")["decision"] == "ALLOW"
    assert c.authorize_action(action="PUSH_BRANCH", branch=c.branch, semantic_owner="CERS")["decision"] == "ALLOW"
    for action in ("MERGE", "FORCE_PUSH", "HISTORY_REWRITE", "VALIDATION_READ", "SCIENTIFIC_PROMOTION"):
        with pytest.raises(LivePilotViolation):
            c.authorize_action(action=action, branch=c.branch, semantic_owner="CERS")
    for branch, owner, path in (("main", "CERS", FIRST_WRITE), (c.branch, "CERS", "README.md"), (c.branch, "OTHER", FIRST_WRITE)):
        with pytest.raises(LivePilotViolation):
            c.authorize_action(action="WRITE_FILE", branch=branch, semantic_owner=owner, path=path)


def test_dispatch_work_identity_is_exact_and_cannot_smuggle_other_payload():
    c = coordinator(); lease = c.acquire_lease()
    with pytest.raises(LivePilotViolation, match="WORK_IDENTITY_MISMATCH"):
        c.start(identity(work_id="0" * 64), lease, packet_class=PACKET_CLASS, first_write_path=FIRST_WRITE, background_assurance=witness())


def test_real_unattended_start_requires_background_assurance_and_caller_absence():
    c = coordinator(); lease = c.acquire_lease()
    started = c.start(identity(), lease, packet_class=PACKET_CLASS, first_write_path=FIRST_WRITE, background_assurance=witness())
    assert started.phase == "START_ACKNOWLEDGED"
    assert c.workers[started.dispatch_id].heartbeat_sequence == 1
    no_background = witness(); no_background["workflows"][0]["status"] = "completed"
    c2 = coordinator(); lease2 = c2.acquire_lease()
    with pytest.raises(LivePilotViolation, match="BACKGROUND_ASSURANCE_NOT_RUNNING"):
        c2.start(identity(), lease2, packet_class=PACKET_CLASS, first_write_path=FIRST_WRITE, background_assurance=no_background)
    no_caller_absence = witness(); no_caller_absence["caller_absent"] = False
    with pytest.raises(LivePilotViolation, match="CALLER_ABSENCE_NOT_OBSERVED"):
        validate_background_assurance_witness(no_caller_absence)


def test_duplicate_authoritative_start_is_hard_quarantined():
    c = coordinator(); lease = c.acquire_lease(); d = identity()
    c.start(d, lease, packet_class=PACKET_CLASS, first_write_path=FIRST_WRITE, background_assurance=witness())
    with pytest.raises(LivePilotViolation, match="DUPLICATE_AUTHORITATIVE_START"):
        c.start(d, lease, packet_class=PACKET_CLASS, first_write_path=FIRST_WRITE, background_assurance=witness())
    assert c.quarantine_reason == "DUPLICATE_AUTHORITATIVE_START"


def test_stale_fence_and_stale_worker_completion_fail_closed():
    c = coordinator(); lease1 = c.acquire_lease(); d1 = identity(1)
    c.start(d1, lease1, packet_class=PACKET_CLASS, first_write_path=FIRST_WRITE, background_assurance=witness())
    checkpoint = c.checkpoint(); restored = LivePilotCoordinator.restore(c.authority, c.freeze, checkpoint); lease2 = restored.acquire_lease()
    assert lease2.fencing_generation == 2
    with pytest.raises(LivePilotViolation, match="STALE_FENCE"):
        c.validate_lease(lease2)
    restored.transactions[d1.dispatch_id] = c.transactions[d1.dispatch_id]; restored.workers[d1.dispatch_id] = c.workers[d1.dispatch_id]
    with pytest.raises(LivePilotViolation, match="STALE_WORKER_AUTHORITATIVE_COMPLETION"):
        restored.complete(d1.dispatch_id, lease2)


def test_unknown_start_reconciles_existing_worker_without_blind_redispatch():
    c = coordinator(); lease = c.acquire_lease(); d = identity()
    assert c.mark_unknown_start(d, lease).phase == "DISPATCH_UNKNOWN"
    assert c.reconcile_unknown(d.dispatch_id, None).phase == "DISPATCH_UNKNOWN"
    observed = WorkerOwnership(d.dispatch_id, f"cers-live-{d.dispatch_id[:20]}", EXECUTOR_ID, 1, heartbeat_sequence=2, authoritative=True)
    resolved = c.reconcile_unknown(d.dispatch_id, observed)
    assert resolved.phase == "START_ACKNOWLEDGED" and resolved.reason == "RECOVERED_EXISTING_START_NO_REDISPATCH"
    assert c.last_reconciliation_id


def test_quiescence_persists_across_zero_chat_restart_and_blocks_new_start():
    c = coordinator(); lease = c.acquire_lease(); c.disable_new_dispatch()
    with pytest.raises(LivePilotViolation, match="QUIESCENCE_BLOCKS_NEW_DISPATCH"):
        c.start(identity(), lease, packet_class=PACKET_CLASS, first_write_path=FIRST_WRITE, background_assurance=witness())
    checkpoint = c.checkpoint()
    assert checkpoint.chat_dependency_count == 0 and checkpoint.quiescence_mode == "DISABLE_NEW_DISPATCH"
    restored = LivePilotCoordinator.restore(c.authority, c.freeze, checkpoint)
    assert restored.current_generation == checkpoint.fencing_generation
    assert restored.quiescence.blocks_new_dispatch is True
    lease2 = restored.acquire_lease()
    with pytest.raises(LivePilotViolation, match="QUIESCENCE_BLOCKS_NEW_DISPATCH"):
        restored.start(identity(lease2.fencing_generation), lease2, packet_class=PACKET_CLASS, first_write_path=FIRST_WRITE, background_assurance=witness())


def test_action_registry_has_no_merge_direct_main_force_or_unknown_allow():
    registry = load(REGISTRY_PATH); by_action = {row["action"]: row for row in registry["entries"]}
    assert registry["status"] == "ACTIVE_BOUNDED_WP6_LIVE_PILOT_ONLY"
    assert set(by_action) == {"WRITE_FILE", "GIT_COMMIT", "PUSH_BRANCH"} and all(row["allowed"] for row in by_action.values())
    assert {"MERGE", "DIRECT_MAIN_WRITE", "FORCE_PUSH"}.issubset(registry["explicit_denies"])
    assert registry["unknown_action"] == {"side_effect_class": "IRREVERSIBLE_OR_UNKNOWN", "decision": "DENY"}


def test_observed_pilot_record_binds_exact_dispatch_and_start_overlap():
    run = load(RUN_PATH)
    assert run["status"] in {"START_ACKNOWLEDGED_LIVE_BRANCH_WRITE_OBSERVED", "COMPLETED_BRANCH_PILOT", "COMPLETED_PASS"}
    assert run["programme_id"] == PROGRAMME_ID and run["packet_id"] == PACKET_ID
    assert run["executor_identity"] == EXECUTOR_ID and run["dispatch_id"] == identity().dispatch_id
    assert run["worker_concurrency"] == 1 and run["max_speculative_depth"] == 1
    assert run["background_assurance"]["status_at_start"] == "IN_PROGRESS" and run["caller_absent_at_start"] is True
    assert run["semantic_actions"] == ["WRITE_FILE", "GIT_COMMIT", "PUSH_BRANCH"]
    assert run["direct_main_mutation"] is False and run["merge_attempted"] is False
    assert run["force_push"] is False and run["history_rewrite"] is False
    if run["status"] == "COMPLETED_BRANCH_PILOT":
        assert run["heartbeat_sequence"] == 2
        assert run["post_pilot_quiescence"] == "DISABLE_NEW_DISPATCH"
        assert run["background_assurance"]["exact_status_at_branch_pilot_completion"] == "UNVERIFIED_NOT_REQUIRED_BY_ACCEPTANCE"
        assert run["incidents"] == [] and run["stop_conditions_observed"] == []
