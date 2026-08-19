from __future__ import annotations

from dataclasses import asdict
import unittest

from ovc.development.skills.cers.persistent import PersistentDispatchProposal
from ovc.development.skills.cers.persistent_service import (
    DurableSupervisorState,
    PersistentSupervisorService,
    PersistentTimingPolicy,
)


SCOPE = "CERS_PERSISTENT_SUPERVISOR"


def service(mode: str = "RUN") -> tuple[PersistentSupervisorService, object]:
    svc = PersistentSupervisorService(DurableSupervisorState(supervisor_scope=SCOPE, quiescence_mode=mode))
    lease = svc.acquire_lease("CERS-SHADOW-SUPERVISOR")
    return svc, lease


def proposal(fence: int, packet: str = "WP-A") -> PersistentDispatchProposal:
    return PersistentDispatchProposal(
        programme_id="OVC-TEST-PROGRAMME-v1",
        packet_id=packet,
        request_id=f"request-{packet}",
        authority_view_id=f"view-{packet}",
        executor_identity="OVC-SKILL-030@fixture|PACKET_EXECUTION|windows-local-python311",
        action="WRITE_FILE",
        write_domain=f"src/{packet.lower()}/",
        semantic_owner="OVC-TEST",
        fencing_generation=fence,
    )


