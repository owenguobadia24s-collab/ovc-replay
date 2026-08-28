#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote, urlencode

from ovc.development.dsai3v_completion_source_binding import (
    build_github_completion_source_binding,
    has_source_bound_pr_to_materialised,
)
from ovc.development.identity import canonical_sha256
from ovc.development.prvit_remediation import IntegrationAdmissionReceipt
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_late_binding import LateBindingPlacement
from ovc.development.skills.vit_local_completion_executor import (
    FREEZE_SCHEMA,
    complete_frozen_transaction,
    validate_live_transaction_freeze,
)
from ovc.development.skills.vit_materialisation import (
    PhysicalMaterialisationTransaction,
    ReceiptStore,
)
from ovc.development.skills.vit_routing import (
    SIQ_GATEWAY,
    VIT_CONTROLLER,
    validate_vit_lineage_record,
)
from ovc_evidence_store.external_root import resolve_external_root
from tools.ci import vit_post_merge_completion as legacy
from tools.ci.vit_lineage_source import resolve_candidate_lineage


LATE_PLACEMENT_MARKER = "OVC_VIT_LATE_BINDING_PLACEMENT_ACQUIRED="
ADMISSION_MARKER = "OVC_INTEGRATION_ADMISSION_RECEIPT="
RECOVERY_SCHEMA = "ovc-vit-post-merge-recovery-request/v1"
V2_SCHEMA = "ovc-development-latency-canonical-dsai3v/v2"


def _marker_payloads(text: str, marker: str) -> tuple[Mapping[str, Any], ...]:
    rows: list[Mapping[str, Any]] = []
    for line in str(text).splitlines():
        if marker not in line:
            continue
        raw = line.split(marker, 1)[1].strip()
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise legacy.PostMergeCompletionError(
                f"late-binding marker was not valid JSON: {marker}"
            ) from exc
        if not isinstance(value, Mapping):
            raise legacy.PostMergeCompletionError(
                f"late-binding marker was not an object: {marker}"
            )
        rows.append(dict(value))
    return tuple(rows)


