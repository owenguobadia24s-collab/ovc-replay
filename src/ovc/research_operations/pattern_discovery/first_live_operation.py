from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


PLAN_ID = "OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1"
PACKET_ID = "PD-WP5"
GATE_ID = "PD-G5"
AMENDMENT_GATE_ID = "RPS-G4A"
ACTIVATION_MERGE = "aa29b23a7a83e33880ac2d80deb013f0c0390f30"
SOURCE_BINDING_ID = "RPS.BINDING.32fb3003efa072916c11e907"
SIGNING_BINDING_ID = "RPS.SIGNING.50092c28981fef08f53a6cb5"
OPERATOR_ID = "OVC.OPERATOR.PRIMARY.LOCAL.V1"
ACTIVE_RELEASE_ID = "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1"
ACTIVE_MANIFEST_ID = "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1.r1"
ACTIVE_MANIFEST_SHA256 = "c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33"
ACTIVE_AUTHORITY_RECORD = (
    "registries/research_operations/prospective_source/"
    "RPS_G4_ACTIVE_AUTHORITY_v0_1.json"
)
PROPOSED_SLICE_ID = "RPS.DUKASCOPY.GBPUSD.20260728_20260801.v1"
PROPOSED_WINDOW_START = "2026-07-28T00:00:00Z"
PROPOSED_WINDOW_END = "2026-08-01T00:00:00Z"


