#!/usr/bin/env python3
"""Reconcile GRT2-G2.5 limited enforcement from exact Git candidate trees.

After the operator-approved GRT2-G3 rollback, this runtime is again the active
integration-facing GRT surface. Historical G3/G4 and DebtFloor evidence remains
immutable, but FULL_GRT_EXACT and DebtFloor generation are not ordinary
integration prerequisites.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from ovc.programme_genesis.grt_v0_2.pilot import (  # noqa: E402
    PilotEvidenceError,
    evaluate_limited_candidate,
    summarize_pilot,
)

AUTHORITY = ROOT / "registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_3.json"
ROOT_REGISTRY = ROOT / "registries/governance/grt_v0_2/GRT_ROOT_REGISTRY_v0_2.json"
DEFAULT_MANIFEST = ROOT / "docs/programmes/grt-v0-2/gates/GRT2_G2_5_RETROSPECTIVE_CANDIDATE_MANIFEST.json"
ROLLBACK_STATUS = "ROLLED_BACK_TO_G2_5_LIMITED_ENFORCEMENT"


def run(*args: str) -> str:
    cp = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cp.returncode != 0:
        raise PilotEvidenceError(f"GRT2_G2_5_GIT_COMMAND_FAILED:{' '.join(args)}:{cp.stderr.strip()}")
    return cp.stdout.strip()


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotEvidenceError(f"GRT2_G2_5_JSON_UNAVAILABLE:{path.as_posix()}") from exc


def parse_name_status(base: str, head: str) -> list[dict[str, Any]]:
    text = run("git", "diff", "--name-status", "--find-renames", "--find-copies", base, head)
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0][0]
        if status in {"R", "C"}:
            if len(parts) != 3:
                raise PilotEvidenceError("GRT2_G2_5_GIT_DIFF_ROW_INVALID")
            rows.append({"status": status, "old_path": parts[1], "path": parts[2]})
        else:
            if len(parts) != 2:
                raise PilotEvidenceError("GRT2_G2_5_GIT_DIFF_ROW_INVALID")
            rows.append({"status": status, "path": parts[1]})
    return rows


def physical_tree(commit: str) -> str:
    return run("git", "rev-parse", f"{commit}^{{tree}}")


def exact_commit_exists(commit: str) -> None:
    run("git", "cat-file", "-e", f"{commit}^{{commit}}")


def validate_authority(authority: dict[str, Any]) -> None:
    if authority.get("gate_id") != "GRT2-G3":
        raise PilotEvidenceError("GRT2_G2_5_ROLLBACK_AUTHORITY_GATE_MISMATCH")
    if authority.get("authority_status") != "ACTIVE_ON_MAIN_MATERIALISATION":
        raise PilotEvidenceError("GRT2_G2_5_ROLLBACK_AUTHORITY_NOT_ACTIVE")
    if authority.get("enforcement_mode") != "LIMITED_NEW_ARTIFACT_ENFORCEMENT":
        raise PilotEvidenceError("GRT2_G2_5_ROLLBACK_AUTHORITY_MODE_MISMATCH")
    if authority.get("g3_status") != ROLLBACK_STATUS:
        raise PilotEvidenceError("GRT2_G2_5_ROLLBACK_STATUS_MISMATCH")
    if authority.get("full_grt_exact_required") is not False:
        raise PilotEvidenceError("GRT2_G2_5_FULL_EXACT_STILL_REQUIRED")
    if authority.get("ordinary_packet_debt_floor_generation_required") is not False:
        raise PilotEvidenceError("GRT2_G2_5_DEBTFLOOR_STILL_REQUIRED")


def evaluate_manifest(manifest_path: Path, evaluated_at: str) -> dict[str, Any]:
    authority = load(AUTHORITY)
    validate_authority(authority)
    root_registry = load(ROOT_REGISTRY)
    manifest = load(manifest_path)
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise PilotEvidenceError("GRT2_G2_5_RETROSPECTIVE_MANIFEST_EMPTY")

    records: list[dict[str, Any]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise PilotEvidenceError("GRT2_G2_5_RETROSPECTIVE_MANIFEST_ROW_INVALID")
        predecessor = candidate.get("predecessor_main_sha")
        merge_commit = candidate.get("physical_merge_commit")
        expected_tree = candidate.get("candidate_tree_sha")
        for commit in (predecessor, merge_commit):
            if not isinstance(commit, str) or len(commit) != 40:
                raise PilotEvidenceError("GRT2_G2_5_RETROSPECTIVE_COMMIT_INVALID")
            exact_commit_exists(commit)
        actual_tree = physical_tree(merge_commit)
        if actual_tree != expected_tree:
            raise PilotEvidenceError(f"GRT2_G2_5_RETROSPECTIVE_TREE_MISMATCH:{candidate.get('candidate_id')}")
        actual_parent = run("git", "rev-parse", f"{merge_commit}^1")
        if actual_parent != predecessor:
            raise PilotEvidenceError(f"GRT2_G2_5_RETROSPECTIVE_PREDECESSOR_MISMATCH:{candidate.get('candidate_id')}")

        changes = parse_name_status(predecessor, merge_commit)
        evaluation = evaluate_limited_candidate(changes=changes, root_registry=root_registry)
        record = {
            **candidate,
            "candidate_tree_sha": actual_tree,
            "evaluation_started_at": evaluated_at,
            "evaluation_completed_at": evaluated_at,
            "exact_tree_replay": True,
            "changed_path_count": len(changes),
            "pilot_scope_classification": evaluation["pilot_scope_classification"],
            "pilot_decision": evaluation["pilot_decision"],
            "pilot_findings": evaluation["pilot_findings"],
            "full_g3_shadow_status": evaluation["full_g3_shadow_status"],
            "full_g3_shadow_findings": evaluation["full_g3_shadow_findings"],
            "escape_review": evaluation["escape_review"],
            "false_positive_review": evaluation["false_positive_review"],
            "false_negative_probes": evaluation["false_negative_probes"],
            "scope_leakage_review": evaluation["scope_leakage_review"],
            "performance_receipt": {"status": "NOT_EVALUATED_RETROSPECTIVE_RECONCILIATION"},
            "performance_status": "NOT_EVALUATED",
            "override_record": None,
            "qa_disposition": "PASS" if evaluation["pilot_decision"] in {"PASS", "FAIL"} else "NOT_EVALUABLE",
            "authority_effect": "NONE_G2_5_RETROSPECTIVE_EVIDENCE_ONLY",
            "change_evaluations": evaluation["change_evaluations"],
        }
        records.append(record)

    summary = summarize_pilot(
        candidate_records=records,
        pilot_start="2026-08-14T13:53:00+01:00",
        evaluated_at=evaluated_at,
        minimum_elapsed_hours=24,
        minimum_eligible_candidate_count=8,
    )
    return {
        "schema": "ovc-grt2-g2-5-retrospective-reconciliation/v2",
        "programme_id": authority["programme_id"],
        "gate_id": "GRT2-G3",
        "pilot_baseline_commit": authority["pilot_baseline_commit"],
        "runtime_commit": run("git", "rev-parse", "HEAD"),
        "runtime_tree": physical_tree("HEAD"),
        "evaluated_at": evaluated_at,
        "candidate_evaluations": records,
        "summary": summary,
        "authority_effect": "NONE_EVIDENCE_RECONCILIATION_ONLY",
        "g3_status": ROLLBACK_STATUS,
    }


def evaluate_current(base: str, head: str, evaluated_at: str) -> dict[str, Any]:
    authority = load(AUTHORITY)
    validate_authority(authority)
    root_registry = load(ROOT_REGISTRY)
    exact_commit_exists(base)
    exact_commit_exists(head)
    changes = parse_name_status(base, head)
    evaluation = evaluate_limited_candidate(changes=changes, root_registry=root_registry)
    return {
        "schema": "ovc-grt2-g2-5-current-candidate-evaluation/v2",
        "gate_id": "GRT2-G3",
        "base_commit": base,
        "head_commit": head,
        "head_tree": physical_tree(head),
        "evaluated_at": evaluated_at,
        "changed_path_count": len(changes),
        **evaluation,
        "enforcement_result": "BLOCK" if evaluation["pilot_decision"] in {"FAIL", "NOT_EVALUABLE"} else "PASS",
        "g3_status": ROLLBACK_STATUS,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--manifest", type=Path, nargs="?", const=DEFAULT_MANIFEST)
    mode.add_argument("--candidate", action="store_true")
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    evaluated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    try:
        if args.candidate:
            if not args.base or not args.head:
                raise PilotEvidenceError("GRT2_G2_5_CURRENT_CANDIDATE_BASE_HEAD_REQUIRED")
            result = evaluate_current(args.base, args.head, evaluated_at)
            exit_code = 0 if result["enforcement_result"] == "PASS" else 2
        else:
            result = evaluate_manifest(args.manifest, evaluated_at)
            exit_code = 0
    except PilotEvidenceError as exc:
        result = {"schema": "ovc-grt2-g2-5-run-failure/v2", "status": "BLOCK", "reason_code": str(exc)}
        exit_code = 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS" if exit_code == 0 else "BLOCK", "output": str(args.out)}, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