def _late_binding_freeze_from_merge_readiness_logs(
    *,
    repo_root: Path,
    repository: str,
    head_sha: str,
    pr_number: int,
    pr_body: str,
    token: str,
) -> Mapping[str, Any] | None:
    """Recover the deterministic PMT from exact pre-write late-binding evidence.

    Forward generations resolve their payload identity from the detached exact-head
    qualification ledger. Historical PR-body lineage is available only when the
    explicit recovery flag is set.
    """
    owner, repo = repository.split("/", 1)
    query = urlencode(
        {
            "head_sha": head_sha,
            "event": "pull_request",
            "status": "completed",
            "per_page": "100",
        }
    )
    payload = legacy._json(
        f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}/actions/runs?{query}",
        token,
    )
    if not isinstance(payload, Mapping):
        raise legacy.PostMergeCompletionError("late-binding workflow response invalid")
    candidates = [
        row
        for row in payload.get("workflow_runs", [])
        if isinstance(row, Mapping)
        and row.get("name") == "OVC tiered test selection shadow"
        and row.get("conclusion") == "success"
    ]
    candidates.sort(key=lambda row: int(row.get("id", 0)), reverse=True)

    found_merge_readiness = False
    for run in candidates:
        run_id = int(run["id"])
        jobs = legacy._json(
            f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}/actions/runs/{run_id}/jobs?per_page=100",
            token,
        )
        job_rows = jobs.get("jobs", []) if isinstance(jobs, Mapping) else []
        matches = [
            job
            for job in job_rows
            if isinstance(job, Mapping)
            and job.get("name") == "OVC merge readiness"
            and job.get("conclusion") == "success"
        ]
        if not matches:
            continue
        matches.sort(key=lambda row: int(row.get("id", 0)), reverse=True)
        job = matches[0]
        found_merge_readiness = True
        job_id = int(job["id"])
        text = legacy._request_job_log(
            f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}/actions/jobs/{job_id}/logs",
            token,
        ).decode("utf-8", errors="replace")
        placement_rows = _marker_payloads(text, LATE_PLACEMENT_MARKER)
        admission_rows = _marker_payloads(text, ADMISSION_MARKER)
        if len(placement_rows) != 1 or len(admission_rows) != 1:
            raise legacy.PostMergeCompletionError(
                "expected exactly one late-binding placement and one integration admission "
                f"for PR #{pr_number}; found placement={len(placement_rows)} "
                f"admission={len(admission_rows)}"
            )

        placement = LateBindingPlacement(**dict(placement_rows[0]))
        admission_raw = dict(admission_rows[0])
        admission_raw["reason_codes"] = tuple(admission_raw.get("reason_codes") or ())
        admission = IntegrationAdmissionReceipt(**admission_raw)
        if placement.candidate_head_sha != head_sha:
            raise legacy.PostMergeCompletionError("late-binding placement head mismatch")
        if placement.placement_id != admission.placement_id:
            raise legacy.PostMergeCompletionError("late-binding placement/admission id mismatch")
        if placement.pip_id != admission.pip_id:
            raise legacy.PostMergeCompletionError("late-binding placement/admission PIP mismatch")
        if placement.prospective_tree_sha != admission.result_tree:
            raise legacy.PostMergeCompletionError("late-binding placement/admission tree mismatch")
        if admission.disposition != "SHADOW_READY":
            raise legacy.PostMergeCompletionError("late-binding admission was not ready")

        allow_legacy_body = (
            os.environ.get("OVC_VIT_ALLOW_LEGACY_PR_BODY_LINEAGE", "").lower()
            == "true"
        )
        lineage_source = resolve_candidate_lineage(
            root=repo_root,
            head_sha=head_sha,
            body=pr_body,
            require=True,
            allow_legacy_pr_body=allow_legacy_body,
        )
        assert lineage_source is not None
        lineage_record = lineage_source.record
        lineage = validate_vit_lineage_record(lineage_record)
        if not lineage.late_binding:
            return None
        if lineage.pip_id != admission.pip_id:
            raise legacy.PostMergeCompletionError(
                "late-binding qualification/admission PIP mismatch"
            )
        pip = lineage_record.get("pip")
        if not isinstance(pip, Mapping):
            raise legacy.PostMergeCompletionError("late-binding PIP missing")
        if str(pip.get("authority_manifest_id", "")) != placement.authority_manifest_id:
            raise legacy.PostMergeCompletionError(
                "late-binding authority frontier mismatch"
            )
        if str(pip.get("dependency_frontier_id", "")) != placement.dependency_frontier_id:
            raise legacy.PostMergeCompletionError(
                "late-binding dependency frontier mismatch"
            )

        ticket_id = "VIT-LATE-" + canonical_sha256(
            {
                "programme_id": lineage.programme_id,
                "packet_id": lineage.packet_id,
                "pip_id": lineage.pip_id,
                "placement_id": placement.placement_id,
                "base_sha": placement.physical_base_sha,
                "head_sha": head_sha,
                "result_tree": placement.prospective_tree_sha,
            },
            role="DSAI3V_LATE_BINDING_PHYSICAL_MATERIALISATION_TICKET",
        )
        assurance_frontier_id = canonical_sha256(
            {
                "assurance_generation_id": admission.assurance_generation_id,
                "grt_proof_binding_id": admission.grt_proof_binding_id,
                "placement_id": admission.placement_id,
                "result_tree": admission.result_tree,
                "workflow_run_id": str(run_id),
                "workflow_job_id": str(job_id),
            },
            role="DSAI3V_LATE_BINDING_PREWRITE_ASSURANCE_FRONTIER",
        )
        transaction = PhysicalMaterialisationTransaction(
            vit_generation_id=placement.placement_id,
            ticket_id=ticket_id,
            train_generation_id=f"LATE-BINDING:{placement.placement_id}",
            expected_predecessor_commit=placement.physical_base_sha,
            expected_predecessor_tree=placement.physical_base_tree,
            expected_result_tree=placement.prospective_tree_sha,
            authority_frontier_id=placement.authority_manifest_id,
            assurance_frontier_id=assurance_frontier_id,
            materialisation_profile="LIVE_PHYSICAL_MAIN",
            attempt=1,
        )
        completion_transition = dict(pip.get("completion_transition") or {})
        freeze = {
            "schema": FREEZE_SCHEMA,
            "controller": VIT_CONTROLLER,
            "physical_gateway": SIQ_GATEWAY,
            "pr_number": int(pr_number),
            "head_sha": head_sha,
            "pip_id": lineage.pip_id,
            "generation_id": placement.placement_id,
            "placement_id": placement.placement_id,
            "transaction": asdict(transaction),
            "transaction_id": transaction.transaction_id,
            "completion_context": {
                "programme_id": lineage.programme_id,
                "packet_id": lineage.packet_id,
                "implementation_ref": f"github:pr:{int(pr_number)}:head:{head_sha}",
                "qa_ref": (
                    f"github:pr:{int(pr_number)}:head:{head_sha}:"
                    f"merge-readiness-run:{run_id}:job:{job_id}"
                ),
                "gate_decision_ref": f"integration-admission:{admission.receipt_id}",
                "payload_id": lineage.pip_id,
                "next_packet": completion_transition.get("next_packet"),
            },
            "freeze_provenance": {
                "workflow_run_id": str(run_id),
                "workflow_job_id": str(job_id),
                "run_attempt": str(run.get("run_attempt", "")),
                "source": "OVC_MERGE_READINESS_EXACT_FINAL_PREWRITE_EVIDENCE",
                "qualification_source": lineage_source.source,
                "qualification_ref": lineage_source.immutable_ref,
                "evidence_rule": "OBSERVED_IDENTITIES_ONLY_NO_POSTWRITE_PLACEMENT_INFERENCE",
            },
            "binding_policy": "LATE_PHYSICAL_PLACEMENT",
            "authority_effect": "NONE",
        }
        validate_live_transaction_freeze(freeze)
        return freeze

    if found_merge_readiness:
        raise legacy.PostMergeCompletionError(
            f"successful merge-readiness evidence for PR #{pr_number} was not recoverable"
        )
    return None


