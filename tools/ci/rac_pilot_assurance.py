from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
from typing import Any, Mapping

from ovc.development.skills.repository_assurance_pilot import (
    RepositoryAssurancePilotError,
    assurance_surface_id,
    build_pilot_certificate,
    classify_candidate,
    load_json,
    validate_pilot_policy,
)
from tools.ci.vit_lineage_source import resolve_candidate_lineage
import tools.ci.prvitr_live_admission as live

POLICY_PATH = Path("registries/development/skills/REPOSITORY_ASSURANCE_PILOT_POLICY_v0_1.json")
REFERENCE_TIMEOUT_SECONDS = 22 * 60


def _write_output(name: str, value: str) -> None:
    target = os.environ.get("GITHUB_OUTPUT", "").strip()
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")
    print(f"OVC_RAC_PILOT_{name.upper()}={value}")


def _event_pr() -> tuple[int, Mapping[str, Any]]:
    event = live._event()
    pr = live._event_pr(event)
    return int(event.get("number", pr.get("number", -1))), pr


def _load_inputs(root: Path) -> tuple[Mapping[str, Any], Mapping[str, Any] | None]:
    policy = validate_pilot_policy(load_json(root / POLICY_PATH))
    baseline_path = str(policy.get("baseline_certificate_path") or "")
    baseline_file = root / baseline_path if baseline_path else None
    baseline = load_json(baseline_file) if baseline_file is not None and baseline_file.is_file() else None
    return policy, baseline


def _resolve_lineage(root: Path, pr: Mapping[str, Any], head_sha: str) -> Mapping[str, Any]:
    source = resolve_candidate_lineage(
        root=root,
        head_sha=head_sha,
        body=str(pr.get("body") or ""),
        require=True,
        allow_legacy_pr_body=False,
    )
    assert source is not None
    if source.source != "DETACHED_QUALIFICATION_LEDGER":
        raise RepositoryAssurancePilotError("RAC_PILOT_DETACHED_QUALIFICATION_REQUIRED")
    return source.record


def command_classify(root: Path) -> int:
    _, pr = _event_pr()
    head_sha = str((pr.get("head") or {}).get("sha", ""))
    policy, baseline = _load_inputs(root)
    if policy["status"] != "ACTIVE_BOUNDED_PILOT":
        result = {"eligible": False, "reason": "POLICY_INACTIVE", "pilot_class": policy["pilot_class"]}
    elif baseline is None:
        result = {"eligible": False, "reason": "BASELINE_MISSING", "pilot_class": policy["pilot_class"]}
    else:
        lineage = _resolve_lineage(root, pr, head_sha)
        result = classify_candidate(
            root=root,
            candidate_head_sha=head_sha,
            lineage_record=lineage,
            policy=policy,
            baseline=baseline,
        )
    _write_output("eligible", "true" if result["eligible"] else "false")
    _write_output("reason", str(result["reason"]))
    _write_output("pilot_class", str(result["pilot_class"]))
    print("OVC_RAC_PILOT_CLASSIFICATION=" + json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


def command_certify(root: Path) -> int:
    _, pr = _event_pr()
    head_sha = str((pr.get("head") or {}).get("sha", ""))
    policy, baseline = _load_inputs(root)
    lineage = _resolve_lineage(root, pr, head_sha)
    classification = classify_candidate(
        root=root,
        candidate_head_sha=head_sha,
        lineage_record=lineage,
        policy=policy,
        baseline=baseline,
    )
    if classification.get("eligible") is not True:
        raise RepositoryAssurancePilotError(f"RAC_PILOT_NOT_ELIGIBLE:{classification.get('reason')}")
    verified: list[str] = []
    for path in classification.get("receipt_paths", []):
        value = load_json(root / str(path))
        if not value:
            raise RepositoryAssurancePilotError(f"RAC_PILOT_EMPTY_RECEIPT:{path}")
        verified.append(str(path))
    tree_sha = live._tree(head_sha)
    certificate = build_pilot_certificate(
        candidate_head_sha=head_sha,
        candidate_tree_sha=tree_sha,
        classification=classification,
        policy=policy,
        verified_receipt_paths=verified,
    )
    _write_output("certificate_id", str(certificate["certificate_id"]))
    _write_output("pip_id", str(certificate["pip_id"]))
    _write_output("assurance_surface_id", str(certificate["assurance_surface_id"]))
    print("OVC_RAC_PILOT_CERTIFICATE=" + json.dumps(certificate, sort_keys=True, separators=(",", ":")))
    return 0


def command_surface(root: Path, commit_sha: str) -> int:
    policy, _ = _load_inputs(root)
    value = assurance_surface_id(root, commit_sha, policy)
    print(value)
    return 0


def command_reconcile(root: Path) -> int:
    pr_number, pr = _event_pr()
    head_sha = str((pr.get("head") or {}).get("sha", ""))
    deadline = time.time() + REFERENCE_TIMEOUT_SECONDS
    while time.time() < deadline:
        run = live._exact_run(live.TESTS_WORKFLOW, pr_number, head_sha)
        if run is None:
            time.sleep(5)
            continue
        state, jobs = live._run_job_state(run, live.TEST_JOB_NAMES)
        if state == "FAIL":
            failed = [
                str(job.get("name"))
                for job in jobs
                if str(job.get("status")) == "completed" and str(job.get("conclusion")) != "success"
            ]
            raise RepositoryAssurancePilotError(
                "ASSURANCE_MODEL_DIVERGENCE:REFERENCE_FAILURE:" + ",".join(failed)
            )
        if state == "PASS":
            receipt = {
                "schema": "ovc-rac-pilot-reference-reconciliation/v1",
                "status": "PASS",
                "candidate_head_sha": head_sha,
                "tests_run_id": int(run["id"]),
                "reference_job_ids": sorted(int(job["id"]) for job in jobs),
                "authority_effect": "NONE_EVIDENCE_ONLY",
            }
            print("OVC_RAC_PILOT_REFERENCE_RECONCILIATION=" + json.dumps(receipt, sort_keys=True, separators=(",", ":")))
            return 0
        time.sleep(5)
    raise RepositoryAssurancePilotError("RAC_PILOT_REFERENCE_RECONCILIATION_TIMEOUT")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded DSAI3V RAC delta-assurance pilot controller")
    parser.add_argument("command", choices=("classify", "certify", "surface", "reconcile"))
    parser.add_argument("--repo", default=".")
    parser.add_argument("--commit-sha")
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    if args.command == "classify":
        return command_classify(root)
    if args.command == "certify":
        return command_certify(root)
    if args.command == "surface":
        if not args.commit_sha:
            raise RepositoryAssurancePilotError("RAC_PILOT_SURFACE_COMMIT_REQUIRED")
        return command_surface(root, args.commit_sha)
    return command_reconcile(root)


if __name__ == "__main__":
    raise SystemExit(main())
