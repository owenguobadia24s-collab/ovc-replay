from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import tracemalloc
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ovc.research_operations.canonical import canonical_json_bytes, canonical_sha256
from ovc.research_operations.prospective_source import dukascopy_intake as intake
from ovc.research_operations.prospective_source import operator_replay_acceptance as replay

from .backpressure import QueuePolicy, project_review_queue
from .clustering import build_cluster_versions
from .evaluation import (
    evaluate_persistence_trigger,
    evaluate_switching_trigger,
    evaluate_transition_triggers,
    materialize_fired_events,
)
from .fingerprints import build_pattern_fingerprint
from .models import C2Snapshot, PatternDiscoveryError, parse_utc
from .review import build_candidate_detail, build_cluster_view, build_review_queue_item
from .transitions import extract_transitions
from .windows import CandidateWindowManager


PLAN_ID = "OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1"
AUTHORITY_GATE = "PD-G4B"
NEXT_GATE = "PD-G5P"
RESEARCH_ROLE = "PILOT_DISCOVERY"
OPERATION_MODE = "TIME_GATED_REPLAY"
SLICE_ID = "RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1"
SOURCE_MANIFEST_SHA256 = "429b7b568b7a43d04893c1873773f0b1b567730f2d5d4122d6a1c06dd40e3e41"
RUN_ID = "RPS.RUN.7aeb551335d766ee3bf503e6"
BINDING_ID = "RPS.BINDING.32fb3003efa072916c11e907"
OUTPUT_MANIFEST_SHA256 = "3c6295badd04896a9e94b4b5a3ccb354bb51de52d5927839a86f61a40ed679ff"
ACCEPTANCE_ID = "RPS.REPLAY-ACCEPT.0844eddf74e144ced487cc48"
SIGNING_BINDING_ID = "RPS.SIGNING.50092c28981fef08f53a6cb5"
OPERATOR_ID = "OVC.OPERATOR.PRIMARY.LOCAL.V1"
ACTIVE_C2_RELEASE = "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1"
ADMISSIBLE_CUTOFF = "2026-06-25T00:00:00Z"
PILOT_NAMESPACE = "PD.PILOT.GBPUSD.20260622_20260625.v1"
PILOT_BANNER = "PILOT_ONLY · NON_PROMOTABLE · TIME_GATED_REPLAY · GAPPED_SOURCE"
C2_MANIFEST_ID = f"RPS.C2MANIFEST.{OUTPUT_MANIFEST_SHA256[:24]}"
SELECTOR_ID = "OPT-B.C2.GBPUSD.DISCOVERY.ACTIVE"
FIXED_WINDOW_RECORDS = 4
ALLOWED_REVIEW_DISPOSITIONS = {
    "WORKFLOW_ACCEPTED",
    "FLAG_WORKFLOW_DEFECT",
    "FLAG_UI_FRICTION",
    "DEFER_PILOT_OBJECT",
    "REJECT_PILOT_OBJECT",
}


