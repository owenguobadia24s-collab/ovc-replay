from __future__ import annotations

from itertools import combinations
from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256


AUTO_GATE_CLASSES = {"AUTO_EXECUTABLE", "AUTO_RATIFIABLE"}
OPERATOR_GATE_CLASSES = {"OPERATOR_REQUIRED", "OPERATOR_RESERVED"}
PARALLEL_BUILD_CLASS = "PARALLEL_BUILD_ALLOWED_SERIAL_INTEGRATION"
SERIAL_CLASS = "SERIAL_REQUIRED"
SERIAL_INTEGRATION_POLICY = "PDC_SERIAL_FINAL_INTEGRATION_WINDOW_REQUIRED"
LOW_RISK_PACKET_CLASS = "LOW_RISK_IMPLEMENTATION"


def _record(schema: str, role: str, logical: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(logical)
    return {
        "schema": schema,
        **payload,
        "authority_effect": "NONE",
        "record_id": canonical_sha256(payload, role=role),
    }


def _norm_values(values: Sequence[Any] | None) -> list[str]:
    return sorted({str(value).strip() for value in (values or ()) if str(value).strip()})


def normalize_write_path(path: str) -> str:
    value = str(path).replace("\\", "/").strip().strip("/")
    while "//" in value:
        value = value.replace("//", "/")
    for suffix in ("/**/*", "/**", "/*"):
        if value.endswith(suffix):
            value = value[: -len(suffix)]
    return value.rstrip("/")


def _path_overlap(left: str, right: str) -> bool:
    a = normalize_write_path(left)
    b = normalize_write_path(right)
    if not a or not b:
        return False
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def build_packet_descriptor(
    *,
    programme_id: str,
    packet_id: str,
    prerequisites: Sequence[str] = (),
    cross_programme_dependencies: Sequence[str] = (),
    write_paths: Sequence[str] = (),
    semantic_owners: Sequence[str] = (),
    authority_surfaces: Sequence[str] = (),
    frozen_surfaces: Sequence[str] = (),
    gate_class: str = "AUTO_EXECUTABLE",
    authority_delta: str = "NONE",
    packet_class: str = LOW_RISK_PACKET_CLASS,
    status: str = "READY",
    priority: int = 100,
) -> dict[str, Any]:
    if not programme_id or not packet_id:
        raise ValueError("programme_id and packet_id are required")
    logical = {
        "programme_id": str(programme_id),
        "packet_id": str(packet_id),
        "prerequisites": _norm_values(prerequisites),
        "cross_programme_dependencies": _norm_values(cross_programme_dependencies),
        "write_paths": sorted({normalize_write_path(v) for v in write_paths if normalize_write_path(v)}),
        "semantic_owners": _norm_values(semantic_owners),
        "authority_surfaces": _norm_values(authority_surfaces),
        "frozen_surfaces": _norm_values(frozen_surfaces),
        "gate_class": str(gate_class).upper(),
        "authority_delta": str(authority_delta).upper(),
        "packet_class": str(packet_class).upper(),
        "status": str(status).upper(),
        "priority": int(priority),
    }
    result = _record("ovc-dsai2-packet-descriptor/v1", "DSAI2_PACKET_DESCRIPTOR", logical)
    result["write_set_hash"] = canonical_sha256(logical["write_paths"], role="DSAI2_WRITE_SET")
    return result


def classify_packet_pair(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    left_id = str(left.get("packet_id", ""))
    right_id = str(right.get("packet_id", ""))
    if not left_id or not right_id or left_id == right_id:
        raise ValueError("distinct non-empty packet ids are required")

    reasons: list[str] = []
    overlaps: dict[str, list[str]] = {
        "write_paths": [],
        "semantic_owners": [],
        "authority_surfaces": [],
        "frozen_surfaces": [],
    }

    left_deps = set(_norm_values(left.get("prerequisites", ()))) | set(_norm_values(left.get("cross_programme_dependencies", ())))
    right_deps = set(_norm_values(right.get("prerequisites", ()))) | set(_norm_values(right.get("cross_programme_dependencies", ())))
    if right_id in left_deps or left_id in right_deps:
        reasons.append("ORDERED_DEPENDENCY")

    for side in (left, right):
        if str(side.get("packet_class", "")).upper() != LOW_RISK_PACKET_CLASS:
            reasons.append("PACKET_CLASS_NOT_PARALLEL_ELIGIBLE")
        if str(side.get("gate_class", "")).upper() in OPERATOR_GATE_CLASSES:
            reasons.append("OPERATOR_GATE_BOUNDARY")
        if str(side.get("authority_delta", "NONE")).upper() != "NONE":
            reasons.append("NON_NONE_AUTHORITY_DELTA")

    for a in _norm_values(left.get("write_paths", ())):
        for b in _norm_values(right.get("write_paths", ())):
            if _path_overlap(a, b):
                overlaps["write_paths"].append(f"{normalize_write_path(a)}::{normalize_write_path(b)}")
    if overlaps["write_paths"]:
        reasons.append("WRITE_SET_OVERLAP")

    for field, reason in (
        ("semantic_owners", "SEMANTIC_OWNER_OVERLAP"),
        ("authority_surfaces", "AUTHORITY_SURFACE_OVERLAP"),
        ("frozen_surfaces", "FROZEN_SURFACE_OVERLAP"),
    ):
        shared = sorted(set(_norm_values(left.get(field, ()))) & set(_norm_values(right.get(field, ()))))
        overlaps[field] = shared
        if shared:
            reasons.append(reason)

    classification = SERIAL_CLASS if reasons else PARALLEL_BUILD_CLASS
    logical = {
        "left_packet_id": left_id,
        "right_packet_id": right_id,
        "classification": classification,
        "reason_codes": sorted(set(reasons)),
        "overlaps": overlaps,
        "integration_policy": SERIAL_INTEGRATION_POLICY,
        "parallel_merge": False,
    }
    return _record("ovc-dsai2-packet-pair-classification/v1", "DSAI2_PACKET_PAIR_CLASSIFICATION", logical)


def build_conflict_matrix(packets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted(packets, key=lambda item: str(item.get("packet_id", "")))
    ids = [str(item.get("packet_id", "")) for item in ordered]
    if not ids or any(not packet_id for packet_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("packets require unique non-empty packet ids")
    pairs = [classify_packet_pair(left, right) for left, right in combinations(ordered, 2)]
    parallel = sum(1 for pair in pairs if pair["classification"] == PARALLEL_BUILD_CLASS)
    serial = len(pairs) - parallel
    logical = {
        "packet_ids": ids,
        "pair_count": len(pairs),
        "parallel_build_pair_count": parallel,
        "serial_required_pair_count": serial,
        "pairs": pairs,
        "ambiguity_policy": "SERIAL_REQUIRED",
        "integration_policy": SERIAL_INTEGRATION_POLICY,
        "parallel_merge": False,
        "status": "QUALIFIED" if pairs else "INSUFFICIENT_PAIRS",
    }
    return _record("ovc-dsai2-conflict-matrix/v1", "DSAI2_CONFLICT_MATRIX", logical)


def build_packet_train_plan(
    *,
    programme_id: str,
    packets: Sequence[Mapping[str, Any]],
    completed_packet_ids: Sequence[str] = (),
    max_packets: int | None = None,
) -> dict[str, Any]:
    if max_packets is not None and max_packets < 1:
        raise ValueError("max_packets must be positive")
    by_id: dict[str, Mapping[str, Any]] = {}
    for packet in packets:
        packet_id = str(packet.get("packet_id", ""))
        if not packet_id or packet_id in by_id:
            raise ValueError("packets require unique non-empty packet ids")
        if str(packet.get("programme_id", "")) != str(programme_id):
            raise ValueError("ORCH-3 packet train is programme-bounded")
        by_id[packet_id] = packet

    resolved = set(str(v) for v in completed_packet_ids)
    selected: list[str] = []
    operator_boundaries: list[str] = []
    waiting: list[dict[str, Any]] = []
    remaining = set(by_id)

    while remaining and (max_packets is None or len(selected) < max_packets):
        progressed = False
        for packet_id in sorted(remaining):
            packet = by_id[packet_id]
            prerequisites = set(_norm_values(packet.get("prerequisites", ()))) | set(
                _norm_values(packet.get("cross_programme_dependencies", ()))
            )
            if not prerequisites.issubset(resolved):
                continue
            gate_class = str(packet.get("gate_class", "AUTO_EXECUTABLE")).upper()
            authority_delta = str(packet.get("authority_delta", "NONE")).upper()
            packet_class = str(packet.get("packet_class", "")).upper()
            status = str(packet.get("status", "READY")).upper()
            if gate_class in OPERATOR_GATE_CLASSES or authority_delta != "NONE":
                operator_boundaries.append(packet_id)
                remaining.remove(packet_id)
                progressed = True
                break
            if packet_class != LOW_RISK_PACKET_CLASS or status not in {"READY", "PLANNED"}:
                waiting.append({"packet_id": packet_id, "reason": "NOT_AUTO_TRAIN_ELIGIBLE"})
                remaining.remove(packet_id)
                progressed = True
                break
            selected.append(packet_id)
            resolved.add(packet_id)
            remaining.remove(packet_id)
            progressed = True
            break
        if not progressed:
            break

    for packet_id in sorted(remaining):
        packet = by_id[packet_id]
        missing = sorted(
            (
                set(_norm_values(packet.get("prerequisites", ())))
                | set(_norm_values(packet.get("cross_programme_dependencies", ())))
            )
            - resolved
        )
        waiting.append({"packet_id": packet_id, "reason": "MISSING_PREREQUISITE", "missing": missing})

    logical = {
        "programme_id": str(programme_id),
        "selected_packet_ids": selected,
        "operator_boundaries": sorted(operator_boundaries),
        "waiting": waiting,
        "execution_policy": "SEQUENTIAL_PACKET_TRAIN",
        "integration_policy": SERIAL_INTEGRATION_POLICY,
        "orchestrator_stage": "ORCH-3",
        "execution_mode": "SHADOW_ONLY",
        "status": "READY" if selected else ("STOP_OPERATOR" if operator_boundaries else "BLOCKED"),
    }
    return _record("ovc-dsai2-orch3-packet-train-plan/v1", "DSAI2_ORCH3_PACKET_TRAIN", logical)


def build_portfolio_schedule(
    *,
    packets: Sequence[Mapping[str, Any]],
    completed_packet_ids: Sequence[str] = (),
    max_parallel: int = 2,
) -> dict[str, Any]:
    if max_parallel < 1:
        raise ValueError("max_parallel must be positive")
    completed = {str(v) for v in completed_packet_ids}
    candidates: list[Mapping[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    operator_wait: list[str] = []

    for packet in packets:
        packet_id = str(packet.get("packet_id", ""))
        if not packet_id:
            raise ValueError("packet_id is required")
        prerequisites = set(_norm_values(packet.get("prerequisites", ()))) | set(
            _norm_values(packet.get("cross_programme_dependencies", ()))
        )
        missing = sorted(prerequisites - completed)
        if missing:
            blocked.append({"packet_id": packet_id, "reason": "MISSING_PREREQUISITE", "missing": missing})
            continue
        if (
            str(packet.get("gate_class", "")).upper() in OPERATOR_GATE_CLASSES
            or str(packet.get("authority_delta", "NONE")).upper() != "NONE"
        ):
            operator_wait.append(packet_id)
            continue
        if (
            str(packet.get("packet_class", "")).upper() != LOW_RISK_PACKET_CLASS
            or str(packet.get("status", "READY")).upper() not in {"READY", "PLANNED"}
        ):
            blocked.append({"packet_id": packet_id, "reason": "NOT_PORTFOLIO_ELIGIBLE"})
            continue
        candidates.append(packet)

    candidates.sort(key=lambda item: (int(item.get("priority", 100)), str(item.get("programme_id", "")), str(item.get("packet_id", ""))))
    selected: list[Mapping[str, Any]] = []
    waiting: list[dict[str, Any]] = []

    for packet in candidates:
        if len(selected) >= max_parallel:
            waiting.append({"packet_id": str(packet["packet_id"]), "reason": "PARALLEL_SLOT_LIMIT"})
            continue
        conflicts = []
        for chosen in selected:
            pair = classify_packet_pair(chosen, packet)
            if pair["classification"] != PARALLEL_BUILD_CLASS:
                conflicts.append(
                    {
                        "with_packet_id": str(chosen["packet_id"]),
                        "reason_codes": pair["reason_codes"],
                    }
                )
        if conflicts:
            waiting.append({"packet_id": str(packet["packet_id"]), "reason": "SERIAL_FALLBACK", "conflicts": conflicts})
        else:
            selected.append(packet)

    logical = {
        "selected_packet_ids": [str(packet["packet_id"]) for packet in selected],
        "selected_programme_ids": sorted({str(packet["programme_id"]) for packet in selected}),
        "waiting": waiting,
        "blocked": blocked,
        "operator_wait": sorted(operator_wait),
        "max_parallel": int(max_parallel),
        "orchestrator_stage": "ORCH-5",
        "execution_mode": "SHADOW_ONLY",
        "dispatch_authority": "NONE",
        "integration_policy": SERIAL_INTEGRATION_POLICY,
        "parallel_merge": False,
        "status": "READY" if selected else "NO_ELIGIBLE_PACKET",
    }
    return _record("ovc-dsai2-orch5-portfolio-schedule/v1", "DSAI2_ORCH5_PORTFOLIO_SCHEDULE", logical)


def analyze_repository_empirical_corpus(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    programmes: set[str] = set()
    prs: set[int] = set()
    for event in events:
        event_type = str(event.get("event_type", "")).upper()
        if not event_type:
            raise ValueError("event_type is required")
        counts[event_type] = counts.get(event_type, 0) + 1
        if event.get("programme_id"):
            programmes.add(str(event["programme_id"]))
        programmes.update(str(v) for v in event.get("related_programmes", []) if str(v))
        if event.get("pr_number") is not None:
            prs.add(int(event["pr_number"]))

    churn_types = {
        "STALE_BASE_SUPERSESSION",
        "GREEN_ASSURANCE_DISCARDED",
        "MAIN_SYNC_RECONCILIATION",
        "APPROVED_GATE_STALE",
        "RECONCILIATION_NONMERGEABLE",
    }
    churn_pressure = sum(counts.get(name, 0) for name in churn_types)
    packet_train_signal = counts.get("PACKET_TRAIN_PROGRESS", 0) > 0
    parallel_signal = counts.get("LIVE_PARALLEL_PACKET", 0) > 0 or counts.get("CONCURRENT_PROGRAMMES", 0) > 0
    cross_programme_signal = counts.get("CROSS_PROGRAM_DEPENDENCY", 0) > 0
    serialized_integration_signal = counts.get("SERIAL_INTEGRATION_CORRECTION", 0) > 0

    logical = {
        "event_count": len(events),
        "distinct_pr_count": len(prs),
        "distinct_programme_count": len(programmes),
        "programme_ids": sorted(programmes),
        "event_type_counts": dict(sorted(counts.items())),
        "main_head_churn_pressure_events": churn_pressure,
        "signals": {
            "packet_train_progress_observed": packet_train_signal,
            "parallel_build_observed": parallel_signal,
            "cross_programme_dependency_observed": cross_programme_signal,
            "serialized_final_integration_observed": serialized_integration_signal,
        },
        "implementation_justification": {
            "orch3": packet_train_signal,
            "orch4": parallel_signal and churn_pressure > 0 and serialized_integration_signal,
            "orch5": cross_programme_signal and parallel_signal,
        },
        "authority_conclusion": "JUSTIFIES_CONFORMANCE_IMPLEMENTATION_NOT_SELF_ACTIVATION",
    }
    return _record("ovc-dsai2-empirical-corpus-analysis/v1", "DSAI2_EMPIRICAL_CORPUS_ANALYSIS", logical)


def build_activation_readiness(
    *,
    corpus_analysis: Mapping[str, Any],
    conflict_detector_qualified: bool,
    portfolio_scheduler_qualified: bool,
    pdc_terminal_state: str,
    unresolved_s3_s4: int,
) -> dict[str, Any]:
    reasons: list[str] = []
    justification = corpus_analysis.get("implementation_justification", {})
    for stage in ("orch3", "orch4", "orch5"):
        if justification.get(stage) is not True:
            reasons.append(f"{stage.upper()}_EMPIRICAL_JUSTIFICATION_MISSING")
    if not conflict_detector_qualified:
        reasons.append("ORCH4_CONFLICT_DETECTOR_NOT_QUALIFIED")
    if not portfolio_scheduler_qualified:
        reasons.append("ORCH5_PORTFOLIO_SCHEDULER_NOT_QUALIFIED")
    if "PARALLEL_BUILD_SERIALIZED_FINAL_INTEGRATION_WINDOW_ACTIVE" not in str(pdc_terminal_state):
        reasons.append("PDC_SERIAL_FINAL_INTEGRATION_WINDOW_NOT_ACTIVE")
    if int(unresolved_s3_s4) != 0:
        reasons.append("UNRESOLVED_S3_S4_PRESENT")

    proposed_delta = {
        "orch3": "ACTIVE_BOUNDED_LOW_RISK_PACKET_TRAINS",
        "orch4": "ACTIVE_BOUNDED_PARALLEL_BUILD_SERIAL_INTEGRATION",
        "orch5": "ACTIVE_BOUNDED_PORTFOLIO_DISPATCH_ONLY",
        "packet_classes": [LOW_RISK_PACKET_CLASS],
        "parallel_merge": False,
        "integration_policy": SERIAL_INTEGRATION_POLICY,
        "operator_required_gate": "DSAI2-G3",
    }
    logical = {
        "status": "GATE_READY_OPERATOR_REQUIRED" if not reasons else "BLOCKED",
        "reason_codes": sorted(reasons),
        "proposed_authority_delta": proposed_delta,
        "activation_performed": False,
        "self_grant_prohibited": True,
    }
    return _record("ovc-dsai2-orch345-activation-readiness/v1", "DSAI2_ORCH345_ACTIVATION_READINESS", logical)


def resolve_orch345_authority(*, authority: Mapping[str, Any], record_present_on_main: bool) -> dict[str, Any]:
    reasons: list[str] = []
    if authority.get("schema") != "ovc-dsai-orch345-authority/v1":
        reasons.append("AUTHORITY_SCHEMA_MISMATCH")
    if authority.get("gate_id") != "DSAI2-G3":
        reasons.append("GATE_ID_MISMATCH")
    if authority.get("programme_id") != "OVC-DSAI-v0.2":
        reasons.append("PROGRAMME_ID_MISMATCH")
    if authority.get("approved") is not True or authority.get("effective") is not True:
        reasons.append("AUTHORITY_NOT_EFFECTIVE")
    if not record_present_on_main:
        reasons.append("AUTHORITY_RECORD_NOT_PRESENT_ON_MAIN")
    if list(authority.get("enabled_orchestrators", [])) != ["ORCH-3", "ORCH-4", "ORCH-5"]:
        reasons.append("ORCHESTRATOR_ALLOWLIST_DRIFT")
    if list(authority.get("enabled_packet_classes", [])) != [LOW_RISK_PACKET_CLASS]:
        reasons.append("PACKET_CLASS_ALLOWLIST_DRIFT")
    modes = authority.get("modes", {})
    if not isinstance(modes, Mapping):
        reasons.append("MODE_POLICY_MISSING")
    else:
        expected = {
            "ORCH-3": "SERIAL_PACKET_TRAIN",
            "ORCH-4": "PARALLEL_BUILD_SERIAL_INTEGRATION",
            "ORCH-5": "PORTFOLIO_DISPATCH_ONLY",
        }
        for key, value in expected.items():
            if modes.get(key) != value:
                reasons.append(f"{key.replace('-', '')}_MODE_DRIFT")
    integration = authority.get("integration_policy", {})
    if not isinstance(integration, Mapping):
        reasons.append("INTEGRATION_POLICY_MISSING")
    else:
        if integration.get("serialized_final_integration_window") is not True:
            reasons.append("SERIAL_FIW_DISABLED")
        if integration.get("parallel_merge") is not False:
            reasons.append("PARALLEL_MERGE_ENABLED")
        if integration.get("target_branch") != "main":
            reasons.append("MERGE_TARGET_DRIFT")
        if integration.get("merge_method") != "squash":
            reasons.append("MERGE_METHOD_DRIFT")
        if integration.get("direct_main_mutation") is not False:
            reasons.append("DIRECT_MAIN_MUTATION_ENABLED")
        if integration.get("force_push") is not False:
            reasons.append("FORCE_PUSH_ENABLED")
        if integration.get("history_rewrite") is not False:
            reasons.append("HISTORY_REWRITE_ENABLED")
    if authority.get("validation") != "DENIED":
        reasons.append("VALIDATION_BOUNDARY_DRIFT")
    if authority.get("reserved_scientific_execution_authority") != "NONE":
        reasons.append("RESERVED_AUTHORITY_DRIFT")

    unique = sorted(set(reasons))
    return {
        "schema": "ovc-dsai-orch345-authority-resolution/v1",
        "status": "ACTIVE_AUTHORIZED" if not unique else "BLOCK",
        "reason_codes": unique or ["EXACT_DSAI2_G3_BOUNDED_ORCH345_AUTHORITY_ACTIVE"],
        "record_present_on_main": bool(record_present_on_main),
        "authority_effect": "READ_ONLY_RESOLUTION",
    }
