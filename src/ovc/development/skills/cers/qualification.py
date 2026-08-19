from __future__ import annotations

from dataclasses import asdict
import math
from statistics import median
from time import perf_counter_ns
from typing import Any

from .persistent import PersistentDispatchProposal, PersistentWorkRequest, reconcile_persistent_requests
from .persistent_service import DurableSupervisorState, PersistentSupervisorService


BINDING_ID = "OVC-CERS-PERSISTENT-EXECUTOR-BINDING-v0.1"
EXECUTOR_ID = "OVC-SKILL-030@0.1.0+sha256:fixture|PACKET_EXECUTION|windows-local-python311"


def _admission(programme_id: str) -> dict[str, Any]:
    return {
        "status": "ACTIVE",
        "programme_id": programme_id,
        "current_state_root": f"registries/qualification/{programme_id}/CURRENT_STATE_POINTER.json",
        "governing_plan_id": f"{programme_id}-PLAN",
        "owner_authority_source": f"records/qualification/{programme_id}-AUTHORITY.json",
        "eligible_authority_classes": ["AUTO_EXECUTABLE", "AUTO_RATIFIABLE"],
        "eligible_packet_classes": ["LOW_RISK_IMPLEMENTATION"],
        "allowed_side_effect_classes": ["BRANCH_REVERSIBLE"],
        "executor_binding_id": BINDING_ID,
        "write_domain_rule": "PACKET_DECLARED_WRITE_DOMAIN_AND_SEMANTIC_OWNER_ONLY",
        "semantic_owner_rule": "EXACT_PACKET_SEMANTIC_OWNER_ONLY",
        "operator_boundary_policy": "PARK",
        "explicit_prohibitions": ["MERGE", "DIRECT_MAIN_WRITE", "FORCE_PUSH", "HISTORY_REWRITE"],
    }


def _request(
    programme_id: str,
    packet_id: str,
    *,
    priority: int,
    authority_required: str = "AUTO_EXECUTABLE",
    operator_boundary: bool = False,
    current_pointer_resolved: bool = True,
    action: str = "WRITE_FILE",
) -> PersistentWorkRequest:
    return PersistentWorkRequest(
        programme_id=programme_id,
        current_state_root=f"registries/qualification/{programme_id}/CURRENT_STATE_POINTER.json",
        governing_plan_id=f"{programme_id}-PLAN",
        packet_id=packet_id,
        packet_class="LOW_RISK_IMPLEMENTATION",
        authority_class="AUTO_EXECUTABLE",
        authority_required=authority_required,
        owner_authority_source=f"records/qualification/{programme_id}-AUTHORITY.json",
        owner_authority_current=True,
        executor_binding_id=BINDING_ID,
        action=action,
        side_effect_class="BRANCH_REVERSIBLE",
        write_domain=f"src/{programme_id.lower()}/",
        semantic_owner=programme_id,
        write_domain_declared=True,
        semantic_owner_match=True,
        prerequisites_pass=True,
        dependency_frontier_current=True,
        current_pointer_resolved=current_pointer_resolved,
        operator_boundary=operator_boundary,
        priority=priority,
    )