class FirstLiveOperationError(RuntimeError):
    pass


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise FirstLiveOperationError("timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FirstLiveOperationError(f"invalid UTC timestamp:{value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise FirstLiveOperationError(f"timestamp must use UTC:{value}")
    return parsed.astimezone(timezone.utc)


def load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FirstLiveOperationError(f"{code}:{path}") from exc
    if not isinstance(value, dict):
        raise FirstLiveOperationError(f"{code}:{path}")
    return value


def repository_state(repository_root: Path) -> tuple[str, str]:
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        changes = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ACTIVATION_MERGE, "HEAD"],
            cwd=repository_root,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise FirstLiveOperationError("unable to resolve repository state") from exc
    if branch != "main":
        raise FirstLiveOperationError("PD-WP5 operator preflight requires the main branch")
    if changes:
        raise FirstLiveOperationError("PD-WP5 operator preflight requires a clean tracked worktree")
    if ancestor.returncode != 0:
        raise FirstLiveOperationError("RPS-G4 activation merge is not an ancestor of HEAD")
    return branch, commit


def activation_cutoff(repository_root: Path) -> str:
    try:
        value = subprocess.run(
            ["git", "show", "-s", "--format=%cI", ACTIVATION_MERGE],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise FirstLiveOperationError("unable to resolve activation merge timestamp") from exc
    parsed = parse_utc(value)
    return parsed.isoformat().replace("+00:00", "Z")


def validate_activation(value: Mapping[str, Any]) -> None:
    expected = {
        "plan_id": PLAN_ID,
        "gate_id": "RPS-G4",
        "decision": "PASS",
        "decision_authority": "OPERATOR",
        "source_binding_id": SOURCE_BINDING_ID,
        "signing_binding_id": SIGNING_BINDING_ID,
        "operator_id": OPERATOR_ID,
        "active_model_release_id": ACTIVE_RELEASE_ID,
        "operation_mode": "LIVE_PROSPECTIVE",
        "activation_merge_commit": ACTIVATION_MERGE,
        "first_operation_limit": 1,
        "next_packet": PACKET_ID,
        "next_gate": GATE_ID,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise FirstLiveOperationError(f"active authority mismatch:{key}")
    for key in (
        "pd_g4_approved",
        "rps_g4_approved",
        "operator_key_bound",
        "bridge_healthy",
        "write_authority",
        "active_research_triage",
    ):
        if value.get(key) is not True:
            raise FirstLiveOperationError(f"active authority is not enabled:{key}")
    if value.get("candidate_source_resolved") is not False:
        raise FirstLiveOperationError("repository activation must remain candidate-unresolved")
    if value.get("live_append_enabled") is not False:
        raise FirstLiveOperationError("repository activation must remain append-disabled")
    if value.get("time_gated_replay_backfill") != "DENIED":
        raise FirstLiveOperationError("replay backfill must remain denied")


def source_coverage_blocker(activation: Mapping[str, Any], cutoff_utc: str) -> dict[str, Any] | None:
    eligible = parse_utc(str(activation.get("eligible_data_through_utc", "")))
    cutoff = parse_utc(cutoff_utc)
    if eligible <= cutoff:
        return {
            "code": "ACTIVE_BINDING_HAS_NO_POST_ACTIVATION_MARKET_COVERAGE",
            "detail": (
                "The exact active source binding ends at or before the RPS-G4 "
                "activation cutoff and cannot produce a genuine LIVE_PROSPECTIVE candidate."
            ),
            "eligible_data_through_utc": eligible.isoformat().replace("+00:00", "Z"),
            "activation_cutoff_utc": cutoff.isoformat().replace("+00:00", "Z"),
            "replay_substitution": "DENIED",
            "smallest_lawful_resolution": AMENDMENT_GATE_ID,
        }
    return None


def validate_candidate_package(package: Mapping[str, Any], cutoff_utc: str) -> list[str]:
    errors: list[str] = []
    if package.get("operation_mode") != "LIVE_PROSPECTIVE":
        errors.append("candidate package must use LIVE_PROSPECTIVE")
    if package.get("source_binding_id") != SOURCE_BINDING_ID:
        errors.append("candidate package is not bound to the exact active source binding")
    if package.get("signing_binding_id") != SIGNING_BINDING_ID:
        errors.append("candidate package is not bound to the exact active signing binding")
    if package.get("operator_id") != OPERATOR_ID:
        errors.append("candidate package operator mismatch")
    if package.get("active_release_id") != ACTIVE_RELEASE_ID:
        errors.append("candidate package active release mismatch")
    if package.get("active_manifest_id") != ACTIVE_MANIFEST_ID:
        errors.append("candidate package active manifest mismatch")
    if package.get("active_manifest_sha256") != ACTIVE_MANIFEST_SHA256:
        errors.append("candidate package active manifest hash mismatch")
    source_ids = package.get("source_object_ids")
    if (
        not isinstance(source_ids, list)
        or not source_ids
        or len(source_ids) != len(set(source_ids))
        or any(not isinstance(item, str) or not item.strip() for item in source_ids)
    ):
        errors.append("candidate package requires non-empty unique immutable source_object_ids")
    try:
        start = parse_utc(str(package.get("market_window_start_utc", "")))
        end = parse_utc(str(package.get("market_window_end_utc", "")))
        trigger = parse_utc(str(package.get("trigger_first_valid_at", "")))
        cutoff = parse_utc(cutoff_utc)
        if not (start < end):
            errors.append("candidate market window is not increasing")
        if trigger < start or trigger > end:
            errors.append("trigger_first_valid_at is outside the market window")
        if start <= cutoff or end <= cutoff or trigger <= cutoff:
            errors.append("candidate is not strictly post-activation")
    except FirstLiveOperationError as exc:
        errors.append(str(exc))
    return errors


def amendment_proposal(cutoff_utc: str) -> dict[str, Any]:
    start = parse_utc(PROPOSED_WINDOW_START)
    cutoff = parse_utc(cutoff_utc)
    if start <= cutoff:
        raise FirstLiveOperationError("proposed post-activation slice is not after activation cutoff")
    return {
        "gate_id": AMENDMENT_GATE_ID,
        "decision_authority": "OPERATOR",
        "proposed_delta": "AUTHORISE_ONE_POST_ACTIVATION_DUKASCOPY_SOURCE_SLICE_AND_REBIND_PD_WP5",
        "provider": "DUKASCOPY",
        "instrument": "GBPUSD",
        "slice_id": PROPOSED_SLICE_ID,
        "interval": {
            "start_utc": PROPOSED_WINDOW_START,
            "end_utc": PROPOSED_WINDOW_END,
        },
        "streams": ["M1_BID", "M1_ASK", "H1_BID", "H1_ASK"],
        "compressed_byte_limit": 26_214_400,
        "expanded_byte_limit": 104_857_600,
        "provider_request_before_approval": "DENIED",
        "provider_request_in_ci": "DENIED",
        "destination": "OVC_EXTERNAL_ARTIFACT_ROOT_ONLY",
        "native_h1_requirement": "REQUIRED_NO_M1_DERIVED_SUBSTITUTION",
        "current_month_availability_condition": (
            "DEFER_EXECUTION_UNTIL_DUKASCOPY_JULY_2026_NATIVE_H1_BI5_OBJECTS_ARE_AVAILABLE"
        ),
        "source_acceptance": "EXACT_QA_WITH_GAPPED_POLICY_ONLY_IF_SEPARATELY_ACCEPTED_BY_EXISTING_RULES",
        "post_intake_work": [
            "FREEZE_IMMUTABLE_POST_ACTIVATION_SOURCE_SLICE",
            "RUN_15M_2H_OPT_A_TO_C1_TO_C2_PIPELINE",
            "CREATE_NEW_EXACT_NON_REPLAY_SOURCE_BINDING",
            "RUN_ONE_PD_WP5_LIVE_PROSPECTIVE_OPERATION",
            "STOP_AT_PD_G5",
        ],
    }


def preflight(
    repository_root: Path,
    *,
    candidate_package: Path | None = None,
) -> tuple[dict[str, Any], int]:
    branch, commit = repository_state(repository_root)
    cutoff = activation_cutoff(repository_root)
    activation = load_json(
        repository_root / ACTIVE_AUTHORITY_RECORD,
        "INVALID_ACTIVE_AUTHORITY_RECORD",
    )
    validate_activation(activation)
    blocker = source_coverage_blocker(activation, cutoff)
    result: dict[str, Any] = {
        "schema": "ovc-pd-wp5-first-live-operation-preflight/v1",
        "plan_id": PLAN_ID,
        "packet_id": PACKET_ID,
        "next_gate": GATE_ID,
        "repository_branch": branch,
        "repository_commit": commit,
        "activation_merge_commit": ACTIVATION_MERGE,
        "activation_cutoff_utc": cutoff,
        "source_binding_id": SOURCE_BINDING_ID,
        "signing_binding_id": SIGNING_BINDING_ID,
        "operator_id": OPERATOR_ID,
        "operation_mode": "LIVE_PROSPECTIVE",
        "first_operation_limit": 1,
        "provider_network_access_performed": False,
        "replay_backfill": "DENIED",
        "candidate_package_supplied": candidate_package is not None,
        "candidate_package_errors": [],
        "blockers": [],
    }
    if candidate_package is not None:
        package = load_json(candidate_package, "INVALID_CANDIDATE_PACKAGE")
        result["candidate_package_errors"] = validate_candidate_package(package, cutoff)
    if blocker is not None:
        result["blockers"].append(blocker)
        result["amendment_proposal"] = amendment_proposal(cutoff)
        result["status"] = "BLOCKED_POST_ACTIVATION_SOURCE_REQUIRED"
        result["next_action"] = f"OVC APPROVE {AMENDMENT_GATE_ID} OR DEFER"
        return result, 3
    if result["candidate_package_errors"]:
        result["status"] = "BLOCKED_INVALID_LIVE_CANDIDATE_PACKAGE"
        result["next_action"] = "CORRECT_EXTERNAL_CANDIDATE_PACKAGE"
        return result, 2
    if candidate_package is None:
        result["status"] = "BLOCKED_NO_LIVE_CANDIDATE_PACKAGE"
        result["next_action"] = "PROVIDE_OPERATOR_LOCAL_LIVE_CANDIDATE_PACKAGE"
        return result, 3
    result["status"] = "READY_FOR_ONE_PD_WP5_LIVE_PROSPECTIVE_OPERATION"
    result["next_action"] = "EXECUTE_BOUNDED_OPERATION"
    return result, 0


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Fail-closed PD-WP5 first LIVE_PROSPECTIVE operation preflight."
    )
    value.add_argument("command", choices=("preflight",))
    value.add_argument("--repository-root", type=Path, default=Path.cwd())
    value.add_argument("--candidate-package", type=Path)
    return value


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        root = arguments.repository_root.resolve(strict=True)
        package = arguments.candidate_package
        if package is not None:
            package = package.resolve(strict=True)
        result, exit_code = preflight(root, candidate_package=package)
    except FirstLiveOperationError as exc:
        print(f"PD-WP5 blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
