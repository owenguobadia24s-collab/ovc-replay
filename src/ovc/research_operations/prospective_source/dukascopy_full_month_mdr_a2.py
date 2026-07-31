from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Mapping, Sequence

from ovc.research_operations.prospective_source import (
    dukascopy_full_month_mdr as a1,
)

PROGRAMME_ID = "PD-JUNE-FULL-MONTH-MDR"
BASE_PLAN_ID = "OVC-PD-JUNE-FULL-MONTH-MDR.v0.1"
PLAN_AMENDMENT_ID = "PD-JUNE-FM-A2-PAIRED-SPARSE-M1-ACCEPTANCE"
PRIOR_PLAN_AMENDMENT_ID = "PD-JUNE-FM-A1-JULY-NATIVE-H1-WAIVER"
EFFECTIVE_PLAN_VERSION = "0.1+A1+A2"
APPROVED_GATE = "PD-JUNE-FM-G1"
APPROVED_AMENDMENT_GATE = "PD-JUNE-FM-A2-PAIRED-SPARSE-M1-ACCEPTANCE"
PAIRED_SPARSE_POLICY = "ACCEPT_EXACTLY_PAIRED_PROVIDER_ABSENCE_WITH_EXPLICIT_CENSORING"
DOWNSTREAM_POLICY = "INCOMPLETE_REQUIRED_MEMBERSHIP_NOT_EVALUABLE_NO_BRIDGING"
ADAPTER_VERSION = "1.5.0-pd-june-full-month-mdr-a2"

IntakeError = a1.IntakeError
FetchResult = a1.FetchResult
Fetcher = a1.Fetcher
CandleRow = a1.CandleRow

_ORIGINAL_PROVIDER_REQUEST_PLAN = a1.provider_request_plan
_ORIGINAL_COVERAGE_AUDIT = a1._coverage_audit
_ORIGINAL_POST_TARGET_H1_AUDIT = a1._post_target_h1_audit
_ORIGINAL_LOGICAL_MANIFEST = a1._logical_manifest
_ORIGINAL_WRITE_JSON = a1.base._write_json
_ORIGINAL_EXECUTE_INTAKE = a1.execute_intake


def _apply_a2_globals() -> None:
    a1.PLAN_AMENDMENT_ID = PLAN_AMENDMENT_ID
    a1.ADAPTER_VERSION = ADAPTER_VERSION


def source_profile() -> dict[str, object]:
    _apply_a2_globals()
    profile = dict(a1.build_source_profile())
    profile.update(
        {
            "plan_version": EFFECTIVE_PLAN_VERSION,
            "plan_amendment": PLAN_AMENDMENT_ID,
            "prior_plan_amendment": PRIOR_PLAN_AMENDMENT_ID,
            "paired_sparse_m1_policy": PAIRED_SPARSE_POLICY,
            "downstream_incomplete_membership_policy": DOWNSTREAM_POLICY,
            "source_admissibility": (
                "PAIRED_PROVIDER_ABSENCE_ALLOWED_ONLY_WITH_EXACT_BID_ASK_TIMESTAMP_EQUALITY"
            ),
        }
    )
    return profile


def provider_request_plan() -> dict[str, object]:
    _apply_a2_globals()
    plan = dict(_ORIGINAL_PROVIDER_REQUEST_PLAN())
    plan.update(
        {
            "schema": "ovc-pd-june-full-month-mdr-provider-plan-a2/v1",
            "plan_amendment": PLAN_AMENDMENT_ID,
            "prior_plan_amendment": PRIOR_PLAN_AMENDMENT_ID,
            "effective_plan_version": EFFECTIVE_PLAN_VERSION,
            "paired_sparse_m1_policy": PAIRED_SPARSE_POLICY,
            "downstream_incomplete_membership_policy": DOWNSTREAM_POLICY,
        }
    )
    return plan