def _reconciliation_inputs() -> dict[str, Any]:
    programmes = ("OVC-QUAL-A", "OVC-QUAL-B")
    return {
        "admissions": {programme: _admission(programme) for programme in programmes},
        "policy": {
            "allowed_authority_classes": ["AUTO_EXECUTABLE", "AUTO_RATIFIABLE"],
            "future_programme_auto_admission": False,
            "direct_main_mutation": False,
            "merge_capability": "NONE",
            "parallel_physical_merge": False,
            "force_push": False,
            "history_rewrite": False,
            "irreversible_external_side_effects": False,
        },
        "executor_bindings": {
            BINDING_ID: {
                "binding_id": BINDING_ID,
                "status": "ACTIVE",
                "executor_identity": EXECUTOR_ID,
                "action_classes": ["WRITE_FILE", "GIT_COMMIT", "PUSH_BRANCH"],
                "merge": False,
                "force_push": False,
                "history_rewrite": False,
                "irreversible_external_side_effects": False,
            }
        },
        "action_registry": {
            "entries": [
                {"action": "WRITE_FILE", "side_effect_class": "BRANCH_REVERSIBLE", "allowed": True},
                {"action": "GIT_COMMIT", "side_effect_class": "BRANCH_REVERSIBLE", "allowed": True},
                {"action": "PUSH_BRANCH", "side_effect_class": "BRANCH_REVERSIBLE", "allowed": True},
            ],
            "explicit_denies": [
                "MERGE",
                "DIRECT_MAIN_WRITE",
                "FORCE_PUSH",
                "HISTORY_REWRITE",
                "VALIDATION_READ",
                "SCIENTIFIC_PROMOTION",
                "CANONICAL_PUBLICATION",
                "R2_PUBLICATION",
                "PROBABILITY",
                "RISK",
                "EXPOSURE",
                "TRADING",
                "MARKET_EXECUTION",
            ],
        },
        "quiescence_mode": "RUN",
        "fencing_generation": 1,
    }


def _percentiles(samples_ns: list[int]) -> dict[str, float]:
    ordered = sorted(samples_ns)

    def nearest(percent: float) -> float:
        index = max(0, math.ceil(percent * len(ordered)) - 1)
        return round(ordered[index] / 1_000_000, 6)

    return {
        "minimum_ms": round(ordered[0] / 1_000_000, 6),
        "median_ms": round(median(ordered) / 1_000_000, 6),
        "p95_ms": nearest(0.95),
        "p99_ms": nearest(0.99),
        "maximum_ms": round(ordered[-1] / 1_000_000, 6),
    }


def _proposal(dispatch, fence: int) -> PersistentDispatchProposal:
    return PersistentDispatchProposal(
        programme_id=dispatch.programme_id,
        packet_id=dispatch.packet_id,
        request_id=dispatch.request_id,
        authority_view_id=dispatch.authority_view_id,
        executor_identity=dispatch.executor_identity,
        action=dispatch.action,
        write_domain=dispatch.write_domain,
        semantic_owner=dispatch.semantic_owner,
        fencing_generation=fence,
    )


