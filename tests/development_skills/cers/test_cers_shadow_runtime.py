from __future__ import annotations

from ovc.development.skills.cers.model import (
    DispatchIdentity,
    ExecutorCapabilityRecord,
    QuiescenceControl,
    ReconciliationSnapshot,
    RunnableWorkItem,
    SupervisorCheckpoint,
)
from ovc.development.skills.cers.reconcile import ReferenceReconciler
from ovc.development.skills.cers.runtime import DispatchCoordinator, EventLedger, FixtureExecutor, LeaseManager, failure_route, selective_invalidation


def _snapshot():
    return ReconciliationSnapshot(
        physical_main="a" * 40,
        physical_tree="b" * 40,
        programme_states=({"programme_id":"P","status":"RUNNING"},),
        assurance_futures=({"future_id":"F","status":"RUNNING"},),
    )


def _item(**overrides):
    base = dict(
        programme_id="P",
        packet_id="WP2",
        action="BUILD_FIXTURE_SUCCESSOR",
        priority=10,
        authority_class="AUTO_EXECUTABLE",
        authority_delta="NONE",
        prerequisites_pass=True,
        registered_root=True,
        executor_id="CERS_FIXTURE_EXECUTOR_V0_1",
        side_effect_class="REVERSIBLE_LOCAL",
    )
    base.update(overrides)
    return RunnableWorkItem(**base)


def test_reference_reconciliation_is_deterministic_and_builds_ahead_while_assurance_runs():
    executor = FixtureExecutor()
    reconciler = ReferenceReconciler()
    snapshot = _snapshot()
    items = (_item(packet_id="WP3", priority=20), _item(packet_id="WP2", priority=10))
    r1 = reconciler.reconcile(snapshot=snapshot, work_items=items, executors={executor.capability.executor_id:executor.capability}, quiescence=QuiescenceControl("RUN"), fencing_generation=1)
    r2 = reconciler.reconcile(snapshot=snapshot, work_items=reversed(items), executors={executor.capability.executor_id:executor.capability}, quiescence=QuiescenceControl("RUN"), fencing_generation=1)
    assert r1.workset.workset_id == r2.workset.workset_id
    assert [x.packet_id for x in r1.workset.items] == ["WP2", "WP3"]
    assert len(r1.proposed_dispatches) == 2


def test_unknown_root_executor_and_side_effect_fail_closed():
    executor = FixtureExecutor()
    reconciler = ReferenceReconciler()
    rows = (
        _item(packet_id="A", registered_root=False),
        _item(packet_id="B", executor_id="UNKNOWN"),
        _item(packet_id="C", side_effect_class="IRREVERSIBLE_OR_UNKNOWN"),
    )
    result = reconciler.reconcile(snapshot=_snapshot(), work_items=rows, executors={executor.capability.executor_id:executor.capability}, quiescence=QuiescenceControl("RUN"), fencing_generation=1)
    reasons = {r["packet_id"]:r["reason"] for r in result.workset.parked}
    assert reasons == {"A":"UNREGISTERED_PROGRAMME_ROOT","B":"EXECUTOR_UNKNOWN_OR_INACTIVE","C":"IRREVERSIBLE_OR_UNKNOWN_SIDE_EFFECT"}


def test_operator_hold_and_predecessor_materialisation_dominate():
    executor = FixtureExecutor()
    reconciler = ReferenceReconciler()
    held = reconciler.reconcile(snapshot=_snapshot(), work_items=(_item(),), executors={executor.capability.executor_id:executor.capability}, quiescence=QuiescenceControl("HOLD"), fencing_generation=1)
    assert held.workset.parked[0]["reason"] == "QUIESCENCE_HOLD"
    waiting = reconciler.reconcile(snapshot=_snapshot(), work_items=(_item(predecessor_materialisation_required=True),), executors={executor.capability.executor_id:executor.capability}, quiescence=QuiescenceControl("RUN"), fencing_generation=1)
    assert waiting.workset.parked[0]["reason"] == "PREDECESSOR_MATERIALISATION_REQUIRED"