class PilotDiscoveryError(RuntimeError):
    pass


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def logical_sha(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PilotDiscoveryError(f"{code}:{path}") from exc
    if not isinstance(value, dict):
        raise PilotDiscoveryError(f"{code}:{path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise PilotDiscoveryError(f"INVALID_JSONL_OBJECT:{path}:{line_number}")
                result.append(value)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PilotDiscoveryError(f"INVALID_JSONL:{path}") from exc
    return result


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise PilotDiscoveryError(f"refusing to overwrite pilot evidence: {path}")
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: Iterable[Mapping[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise PilotDiscoveryError(f"refusing to overwrite pilot output: {path}")
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for value in values:
            handle.write(json.dumps(dict(value), sort_keys=True, separators=(",", ":")) + "\n")
            count += 1
    return count


def repository_state(repository_root: Path) -> tuple[str, str]:
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"], cwd=repository_root, check=True, capture_output=True, text=True
        ).stdout.strip()
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repository_root, check=True, capture_output=True, text=True
        ).stdout.strip()
        changes = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PilotDiscoveryError("unable to resolve repository state") from exc
    if branch != "main":
        raise PilotDiscoveryError("PD-WP5-PILOT local execution requires main")
    if changes:
        raise PilotDiscoveryError("PD-WP5-PILOT requires a clean tracked worktree")
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise PilotDiscoveryError("invalid repository commit identity")
    return branch, commit


def external_root(repository_root: Path, environ: Mapping[str, str]) -> Path:
    try:
        return intake._resolve_root(repository_root, environ)
    except intake.IntakeError as exc:
        raise PilotDiscoveryError(str(exc)) from exc


def safe_file(root: Path, relative: str) -> Path:
    candidate = root / Path(relative)
    if candidate.is_symlink() or not candidate.is_file():
        raise PilotDiscoveryError(f"required regular pilot input unavailable: {relative}")
    resolved_root = root.resolve(strict=True)
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise PilotDiscoveryError(f"pilot input escapes governed root: {relative}") from exc
    return resolved


def _repo_json(repository_root: Path, relative: str, code: str) -> dict[str, Any]:
    return load_json(repository_root / relative, code)


def load_governed_authority(repository_root: Path) -> dict[str, Any]:
    gate = _repo_json(
        repository_root,
        "registries/research_operations/pattern_discovery/PD_G4B_PILOT_DISCOVERY_GATE_STATE_v0_1.json",
        "INVALID_PD_G4B_STATE",
    )
    packet = _repo_json(
        repository_root,
        "registries/research_operations/pattern_discovery/PD_WP5_STATE_v0_1.json",
        "INVALID_PD_WP5_STATE",
    )
    signing = _repo_json(
        repository_root,
        "docs/releases/prospective-source-v0-1/rps-wp4/evidence/operator-signing-binding.json",
        "INVALID_SIGNING_BINDING",
    )
    acceptance = _repo_json(
        repository_root,
        "docs/releases/prospective-source-v0-1/rps-wp4/evidence/time-gated-replay-acceptance.json",
        "INVALID_REPLAY_ACCEPTANCE",
    )
    required_gate = {
        "gate_id": AUTHORITY_GATE,
        "gate_status": "APPROVED",
        "decision": "PASS",
        "research_role": RESEARCH_ROLE,
        "operation_mode": OPERATION_MODE,
        "source_slice_id": SLICE_ID,
        "compute_run_id": RUN_ID,
        "source_binding_id": BINDING_ID,
        "signed_replay_acceptance_id": ACCEPTANCE_ID,
        "signing_binding_id": SIGNING_BINDING_ID,
        "operator_id": OPERATOR_ID,
        "pilot_only": True,
        "promotion_eligibility": "NON_PROMOTABLE",
        "canonical_discovery_population": False,
        "canonical_append": "DENIED",
        "live_prospective_relabelling": "DENIED",
        "next_gate": NEXT_GATE,
    }
    for key, expected in required_gate.items():
        if gate.get(key) != expected:
            raise PilotDiscoveryError(f"PD_G4B_AUTHORITY_MISMATCH:{key}")
    if packet.get("packet_status") != "APPROVED" or packet.get("next_packet") != "PD-WP5-PILOT":
        raise PilotDiscoveryError("PD-WP5-PILOT is not authorised")
    expected_signing = {
        "signing_binding_id": SIGNING_BINDING_ID,
        "binding_id": BINDING_ID,
        "run_id": RUN_ID,
        "source_slice_id": SLICE_ID,
        "operator_id": OPERATOR_ID,
        "algorithm": "ED25519",
        "signature_namespace": replay.SIGNATURE_NAMESPACE,
    }
    for key, expected in expected_signing.items():
        if signing.get(key) != expected:
            raise PilotDiscoveryError(f"SIGNING_BINDING_MISMATCH:{key}")
    expected_acceptance = {
        "acceptance_id": ACCEPTANCE_ID,
        "binding_id": BINDING_ID,
        "run_id": RUN_ID,
        "source_slice_id": SLICE_ID,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "output_manifest_sha256": OUTPUT_MANIFEST_SHA256,
        "operation_mode": OPERATION_MODE,
        "operator_id": OPERATOR_ID,
        "signing_binding_id": SIGNING_BINDING_ID,
        "acceptance": "ACCEPTED_FOR_TIME_GATED_REPLAY_ONLY",
    }
    for key, expected in expected_acceptance.items():
        if acceptance.get(key) != expected:
            raise PilotDiscoveryError(f"REPLAY_ACCEPTANCE_MISMATCH:{key}")
    return {"gate": gate, "packet": packet, "signing": signing, "acceptance": acceptance}


def _pilot_id(kind: str, source: object) -> str:
    return f"PDPILOT-{kind}-{canonical_sha256({'namespace': PILOT_NAMESPACE, 'source': source})[:24]}"


def _expected_step_seconds(clock: str) -> int:
    return 15 * 60 if clock == "15M" else 2 * 60 * 60


def normalise_c2_states(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for source in rows:
        item = dict(source)
        clock = str(item.get("clock") or "")
        side = str(item.get("side") or "")
        scope = str(item.get("evaluation_scope_id") or "")
        if clock not in {"15M", "2H_A_L"} or side not in {"BID", "ASK"} or not scope:
            raise PilotDiscoveryError("unsupported C2 state scope in pilot input")
        item["c2_release_id"] = ACTIVE_C2_RELEASE
        item["c2_manifest_id"] = C2_MANIFEST_ID
        item["selector_id"] = SELECTOR_ID
        item["authority_state"] = str(item.get("authority_state") or "TIME_GATED_REPLAY_DERIVED")
        containers = sorted(str(value) for value in item.get("container_ids", ()) if value)
        item["parent_container_id"] = str(item.get("parent_container_id") or (containers[0] if containers else "UNRESOLVED"))
        item["boundary_or_relation_id"] = str(item.get("boundary_or_relation_id") or item.get("relation_set_id") or "UNRESOLVED")
        item["gap_before"] = bool(item.get("gap_before", False))
        groups[(clock, side, scope)].append(item)

    output: list[dict[str, Any]] = []
    for key in sorted(groups):
        ordered = sorted(groups[key], key=lambda item: (parse_utc(str(item["first_valid_time"])), str(item["c2_state_id"])))
        previous_time = None
        for item in ordered:
            current_time = parse_utc(str(item["first_valid_time"]))
            if previous_time is not None:
                delta = int((current_time - previous_time).total_seconds())
                if delta > _expected_step_seconds(key[0]):
                    item["gap_before"] = True
            C2Snapshot.from_mapping(item)
            output.append(item)
            previous_time = current_time
    return output


def load_exact_c2_states(compute_root: Path, manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    paths = sorted(
        str(item.get("path"))
        for item in manifest.get("files", ())
        if str(item.get("path", "")).startswith("c2/states/") and str(item.get("path", "")).endswith(".jsonl")
    )
    if len(paths) != 6:
        raise PilotDiscoveryError(f"expected six exact C2 state payloads, found {len(paths)}")
    rows: list[dict[str, Any]] = []
    for relative in paths:
        rows.extend(load_jsonl(safe_file(compute_root, relative)))
    if not rows:
        raise PilotDiscoveryError("accepted compute run contains no C2 states")
    return normalise_c2_states(rows)


def _pilot_markings() -> dict[str, Any]:
    return {
        "research_role": RESEARCH_ROLE,
        "operation_mode": OPERATION_MODE,
        "pilot_only": True,
        "promotion_eligibility": "NON_PROMOTABLE",
        "canonical_discovery_population": False,
        "live_prospective": False,
        "identity_namespace": PILOT_NAMESPACE,
    }


def _group_states(states: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for source in states:
        item = dict(source)
        groups[(str(item["clock"]), str(item["side"]), str(item["evaluation_scope_id"]))].append(item)
    return {
        key: sorted(values, key=lambda item: (parse_utc(str(item["first_valid_time"])), str(item["c2_state_id"])))
        for key, values in sorted(groups.items())
    }


def run_pilot_from_states(states: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    normalized = normalise_c2_states(states)
    all_transitions: list[dict[str, Any]] = []
    all_events: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    state_by_id = {str(item["c2_state_id"]): dict(item) for item in normalized}
    event_metadata: dict[str, dict[str, Any]] = {}

    for (clock, side, scope), group in _group_states(normalized).items():
        manager = CandidateWindowManager(max_open_per_family_scope=1, max_open_per_instrument=20)
        history: list[dict[str, Any]] = []
        for index, current in enumerate(group):
            history.append(current)
            if index == 0:
                continue
            previous = group[index - 1]
            transitions = extract_transitions(previous, current)
            marked_transitions = [{**item, **_pilot_markings()} for item in transitions]
            all_transitions.extend(marked_transitions)

            for window in manager.all_windows():
                if window["status"] not in {"OPEN", "OPEN_PENDING_INPUT", "ACCUMULATING"}:
                    continue
                updated = manager.accumulate(str(window["window_id"]), current)
                if updated["status"] in {"OPEN", "OPEN_PENDING_INPUT", "ACCUMULATING"} and len(updated["source_c2_record_ids"]) >= FIXED_WINDOW_RECORDS:
                    manager.close(str(updated["window_id"]), str(current["first_valid_time"]), "PILOT_FIXED_HORIZON_4_RECORDS")

            evaluations = evaluate_transition_triggers(previous, current, transitions)
            evaluations.append(evaluate_persistence_trigger(history, transitions))
            evaluations.append(evaluate_switching_trigger(history, transitions))
            events = materialize_fired_events(evaluations, transitions, operation_mode=OPERATION_MODE)
            family_by_trigger = {item.trigger_id: item.family for item in evaluations}
            for event in events:
                engine_event_id = str(event["trigger_event_id"])
                pilot_event_id = _pilot_id("TRIGGER", engine_event_id)
                marked_event = {
                    **event,
                    "engine_trigger_event_id": engine_event_id,
                    "trigger_event_id": pilot_event_id,
                    "trigger_family": family_by_trigger.get(str(event["trigger_id"]), "CONTROL"),
                    **_pilot_markings(),
                }
                all_events.append(marked_event)
                event_metadata[pilot_event_id] = marked_event
                engine_window = manager.open_from_trigger(
                    current,
                    event,
                    trigger_family=str(marked_event["trigger_family"]),
                )
                # The engine uses the immutable event identity internally. It is replaced
                # only in the isolated public pilot namespace below.
                event_metadata[engine_event_id] = marked_event

        if group:
            final_time = str(group[-1]["first_valid_time"])
            for window in manager.all_windows():
                if window["status"] in {"OPEN", "OPEN_PENDING_INPUT", "ACCUMULATING"}:
                    manager.close(str(window["window_id"]), final_time, "PILOT_SOURCE_WINDOW_END")

        for window in manager.all_windows():
            engine_window_id = str(window["window_id"])
            trigger_ids = [str(item) for item in window.get("trigger_event_ids", ())]
            marked_trigger_ids = [
                str(event_metadata[item]["trigger_event_id"]) if item in event_metadata else _pilot_id("TRIGGER", item)
                for item in trigger_ids
            ]
            primary_event = next((event_metadata[item] for item in trigger_ids if item in event_metadata), None)
            source_ids = [str(item) for item in window.get("source_c2_record_ids", ())]
            sequence = [state_by_id[item] for item in source_ids if item in state_by_id]
            pilot_window_id = _pilot_id("CANDIDATE", engine_window_id)
            closure_reason = str(window.get("closure_reason") or "UNRESOLVED")
            candidate = {
                **window,
                "engine_window_id": engine_window_id,
                "window_id": pilot_window_id,
                "trigger_event_ids": marked_trigger_ids,
                "trigger_family": str(primary_event.get("trigger_family") if primary_event else "CONTROL"),
                "primary_trigger_reason": str(primary_event.get("reason_code") if primary_event else closure_reason),
                "primary_transition_grammar": str(primary_event.get("trigger_family") if primary_event else "CONTROL"),
                "boundary_interaction_class": str(primary_event.get("rate_limit_group") if primary_event else "UNRESOLVED"),
                "parent_containment_class": "WITH_2H_PARENT" if "WITH-2H-PARENT" in scope else "LOCAL_ONLY",
                "closure_class": closure_reason,
                "source_lineage_status": "RESOLVED",
                "duration_records": len(sequence),
                "transition_summary": sorted({str(item["axis_or_relation"]) for item in all_transitions if item.get("scope_id") == scope and item.get("clock") == clock and item.get("price_side") == side}),
                "timeline": [
                    {"c2_state_id": item["c2_state_id"], "first_valid_time": item["first_valid_time"], "axes": item["axes"]}
                    for item in sequence
                ],
                **_pilot_markings(),
            }
            candidates.append(candidate)

    candidates = sorted(candidates, key=lambda item: (str(item["trigger_first_valid_at"]), str(item["window_id"])))
    if not candidates:
        raise PilotDiscoveryError("pilot trigger evaluation produced no candidate windows")

    fingerprints: list[dict[str, Any]] = []
    for candidate in candidates:
        sequence = [state_by_id[item] for item in candidate.get("source_c2_record_ids", ()) if item in state_by_id]
        transition_sequence = [str(item) for item in candidate.get("transition_summary", ())]
        fingerprint = build_pattern_fingerprint(
            candidate,
            state_sequence=sequence,
            transition_sequence=transition_sequence,
            interaction_events=[str(candidate.get("primary_trigger_reason"))],
            cross_scale_context={"containment_class": candidate["parent_containment_class"]},
        )
        engine_fingerprint_id = str(fingerprint["fingerprint_id"])
        fingerprints.append(
            {
                **fingerprint,
                "engine_fingerprint_id": engine_fingerprint_id,
                "fingerprint_id": _pilot_id("FINGERPRINT", engine_fingerprint_id),
                "candidate_status": candidate["status"],
                "source_lineage_status": "RESOLVED",
                **_pilot_markings(),
            }
        )

    cluster_versions = build_cluster_versions(fingerprints)
    marked_clusters: list[dict[str, Any]] = []
    for cluster in cluster_versions:
        engine_version_id = str(cluster["cluster_version_id"])
        rows = []
        for row in cluster.get("clusters", ()):
            engine_cluster_id = str(row["cluster_id"])
            rows.append({**row, "engine_cluster_id": engine_cluster_id, "cluster_id": _pilot_id("CLUSTER", engine_cluster_id), **_pilot_markings()})
        marked_clusters.append(
            {
                **cluster,
                "engine_cluster_version_id": engine_version_id,
                "cluster_version_id": _pilot_id("CLUSTER-VERSION", engine_version_id),
                "clusters": rows,
                "semantic_authority": "NONE",
                "family_promotion": "DENIED",
                **_pilot_markings(),
            }
        )

    queue_projection = project_review_queue(candidates, unresolved_queue_depth=0, policy=QueuePolicy())
    fingerprint_by_candidate = {str(item["candidate_window_id"]): item for item in fingerprints}

    def cluster_for(fingerprint_id: str) -> dict[str, Any] | None:
        for cluster in marked_clusters:
            if fingerprint_id in cluster.get("assignments", {}):
                return cluster
        return None

    queue_items: list[dict[str, Any]] = []
    candidate_details: dict[str, dict[str, Any]] = {}
    for candidate in queue_projection["promoted"]:
        candidate_id = str(candidate["window_id"])
        fingerprint = fingerprint_by_candidate[candidate_id]
        cluster = cluster_for(str(fingerprint["fingerprint_id"]))
        queue_item = {**build_review_queue_item(candidate, fingerprint=fingerprint, cluster_version=cluster), **_pilot_markings()}
        queue_item["authority"] = "PILOT_READ_ONLY_REVIEW"
        queue_items.append(queue_item)
        detail = build_candidate_detail(candidate, fingerprint=fingerprint, cluster_version=cluster)
        detail["authority_banner"] = PILOT_BANNER
        detail["pilot"] = _pilot_markings()
        candidate_details[candidate_id] = detail

    console_bundle = {
        "pilot": {**_pilot_markings(), "banner": PILOT_BANNER, "coverage_state": "GAPPED"},
        "authority": {
            "active_research_triage": True,
            "candidate_source_resolved": True,
            "live_append_enabled": False,
            "canonical_append_enabled": False,
            "operation_mode": OPERATION_MODE,
            "authority_label": PILOT_BANNER,
        },
        "queue_items": queue_items,
        "candidate_details": candidate_details,
        "cluster_views": [build_cluster_view(item) | {"authority_banner": PILOT_BANNER} for item in marked_clusters],
    }
    if len(marked_clusters) == 1:
        console_bundle["cluster_view"] = console_bundle["cluster_views"][0]

    review_template = {
        "schema": "ovc-pd-wp5-pilot-review-input/v1",
        "pilot_namespace": PILOT_NAMESPACE,
        "pilot_run_id": "TO_BE_BOUND_AT_EXECUTION",
        "operator_id": OPERATOR_ID,
        "reviewed_at_utc": "REPLACE_WITH_UTC_TIMESTAMP",
        "decisions": [
            {
                "candidate_window_id": item["candidate_window_id"],
                "review_disposition": "REPLACE_WITH_ALLOWED_DISPOSITION",
                "notes": "",
                "ui_friction_codes": [],
            }
            for item in queue_items
        ],
        "allowed_dispositions": sorted(ALLOWED_REVIEW_DISPOSITIONS),
        "pilot_only": True,
        "promotion_eligibility": "NON_PROMOTABLE",
        "canonical_append": "DENIED",
    }

    return {
        "schema": "ovc-pd-wp5-pilot-derived-bundle/v1",
        "pilot_namespace": PILOT_NAMESPACE,
        "source_slice_id": SLICE_ID,
        "compute_run_id": RUN_ID,
        "source_binding_id": BINDING_ID,
        "signed_replay_acceptance_id": ACCEPTANCE_ID,
        "operation_mode": OPERATION_MODE,
        "research_role": RESEARCH_ROLE,
        "coverage_state": "GAPPED",
        "transitions": sorted(all_transitions, key=lambda item: (str(item["first_valid_at"]), str(item["transition_id"]))),
        "trigger_events": sorted(all_events, key=lambda item: (str(item["first_valid_at"]), str(item["trigger_event_id"]))),
        "candidates": candidates,
        "fingerprints": sorted(fingerprints, key=lambda item: str(item["fingerprint_id"])),
        "cluster_versions": sorted(marked_clusters, key=lambda item: str(item["cluster_version_id"])),
        "queue_projection": queue_projection,
        "console_bundle": console_bundle,
        "review_template": review_template,
        "counts": {
            "c2_states": len(normalized),
            "transitions": len(all_transitions),
            "trigger_events": len(all_events),
            "candidates": len(candidates),
            "queue_promoted": len(queue_items),
            "queue_suppressed": len(queue_projection["suppressed"]),
            "fingerprints": len(fingerprints),
            "cluster_versions": len(marked_clusters),
            "cluster_rows": sum(len(item.get("clusters", ())) for item in marked_clusters),
        },
        "authority": {
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_discovery_population": False,
            "canonical_append": "DENIED",
            "live_prospective_relabelling": "DENIED",
            "semantic_promotion": "DENIED",
            "family_promotion": "DENIED",
            "active_novelty_ranking": "DENIED",
            "selector_mutation": "DENIED",
            "release_mutation": "DENIED",
            "r2_publication": "DENIED",
            "validation_consumption": "DENIED",
            "probability_authority": "NONE",
            "risk_authority": "NONE",
            "exposure_authority": "NONE",
            "trading_authority": "NONE",
            "execution_authority": "NONE",
            "agent_write_authority": "NONE",
        },
    }


def _file_inventory(root: Path, paths: Sequence[Path]) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha_file(path),
        }
        for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix())
    ]


def _quarantine(staging: Path, reason: str) -> Path | None:
    if not staging.exists():
        return None
    root = staging.parent / "quarantine"
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"PD-WP5-PILOT.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.{uuid.uuid4().hex[:8]}"
    try:
        write_json(
            staging / "failure-receipt.json",
            {
                "schema": "ovc-pd-wp5-pilot-failure/v1",
                "reason": reason,
                "pilot_namespace": PILOT_NAMESPACE,
                "canonical_append": "DENIED",
                "live_prospective_relabelling": "DENIED",
                "provider_network_access_performed": False,
            },
        )
    except Exception:
        pass
    staging.rename(target)
    return target


def preflight(repository_root: Path, *, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    branch, commit = repository_state(repository_root)
    authority = load_governed_authority(repository_root)
    compute_root, manifest, run, binding, _ = replay.verify_compute_run(repository_root, values)
    private_key, public_key = replay.key_paths(repository_root, values, OPERATOR_ID)
    return {
        "status": "READY_FOR_PD_WP5_PILOT_EXECUTION",
        "repository_branch": branch,
        "repository_commit": commit,
        "authority_gate": AUTHORITY_GATE,
        "next_gate": NEXT_GATE,
        "pilot_namespace": PILOT_NAMESPACE,
        "source_slice_id": SLICE_ID,
        "compute_run_id": RUN_ID,
        "source_binding_id": BINDING_ID,
        "signed_replay_acceptance_id": ACCEPTANCE_ID,
        "signing_binding_id": SIGNING_BINDING_ID,
        "operator_id": OPERATOR_ID,
        "compute_root": str(compute_root),
        "compute_file_count": manifest["file_count"],
        "compute_status": run["status"],
        "binding_status": binding["status"],
        "private_key_exists": private_key.is_file() and not private_key.is_symlink(),
        "public_key_exists": public_key.is_file() and not public_key.is_symlink(),
        "operator_approval_recorded": authority["gate"]["decision"] == "PASS",
        "provider_network_access_performed": False,
        "canonical_append": "DENIED",
    }


def execute(
    repository_root: Path,
    *,
    authority_gate: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    if authority_gate != AUTHORITY_GATE:
        raise PilotDiscoveryError(f"exact operator authority required: --gate {AUTHORITY_GATE}")
    if truthy(values.get("CI")) or truthy(values.get("GITHUB_ACTIONS")):
        raise PilotDiscoveryError("PD-WP5-PILOT external execution is prohibited in CI")
    _, code_commit = repository_state(repository_root)
    authority = load_governed_authority(repository_root)
    compute_root, manifest, _, _, _ = replay.verify_compute_run(repository_root, values)
    states = load_exact_c2_states(compute_root, manifest)

    tracemalloc.start()
    started = time.perf_counter()
    first = run_pilot_from_states(states)
    second = run_pilot_from_states(states)
    elapsed = time.perf_counter() - started
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    first_hash = logical_sha(first)
    second_hash = logical_sha(second)
    if first_hash != second_hash:
        raise PilotDiscoveryError("deterministic pilot rerun mismatch")

    identity = {
        "pilot_namespace": PILOT_NAMESPACE,
        "source_slice_id": SLICE_ID,
        "compute_run_id": RUN_ID,
        "source_binding_id": BINDING_ID,
        "derived_bundle_sha256": first_hash,
        "code_commit": code_commit,
    }
    pilot_run_id = f"PD.PILOT.RUN.{canonical_sha256(identity)[:24]}"
    first["review_template"]["pilot_run_id"] = pilot_run_id

    private_key, public_key_path = replay.key_paths(repository_root, values, OPERATOR_ID)
    if private_key.is_symlink() or not private_key.is_file() or public_key_path.is_symlink() or not public_key_path.is_file():
        raise PilotDiscoveryError("exact operator Ed25519 key pair is unavailable or unsafe")
    public = replay.public_key_details(public_key_path, OPERATOR_ID)
    signing = authority["signing"]
    if public["public_key_sha256"] != signing["public_key_sha256"] or public["public_key_fingerprint"] != signing["public_key_fingerprint"]:
        raise PilotDiscoveryError("operator key does not match the approved signing binding")

    output_root = external_root(repository_root, values) / "pattern-discovery" / "pilot" / PILOT_NAMESPACE
    output_root.mkdir(parents=True, exist_ok=True)
    final = output_root / pilot_run_id
    if final.exists():
        raise PilotDiscoveryError(f"refusing to overwrite Pilot Discovery run: {final}")
    staging = output_root / f".PD-WP5-PILOT.staging.{uuid.uuid4().hex}"
    staging.mkdir(parents=False, exist_ok=False)
    try:
        paths: list[Path] = []
        for relative, values_to_write in (
            ("derived/transitions.jsonl", first["transitions"]),
            ("derived/trigger-events.jsonl", first["trigger_events"]),
            ("derived/candidates.jsonl", first["candidates"]),
            ("derived/fingerprints.jsonl", first["fingerprints"]),
            ("derived/cluster-versions.jsonl", first["cluster_versions"]),
            ("review/queue-items.jsonl", first["console_bundle"]["queue_items"]),
        ):
            path = staging / relative
            write_jsonl(path, values_to_write)
            paths.append(path)

        for relative, value in (
            ("review/console-bundle.json", first["console_bundle"]),
            ("review/pilot-review-input.template.json", first["review_template"]),
            ("qa/queue-projection.json", first["queue_projection"]),
            ("qa/defect-ledger.json", {"schema": "ovc-pd-wp5-pilot-defect-ledger/v1", "pilot_run_id": pilot_run_id, "defects": [], "status": "OPEN_FOR_OPERATOR_REVIEW"}),
        ):
            path = staging / relative
            write_json(path, value)
            paths.append(path)

        run_body = {
            "schema": "ovc-pd-wp5-pilot-run/v1",
            "pilot_run_id": pilot_run_id,
            "pilot_namespace": PILOT_NAMESPACE,
            "plan_id": PLAN_ID,
            "authority_gate": AUTHORITY_GATE,
            "next_gate": NEXT_GATE,
            "source_slice_id": SLICE_ID,
            "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
            "compute_run_id": RUN_ID,
            "compute_output_manifest_sha256": OUTPUT_MANIFEST_SHA256,
            "source_binding_id": BINDING_ID,
            "signed_replay_acceptance_id": ACCEPTANCE_ID,
            "signing_binding_id": SIGNING_BINDING_ID,
            "operator_id": OPERATOR_ID,
            "operation_mode": OPERATION_MODE,
            "research_role": RESEARCH_ROLE,
            "coverage_state": "GAPPED",
            "admissible_cutoff_utc": ADMISSIBLE_CUTOFF,
            "code_commit": code_commit,
            "derived_bundle_sha256": first_hash,
            "deterministic_rerun_sha256": second_hash,
            "deterministic_rerun_match": True,
            "counts": first["counts"],
            "elapsed_seconds_two_runs": round(elapsed, 6),
            "peak_memory_bytes": peak_memory,
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_discovery_population": False,
            "canonical_append": "DENIED",
            "live_prospective_relabelling": "DENIED",
            "provider_network_access_performed": False,
            "status": "AWAITING_OPERATOR_REVIEW",
        }
        signature, signature_sha = replay.sign_and_verify(
            private_key=private_key,
            public_key=public["public_key"],
            operator_id=OPERATOR_ID,
            payload=canonical_bytes(run_body),
        )
        run_record = {
            **run_body,
            "signature_algorithm": "ED25519",
            "signature_format": replay.SIGNATURE_FORMAT,
            "signature_namespace": replay.SIGNATURE_NAMESPACE,
            "signed_payload_sha256": logical_sha(run_body),
            "signature_sha256": signature_sha,
            "signature": signature,
        }
        run_path = staging / "pilot-run.json"
        write_json(run_path, run_record)
        paths.append(run_path)

        qa = {
            "schema": "ovc-pd-wp5-pilot-qa/v1",
            "pilot_run_id": pilot_run_id,
            "deterministic_rerun_match": True,
            "source_lineage_verified": True,
            "signed_replay_binding_verified": True,
            "pilot_namespace_isolated": True,
            "all_objects_pilot_only": True,
            "all_objects_non_promotable": True,
            "canonical_append": "DENIED",
            "live_prospective_relabelling": "DENIED",
            "outcome_features_consumed": False,
            "provider_network_access_performed": False,
            "operator_review_complete": False,
            "pd_g5p_ready": False,
            "qa_state": "PASS_MACHINE_REHEARSAL_AWAITING_OPERATOR_REVIEW",
        }
        qa_path = staging / "qa/pilot-qa.json"
        write_json(qa_path, qa)
        paths.append(qa_path)

        inventory = _file_inventory(staging, paths)
        output_manifest_body = {
            "schema": "ovc-pd-wp5-pilot-output-manifest/v1",
            "pilot_run_id": pilot_run_id,
            "pilot_namespace": PILOT_NAMESPACE,
            "source_slice_id": SLICE_ID,
            "compute_run_id": RUN_ID,
            "source_binding_id": BINDING_ID,
            "files": inventory,
            "file_count": len(inventory),
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_append": "DENIED",
            "r2_publication": "DENIED",
        }
        output_manifest = {**output_manifest_body, "output_manifest_sha256": logical_sha(output_manifest_body)}
        write_json(staging / "output-manifest.json", output_manifest)
        staging.rename(final)
        return {
            "status": "PILOT_MACHINE_REHEARSAL_COMPLETE_AWAITING_OPERATOR_REVIEW",
            "pilot_run_id": pilot_run_id,
            "pilot_root": str(final),
            "review_template": str(final / "review/pilot-review-input.template.json"),
            "next_command": f"finalize --pilot-run-id {pilot_run_id} --review-file <completed-review.json> --gate {AUTHORITY_GATE}",
            "counts": first["counts"],
            "deterministic_rerun_match": True,
            "next_gate": NEXT_GATE,
            "canonical_append": "DENIED",
        }
    except Exception as exc:
        quarantined = _quarantine(staging, str(exc))
        suffix = f"; staging quarantined at {quarantined}" if quarantined else ""
        if isinstance(exc, PilotDiscoveryError):
            raise PilotDiscoveryError(str(exc) + suffix) from exc
        raise PilotDiscoveryError(f"unexpected pilot execution failure: {exc}{suffix}") from exc


def _validate_review(review: Mapping[str, Any], template: Mapping[str, Any], pilot_run_id: str) -> list[dict[str, Any]]:
    if review.get("schema") != "ovc-pd-wp5-pilot-review-input/v1":
        raise PilotDiscoveryError("invalid pilot review schema")
    if review.get("pilot_run_id") != pilot_run_id or review.get("operator_id") != OPERATOR_ID:
        raise PilotDiscoveryError("pilot review identity mismatch")
    parse_utc(str(review.get("reviewed_at_utc") or ""))
    expected = {str(item["candidate_window_id"]) for item in template.get("decisions", ())}
    decisions = review.get("decisions")
    if not isinstance(decisions, list):
        raise PilotDiscoveryError("pilot review decisions must be a list")
    observed: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for source in decisions:
        if not isinstance(source, Mapping):
            raise PilotDiscoveryError("invalid pilot review decision")
        candidate_id = str(source.get("candidate_window_id") or "")
        disposition = str(source.get("review_disposition") or "")
        if candidate_id not in expected or candidate_id in observed:
            raise PilotDiscoveryError(f"unexpected or duplicate reviewed candidate: {candidate_id}")
        if disposition not in ALLOWED_REVIEW_DISPOSITIONS:
            raise PilotDiscoveryError(f"invalid pilot review disposition: {disposition}")
        observed.add(candidate_id)
        normalized.append(
            {
                "candidate_window_id": candidate_id,
                "review_disposition": disposition,
                "notes": str(source.get("notes") or ""),
                "ui_friction_codes": sorted(str(item) for item in source.get("ui_friction_codes", ())),
                **_pilot_markings(),
            }
        )
    if observed != expected:
        raise PilotDiscoveryError(f"pilot review is incomplete; missing {sorted(expected - observed)}")
    return sorted(normalized, key=lambda item: item["candidate_window_id"])


def finalize(
    repository_root: Path,
    *,
    pilot_run_id: str,
    review_file: Path,
    authority_gate: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    if authority_gate != AUTHORITY_GATE:
        raise PilotDiscoveryError(f"exact operator authority required: --gate {AUTHORITY_GATE}")
    if truthy(values.get("CI")) or truthy(values.get("GITHUB_ACTIONS")):
        raise PilotDiscoveryError("PD-WP5-PILOT review finalization is prohibited in CI")
    _, code_commit = repository_state(repository_root)
    authority = load_governed_authority(repository_root)
    replay.verify_compute_run(repository_root, values)
    root = external_root(repository_root, values) / "pattern-discovery" / "pilot" / PILOT_NAMESPACE / pilot_run_id
    if not root.is_dir():
        raise PilotDiscoveryError(f"pilot run unavailable: {root}")
    run = load_json(safe_file(root, "pilot-run.json"), "INVALID_PILOT_RUN")
    manifest = load_json(safe_file(root, "output-manifest.json"), "INVALID_PILOT_OUTPUT_MANIFEST")
    template = load_json(safe_file(root, "review/pilot-review-input.template.json"), "INVALID_PILOT_REVIEW_TEMPLATE")
    review = load_json(review_file.resolve(strict=True), "INVALID_OPERATOR_REVIEW")
    if run.get("pilot_run_id") != pilot_run_id or run.get("status") != "AWAITING_OPERATOR_REVIEW":
        raise PilotDiscoveryError("pilot run is not review-finalization eligible")
    if run.get("derived_bundle_sha256") != run.get("deterministic_rerun_sha256"):
        raise PilotDiscoveryError("pilot deterministic evidence is inconsistent")
    decisions = _validate_review(review, template, pilot_run_id)

    private_key, public_key_path = replay.key_paths(repository_root, values, OPERATOR_ID)
    public = replay.public_key_details(public_key_path, OPERATOR_ID)
    if public["public_key_sha256"] != authority["signing"]["public_key_sha256"]:
        raise PilotDiscoveryError("operator key does not match approved signing binding")

    final_root = root / "operator-review"
    if final_root.exists():
        raise PilotDiscoveryError(f"refusing to overwrite pilot operator review: {final_root}")
    staging = root / f".operator-review.staging.{uuid.uuid4().hex}"
    staging.mkdir(parents=False, exist_ok=False)
    try:
        reviewed_at = str(review["reviewed_at_utc"])
        review_payload = {
            "schema": "ovc-pd-wp5-pilot-review-receipt/v1",
            "pilot_run_id": pilot_run_id,
            "pilot_namespace": PILOT_NAMESPACE,
            "operator_id": OPERATOR_ID,
            "reviewed_at_utc": reviewed_at,
            "decisions": decisions,
            "decision_count": len(decisions),
            "pilot_output_manifest_sha256": manifest["output_manifest_sha256"],
            "derived_bundle_sha256": run["derived_bundle_sha256"],
            "code_commit": code_commit,
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_discovery_population": False,
            "canonical_append": "DENIED",
            "status": "OPERATOR_REVIEW_COMPLETE",
        }
        signature, signature_sha = replay.sign_and_verify(
            private_key=private_key,
            public_key=public["public_key"],
            operator_id=OPERATOR_ID,
            payload=canonical_bytes(review_payload),
        )
        signed_review = {
            **review_payload,
            "signature_algorithm": "ED25519",
            "signature_format": replay.SIGNATURE_FORMAT,
            "signature_namespace": replay.SIGNATURE_NAMESPACE,
            "signed_payload_sha256": logical_sha(review_payload),
            "signature_sha256": signature_sha,
            "signature": signature,
        }
        review_path = staging / "pilot-review-receipt.json"
        write_json(review_path, signed_review)

        defect_rows = [
            {
                "candidate_window_id": item["candidate_window_id"],
                "review_disposition": item["review_disposition"],
                "notes": item["notes"],
                "ui_friction_codes": item["ui_friction_codes"],
            }
            for item in decisions
            if item["review_disposition"] != "WORKFLOW_ACCEPTED" or item["ui_friction_codes"]
        ]
        defect_ledger = {
            "schema": "ovc-pd-wp5-pilot-defect-ledger/v1",
            "pilot_run_id": pilot_run_id,
            "defects": defect_rows,
            "defect_count": len(defect_rows),
            "contract_changes_required": bool(defect_rows),
            "status": "REVIEWED_VERSIONED_CORRECTION_REQUIRED" if defect_rows else "REVIEWED_NO_BLOCKING_DEFECT_RECORDED",
        }
        defect_path = staging / "pilot-defect-ledger.json"
        write_json(defect_path, defect_ledger)

        evidence_inventory_body = {
            "schema": "ovc-pd-wp5-signed-pilot-evidence-inventory/v1",
            "pilot_run_id": pilot_run_id,
            "pilot_namespace": PILOT_NAMESPACE,
            "source_slice_id": SLICE_ID,
            "compute_run_id": RUN_ID,
            "source_binding_id": BINDING_ID,
            "signed_replay_acceptance_id": ACCEPTANCE_ID,
            "pilot_run_file_sha256": sha_file(root / "pilot-run.json"),
            "pilot_output_manifest_file_sha256": sha_file(root / "output-manifest.json"),
            "pilot_review_receipt_file_sha256": sha_file(review_path),
            "pilot_defect_ledger_file_sha256": sha_file(defect_path),
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_append": "DENIED",
        }
        inventory_signature, inventory_signature_sha = replay.sign_and_verify(
            private_key=private_key,
            public_key=public["public_key"],
            operator_id=OPERATOR_ID,
            payload=canonical_bytes(evidence_inventory_body),
        )
        evidence_inventory = {
            **evidence_inventory_body,
            "inventory_id": f"PD.PILOT.EVIDENCE.{logical_sha(evidence_inventory_body)[:24]}",
            "operator_id": OPERATOR_ID,
            "signing_binding_id": SIGNING_BINDING_ID,
            "signature_algorithm": "ED25519",
            "signature_format": replay.SIGNATURE_FORMAT,
            "signature_namespace": replay.SIGNATURE_NAMESPACE,
            "signed_payload_sha256": logical_sha(evidence_inventory_body),
            "signature_sha256": inventory_signature_sha,
            "signature": inventory_signature,
            "status": "SIGNED_PILOT_EVIDENCE_COMPLETE",
        }
        evidence_path = staging / "signed-pilot-evidence-inventory.json"
        write_json(evidence_path, evidence_inventory)

        gate_input = {
            "schema": "ovc-pd-g5p-pilot-operations-gate-input/v1",
            "gate_id": NEXT_GATE,
            "plan_id": PLAN_ID,
            "pilot_run_id": pilot_run_id,
            "pilot_namespace": PILOT_NAMESPACE,
            "source_slice_id": SLICE_ID,
            "compute_run_id": RUN_ID,
            "source_binding_id": BINDING_ID,
            "signed_replay_acceptance_id": ACCEPTANCE_ID,
            "signing_binding_id": SIGNING_BINDING_ID,
            "operator_id": OPERATOR_ID,
            "pilot_output_manifest_sha256": manifest["output_manifest_sha256"],
            "derived_bundle_sha256": run["derived_bundle_sha256"],
            "deterministic_rerun_match": True,
            "operator_review_complete": True,
            "defect_count": len(defect_rows),
            "contract_changes_required": bool(defect_rows),
            "signed_pilot_evidence_inventory_file_sha256": sha_file(evidence_path),
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_discovery_population": False,
            "canonical_append": "DENIED",
            "live_prospective_relabelling": "DENIED",
            "identity_reset_before_canonical": "REQUIRED",
            "operator_approval_required": True,
            "allowed_decisions": ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"],
            "status": "PD_G5P_EVIDENCE_CANDIDATE",
        }
        gate_path = staging / "pd-g5p-gate-input.json"
        write_json(gate_path, gate_input)
        staging.rename(final_root)
        return {
            "status": "PD_G5P_OPERATOR_GATE_INPUT_READY",
            "pilot_run_id": pilot_run_id,
            "operator_review_root": str(final_root),
            "gate_input": str(final_root / "pd-g5p-gate-input.json"),
            "signed_evidence_inventory": str(final_root / "signed-pilot-evidence-inventory.json"),
            "defect_count": len(defect_rows),
            "next_gate": NEXT_GATE,
            "canonical_discovery_available": False,
        }
    except Exception as exc:
        quarantined = _quarantine(staging, str(exc))
        suffix = f"; staging quarantined at {quarantined}" if quarantined else ""
        if isinstance(exc, PilotDiscoveryError):
            raise PilotDiscoveryError(str(exc) + suffix) from exc
        raise PilotDiscoveryError(f"unexpected pilot review finalization failure: {exc}{suffix}") from exc


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Operator-local PD-WP5 Pilot Discovery rehearsal.")
    result.add_argument("command", choices=("preflight", "execute", "finalize"))
    result.add_argument("--repository-root", type=Path, default=Path.cwd())
    result.add_argument("--gate", default=None)
    result.add_argument("--pilot-run-id", default=None)
    result.add_argument("--review-file", type=Path, default=None)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        repository_root = arguments.repository_root.resolve(strict=True)
        if arguments.command == "preflight":
            result = preflight(repository_root)
        elif arguments.command == "execute":
            result = execute(repository_root, authority_gate=arguments.gate or "")
        else:
            if not arguments.pilot_run_id or arguments.review_file is None:
                raise PilotDiscoveryError("finalize requires --pilot-run-id and --review-file")
            result = finalize(
                repository_root,
                pilot_run_id=arguments.pilot_run_id,
                review_file=arguments.review_file,
                authority_gate=arguments.gate or "",
            )
    except (PilotDiscoveryError, PatternDiscoveryError, replay.ReplayAcceptanceError) as exc:
        print(f"PD-WP5-PILOT blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
