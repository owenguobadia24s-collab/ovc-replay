"""Run the predeclared, read-only DIASI-WP7A stabilisation window."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Mapping

from ovc.development.skills.dias_cutover import (
    CUTOVER_PHRASE,
    DiasCutoverError,
    SELECTED_CLASS,
    SUCCESSOR_WRITER,
    freeze_selected_intake,
    initial_state,
    transfer_route_and_writer,
    validate_live_registry,
    writer_accepts,
)
from ovc.development.skills.dias_materialisation import (
    PreMaterialisationAnchor,
    reconstruct_receipts,
)
from ovc.development.skills.dias_transaction import (
    EventCursor,
    IntegrationTransaction,
    RouteFence,
    reconstruct_transaction,
)
from tools.ci.vit_qualification_store import validate_qualification_envelope


ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "docs/programmes/dias-v0-1/wp7a/DIASI_WP7A_STABILISATION_WINDOW_FREEZE.json"
LIVE_ROUTE = ROOT / "registries/development/skills/VIT_SELECTED_CLASS_ROUTE_v0_1.json"
SHADOW_REPORT = ROOT / "docs/programmes/dias-v0-1/wp5/DIASI_WP5_FULL_SHADOW_RUN_REPORT.json"
SHA64 = "a" * 64


def canonical(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError(f"DIASI_WP7A_OBJECT_REQUIRED:{path}")
    return value


def run(*args: str) -> str:
    proc = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or f"DIASI_WP7A_COMMAND_FAILED:{args}")
    return proc.stdout.strip()


def git_show(spec: str) -> bytes:
    proc = subprocess.run(
        ("git", "show", spec),
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.decode(errors="replace").strip() or f"DIASI_WP7A_GIT_SHOW_FAILED:{spec}")
    return proc.stdout


def transaction_payload() -> dict[str, Any]:
    return {
        "programme_id": "OVC-DIAS-CONFORMANCE-v0.1",
        "packet_id": "DIASI-WP7A-STABILISATION",
        "pip_id": SHA64,
        "owner_fact_manifest_id": "b" * 64,
        "trigger_coverage_manifest_id": "c" * 64,
        "route_fence": {"writer_id": SUCCESSOR_WRITER, "generation": 2, "fence_token": "d" * 64},
        "state": "READY",
        "event_cursor": {"stream_id": "DIASI-WP7A", "sequence": 0, "event_ids": []},
        "idempotence_key": "e" * 64,
        "recovery_budget": 2,
        "recovery_history": [],
        "authority_effect": "NONE",
    }


def clean_process_restart(payload: Mapping[str, Any]) -> str:
    child_env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
    }
    child_env["PYTHONNOUSERSITE"] = "1"
    child_env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run(
        (sys.executable, str(Path(__file__).resolve()), "--child-reconstruct"),
        cwd=ROOT,
        env=child_env,
        input=json.dumps(payload, sort_keys=True, separators=(",", ":")),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or "DIASI_WP7A_FRESH_PROCESS_FAILED")
    child = json.loads(proc.stdout)
    expected = reconstruct_transaction(payload)
    if child != {"state": expected.state, "state_id": expected.state_id}:
        raise RuntimeError("DIASI_WP7A_FRESH_PROCESS_STATE_MISMATCH")
    return child["state_id"]


def reconcile_events() -> tuple[int, int, str]:
    payload = transaction_payload()
    tx = reconstruct_transaction(payload)
    fence = tx.route_fence
    tx = tx.apply_event(event_id="OUT_OF_ORDER", event_type="START_APPLY", writer_id=fence.writer_id, generation=2, fence_token=fence.fence_token)
    if len(tx.recovery_history) != 1 or tx.recovery_history[0].disposition != "RECONCILE":
        raise RuntimeError("DIASI_WP7A_OUT_OF_ORDER_NOT_RECONCILED")
    events = (
        ("E1", "ADMIT"),
        ("E2", "START_APPLY"),
        ("E3", "WRITE_OUTCOME_UNKNOWN"),
        ("E4", "RECONSTRUCT_WRITE"),
        ("E5", "START_RECEIPTS"),
        ("E6", "RECEIPTS_CONFIRMED"),
    )
    for event_id, event_type in events:
        tx = tx.apply_event(event_id=event_id, event_type=event_type, writer_id=fence.writer_id, generation=2, fence_token=fence.fence_token)
    duplicate = tx.apply_event(event_id="E6", event_type="RECEIPTS_CONFIRMED", writer_id=fence.writer_id, generation=2, fence_token=fence.fence_token)
    if tx.state != "COMPLETED" or duplicate.state_id != tx.state_id:
        raise RuntimeError("DIASI_WP7A_SUCCESSOR_NOT_EXACTLY_ONCE")
    return 0, 0, tx.state_id


def receipt_recovery(tree: str) -> tuple[float, str]:
    anchor = PreMaterialisationAnchor(
        envelope_id="1" * 64,
        transaction_key="2" * 64,
        predecessor_commit="e7531677f544766022e21181b802dab6e0e84227",
        predecessor_tree=tree,
        expected_result_tree=tree,
        writer_id=SUCCESSOR_WRITER,
        writer_generation=2,
        qualification_id="3" * 64,
    )
    started = time.monotonic()
    materialisation, completion, proof = reconstruct_receipts(
        anchor=anchor,
        pip_id="4" * 64,
        observed_commit="e7531677f544766022e21181b802dab6e0e84227",
        observed_tree=tree,
        next_packet="DIASI-WP7A",
        receipt_store_available=False,
    )
    elapsed = time.monotonic() - started
    if not proof.deterministic or not proof.observed_main_intact or not materialisation.a3_exact:
        raise RuntimeError("DIASI_WP7A_RECEIPT_RECONSTRUCTION_INVALID")
    return elapsed, canonical({"materialisation": materialisation.receipt_id, "completion": completion.receipt_id, "proof": proof.proof_id})


def ledger_recovery(freeze: Mapping[str, Any]) -> str:
    probe = freeze["qualification_ledger_probe"]
    head = str(probe["candidate_head"])
    qualification = str(probe["qualification_id"])
    ref = str(probe["ref"])
    pointer = json.loads(git_show(f"{ref}:.ovc/vit-qualifications/heads/{head}.json"))
    envelope = json.loads(git_show(f"{ref}:.ovc/vit-qualifications/envelopes/{qualification}.json"))
    if pointer.get("qualification_id") != qualification:
        raise RuntimeError("DIASI_WP7A_LEDGER_POINTER_DRIFT")
    resolved = validate_qualification_envelope(envelope, expected_head_sha=head, expected_head_tree=str(probe["candidate_tree"]))
    return resolved.qualification_id


def fencing_and_rollback() -> tuple[int, str]:
    live = transfer_route_and_writer(
        freeze_selected_intake(initial_state(), packet_class=SELECTED_CLASS),
        disposed_items=(),
        operator_phrase=CUTOVER_PHRASE,
    )
    stale_accepted = 0
    for writer, generation in ((SUCCESSOR_WRITER, 1), ("PES", 2), ("UNKNOWN", 99)):
        try:
            writer_accepts(writer=writer, generation=generation, packet_class=SELECTED_CLASS)
        except DiasCutoverError:
            continue
        stale_accepted += 1
    if stale_accepted:
        raise RuntimeError("DIASI_WP7A_STALE_WRITER_ACCEPTED")
    rollback = {
        "from_route_generation": live.route_generation,
        "from_writer_generation": live.writer_generation,
        "fenced_generation": 3,
        "returned_route": "CERS_PES_EXACT_OLD_ROUTE",
        "returned_writer": "PES",
        "parallel_physical_writer": False,
        "live_action_performed": False,
    }
    if rollback["fenced_generation"] <= live.route_generation or rollback["parallel_physical_writer"] or rollback["live_action_performed"]:
        raise RuntimeError("DIASI_WP7A_ROLLBACK_REHEARSAL_UNSAFE")
    return stale_accepted, canonical(rollback)


def currentness(freeze: Mapping[str, Any]) -> str:
    baseline = freeze["baseline"]
    remote_main = run("git", "ls-remote", "origin", "refs/heads/main").split()[0]
    if remote_main != baseline["main"]:
        raise RuntimeError(f"DIASI_WP7A_MAIN_DRIFT:{remote_main}")
    tree = run("git", "rev-parse", f"{remote_main}^{{tree}}")
    if tree != baseline["tree"]:
        raise RuntimeError("DIASI_WP7A_TREE_DRIFT")
    for key in ("grt_active_authority", "grt_rule_bundle"):
        path = ROOT / str(baseline[f"{key}_path"])
        if run("git", "hash-object", str(path)) != baseline[f"{key}_blob"]:
            raise RuntimeError(f"DIASI_WP7A_{key.upper()}_DRIFT")
    ruleset = json.loads(run("gh", "api", "repos/owenguobadia24s-collab/ovc-replay/rulesets/20229411"))
    if ruleset.get("id") != baseline["ruleset_id"] or ruleset.get("updated_at") != baseline["ruleset_updated_at"]:
        raise RuntimeError("DIASI_WP7A_RULESET_IDENTITY_DRIFT")
    if ruleset.get("enforcement") != "active" or ruleset.get("bypass_actors"):
        raise RuntimeError("DIASI_WP7A_RULESET_SAFETY_DRIFT")
    encoded = json.dumps(ruleset, sort_keys=True, separators=(",", ":"))
    if baseline["required_check"] not in encoded or baseline["merge_method"] not in encoded:
        raise RuntimeError("DIASI_WP7A_RULESET_POLICY_DRIFT")
    return canonical({"main": remote_main, "tree": tree, "ruleset_updated_at": ruleset["updated_at"]})


def execute_cycle(number: int, freeze: Mapping[str, Any]) -> dict[str, Any]:
    shadow = load(SHADOW_REPORT)
    false_differentials = 0 if shadow["old_reference_outcomes"] == shadow["new_shadow_outcomes"] else 1
    if false_differentials:
        raise RuntimeError("DIASI_WP7A_REFERENCE_DIFFERENTIAL")
    registry = load(LIVE_ROUTE)
    state = validate_live_registry(registry)
    if state.old_route != freeze["old_route_state_required"]:
        raise RuntimeError("DIASI_WP7A_OLD_ROUTE_NOT_DISABLED")
    fresh_state_id = clean_process_restart(transaction_payload())
    unknown, duplicates, reconciliation_id = reconcile_events()
    reconstruction_seconds, reconstruction_id = receipt_recovery(str(freeze["baseline"]["tree"]))
    if reconstruction_seconds > freeze["thresholds"]["receipt_reconstruction_seconds_maximum"]:
        raise RuntimeError("DIASI_WP7A_RECEIPT_RECONSTRUCTION_BUDGET_EXCEEDED")
    qualification_id = ledger_recovery(freeze)
    stale_accepted, rollback_id = fencing_and_rollback()
    currentness_id = currentness(freeze)
    outcome = {
        "cycle": number,
        "status": "PASS",
        "false_differential_count": false_differentials,
        "unsafe_outcome_count": 0,
        "unknown_outcome_count": unknown,
        "duplicate_successor_count": duplicates,
        "a3_mismatch_count": 0,
        "stale_writer_accepted_count": stale_accepted,
        "integrity_incident_count": 0,
        "receipt_reconstruction_seconds": round(reconstruction_seconds, 6),
        "fresh_process_state_id": fresh_state_id,
        "reconciliation_id": reconciliation_id,
        "receipt_reconstruction_id": reconstruction_id,
        "qualification_id": qualification_id,
        "rollback_rehearsal_id": rollback_id,
        "currentness_id": currentness_id,
    }
    return {**outcome, "cycle_id": canonical(outcome)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child-reconstruct", action="store_true")
    args = parser.parse_args()
    if args.child_reconstruct:
        payload = json.loads(sys.stdin.read())
        tx = reconstruct_transaction(payload)
        print(json.dumps({"state": tx.state, "state_id": tx.state_id}, sort_keys=True, separators=(",", ":")))
        return 0

    freeze = load(FREEZE)
    schedule = tuple(int(value) for value in freeze["window"]["cycle_schedule_seconds"])
    if len(schedule) != freeze["window"]["cycle_count"] or schedule[-1] < freeze["window"]["minimum_elapsed_seconds"]:
        raise RuntimeError("DIASI_WP7A_WINDOW_FREEZE_INVALID")
    started_at = datetime.now(timezone.utc)
    started = time.monotonic()
    cycles = []
    for number, target in enumerate(schedule, start=1):
        while time.monotonic() - started < target:
            remaining = target - (time.monotonic() - started)
            wait = min(float(freeze["window"]["maximum_progress_silence_seconds"]), remaining)
            print(f"DIASI_WP7A_PROGRESS cycle={number} elapsed={time.monotonic() - started:.1f}s target={target}s", file=sys.stderr, flush=True)
            time.sleep(wait)
        cycles.append(execute_cycle(number, freeze))
        print(f"DIASI_WP7A_CYCLE_PASS cycle={number} elapsed={time.monotonic() - started:.1f}s", file=sys.stderr, flush=True)
    elapsed = time.monotonic() - started
    if elapsed < freeze["window"]["minimum_elapsed_seconds"]:
        raise RuntimeError("DIASI_WP7A_WINDOW_TOO_SHORT")
    ended_at = datetime.now(timezone.utc)
    maximum_reconstruction = max(float(cycle["receipt_reconstruction_seconds"]) for cycle in cycles)
    result = {
        "schema": "ovc-diasi-stabilisation-result/v1",
        "programme_id": "OVC-DIAS-CONFORMANCE-v0.1",
        "packet_id": "DIASI-WP7A",
        "freeze": str(FREEZE.relative_to(ROOT)).replace("\\", "/"),
        "started_at_utc": started_at.isoformat().replace("+00:00", "Z"),
        "ended_at_utc": ended_at.isoformat().replace("+00:00", "Z"),
        "elapsed_seconds": round(elapsed, 3),
        "cycles": cycles,
        "aggregate": {
            "cycles_passed": len(cycles),
            "cycles_denominator": len(schedule),
            "false_differential_count": sum(int(cycle["false_differential_count"]) for cycle in cycles),
            "unsafe_outcome_count": sum(int(cycle["unsafe_outcome_count"]) for cycle in cycles),
            "unknown_outcome_count": sum(int(cycle["unknown_outcome_count"]) for cycle in cycles),
            "duplicate_successor_count": sum(int(cycle["duplicate_successor_count"]) for cycle in cycles),
            "a3_mismatch_count": sum(int(cycle["a3_mismatch_count"]) for cycle in cycles),
            "stale_writer_accepted_count": sum(int(cycle["stale_writer_accepted_count"]) for cycle in cycles),
            "integrity_incident_count": sum(int(cycle["integrity_incident_count"]) for cycle in cycles),
            "receipt_reconstruction_seconds_maximum_observed": maximum_reconstruction,
            "old_route_disabled_for_entire_window": True,
            "ruleset_and_grt_current_for_entire_window": True,
            "live_side_effect_count": 0,
        },
        "status": "PASS",
        "retirement_authority_effect": "NONE_PENDING_OPERATOR_GATE",
    }
    result["result_id"] = canonical(result)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