def _coverage_audit(
    rows: Sequence[CandleRow],
    *,
    clock: str,
    side: str,
) -> dict[str, object]:
    result = dict(_ORIGINAL_COVERAGE_AUDIT(rows, clock=clock, side=side))
    gap_runs = list(result["unexpected_intra_session_gaps"])
    step_seconds = 60 if clock == "M1" else 3600
    absent_timestamp_count = sum(
        max(0, int(item["duration_seconds"]) // step_seconds - 1)
        for item in gap_runs
    )
    result.update(
        {
            "raw_gap_classification": "PROVIDER_ABSENCE_PENDING_PAIR_RECONCILIATION",
            "paired_sparse_policy": PAIRED_SPARSE_POLICY,
            "gap_run_count": len(gap_runs),
            "absent_timestamp_count": absent_timestamp_count,
            "gaps_require_exact_other_side_match": True,
            "downstream_policy": DOWNSTREAM_POLICY,
        }
    )
    result["qa_state"] = (
        "PASS"
        if rows
        and result["duplicates"] == 0
        and result["non_monotonic"] == 0
        and result["start_boundary_accepted"]
        and result["end_boundary_accepted"]
        else "BLOCK"
    )
    return result


def _post_target_h1_audit(
    m1_rows: Sequence[CandleRow],
    *,
    side: str,
) -> tuple[list[CandleRow], dict[str, object]]:
    derived, result = _ORIGINAL_POST_TARGET_H1_AUDIT(m1_rows, side=side)
    result = dict(result)
    missing = list(result["missing_hours_utc"])
    result.update(
        {
            "paired_sparse_policy": PAIRED_SPARSE_POLICY,
            "incomplete_hours_disposition": "CENSORED_NOT_REPAIRED",
            "downstream_policy": DOWNSTREAM_POLICY,
            "minimum_complete_hour_count": 1,
        }
    )
    result["qa_state"] = (
        "PASS"
        if not result["unexpected_hours_utc"]
        and result["derived_complete_hour_count"] >= 1
        else "BLOCK"
    )
    result["censored_hours_utc"] = missing
    return derived, result


def _logical_manifest(source_objects: Sequence[dict[str, object]]) -> dict[str, object]:
    manifest = dict(_ORIGINAL_LOGICAL_MANIFEST(source_objects))
    manifest.update(
        {
            "schema": "ovc-pd-june-full-month-mdr-source-manifest-a2/v1",
            "plan_amendment": PLAN_AMENDMENT_ID,
            "prior_plan_amendment": PRIOR_PLAN_AMENDMENT_ID,
            "effective_plan_version": EFFECTIVE_PLAN_VERSION,
            "coverage_state": (
                "ACCEPTED_WITH_EXPLICIT_PAIRED_PROVIDER_ABSENCE_AND_CENSORING"
            ),
            "paired_sparse_m1_policy": PAIRED_SPARSE_POLICY,
            "downstream_incomplete_membership_policy": DOWNSTREAM_POLICY,
            "repair_performed": False,
            "synthetic_price_insertion": "DENIED",
        }
    )
    manifest["manifest_sha256"] = a1.base._canonical_sha256(manifest)
    return manifest


def _augment_receipt(path: Path, value: object) -> object:
    if not isinstance(value, dict):
        return value
    amended = dict(value)
    amended["plan_amendment"] = PLAN_AMENDMENT_ID
    amended["prior_plan_amendment"] = PRIOR_PLAN_AMENDMENT_ID
    amended["effective_plan_version"] = EFFECTIVE_PLAN_VERSION
    amended["paired_sparse_m1_policy"] = PAIRED_SPARSE_POLICY
    amended["downstream_incomplete_membership_policy"] = DOWNSTREAM_POLICY
    if path.name == "coverage-gap-duplicate-qa.json":
        amended["qa_disposition"] = (
            "PASS_PAIRED_PROVIDER_ABSENCE_RECORDED_DEPENDENT_BUCKETS_CENSORED"
        )
        amended["repair_performed"] = False
    elif path.name == "bid-ask-reconciliation.json":
        amended["exact_timestamp_pairing_required"] = True
    elif path.name == "native-h1-reconciliation.json":
        amended["native_h1_repair_authority"] = "NONE"
        amended["incomplete_post_target_hours"] = "CENSORED_NOT_REPAIRED"
    elif path.name == "freeze-receipt.json":
        amended["source_admissibility"] = (
            "PAIRED_PROVIDER_ABSENCE_ACCEPTED_WITH_EXPLICIT_CENSORING"
        )
        amended["repair_performed"] = False
        amended["synthetic_price_insertion"] = "DENIED"
    elif path.name == "provider-request-receipt.json":
        amended["adapter_version"] = ADAPTER_VERSION
    return amended


def _write_json(path: Path, value: object) -> None:
    _ORIGINAL_WRITE_JSON(path, _augment_receipt(path, value))


def preflight(
    *,
    repository_root: Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    _apply_a2_globals()
    original_plan = a1.provider_request_plan
    try:
        a1.provider_request_plan = provider_request_plan
        result = dict(a1.preflight(repository_root=repository_root, environ=environ))
    finally:
        a1.provider_request_plan = original_plan
    result.update(
        {
            "plan_amendment": PLAN_AMENDMENT_ID,
            "prior_plan_amendment": PRIOR_PLAN_AMENDMENT_ID,
            "effective_plan_version": EFFECTIVE_PLAN_VERSION,
            "amendment_gate": APPROVED_AMENDMENT_GATE,
            "paired_sparse_m1_policy": PAIRED_SPARSE_POLICY,
            "downstream_incomplete_membership_policy": DOWNSTREAM_POLICY,
        }
    )
    return result


def execute_intake(
    *,
    repository_root: Path,
    gate: str,
    amendment_gate: str,
    environ: Mapping[str, str] | None = None,
    fetcher: Fetcher = a1.base._request,
) -> dict[str, object]:
    if gate != APPROVED_GATE:
        raise IntakeError(f"exact operator approval binding required: --gate {APPROVED_GATE}")
    if amendment_gate != APPROVED_AMENDMENT_GATE:
        raise IntakeError(
            "exact A2 operator approval binding required: "
            f"--amendment-gate {APPROVED_AMENDMENT_GATE}"
        )
    _apply_a2_globals()
    originals = {
        "provider_request_plan": a1.provider_request_plan,
        "coverage_audit": a1._coverage_audit,
        "post_target_h1_audit": a1._post_target_h1_audit,
        "logical_manifest": a1._logical_manifest,
        "write_json": a1.base._write_json,
    }
    try:
        a1.provider_request_plan = provider_request_plan
        a1._coverage_audit = _coverage_audit
        a1._post_target_h1_audit = _post_target_h1_audit
        a1._logical_manifest = _logical_manifest
        a1.base._write_json = _write_json
        result = dict(
            _ORIGINAL_EXECUTE_INTAKE(
                repository_root=repository_root,
                gate=gate,
                environ=environ,
                fetcher=fetcher,
            )
        )
    finally:
        a1.provider_request_plan = originals["provider_request_plan"]
        a1._coverage_audit = originals["coverage_audit"]
        a1._post_target_h1_audit = originals["post_target_h1_audit"]
        a1._logical_manifest = originals["logical_manifest"]
        a1.base._write_json = originals["write_json"]
    result.update(
        {
            "plan_amendment": PLAN_AMENDMENT_ID,
            "prior_plan_amendment": PRIOR_PLAN_AMENDMENT_ID,
            "effective_plan_version": EFFECTIVE_PLAN_VERSION,
            "paired_sparse_m1_policy": PAIRED_SPARSE_POLICY,
            "downstream_incomplete_membership_policy": DOWNSTREAM_POLICY,
            "source_admissibility": (
                "PAIRED_PROVIDER_ABSENCE_ACCEPTED_WITH_EXPLICIT_CENSORING"
            ),
        }
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Operator-local full-month MDR A2 intake. Exact paired provider "
            "absence is admissible only with explicit downstream censoring."
        )
    )
    parser.add_argument("command", choices=("profile", "plan", "preflight", "execute"))
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--gate", default=None)
    parser.add_argument("--amendment-gate", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        repository_root = arguments.repository_root.resolve(strict=True)
        if arguments.command == "profile":
            result = source_profile()
        elif arguments.command == "plan":
            result = provider_request_plan()
        elif arguments.command == "preflight":
            result = preflight(repository_root=repository_root)
        else:
            result = execute_intake(
                repository_root=repository_root,
                gate=arguments.gate or "",
                amendment_gate=arguments.amendment_gate or "",
            )
    except IntakeError as exc:
        print(f"PD-JUNE-FM-WP1 A2 intake blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