def _freeze_for_pr(
    *,
    repo_root: Path,
    repository: str,
    head_sha: str,
    pr_number: int,
    pr_body: str,
    token: str,
) -> Mapping[str, Any]:
    late = _late_binding_freeze_from_merge_readiness_logs(
        repo_root=repo_root,
        repository=repository,
        head_sha=head_sha,
        pr_number=pr_number,
        pr_body=pr_body,
        token=token,
    )
    if late is not None:
        return late
    return legacy._freeze_from_prewrite_logs(
        repository=repository,
        head_sha=head_sha,
        pr_number=pr_number,
        token=token,
    )


def _prospective_v2_rows(
    receipt_store: ReceiptStore, completion_receipt_id: str
) -> tuple[Mapping[str, Any], ...]:
    rows: list[Mapping[str, Any]] = []
    for path in sorted(receipt_store.root.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            isinstance(value, Mapping)
            and value.get("schema") == V2_SCHEMA
            and str(value.get("completion_receipt_id", ""))
            == completion_receipt_id
        ):
            rows.append(dict(value))
    return tuple(rows)


def _already_completed(receipt_store: ReceiptStore, merge_sha: str) -> bool:
    proof_root = receipt_store.root / "proofs"
    if not proof_root.is_dir():
        return False
    for path in sorted(proof_root.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(value, Mapping):
            continue
        if (
            str(value.get("observed_commit", "")) == merge_sha
            and value.get("exact_tree_equal") is True
            and value.get("four_content_addressed_receipts_present") is True
        ):
            receipt_ids = value.get("receipt_ids")
            completion_id = (
                str(receipt_ids.get("completion_receipt_id", ""))
                if isinstance(receipt_ids, Mapping)
                else ""
            )
            v2_rows = (
                _prospective_v2_rows(receipt_store, completion_id)
                if completion_id
                else ()
            )
            if not v2_rows:
                print(
                    f"OVC_VIT_POST_MERGE_COMPLETION_ALREADY_PRESENT merge={merge_sha} "
                    f"proof={value.get('proof_id', path.stem)}",
                    flush=True,
                )
                return True
            if any(has_source_bound_pr_to_materialised(row) for row in v2_rows):
                print(
                    f"OVC_VIT_POST_MERGE_COMPLETION_ALREADY_PRESENT_SOURCE_BOUND_V2 "
                    f"merge={merge_sha} proof={value.get('proof_id', path.stem)}",
                    flush=True,
                )
                return True
            print(
                f"OVC_DSAI3V_V2_SOURCE_BINDING_REPLAY_REQUIRED merge={merge_sha} "
                f"proof={value.get('proof_id', path.stem)}",
                flush=True,
            )
            return False
    return False


def _recover_one(
    *, repo_root: Path, merge_sha: str, receipt_store: ReceiptStore
) -> Mapping[str, Any]:
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if "/" not in repository or not token:
        raise legacy.PostMergeCompletionError("GITHUB_REPOSITORY/GITHUB_TOKEN are required")
    merge_sha = legacy._git(repo_root, "rev-parse", merge_sha)
    if _already_completed(receipt_store, merge_sha):
        return {"observed_commit": merge_sha, "status": "ALREADY_COMPLETED"}

    observed_tree = legacy._git(repo_root, "rev-parse", f"{merge_sha}^{{tree}}")
    observed_parent = legacy._git(repo_root, "rev-parse", f"{merge_sha}^")
    pr = legacy._associated_pr(repository, merge_sha, token)
    pr_number = int(pr["number"])
    head_sha = str((pr.get("head") or {}).get("sha") or "")
    merged_at = str(pr.get("merged_at") or "")
    if not merged_at:
        raise legacy.PostMergeCompletionError("associated PR merged_at is required")
    if head_sha:
        try:
            legacy._git(repo_root, "cat-file", "-e", f"{head_sha}^{{commit}}")
        except Exception:
            legacy._git(repo_root, "fetch", "--no-tags", "origin", head_sha)
    freeze = _freeze_for_pr(
        repo_root=repo_root,
        repository=repository,
        head_sha=head_sha,
        pr_number=pr_number,
        pr_body=str(pr.get("body") or ""),
        token=token,
    )
    transaction = freeze["transaction"]
    if str(transaction["expected_predecessor_commit"]) != observed_parent:
        raise legacy.PostMergeCompletionError(
            "physical predecessor does not match recovered pre-write transaction"
        )
    if str(transaction["expected_result_tree"]) != observed_tree:
        raise legacy.PostMergeCompletionError(
            "physical tree does not match recovered pre-write transaction"
        )

    trace_bundle: Mapping[str, Any] | None = None
    source_binding: Mapping[str, Any] | None = None
    context = freeze.get("completion_context")
    if isinstance(context, Mapping):
        workflow_runs, jobs_by_run = legacy._pr_head_workflow_observations(
            repository,
            head_sha,
            token,
        )
        source_binding = build_github_completion_source_binding(
            pr=pr,
            workflow_runs=workflow_runs,
            jobs_by_run=jobs_by_run,
        )
        try:
            trace_bundle = legacy.build_observed_completion_trace(
                programme_id=str(context["programme_id"]),
                packet_id=str(context["packet_id"]),
                pr_number=pr_number,
                head_sha=head_sha,
                merged_at_utc=merged_at,
                workflow_runs=workflow_runs,
                jobs_by_run=jobs_by_run,
            )
        except (legacy.PostMergeCompletionError, ValueError, KeyError) as exc:
            print(
                "::warning title=DEVOBS routine trace unavailable::"
                f"observed workflow timing could not be attached; canonical completion remains fail-honest: {exc}",
                flush=True,
            )

    if trace_bundle is not None:
        for event in trace_bundle.get("trace_events", []):
            if not isinstance(event, Mapping):
                raise legacy.PostMergeCompletionError("DEVOBS trace event invalid")
            record_id = event.get("record_id")
            if not isinstance(record_id, str) or not record_id:
                raise legacy.PostMergeCompletionError("DEVOBS trace event id missing")
            receipt_store.put(dict(event), record_id)

    proof = complete_frozen_transaction(
        freeze=freeze,
        observed_commit=merge_sha,
        observed_tree=observed_tree,
        receipt_store=receipt_store,
        siq_receipts=legacy._siq_observations(repository, head_sha, token),
        trace_summary=(
            trace_bundle.get("trace_summary") if trace_bundle is not None else None
        ),
        async_assurance_metrics=(
            trace_bundle.get("async_assurance_metrics")
            if trace_bundle is not None
            else None
        ),
        completion_timing_sources=(
            source_binding.get("timing_sources") if source_binding is not None else ()
        ),
        completion_aa0_observability=(
            source_binding.get("aa0_observability")
            if source_binding is not None
            else None
        ),
    )
    safe = {
        "schema": proof["schema"],
        "proof_id": proof["proof_id"],
        "transaction_id": proof["transaction_id"],
        "observed_commit": proof["observed_commit"],
        "observed_tree": proof["observed_tree"],
        "exact_tree_equal": proof["exact_tree_equal"],
        "four_content_addressed_receipts_present": proof[
            "four_content_addressed_receipts_present"
        ],
        "receipt_ids": proof["receipt_ids"],
        "authority_effect": proof["authority_effect"],
    }
    if proof.get("trace_summary_id"):
        safe["trace_summary_id"] = proof["trace_summary_id"]
    v2_ids = proof.get("v2_receipt_ids")
    if isinstance(v2_ids, Mapping):
        safe["v2_receipt_ids"] = dict(v2_ids)
        v2_receipt_id = str(v2_ids.get("v2_development_latency_receipt_id", ""))
        if v2_receipt_id:
            v2_path = receipt_store.root / f"{v2_receipt_id}.json"
            v2_payload = json.loads(v2_path.read_text(encoding="utf-8"))
            timing = v2_payload.get("timing") if isinstance(v2_payload, Mapping) else None
            if isinstance(timing, Mapping):
                safe["v2_timing_status"] = timing.get("status")
                derived = timing.get("derived_latency_ms")
                if isinstance(derived, Mapping):
                    safe["pr_open_to_materialised_ms"] = derived.get(
                        "pr_open_to_materialised_ms"
                    )
    print(
        "OVC_VIT_POST_MERGE_COMPLETION_PROOF " + json.dumps(safe, sort_keys=True),
        flush=True,
    )
    return safe


def _manifest_requests(path: Path | None) -> tuple[str, ...]:
    if path is None or not path.is_file():
        return ()
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping) or value.get("schema") != RECOVERY_SCHEMA:
        raise legacy.PostMergeCompletionError("post-merge recovery manifest schema invalid")
    requests = value.get("requests")
    if not isinstance(requests, list):
        raise legacy.PostMergeCompletionError(
            "post-merge recovery manifest requests invalid"
        )
    result: list[str] = []
    for row in requests:
        if not isinstance(row, Mapping):
            raise legacy.PostMergeCompletionError("post-merge recovery request invalid")
        sha = str(row.get("merge_sha", ""))
        if len(sha) != 40 or sha.lower() != sha:
            raise legacy.PostMergeCompletionError("post-merge recovery merge SHA invalid")
        try:
            int(sha, 16)
        except ValueError as exc:
            raise legacy.PostMergeCompletionError(
                "post-merge recovery merge SHA invalid"
            ) from exc
        if row.get("authority_effect") != "NONE":
            raise legacy.PostMergeCompletionError(
                "post-merge recovery authority effect invalid"
            )
        result.append(sha)
    return tuple(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--merge-sha", required=True)
    parser.add_argument("--recovery-manifest")
    args = parser.parse_args()
    try:
        repo_root = Path(args.repo_root).resolve()
        external_root = resolve_external_root(
            repository_root=repo_root,
            environ=os.environ,
            create=False,
        )
        receipt_store = ReceiptStore(external_root / "receipts")
        recovery_path = (
            Path(args.recovery_manifest).resolve() if args.recovery_manifest else None
        )
        requested = [args.merge_sha, *_manifest_requests(recovery_path)]
        seen: set[str] = set()
        queue = [sha for sha in requested if not (sha in seen or seen.add(sha))]
        for merge_sha in queue:
            _recover_one(
                repo_root=repo_root,
                merge_sha=merge_sha,
                receipt_store=receipt_store,
            )
        return 0
    except (
        legacy.PostMergeCompletionError,
        VitContractError,
        RuntimeError,
        ValueError,
        KeyError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        print(
            "::error title=DSAI3V late-binding post-merge completion failed::"
            f"OVC_VIT_POST_MERGE_COMPLETION_FAILED: {exc}",
            flush=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