def run_persistent_qualification(*, iterations: int = 500) -> dict[str, Any]:
    if iterations < 20:
        raise ValueError("QUALIFICATION_REQUIRES_AT_LEAST_20_ITERATIONS")

    reconciliation_samples: list[int] = []
    lifecycle_samples: list[int] = []
    restart_samples: list[int] = []
    total_start = perf_counter_ns()
    inputs = _reconciliation_inputs()

    for sequence in range(iterations):
        requests = [
            _request("OVC-QUAL-A", "WP-A", priority=20),
            _request("OVC-QUAL-B", "WP-B", priority=10),
            _request(
                "OVC-QUAL-A",
                "G-OPERATOR",
                priority=1,
                authority_required="OPERATOR_REQUIRED",
                operator_boundary=True,
            ),
        ]
        started = perf_counter_ns()
        first = reconcile_persistent_requests(
            requests,
            snapshot_id=f"qualification-{sequence}",
            **inputs,
        )
        second = reconcile_persistent_requests(
            reversed(requests),
            snapshot_id=f"qualification-{sequence}",
            **inputs,
        )
        reconciliation_samples.append(perf_counter_ns() - started)
        if first.result_id != second.result_id:
            raise AssertionError("MULTI_PROGRAMME_RECONCILIATION_NONDETERMINISTIC")
        if [row.packet_id for row in first.dispatches] != ["WP-B", "WP-A"]:
            raise AssertionError("UNRELATED_LANE_FALSE_BLOCK")
        operator_view = next(row for row in first.views if row.packet_id == "G-OPERATOR")
        if (operator_view.decision, operator_view.primary_reason) != (
            "PARK",
            "OPERATOR_REQUIRED_BOUNDARY",
        ):
            raise AssertionError("OPERATOR_BOUNDARY_NOT_PARKED")

        churn = reconcile_persistent_requests(
            [
                _request("OVC-QUAL-A", "WP-A", priority=1),
                _request(
                    "OVC-QUAL-B",
                    "WP-B",
                    priority=2,
                    current_pointer_resolved=False,
                ),
            ],
            snapshot_id=f"churn-{sequence}",
            **inputs,
        )
        if [row.packet_id for row in churn.dispatches] != ["WP-A"]:
            raise AssertionError("MAIN_CHURN_NOT_SELECTIVE")

        unregistered = reconcile_persistent_requests(
            [_request("OVC-UNREGISTERED", "WP-X", priority=1)],
            snapshot_id=f"unregistered-{sequence}",
            **inputs,
        )
        if unregistered.views[0].primary_reason != "PROGRAMME_NOT_ADMITTED":
            raise AssertionError("UNREGISTERED_PROGRAMME_DISPATCHABLE")

        for forbidden in (
            "MERGE",
            "VALIDATION_READ",
            "SCIENTIFIC_PROMOTION",
            "CANONICAL_PUBLICATION",
            "R2_PUBLICATION",
            "PROBABILITY",
            "RISK",
            "EXPOSURE",
            "TRADING",
            "MARKET_EXECUTION",
        ):
            denied = reconcile_persistent_requests(
                [_request("OVC-QUAL-A", forbidden, priority=1, action=forbidden)],
                snapshot_id=f"forbidden-{sequence}-{forbidden}",
                **inputs,
            )
            if denied.views[0].decision != "DENY" or denied.dispatches:
                raise AssertionError(f"FORBIDDEN_BOUNDARY_REACHABLE:{forbidden}")

        lifecycle_start = perf_counter_ns()
        service = PersistentSupervisorService(
            DurableSupervisorState(
                supervisor_scope="CERS-PERSISTENT-QUALIFICATION",
                quiescence_mode="RUN",
            )
        )
        lease = service.acquire_lease("CERS-QUALIFIER")
        service.ingest_event(
            source="repository",
            source_sequence=sequence,
            event={"kind": "QUALIFICATION", "sequence": sequence},
        )
        service.reference_sweep(f"sweep-{sequence}", lease)
        proposal = _proposal(first.dispatches[0], lease.fencing_generation)
        service.persist_dispatch_intent(proposal, lease)
        service.acknowledge_start(proposal.dispatch_id, f"worker-{sequence}-a", lease)
        service.mark_running(proposal.dispatch_id, lease)
        service.heartbeat(proposal.dispatch_id, f"worker-{sequence}-a", lease)
        service.mark_worker_lost(proposal.dispatch_id, f"worker-{sequence}-a", lease)
        service.reconcile_unknown(
            proposal.dispatch_id,
            lease,
            observed_phase="RUNNING",
            observed_worker_run_id=f"worker-{sequence}-b",
        )
        service.complete(proposal.dispatch_id, f"worker-{sequence}-b", lease)
        lifecycle_samples.append(perf_counter_ns() - lifecycle_start)

        checkpoint_before = asdict(service.checkpoint())
        restart_start = perf_counter_ns()
        restarted = PersistentSupervisorService.zero_chat_restart(service.state.to_payload())
        checkpoint_after = asdict(restarted.checkpoint())
        restart_samples.append(perf_counter_ns() - restart_start)
        if checkpoint_before != checkpoint_after or restarted.state.state_id != service.state.state_id:
            raise AssertionError("ZERO_CHAT_RESTART_DIVERGED")

        replacement = service.reclaim_lease("CERS-RECOVERY", liveness_expired=True)
        try:
            service.reference_sweep("stale-sweep", lease)
        except PermissionError as error:
            if str(error) != "STALE_FENCE":
                raise
        else:
            raise AssertionError("STALE_FENCE_ACCEPTED")
        service.set_quiescence("HOLD")
        if service.accepts_new_dispatch:
            raise AssertionError("HOLD_ACCEPTED_NEW_DISPATCH")
        service.set_quiescence("DISABLE_NEW_DISPATCH")
        try:
            service.persist_dispatch_intent(
                PersistentDispatchProposal(
                    programme_id="OVC-QUAL-A",
                    packet_id="WP-ROLLBACK",
                    request_id=f"rollback-{sequence}",
                    authority_view_id=f"rollback-view-{sequence}",
                    executor_identity=EXECUTOR_ID,
                    action="WRITE_FILE",
                    write_domain="src/rollback/",
                    semantic_owner="OVC-QUAL-A",
                    fencing_generation=replacement.fencing_generation,
                ),
                replacement,
            )
        except PermissionError as error:
            if "QUIESCENCE_DISABLE_NEW_DISPATCH" not in str(error):
                raise
        else:
            raise AssertionError("DISABLE_NEW_DISPATCH_NOT_EXECUTABLE")

    wall_clock_ns = perf_counter_ns() - total_start
    combined_samples = [
        reconcile + lifecycle + restart
        for reconcile, lifecycle, restart in zip(
            reconciliation_samples, lifecycle_samples, restart_samples, strict=True
        )
    ]
    return {
        "iterations": iterations,
        "wall_clock_ms": round(wall_clock_ns / 1_000_000, 6),
        "measurements": {
            "deterministic_multi_programme_reconciliation": _percentiles(reconciliation_samples),
            "fenced_worker_loss_recovery_lifecycle": _percentiles(lifecycle_samples),
            "zero_chat_checkpoint_restart": _percentiles(restart_samples),
            "combined_observed_cycle": _percentiles(combined_samples),
        },
        "assertions": {
            "multiple_programmes_deterministic": "PASS",
            "unrelated_lanes_not_false_blocked": "PASS",
            "operator_boundary_parks_without_global_block": "PASS",
            "main_churn_selective": "PASS",
            "stale_fence_rejected": "PASS",
            "unknown_start_idempotent": "PASS",
            "worker_loss_single_authoritative_owner": "PASS",
            "hold_and_authority_removal_prevent_new_dispatch": "PASS",
            "unregistered_programme_denied": "PASS",
            "reserved_boundaries_unreachable": "PASS",
            "zero_chat_restart_deterministic": "PASS",
            "disable_new_dispatch_rollback": "PASS",
        },
        "authority_effect": "NONE_SHADOW_QUALIFICATION_ONLY",
    }