class PersistentSupervisorWp3Tests(unittest.TestCase):
    def test_exclusive_lease_and_stale_fence_rejection(self):
        svc, lease1 = service()
        with self.assertRaisesRegex(RuntimeError, "SUPERVISOR_LEASE_ALREADY_HELD"):
            svc.acquire_lease("SECOND")
        svc.release_lease(lease1)
        lease2 = svc.acquire_lease("SECOND")
        self.assertGreater(lease2.fencing_generation, lease1.fencing_generation)
        self.assertFalse(svc.validate_lease(lease1))
        with self.assertRaisesRegex(PermissionError, "STALE_FENCE"):
            svc.reference_sweep("sweep-stale", lease1)

    def test_reclaim_requires_explicit_liveness_expiry_signal(self):
        svc, lease1 = service()
        with self.assertRaisesRegex(RuntimeError, "RECLAIM_REQUIRES_QUALIFIED_LIVENESS_EXPIRY"):
            svc.reclaim_lease("RECOVERY", liveness_expired=False)
        lease2 = svc.reclaim_lease("RECOVERY", liveness_expired=True)
        self.assertGreater(lease2.fencing_generation, lease1.fencing_generation)
        self.assertFalse(svc.validate_lease(lease1))

    def test_event_trigger_and_reference_sweep_are_idempotent(self):
        svc, lease = service()
        event = {"kind": "PROGRAMME_STATE_CHANGED", "root": "state-v2"}
        self.assertTrue(svc.ingest_event(source="repo", source_sequence=1, event=event))
        self.assertFalse(svc.ingest_event(source="repo", source_sequence=1, event=event))
        with self.assertRaisesRegex(ValueError, "EVENT_IDENTITY_CONFLICT"):
            svc.ingest_event(source="repo", source_sequence=1, event={"kind": "OTHER"})
        self.assertTrue(svc.reference_sweep("reconciliation-1", lease))
        self.assertFalse(svc.reference_sweep("reconciliation-1", lease))
        self.assertEqual(svc.state.last_reconciliation_id, "reconciliation-1")

    def test_run_allows_new_intent_while_drain_hold_and_disable_block(self):
        svc, lease = service("RUN")
        p = proposal(lease.fencing_generation)
        self.assertEqual(svc.persist_dispatch_intent(p, lease)["phase"], "INTENT_PERSISTED")
        for mode in ("DRAIN", "HOLD", "DISABLE_NEW_DISPATCH"):
            svc.set_quiescence(mode)
            other = proposal(lease.fencing_generation, packet=f"WP-{mode}")
            with self.assertRaisesRegex(PermissionError, "BLOCKS_NEW_DISPATCH"):
                svc.persist_dispatch_intent(other, lease)

    def test_start_ack_is_required_before_running_and_duplicate_start_is_rejected(self):
        svc, lease = service()
        p = proposal(lease.fencing_generation)
        svc.persist_dispatch_intent(p, lease)
        with self.assertRaisesRegex(RuntimeError, "RUNNING_REQUIRES_START_ACKNOWLEDGED"):
            svc.mark_running(p.dispatch_id, lease)
        ack = svc.acknowledge_start(p.dispatch_id, "worker-1", lease)
        self.assertEqual(ack["phase"], "START_ACKNOWLEDGED")
        with self.assertRaisesRegex(RuntimeError, "DUPLICATE_AUTHORITATIVE_START"):
            svc.acknowledge_start(p.dispatch_id, "worker-2", lease)
        self.assertEqual(svc.mark_running(p.dispatch_id, lease)["phase"], "RUNNING")

    def test_unknown_start_must_reconcile_before_redispatch(self):
        svc, lease = service()
        p = proposal(lease.fencing_generation)
        svc.persist_dispatch_intent(p, lease)
        svc.mark_unknown_start(p.dispatch_id, lease)
        with self.assertRaisesRegex(RuntimeError, "UNKNOWN_START_MUST_RECONCILE_BEFORE_REDISPATCH"):
            svc.persist_dispatch_intent(p, lease)
        reconciled = svc.reconcile_unknown(p.dispatch_id, lease, observed_phase="NO_START")
        self.assertEqual(reconciled["phase"], "INTENT_PERSISTED")
        self.assertEqual(svc.persist_dispatch_intent(p, lease)["phase"], "INTENT_PERSISTED")

    def test_worker_loss_and_reconciliation_preserve_single_authoritative_owner(self):
        svc, lease = service()
        p = proposal(lease.fencing_generation)
        svc.persist_dispatch_intent(p, lease)
        svc.acknowledge_start(p.dispatch_id, "worker-1", lease)
        svc.mark_running(p.dispatch_id, lease)
        self.assertEqual(svc.heartbeat(p.dispatch_id, "worker-1", lease)["heartbeat_sequence"], 1)
        lost = svc.mark_worker_lost(p.dispatch_id, "worker-1", lease)
        self.assertEqual(lost["phase"], "DISPATCH_UNKNOWN")
        with self.assertRaisesRegex(PermissionError, "NO_AUTHORITATIVE_WORKER_OWNERSHIP"):
            svc.complete(p.dispatch_id, "worker-1", lease)
        recovered = svc.reconcile_unknown(p.dispatch_id, lease, observed_phase="RUNNING", observed_worker_run_id="worker-2")
        self.assertEqual(recovered["worker_run_id"], "worker-2")
        self.assertEqual(svc.complete(p.dispatch_id, "worker-2", lease)["phase"], "COMPLETED")

    def test_zero_chat_restart_reconstructs_same_durable_frontier(self):
        svc, lease = service()
        svc.ingest_event(source="repo", source_sequence=4, event={"kind": "CHANGE"})
        svc.reference_sweep("reconciliation-4", lease)
        p = proposal(lease.fencing_generation)
        svc.persist_dispatch_intent(p, lease)
        svc.acknowledge_start(p.dispatch_id, "worker-4", lease)
        before = svc.state.to_payload()
        restarted = PersistentSupervisorService.zero_chat_restart(before)
        after = restarted.state.to_payload()
        self.assertEqual(before, after)
        self.assertEqual(restarted.state.state_id, svc.state.state_id)
        self.assertEqual(asdict(restarted.checkpoint()), asdict(svc.checkpoint()))
        self.assertEqual(after["chat_dependency_count"], 0)

    def test_activation_timing_is_measure_before_freeze_and_backoff_is_bounded_only_after_freeze(self):
        svc, _ = service()
        self.assertFalse(svc.timing_policy.activation_ready)
        with self.assertRaisesRegex(RuntimeError, "TIMING_POLICY_NOT_FROZEN"):
            svc.backoff_for_attempt("provider", 0)
        measured = PersistentTimingPolicy(
            status="FROZEN_QUALIFIED",
            sweep_cadence_seconds=11,
            heartbeat_cadence_seconds=13,
            liveness_threshold_seconds=17,
            reclaim_after_seconds=23,
            provider_backoff_seconds=(1, 2, 5),
        )
        restarted = PersistentSupervisorService.zero_chat_restart(svc.state.to_payload(), timing_policy=measured)
        self.assertEqual(restarted.backoff_for_attempt("provider", 100), 5)

    def test_service_exposes_no_main_write_merge_or_history_rewrite_operation(self):
        svc, _ = service()
        for forbidden in ("merge", "write_main", "force_push", "rewrite_history"):
            self.assertFalse(hasattr(svc, forbidden))


if __name__ == "__main__":
    unittest.main()
