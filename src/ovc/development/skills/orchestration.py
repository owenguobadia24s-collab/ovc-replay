from __future__ import annotations

from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256


COMMANDS = {"RUN", "CONTINUE", "HOLD"}
SIDE_EFFECT_BARRIERS = {"B1_MUTATION", "B2_REMOTE_WRITE", "B3_INTEGRATION", "B4_AUTHORITY_TRANSITION"}
OPERATOR_GATE_CLASSES = {"OPERATOR_REQUIRED", "OPERATOR_RESERVED"}


def _record(schema: str, role: str, logical: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(logical)
    return {
        "schema": schema,
        **payload,
        "authority_effect": "NONE",
        "record_id": canonical_sha256(payload, role=role),
    }


def build_run_intent(*, command: str, scope: Mapping[str, Any], continuation_record_id: str | None = None) -> dict[str, Any]:
    cmd = str(command).upper()
    if cmd not in COMMANDS:
        raise ValueError(f"unsupported OVC command {cmd}")
    if not isinstance(scope, Mapping) or not scope.get("programme_id"):
        raise ValueError("scope with programme_id is required")
    logical = {
        "command": cmd,
        "scope": dict(scope),
        "continuation_record_id": continuation_record_id,
        "mutation_requested": False,
        "merge_requested": False,
    }
    return _record("ovc-dsai-run-intent/v1", "DSAI_RUN_INTENT", logical)


def build_scope_resolution(*, run_intent: Mapping[str, Any], programme_state: Mapping[str, Any]) -> dict[str, Any]:
    requested = dict(run_intent.get("scope", {}))
    programme_id = str(programme_state.get("programme_id", ""))
    if requested.get("programme_id") != programme_id:
        status = "BLOCKED"
        reason_codes = ["SCOPE_PROGRAMME_MISMATCH"]
        packet_ids: list[str] = []
    else:
        requested_packets = [str(v) for v in requested.get("packet_ids", [])]
        if not requested_packets:
            next_packet = programme_state.get("next_packet")
            requested_packets = [str(next_packet)] if next_packet else []
        status = "RESOLVED" if requested_packets else "BLOCKED"
        reason_codes = [] if requested_packets else ["SCOPE_PACKET_UNRESOLVED"]
        packet_ids = requested_packets
    logical = {
        "run_intent_id": run_intent.get("record_id"),
        "programme_id": programme_id,
        "packet_ids": packet_ids,
        "explicit_exclusions": sorted(str(v) for v in requested.get("exclude_packet_ids", [])),
        "status": status,
        "reason_codes": reason_codes,
    }
    return _record("ovc-dsai-scope-resolution-record/v1", "DSAI_SCOPE_RESOLUTION", logical)


def build_packet_graph_snapshot(*, programme_id: str, baseline_main: str, packets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in packets:
        packet_id = str(raw.get("packet_id", ""))
        if not packet_id or packet_id in seen:
            raise ValueError("packet ids must be non-empty and unique")
        seen.add(packet_id)
        nodes.append(
            {
                "packet_id": packet_id,
                "prerequisites": sorted(str(v) for v in raw.get("prerequisites", [])),
                "required_capabilities": list(dict.fromkeys(str(v) for v in raw.get("required_capabilities", []))),
                "gate_class": str(raw.get("gate_class", "AUTO_EXECUTABLE")),
                "authority_delta": str(raw.get("authority_delta", "NONE")),
                "packet_class": str(raw.get("packet_class", "IMPLEMENTATION")),
            }
        )
    nodes.sort(key=lambda row: row["packet_id"])
    logical = {"programme_id": str(programme_id), "baseline_main": str(baseline_main), "nodes": nodes}
    result = _record("ovc-dsai-packet-graph-snapshot/v1", "DSAI_PACKET_GRAPH_SNAPSHOT", logical)
    result["graph_hash"] = canonical_sha256(logical, role="DSAI_PACKET_GRAPH")
    return result


def build_packet_eligibility_record(
    *,
    packet_id: str,
    packet_graph: Mapping[str, Any],
    completed_prerequisites: Sequence[str],
    authority_prerequisites: Sequence[str] = (),
    satisfied_authority: Sequence[str] = (),
) -> dict[str, Any]:
    node = next((row for row in packet_graph.get("nodes", []) if row.get("packet_id") == packet_id), None)
    if node is None:
        raise ValueError(f"packet {packet_id} absent from graph")
    completed = {str(v) for v in completed_prerequisites}
    missing = sorted(set(str(v) for v in node.get("prerequisites", [])) - completed)
    authority_required = {str(v) for v in authority_prerequisites}
    authority_have = {str(v) for v in satisfied_authority}
    missing_authority = sorted(authority_required - authority_have)
    if missing:
        status, reasons = "BLOCKED", ["MISSING_PREREQUISITE"]
    elif missing_authority:
        status, reasons = "NEEDS_AUTHORITY", ["MISSING_AUTHORITY_PREREQUISITE"]
    else:
        status, reasons = "ELIGIBLE", []
    logical = {
        "packet_id": str(packet_id),
        "packet_graph_id": packet_graph.get("record_id"),
        "status": status,
        "missing_prerequisites": missing,
        "missing_authority": missing_authority,
        "reason_codes": reasons,
    }
    return _record("ovc-dsai-packet-eligibility-record/v1", "DSAI_PACKET_ELIGIBILITY", logical)


def build_capability_execution_graph(
    *, packet_id: str, required_capabilities: Sequence[str], resolution: Mapping[str, str]
) -> dict[str, Any]:
    ordered = list(dict.fromkeys(str(v) for v in required_capabilities))
    missing = [capability for capability in ordered if not resolution.get(capability)]
    stages = [
        {"stage_index": index, "capability_id": capability, "release_id": str(resolution[capability])}
        for index, capability in enumerate(ordered, start=1)
        if capability not in missing
    ]
    logical = {
        "packet_id": str(packet_id),
        "required_capabilities": ordered,
        "stages": stages,
        "missing_capabilities": missing,
        "status": "FROZEN" if ordered and not missing else "BLOCKED",
    }
    return _record("ovc-dsai-capability-execution-graph/v1", "DSAI_CAPABILITY_EXECUTION_GRAPH", logical)


def build_orchestration_run_manifest(
    *,
    run_intent: Mapping[str, Any],
    scope_resolution: Mapping[str, Any],
    packet_graph: Mapping[str, Any],
    packet_eligibility: Mapping[str, Any],
    capability_graph: Mapping[str, Any],
    baseline_main: str,
    environment_id: str,
) -> dict[str, Any]:
    ready = (
        scope_resolution.get("status") == "RESOLVED"
        and packet_eligibility.get("status") == "ELIGIBLE"
        and capability_graph.get("status") == "FROZEN"
    )
    logical = {
        "run_intent_id": run_intent.get("record_id"),
        "scope_resolution_id": scope_resolution.get("record_id"),
        "packet_graph_id": packet_graph.get("record_id"),
        "packet_eligibility_id": packet_eligibility.get("record_id"),
        "capability_execution_graph_id": capability_graph.get("record_id"),
        "baseline_main": str(baseline_main),
        "environment_id": str(environment_id),
        "orchestrator_stage": "ORCH-0",
        "execution_mode": "SHADOW_ONLY",
        "status": "READY" if ready else "BLOCKED",
        "write_authority": "NONE",
        "merge_authority": "NONE",
    }
    return _record("ovc-dsai-orchestration-run-manifest/v1", "DSAI_ORCHESTRATION_RUN_MANIFEST", logical)


def build_stage_execution_record(*, run_id: str, stage_index: int, capability_id: str, release_id: str, status: str) -> dict[str, Any]:
    logical = {
        "run_id": str(run_id),
        "stage_index": int(stage_index),
        "capability_id": str(capability_id),
        "release_id": str(release_id),
        "status": str(status),
        "writes_performed": [],
    }
    return _record("ovc-dsai-stage-execution-record/v1", "DSAI_STAGE_EXECUTION", logical)


def build_remediation_cycle_record(*, run_id: str, cycle: int, failure_class: str, action: str, status: str) -> dict[str, Any]:
    forbidden = {"CONTRACT_WEAKEN", "AUTHORITY_EXPAND", "TEST_WEAKEN", "EVIDENCE_DELETE"}
    if str(action).upper() in forbidden:
        raise ValueError("remediation action would weaken a frozen boundary")
    logical = {
        "run_id": str(run_id),
        "cycle": int(cycle),
        "failure_class": str(failure_class),
        "action": str(action),
        "status": str(status),
        "authority_delta": "NONE",
    }
    return _record("ovc-dsai-remediation-cycle-record/v1", "DSAI_REMEDIATION_CYCLE", logical)


def evaluate_side_effect_barrier(
    *,
    barrier: str,
    baseline_main: str,
    current_main: str,
    gate_class: str = "AUTO_EXECUTABLE",
    authority_delta: str = "NONE",
    remote_write_authorized: bool = False,
) -> dict[str, Any]:
    barrier_id = str(barrier).upper()
    if barrier_id not in SIDE_EFFECT_BARRIERS:
        raise ValueError(f"unsupported side-effect barrier {barrier_id}")
    reasons: list[str] = []
    status = "PASS"
    if baseline_main != current_main:
        status = "REVALIDATE_REQUIRED"
        reasons.append("MAIN_HEAD_CHURN")
    if barrier_id == "B2_REMOTE_WRITE" and not remote_write_authorized:
        status = "BLOCKED"
        reasons.append("REMOTE_WRITE_NOT_AUTHORIZED")
    if barrier_id == "B4_AUTHORITY_TRANSITION" and (
        str(gate_class).upper() in OPERATOR_GATE_CLASSES or str(authority_delta).upper() != "NONE"
    ):
        status = "NEEDS_AUTHORITY"
        reasons.append("OPERATOR_REQUIRED_RESERVED_DELTA")
    logical = {
        "barrier": barrier_id,
        "baseline_main": str(baseline_main),
        "current_main": str(current_main),
        "gate_class": str(gate_class).upper(),
        "authority_delta": str(authority_delta).upper(),
        "status": status,
        "reason_codes": sorted(set(reasons)),
    }
    return _record("ovc-dsai-side-effect-barrier-record/v1", "DSAI_SIDE_EFFECT_BARRIER", logical)


def build_continuation_record(
    *,
    programme_id: str,
    run_id: str,
    current_packet: str,
    next_action: str,
    baseline_main: str,
    evidence_refs: Sequence[str],
) -> dict[str, Any]:
    refs = sorted(set(str(v) for v in evidence_refs if str(v)))
    if not refs:
        raise ValueError("durable repository evidence refs are required")
    logical = {
        "programme_id": str(programme_id),
        "run_id": str(run_id),
        "current_packet": str(current_packet),
        "next_action": str(next_action),
        "baseline_main": str(baseline_main),
        "evidence_refs": refs,
        "source_of_truth": "DURABLE_REPOSITORY_EVIDENCE",
    }
    return _record("ovc-dsai-continuation-record/v1", "DSAI_CONTINUATION", logical)


def reconstruct_continuation(*, continuation_record: Mapping[str, Any], programme_state: Mapping[str, Any], current_main: str) -> dict[str, Any]:
    reasons: list[str] = []
    if continuation_record.get("source_of_truth") != "DURABLE_REPOSITORY_EVIDENCE":
        reasons.append("NON_DURABLE_CONTINUATION_SOURCE")
    if continuation_record.get("programme_id") != programme_state.get("programme_id"):
        reasons.append("CONTINUATION_PROGRAMME_MISMATCH")
    if not continuation_record.get("evidence_refs"):
        reasons.append("CONTINUATION_EVIDENCE_MISSING")
    if continuation_record.get("baseline_main") != current_main:
        reasons.append("MAIN_HEAD_CHURN")
    return {
        "schema": "ovc-dsai-continuation-reconstruction/v1",
        "status": "PASS" if not reasons else "BLOCKED",
        "reason_codes": sorted(set(reasons)),
        "next_action": continuation_record.get("next_action"),
        "authority_effect": "NONE",
    }


def build_stop_record(*, run_id: str, state: str, failure_class: str, reason_codes: Sequence[str], next_action: str) -> dict[str, Any]:
    logical = {
        "run_id": str(run_id),
        "state": str(state),
        "failure_class": str(failure_class),
        "reason_codes": sorted(set(str(v) for v in reason_codes)),
        "next_action": str(next_action),
    }
    return _record("ovc-dsai-orchestration-stop-record/v1", "DSAI_ORCHESTRATION_STOP", logical)


def orch0_shadow(
    *,
    run_intent: Mapping[str, Any],
    programme_state: Mapping[str, Any],
    packet_graph: Mapping[str, Any],
    packet_eligibility: Mapping[str, Any],
    capability_graph: Mapping[str, Any],
    baseline_main: str,
    current_main: str,
    environment_id: str,
    next_gate_class: str = "AUTO_EXECUTABLE",
    next_authority_delta: str = "NONE",
    continuation_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    scope = build_scope_resolution(run_intent=run_intent, programme_state=programme_state)
    run_id = canonical_sha256(
        {"intent": run_intent.get("record_id"), "scope": scope.get("record_id"), "baseline_main": baseline_main},
        role="DSAI_ORCH0_RUN",
    )
    command = str(run_intent.get("command", "")).upper()
    base_result: dict[str, Any] = {
        "schema": "ovc-dsai-orch0-shadow-result/v1",
        "run_id": run_id,
        "orchestrator_stage": "ORCH-0",
        "execution_mode": "SHADOW_ONLY",
        "authority_effect": "NONE",
        "writes_performed": [],
        "merge_requested": False,
        "merge_performed": False,
    }
    if command == "HOLD":
        continuation = build_continuation_record(
            programme_id=str(programme_state.get("programme_id")),
            run_id=run_id,
            current_packet=str(programme_state.get("next_packet") or programme_state.get("current_packet")),
            next_action="OVC CONTINUE",
            baseline_main=baseline_main,
            evidence_refs=["registries/implementation/dsai/CURRENT_STATE_POINTER.json"],
        )
        return {
            **base_result,
            "status": "HELD",
            "stop_record": build_stop_record(
                run_id=run_id, state="HELD", failure_class="OPERATOR_HOLD", reason_codes=["OPERATOR_HOLD"], next_action="OVC CONTINUE"
            ),
            "continuation_record": continuation,
        }
    if command == "CONTINUE":
        if continuation_record is None:
            return {
                **base_result,
                "status": "BLOCKED",
                "stop_record": build_stop_record(
                    run_id=run_id,
                    state="BLOCKED",
                    failure_class="INTEGRITY_BLOCK",
                    reason_codes=["CONTINUATION_RECORD_REQUIRED"],
                    next_action="MATERIALISE_DURABLE_CONTINUATION",
                ),
            }
        reconstruction = reconstruct_continuation(
            continuation_record=continuation_record, programme_state=programme_state, current_main=current_main
        )
        if reconstruction["status"] != "PASS":
            return {
                **base_result,
                "status": "BLOCKED",
                "continuation_reconstruction": reconstruction,
                "stop_record": build_stop_record(
                    run_id=run_id,
                    state="BLOCKED",
                    failure_class="INTEGRITY_BLOCK",
                    reason_codes=reconstruction["reason_codes"],
                    next_action="RECONCILE_REPOSITORY_STATE",
                ),
            }
    if scope.get("status") != "RESOLVED" or packet_eligibility.get("status") != "ELIGIBLE" or capability_graph.get("status") != "FROZEN":
        reasons = list(scope.get("reason_codes", [])) + list(packet_eligibility.get("reason_codes", []))
        if capability_graph.get("status") != "FROZEN":
            reasons.append("CAPABILITY_GRAPH_NOT_FROZEN")
        return {
            **base_result,
            "status": "BLOCKED",
            "stop_record": build_stop_record(
                run_id=run_id,
                state="BLOCKED",
                failure_class="DEPENDENCY_BLOCK",
                reason_codes=reasons or ["PACKET_NOT_ELIGIBLE"],
                next_action="RECONCILE_PACKET_ELIGIBILITY",
            ),
        }
    if baseline_main != current_main:
        barrier = evaluate_side_effect_barrier(
            barrier="B1_MUTATION", baseline_main=baseline_main, current_main=current_main
        )
        return {
            **base_result,
            "status": "BLOCKED",
            "barrier_record": barrier,
            "stop_record": build_stop_record(
                run_id=run_id,
                state="BLOCKED",
                failure_class="INTEGRITY_BLOCK",
                reason_codes=["MAIN_HEAD_CHURN"],
                next_action="RE_PREFLIGHT_CURRENT_MAIN",
            ),
        }
    manifest = build_orchestration_run_manifest(
        run_intent=run_intent,
        scope_resolution=scope,
        packet_graph=packet_graph,
        packet_eligibility=packet_eligibility,
        capability_graph=capability_graph,
        baseline_main=baseline_main,
        environment_id=environment_id,
    )
    gate_barrier = evaluate_side_effect_barrier(
        barrier="B4_AUTHORITY_TRANSITION",
        baseline_main=baseline_main,
        current_main=current_main,
        gate_class=next_gate_class,
        authority_delta=next_authority_delta,
    )
    if gate_barrier["status"] == "NEEDS_AUTHORITY":
        return {
            **base_result,
            "status": "WOULD_EXECUTE_TO_OPERATOR_GATE",
            "manifest": manifest,
            "barrier_record": gate_barrier,
            "stop_record": build_stop_record(
                run_id=run_id,
                state="GATE_READY",
                failure_class="NEEDS_AUTHORITY",
                reason_codes=gate_barrier["reason_codes"],
                next_action="OPERATOR_DECISION_REQUIRED",
            ),
        }
    stages = [
        build_stage_execution_record(
            run_id=run_id,
            stage_index=int(row["stage_index"]),
            capability_id=str(row["capability_id"]),
            release_id=str(row["release_id"]),
            status="WOULD_EXECUTE",
        )
        for row in capability_graph.get("stages", [])
    ]
    return {**base_result, "status": "WOULD_EXECUTE_AND_CONTINUE", "manifest": manifest, "stage_records": stages}


def orch1_assisted_plan(
    *, packet_class: str, enabled_packet_classes: Sequence[str], g8c_authority_effective: bool = False
) -> dict[str, Any]:
    enabled = {str(v) for v in enabled_packet_classes}
    packet = str(packet_class)
    if not g8c_authority_effective:
        status, reasons = "BLOCKED", ["DSAI_G8C_AUTHORITY_REQUIRED"]
    elif packet not in enabled:
        status, reasons = "BLOCKED", ["PACKET_CLASS_NOT_ENABLED"]
    else:
        status, reasons = "ASSISTED_EXECUTION_ELIGIBLE", []
    return {
        "schema": "ovc-dsai-orch1-assisted-plan/v1",
        "packet_class": packet,
        "enabled_packet_classes": sorted(enabled),
        "status": status,
        "reason_codes": reasons,
        "automatic_merge": False,
        "merge_authority": "NONE",
        "authority_effect": "NONE",
    }