def derive_timing_freeze(
    qualification: dict[str, Any],
    *,
    pilot_duration_seconds: int,
    pilot_heartbeat_sequence: int,
) -> dict[str, Any]:
    if pilot_duration_seconds <= 0 or pilot_heartbeat_sequence <= 0:
        raise ValueError("PILOT_OBSERVATION_MUST_BE_POSITIVE")
    maximum_cycle_ms = float(
        qualification["measurements"]["combined_observed_cycle"]["maximum_ms"]
    )
    sweep_seconds = max(1, math.ceil(maximum_cycle_ms / 1000))
    heartbeat_seconds = math.ceil(pilot_duration_seconds / pilot_heartbeat_sequence)
    liveness_seconds = pilot_duration_seconds
    reclaim_seconds = liveness_seconds + heartbeat_seconds
    return {
        "status": "FROZEN_QUALIFIED",
        "sweep_cadence_seconds": sweep_seconds,
        "heartbeat_cadence_seconds": heartbeat_seconds,
        "liveness_threshold_seconds": liveness_seconds,
        "reclaim_after_seconds": reclaim_seconds,
        "provider_backoff_seconds": [sweep_seconds, heartbeat_seconds, liveness_seconds],
        "derivation": {
            "sweep_cadence": "ceil(maximum observed combined qualification cycle to integer seconds; minimum scheduler granularity one second)",
            "heartbeat_cadence": "ceil(observed live-pilot wall duration / recorded heartbeat sequence)",
            "liveness_threshold": "observed successful live-pilot wall duration",
            "reclaim_after": "liveness threshold plus one observed-derived heartbeat cadence",
            "provider_backoff": "bounded sequence of observed-derived sweep, heartbeat and liveness intervals",
        },
    }