def test_fencing_is_monotonic_and_stale_fence_is_rejected():
    leases = LeaseManager()
    first = leases.acquire("lane:P", "supervisor-A")
    second = leases.acquire("lane:P", "supervisor-B")
    assert second.fencing_generation == first.fencing_generation + 1
    assert not leases.validate(first)
    executor = FixtureExecutor()
    identity = DispatchIdentity("P","WP2","BUILD_FIXTURE_SUCCESSOR",_item().work_id,executor.capability.executor_id,first.fencing_generation)
    coordinator = DispatchCoordinator(leases, executor)
    try:
        coordinator.dispatch(identity, first, QuiescenceControl("RUN"))
    except PermissionError as exc:
        assert "STALE_FENCE" in str(exc)
    else:
        raise AssertionError("stale fence was accepted")


def test_duplicate_wake_produces_one_authoritative_start_and_heartbeat():
    leases = LeaseManager(); lease = leases.acquire("lane:P", "supervisor")
    executor = FixtureExecutor(); coordinator = DispatchCoordinator(leases, executor)
    item = _item(); identity = DispatchIdentity("P",item.packet_id,item.action,item.work_id,executor.capability.executor_id,lease.fencing_generation)
    first = coordinator.dispatch(identity, lease, QuiescenceControl("RUN"))
    second = coordinator.dispatch(identity, lease, QuiescenceControl("RUN"))
    assert first == second
    assert len(executor.starts) == 1
    worker = executor.heartbeat(identity.dispatch_id, lease.fencing_generation)
    assert worker.heartbeat_sequence == 2
    assert executor.complete(identity.dispatch_id, lease.fencing_generation).phase == "COMPLETED"


def test_unknown_start_is_reconciled_not_blindly_redispatched():
    leases = LeaseManager(); lease = leases.acquire("lane:P", "supervisor")
    executor = FixtureExecutor(); coordinator = DispatchCoordinator(leases, executor)
    item = _item(); identity = DispatchIdentity("P",item.packet_id,item.action,item.work_id,executor.capability.executor_id,lease.fencing_generation)
    unknown = coordinator.mark_unknown_start(identity, lease)
    assert unknown.phase == "DISPATCH_UNKNOWN" and unknown.reason == "UNKNOWN_START_STATE"
    assert coordinator.reconcile_unknown(identity.dispatch_id).phase == "DISPATCH_UNKNOWN"
    assert len(executor.starts) == 0


def test_event_ledger_is_at_least_once_idempotent_and_orders_out_of_order_events():
    ledger = EventLedger()
    assert ledger.ingest(source="github", source_sequence=2, event={"state":"done"})
    assert ledger.ingest(source="github", source_sequence=1, event={"state":"running"})
    assert not ledger.ingest(source="github", source_sequence=1, event={"state":"running"})
    assert [e["state"] for e in ledger.ordered()] == ["running","done"]


def test_fixture_executor_has_zero_write_reachability_and_quiescence_blocks_start():
    executor = FixtureExecutor()
    assert executor.capability.non_writing_fixture_only
    assert not executor.capability.repository_write
    assert not executor.capability.branch_ref_write
    assert not executor.capability.merge
    assert not executor.capability.force_push
    leases = LeaseManager(); lease = leases.acquire("lane:P","s")
    item = _item(); identity = DispatchIdentity("P",item.packet_id,item.action,item.work_id,executor.capability.executor_id,lease.fencing_generation)
    try:
        executor.start(identity, lease, QuiescenceControl("DISABLE_NEW_DISPATCH"))
    except PermissionError:
        pass
    else:
        raise AssertionError("quiescence did not block start")


def test_selective_invalidation_and_failure_owner_routing():
    descendants = ({"packet_id":"WP3","dependencies":["WP2"]},{"packet_id":"WPX","dependencies":["OTHER"]})
    assert selective_invalidation(changed_dependency="WP2", descendants=descendants) == ("WP3",)
    route = failure_route("P","WP2")
    assert route["route"] == "EXISTING_PROGRAMME_REPAIR_OWNER"
    assert route["cers_remediation_authority"] == "NONE"


def test_checkpoint_has_zero_chat_dependency():
    cp = SupervisorCheckpoint(fencing_generation=1, chat_dependency_count=0)
    assert cp.chat_dependency_count == 0
    try:
        SupervisorCheckpoint(fencing_generation=1, chat_dependency_count=1)
    except ValueError:
        pass
    else:
        raise AssertionError("chat dependent checkpoint accepted")
