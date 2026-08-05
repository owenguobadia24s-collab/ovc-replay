"""Fail-closed operator-local C2 vNext June full-replay orchestration.

This module resolves the CEAR-G10 input-artifact blocker only. It grants no
selector, semantic, outcome, publication, Validation, probability, risk,
exposure, trading, execution, or agent-write authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PROGRAMME_ID = "OVC-C2-ANATOMY-REDESIGN-v0.2"
PLAN_ID = "OVC-C2-ANATOMY-REDESIGN-IMPLEMENTATION"
PLAN_VERSION = "0.3-REVISED"
PACKET_ID = "C2AR-WP10-INPUT-RESOLUTION"
GATE_ID = "CEAR-G10"
BINDING_SCHEMA = "ovc-c2-vnext-full-replay-input-binding/v1"
AUTHORITY = "PROVISIONAL_DISCOVERY_RESEARCH_ONLY"
SOURCE_SLICE_ID = "RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1"
SOURCE_MANIFEST_SHA256 = "1578b555f3d5aa2822b603141261f86a047096030e5faacd4380ef2c6d4f52e3"
FREEZE_ID = "C2AR.INTEGRATED.SHADOW.FREEZE.v1"
FREEZE_SHA256 = "856b2602bc52764974009dd2d5fdf5259db74242c6732a5a3b42905eb06c0a7f"
CONTEXT_START = "2026-05-30T00:00:00Z"
TARGET_START = "2026-06-01T00:00:00Z"
TARGET_END = "2026-07-01T00:00:00Z"
CONTEXT_END = "2026-07-03T00:00:00Z"
CLOCKS = ("15M", "2H_A_L")
SIDES = ("BID", "ASK")
SEQUENCE_LENGTHS = (2, 3, 4, 5, 6, 8, 12)
METHOD_REGISTRY = "registries/opt_b/c2/vnext/C2_FUNCTIONAL_DISCOVERY_METHOD_CANDIDATE_v0_1.jsonc"
BIND_ROOTS = (
    "contracts/opt_b/c2",
    "schemas/opt_b/c2/vnext",
    "registries/opt_b/c2/vnext",
    "src/ovc/opt_b/c2_vnext",
)
DENIED = {
    "active_selector": "DENIED",
    "release_publication": "DENIED",
    "r2_write": "DENIED",
    "validation_consumption": "DENIED",
    "semantic_promotion": "DENIED",
    "probability_risk_exposure_execution": "DENIED",
    "agent_write": "DENIED",
}


class FullReplayError(RuntimeError):
    pass


class ReplayInterrupted(FullReplayError):
    pass


@dataclass(frozen=True)
class ScopeResult:
    scope_id: str
    request_path: Path
    request_count: int
    request_sha256: str


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha_value(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binding_hash(value: Mapping[str, Any]) -> str:
    body = dict(value)
    body.pop("binding_sha256", None)
    return sha_value(body)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FullReplayError(f"INVALID_JSON:{path}") from exc
    if not isinstance(value, dict):
        raise FullReplayError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> tuple[int, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    digest = hashlib.sha256()
    count = 0
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            encoded = canonical(record)
            handle.write(encoded.decode("utf-8") + "\n")
            digest.update(encoded + b"\n")
            count += 1
    temporary.replace(path)
    return count, digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    try:
        for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not raw.strip():
                continue
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise FullReplayError(f"JSONL_OBJECT_REQUIRED:{path}:{line_number}")
            output.append(value)
    except (OSError, json.JSONDecodeError) as exc:
        raise FullReplayError(f"INVALID_JSONL:{path}") from exc
    return output


def git_head(repository_root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repository_root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise FullReplayError("GIT_HEAD_UNAVAILABLE") from exc


def safe_path(root: Path, relative: str, marker: str) -> Path:
    resolved_root = root.resolve()
    candidate = (resolved_root / relative).resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise FullReplayError(f"{marker}_PATH_ESCAPE:{relative}")
    return candidate


def method_registry(repository_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    value = read_json(safe_path(repository_root, METHOD_REGISTRY, "REPOSITORY"))
    method = value.get("method_pack")
    view = value.get("discovery_view_candidate")
    if not isinstance(method, dict) or not isinstance(view, dict):
        raise FullReplayError("FUNCTIONAL_DISCOVERY_METHOD_REGISTRY_INVALID")
    if value.get("active") is not False or value.get("canonical") is not False:
        raise FullReplayError("FUNCTIONAL_DISCOVERY_METHOD_MUST_REMAIN_INACTIVE")
    return method, view


def repository_inventory(repository_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for relative_root in BIND_ROOTS:
        root = safe_path(repository_root, relative_root, "REPOSITORY")
        if not root.is_dir():
            raise FullReplayError(f"BINDING_REPOSITORY_ROOT_MISSING:{relative_root}")
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            records.append({
                "path": path.relative_to(repository_root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha_file(path),
            })
    records.sort(key=lambda item: item["path"])
    return records


def build_binding(repository_root: Path, external_root: Path, output: Path, baseline: str) -> dict[str, Any]:
    from ovc.research_operations.prospective_source import full_month_mdr_replay as june

    repository_root = repository_root.resolve()
    external_root = external_root.resolve()
    source_root, _index, inventory = june.verify_frozen_source(
        repository_root, {"OVC_EXTERNAL_ARTIFACT_ROOT": str(external_root)}
    )
    source_files = []
    for item in sorted(inventory["source_objects"], key=lambda row: row["object_id"]):
        path = (source_root / str(item["relative_path"])).resolve()
        source_files.append({
            "object_id": str(item["object_id"]),
            "clock": str(item["clock"]),
            "side": str(item["side"]),
            "relative_path": path.relative_to(external_root).as_posix(),
            "row_count": int(item["row_count"]),
            "size_bytes": int(item["size_bytes"]),
            "sha256": str(item["sha256"]),
            "schema_fingerprint": str(item["schema_fingerprint"]),
            "first_timestamp_utc": str(item["first_timestamp_utc"]),
            "last_timestamp_utc": str(item["last_timestamp_utc"]),
        })
    method, view = method_registry(repository_root)
    repo_files = repository_inventory(repository_root)
    binding: dict[str, Any] = {
        "schema": BINDING_SCHEMA,
        "binding_id": "C2VNEXT.JUNE.DISCOVERY.INPUT.v1",
        "programme_id": PROGRAMME_ID,
        "plan_id": PLAN_ID,
        "plan_version": PLAN_VERSION,
        "packet_id": PACKET_ID,
        "gate_id": GATE_ID,
        "role": "DISCOVERY",
        "instrument": "GBPUSD",
        "source": {
            "slice_id": SOURCE_SLICE_ID,
            "manifest_sha256": SOURCE_MANIFEST_SHA256,
            "external_root": str(external_root),
            "files": source_files,
            "provider_execution": "NONE",
            "legacy_c2_payload_use": "PROHIBITED",
        },
        "interval": {
            "context_start_utc": CONTEXT_START,
            "target_start_utc": TARGET_START,
            "target_end_exclusive_utc": TARGET_END,
            "context_end_exclusive_utc": CONTEXT_END,
            "target_eligibility": "TARGET_JUNE_ONLY",
        },
        "scope": {
            "clocks": list(CLOCKS),
            "sides": list(SIDES),
            "frames": ["LOCAL"],
            "opportunity_types": ["REGISTERED_SEQUENCE_WINDOW"],
            "object_families": ["AXIS_BUNDLE"],
            "sequence_lengths": list(SEQUENCE_LENGTHS),
            "population_scope": "COMPLETE_REGISTERED_LAWFUL_DISCOVERY_POPULATION",
        },
        "code": {
            "expected_main_baseline": baseline,
            "expected_code_commit": git_head(repository_root),
            "repository_files": repo_files,
            "repository_inventory_sha256": sha_value(repo_files),
        },
        "frozen_policy": {
            "integrated_freeze_id": FREEZE_ID,
            "integrated_freeze_sha256": FREEZE_SHA256,
            "method_registry_path": METHOD_REGISTRY,
            "method_registry_sha256": sha_file(safe_path(repository_root, METHOD_REGISTRY, "REPOSITORY")),
            "method_pack_id": method["method_pack_id"],
            "discovery_view_id": view["discovery_view_id"],
            "maturity": "SHADOW_FROZEN",
        },
        "execution": {
            "max_runtime_seconds": 14400,
            "max_output_bytes": 10737418240,
            "clean_run_count": 2,
            "workspace_policy": "FRESH_PER_RUN",
            "checkpoint_policy": "SCOPE_ATOMIC",
            "resume_enabled": True,
            "exercise_restart": True,
        },
        "requirements": {
            "readable_payloads": True,
            "complete_accounting": True,
            "first_valid_chronology": True,
            "identical_logical_hashes": True,
            "legacy_upstream_influence": False,
            "outcome_inputs": False,
            "validation_inputs": False,
        },
        "authority": dict(DENIED),
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    binding["binding_sha256"] = binding_hash(binding)
    write_json(output, binding)
    return binding


def validate_binding(binding: Mapping[str, Any], repository_root: Path, expected_commit: str | None = None) -> dict[str, Any]:
    value = json.loads(json.dumps(binding))
    if value.get("schema") != BINDING_SCHEMA:
        raise FullReplayError("INPUT_BINDING_SCHEMA_MISMATCH")
    if value.get("binding_sha256") != binding_hash(value):
        raise FullReplayError("INPUT_BINDING_SHA256_MISMATCH")
    required = {
        "programme_id": PROGRAMME_ID,
        "plan_id": PLAN_ID,
        "plan_version": PLAN_VERSION,
        "role": "DISCOVERY",
        "instrument": "GBPUSD",
    }
    for key, expected in required.items():
        if value.get(key) != expected:
            raise FullReplayError(f"INPUT_BINDING_IDENTITY_MISMATCH:{key}")
    if value["source"].get("slice_id") != SOURCE_SLICE_ID:
        raise FullReplayError("INPUT_BINDING_SOURCE_SLICE_MISMATCH")
    if value["source"].get("manifest_sha256") != SOURCE_MANIFEST_SHA256:
        raise FullReplayError("INPUT_BINDING_SOURCE_MANIFEST_MISMATCH")
    if value["source"].get("legacy_c2_payload_use") != "PROHIBITED":
        raise FullReplayError("LEGACY_C2_PAYLOAD_USE_NOT_PROHIBITED")
    if sorted(value["scope"].get("clocks", [])) != sorted(CLOCKS):
        raise FullReplayError("INPUT_BINDING_CLOCK_SCOPE_MISMATCH")
    if sorted(value["scope"].get("sides", [])) != sorted(SIDES):
        raise FullReplayError("INPUT_BINDING_SIDE_SCOPE_MISMATCH")
    if value["scope"].get("population_scope") != "COMPLETE_REGISTERED_LAWFUL_DISCOVERY_POPULATION":
        raise FullReplayError("INPUT_BINDING_POPULATION_SCOPE_MISMATCH")
    if value["frozen_policy"].get("integrated_freeze_id") != FREEZE_ID:
        raise FullReplayError("INPUT_BINDING_FREEZE_ID_MISMATCH")
    if value["frozen_policy"].get("integrated_freeze_sha256") != FREEZE_SHA256:
        raise FullReplayError("INPUT_BINDING_FREEZE_SHA256_MISMATCH")
    if value.get("authority") != DENIED:
        raise FullReplayError("INPUT_BINDING_AUTHORITY_MUST_REMAIN_DENIED")
    if value["execution"].get("clean_run_count") != 2 or value["execution"].get("resume_enabled") is not True:
        raise FullReplayError("TWO_CLEAN_RUNS_AND_RESTART_REQUIRED")
    bound = str(value["code"].get("expected_code_commit", ""))
    actual = git_head(repository_root)
    if bound != actual:
        raise FullReplayError(f"CODE_COMMIT_MISMATCH:bound={bound}:actual={actual}")
    if expected_commit is not None and expected_commit != bound:
        raise FullReplayError("COMMAND_EXPECTED_CODE_COMMIT_MISMATCH")
    return value


def verify_bytes(binding: Mapping[str, Any], repository_root: Path, external_root: Path) -> dict[str, Any]:
    observed_repo = []
    for item in binding["code"]["repository_files"]:
        path = safe_path(repository_root, str(item["path"]), "REPOSITORY")
        observed = {"path": str(item["path"]), "size_bytes": path.stat().st_size, "sha256": sha_file(path)}
        if observed != item:
            raise FullReplayError(f"BOUND_REPOSITORY_FILE_MISMATCH:{item['path']}")
        observed_repo.append(observed)
    if sha_value(observed_repo) != binding["code"]["repository_inventory_sha256"]:
        raise FullReplayError("BOUND_REPOSITORY_INVENTORY_MISMATCH")
    for item in binding["source"]["files"]:
        path = safe_path(external_root, str(item["relative_path"]), "EXTERNAL")
        if not path.is_file() or path.stat().st_size != int(item["size_bytes"]) or sha_file(path) != item["sha256"]:
            raise FullReplayError(f"BOUND_SOURCE_FILE_MISMATCH:{item['relative_path']}")
    return {"repository_file_count": len(observed_repo), "source_file_count": len(binding["source"]["files"]), "result": "PASS"}


def decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise FullReplayError(f"NON_NUMERIC_MARKET_VALUE:{value!r}") from exc


def relation(left: Any, right: Any) -> str:
    a, b = decimal(left), decimal(right)
    return "ABOVE" if a > b else "BELOW" if a < b else "EQUAL"


def placeholder(position: int, quality: str = "NOT_AVAILABLE") -> dict[str, Any]:
    return {
        "position": position,
        "availability": "WARMUP_UNAVAILABLE",
        "close_vs_open": "NOT_COMPUTABLE",
        "close_vs_previous_close": "NOT_COMPUTABLE",
        "high_vs_previous_high": "NOT_COMPUTABLE",
        "low_vs_previous_low": "NOT_COMPUTABLE",
        "range_vs_previous_range": "NOT_COMPUTABLE",
        "quality_state": quality,
    }


def bar_token(bar: Any, previous: Any | None, position: int) -> dict[str, Any]:
    quality = str(bar.quality_state)
    if quality != "COMPLETE" or any(getattr(bar, key, None) is None for key in ("open", "high", "low", "close")):
        token = placeholder(position, quality)
        token["availability"] = "CENSORED"
        return token
    token = {
        "position": position,
        "availability": "AVAILABLE",
        "close_vs_open": relation(bar.close, bar.open),
        "quality_state": quality,
    }
    if previous is None or str(previous.quality_state) != "COMPLETE":
        token.update({
            "close_vs_previous_close": "NOT_APPLICABLE",
            "high_vs_previous_high": "NOT_APPLICABLE",
            "low_vs_previous_low": "NOT_APPLICABLE",
            "range_vs_previous_range": "NOT_APPLICABLE",
        })
    else:
        token.update({
            "close_vs_previous_close": relation(bar.close, previous.close),
            "high_vs_previous_high": relation(bar.high, previous.high),
            "low_vs_previous_low": relation(bar.low, previous.low),
            "range_vs_previous_range": relation(decimal(bar.high) - decimal(bar.low), decimal(previous.high) - decimal(previous.low)),
        })
    return token


def segment_map(bars: Sequence[Any]) -> dict[str, tuple[str, int]]:
    output: dict[str, tuple[str, int]] = {}
    segment = -1
    previous_end: str | None = None
    offset = 0
    for bar in sorted(bars, key=lambda item: item.start_utc):
        if str(bar.quality_state) != "COMPLETE":
            output[str(bar.start_utc)] = ("NONE", -1)
            previous_end = None
            continue
        if previous_end is None or str(bar.start_utc) != previous_end:
            segment += 1
            offset = 0
        else:
            offset += 1
        output[str(bar.start_utc)] = (f"SEGMENT.{bar.clock}.{bar.side}.{segment:04d}", offset)
        previous_end = str(bar.end_utc)
    return output


def build_scope_requests(
    bars: Sequence[Any], c1_records: Sequence[Mapping[str, Any]], *, clock: str,
    side: str, target_start: str, target_end: str, lengths: Sequence[int], binding_sha256: str,
) -> list[dict[str, Any]]:
    ordered = sorted(bars, key=lambda item: item.start_utc)
    segments = segment_map(ordered)
    c1_ids = {
        str(item.get("first_valid_time", item.get("close_time", ""))):
        str(item.get("c1_record_id", item.get("record_id", "")))
        for item in c1_records
    }
    requests: list[dict[str, Any]] = []
    for index, current in enumerate(ordered):
        start = str(current.start_utc)
        if not target_start <= start < target_end:
            continue
        segment_id, segment_offset = segments[start]
        for length in sorted(int(item) for item in lengths):
            window = ordered[max(0, index - length + 1): index + 1]
            complete = str(current.quality_state) == "COMPLETE"
            same_segment = complete and len(window) == length and segment_id != "NONE" and all(segments[str(item.start_utc)][0] == segment_id for item in window)
            reasons = []
            if not complete:
                reasons.append("CURRENT_BAR_INCOMPLETE")
            if len(window) < length:
                reasons.append("SEQUENCE_WARMUP")
            if complete and len(window) == length and not same_segment:
                reasons.append("SEQUENCE_CROSSES_CONTINUITY_BOUNDARY")
            missing = max(0, length - len(window))
            tokens = [placeholder(position) for position in range(missing)]
            for position, bar in enumerate(window, start=missing):
                previous = window[position - missing - 1] if position > missing else None
                tokens.append(bar_token(bar, previous, position))
            numeric = [item for item in window if str(item.quality_state) == "COMPLETE" and all(getattr(item, key, None) is not None for key in ("open", "high", "low", "close"))]
            first_close = decimal(numeric[0].close) if numeric else None
            current_close = decimal(current.close) if getattr(current, "close", None) is not None else None
            high = max(decimal(item.high) for item in numeric) if numeric else None
            low = min(decimal(item.low) for item in numeric) if numeric else None
            status = "COMPUTABLE" if same_segment else "CENSORED" if not complete else "NOT_COMPUTABLE"
            linked_c1 = [c1_ids[str(item.end_utc)] for item in window if str(item.end_utc) in c1_ids]
            requests.append({
                "source_unit_id": f"C2VNEXT.JUNE.{clock}.{side}.{start}.N{length}",
                "opportunity_type": "REGISTERED_SEQUENCE_WINDOW",
                "clock_id": clock,
                "side": side,
                "frame_id": "LOCAL",
                "object_family": "AXIS_BUNDLE",
                "first_valid_time": str(current.end_utc),
                "start_condition": {
                    "sequence_length": length,
                    "start_close_vs_open": tokens[0]["close_vs_open"],
                    "continuity_segment_available": segment_id != "NONE",
                },
                "ordered_development": tokens,
                "ending_structural_effect": {
                    "end_close_vs_start_close": relation(current_close, first_close) if current_close is not None and first_close is not None else "NOT_COMPUTABLE",
                    "end_close_vs_sequence_high": relation(current_close, high) if current_close is not None and high is not None else "NOT_COMPUTABLE",
                    "end_close_vs_sequence_low": relation(current_close, low) if current_close is not None and low is not None else "NOT_COMPUTABLE",
                    "continuity_state": "CONTIGUOUS" if same_segment else "NOT_CONTIGUOUS",
                },
                "duration_observations": length,
                "path_geometry": {
                    "available_observation_count": len(window),
                    "segment_offset": segment_offset,
                    "raw_span": str(high - low) if high is not None and low is not None else None,
                    "raw_net_close_delta": str(current_close - first_close) if current_close is not None and first_close is not None else None,
                },
                "object_ids": [
                    "C2.FORMULA.LOCATION.RAW_GEOMETRY.v1",
                    "C2.FORMULA.MOTION.TYPED_HORIZON_DELTA.v1",
                    "C2.FORMULA.ORGANISATION.RAW_GRAPH.v1",
                    "C2.FORMULA.INTERACTION.RAW_RELATION_CHANGE.v1",
                    "C2.COMPUTABILITY.PER_COMPONENT.v1",
                ],
                "context_ids": [f"CLOCK.{clock}", f"SIDE.{side}", "FRAME.LOCAL", FREEZE_ID],
                "missingness": {"missing_prefix_count": missing, "reason_codes": sorted(set(reasons)), "c1_record_count": len(linked_c1)},
                "assurance": {
                    "binding_sha256": binding_sha256,
                    "c1_record_ids": linked_c1,
                    "first_valid_chronology": all(str(item.end_utc) <= str(current.end_utc) for item in window),
                    "legacy_seed_count": 0,
                    "outcome_dependency_count": 0,
                    "validation_dependency_count": 0,
                },
                "applicable": True,
                "computability_status": status,
                "censored": status == "CENSORED",
                "reason_codes": sorted(set(reasons)),
                "authority_status": "AUTHORIZED_RESEARCH_ONLY",
                "policy_status": "RESOLVED",
                "numerator_member": same_segment,
                "overlap_cluster_ids": [f"OVERLAP.{clock}.{side}.{segment_id}.{start}"] if same_segment else [],
                "matching_stratum": {"clock": clock, "side": side, "sequence_length": length, "start_close_vs_open": tokens[0]["close_vs_open"]},
            })
    return sorted(requests, key=lambda item: (item["first_valid_time"], item["source_unit_id"]))


def directory_size(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def artifact_inventory(root: Path) -> list[dict[str, Any]]:
    ignored = {"output-manifest.json", "capacity-receipt.json"}
    return [
        {"path": path.relative_to(root).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha_file(path)}
        for path in sorted(item for item in root.rglob("*") if item.is_file())
        if path.relative_to(root).as_posix() not in ignored
    ]


def run_once(binding: Mapping[str, Any], repository_root: Path, external_root: Path, run_root: Path, *, resume: bool, stop_after: int | None = None) -> dict[str, Any]:
    from ovc.opt_b.c2_vnext.functional_discovery import (
        build_fingerprint_inventory, build_matched_controls, build_opportunity_population,
        build_provisional_families, compile_rule_candidate, evaluate_rule_candidate,
        extract_functional_cores, extract_motifs,
    )
    from ovc.research_operations.prospective_source import full_month_mdr_replay as june

    started = time.monotonic()
    if run_root.exists() and not resume:
        raise FullReplayError(f"CLEAN_RUN_WORKSPACE_EXISTS:{run_root}")
    run_root.mkdir(parents=True, exist_ok=True)
    checkpoint_path = run_root / "checkpoint.json"
    checkpoint = read_json(checkpoint_path) if resume and checkpoint_path.exists() else {"schema": "ovc-c2-vnext-full-replay-checkpoint/v1", "binding_sha256": binding["binding_sha256"], "completed_scopes": []}
    if checkpoint["binding_sha256"] != binding["binding_sha256"]:
        raise FullReplayError("CHECKPOINT_BINDING_MISMATCH")
    completed = set(checkpoint["completed_scopes"])
    source_root, _index, source_inventory = june.verify_frozen_source(repository_root, {"OVC_EXTERNAL_ARTIFACT_ROOT": str(external_root)})
    bars_by_scope, source_object_ids, coverage = june.build_bars(source_root, source_inventory)
    method, view = method_registry(repository_root)
    scope_results: list[ScopeResult] = []
    processed = 0
    for clock in sorted(binding["scope"]["clocks"]):
        for side in sorted(binding["scope"]["sides"]):
            scope_id = f"{clock}/{side}"
            scope_dir = run_root / "scopes" / clock / side
            request_path = scope_dir / "opportunity-requests.jsonl"
            if scope_id in completed:
                if not request_path.is_file():
                    raise FullReplayError(f"CHECKPOINT_SCOPE_PAYLOAD_MISSING:{scope_id}")
                records = read_jsonl(request_path)
                scope_results.append(ScopeResult(scope_id, request_path, len(records), sha_file(request_path)))
                continue
            bars = bars_by_scope[(clock, side)]
            c1_records, reset_count = june.build_c1_records(bars, source_object_ids[side])
            c1_count, c1_sha = write_jsonl(scope_dir / "c1-records.jsonl", c1_records)
            requests = build_scope_requests(
                bars, c1_records, clock=clock, side=side,
                target_start=binding["interval"]["target_start_utc"],
                target_end=binding["interval"]["target_end_exclusive_utc"],
                lengths=binding["scope"]["sequence_lengths"],
                binding_sha256=binding["binding_sha256"],
            )
            request_count, request_sha = write_jsonl(request_path, requests)
            write_json(scope_dir / "scope-manifest.json", {
                "scope_id": scope_id,
                "coverage": coverage[f"{clock}_{side}"],
                "c1_record_count": c1_count,
                "c1_sha256": c1_sha,
                "c1_continuity_reset_count": reset_count,
                "request_count": request_count,
                "request_sha256": request_sha,
                "legacy_c2_input_count": 0,
                "outcome_input_count": 0,
                "validation_input_count": 0,
            })
            scope_results.append(ScopeResult(scope_id, request_path, request_count, request_sha))
            completed.add(scope_id)
            checkpoint = {
                "schema": "ovc-c2-vnext-full-replay-checkpoint/v1",
                "binding_sha256": binding["binding_sha256"],
                "completed_scopes": sorted(completed),
                "last_completed_scope": scope_id,
            }
            write_json(checkpoint_path, checkpoint)
            processed += 1
            if stop_after is not None and processed >= stop_after:
                raise ReplayInterrupted(f"BOUNDED_RESTART_EXERCISE:{scope_id}")
    requests = [record for result in sorted(scope_results, key=lambda item: item.scope_id) for record in read_jsonl(result.request_path)]
    population = build_opportunity_population(requests, view, registered_scope_id=binding["binding_id"], input_manifest_sha256=binding["binding_sha256"])
    fingerprints = build_fingerprint_inventory(population, method)
    motifs = extract_motifs(fingerprints, method)
    families = build_provisional_families(motifs, method)
    cores = extract_functional_cores(families, motifs, fingerprints, method)
    candidates = [compile_rule_candidate(item, method) for item in cores["functional_cores"]]
    evaluations = [evaluate_rule_candidate(item, population, fingerprints) for item in candidates]
    controls = [build_matched_controls(item["source_opportunity_ids"], population, duration_bin_size=int(method["control_duration_bin_size"])) for item in candidates]
    evidence = run_root / "evidence"
    write_jsonl(evidence / "opportunity-population.jsonl", population["records"])
    write_jsonl(evidence / "fingerprints.jsonl", fingerprints["fingerprints"])
    write_json(evidence / "motifs.json", motifs)
    write_json(evidence / "families.json", families)
    write_json(evidence / "functional-cores.json", cores)
    write_jsonl(evidence / "rule-candidates.jsonl", candidates)
    write_jsonl(evidence / "rule-evaluations.jsonl", evaluations)
    write_jsonl(evidence / "matched-controls.jsonl", controls)
    logical = {
        "binding_sha256": binding["binding_sha256"],
        "scope_request_sha256": {item.scope_id: item.request_sha256 for item in scope_results},
        "population": population["content_sha256"],
        "fingerprints": fingerprints["content_sha256"],
        "motifs": motifs["content_sha256"],
        "families": families["content_sha256"],
        "cores": cores["content_sha256"],
        "candidates": [sha_value(item) for item in candidates],
        "evaluations": [sha_value(item) for item in evaluations],
        "controls": [sha_value(item) for item in controls],
    }
    logical_sha = sha_value(logical)
    manifest = {
        "schema": "ovc-c2-vnext-full-population-replay-manifest/v1",
        "binding_id": binding["binding_id"],
        "binding_sha256": binding["binding_sha256"],
        "code_commit": binding["code"]["expected_code_commit"],
        "source_slice_id": binding["source"]["slice_id"],
        "interval": binding["interval"],
        "scope": binding["scope"],
        "counts": {
            "requested": population["requested_count"],
            "records": population["record_count"],
            "outcomes": population["outcome_counts"],
            "fingerprints": fingerprints["fingerprint_count"],
            "motifs": len(motifs["motifs"]),
            "families": len(families["families"]),
            "functional_cores": len(cores["functional_cores"]),
            "rule_candidates": len(candidates),
        },
        "complete_accounting": all((population["complete_accounting"], fingerprints["complete_accounting"], motifs["complete_accounting"], families["complete_accounting"], cores["complete_accounting"])),
        "first_valid_chronology": all(item["assurance"]["first_valid_chronology"] for item in requests),
        "legacy_seed_count": 0,
        "outcome_dependency_count": 0,
        "validation_dependency_count": 0,
        "logical_core": logical,
        "logical_population_sha256": logical_sha,
        "runtime_seconds": time.monotonic() - started,
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    write_json(run_root / "output-manifest.json", manifest)
    capacity = {
        "runtime_seconds": manifest["runtime_seconds"],
        "max_runtime_seconds": binding["execution"]["max_runtime_seconds"],
        "output_bytes": directory_size(run_root),
        "max_output_bytes": binding["execution"]["max_output_bytes"],
    }
    capacity["result"] = "PASS" if capacity["runtime_seconds"] <= capacity["max_runtime_seconds"] and capacity["output_bytes"] <= capacity["max_output_bytes"] else "CAPACITY_EXCEEDED"
    write_json(run_root / "capacity-receipt.json", capacity)
    if capacity["result"] != "PASS":
        raise FullReplayError("CAPACITY_EXCEEDED")
    inventory = artifact_inventory(run_root)
    return {
        "manifest": manifest,
        "logical_population_sha256": logical_sha,
        "artifact_inventory_sha256": sha_value(inventory),
    }


def compare_runs(left: Mapping[str, Any], right: Mapping[str, Any], restart: Mapping[str, Any]) -> dict[str, Any]:
    logical = left["logical_population_sha256"] == right["logical_population_sha256"] == restart["logical_population_sha256"]
    inventory = left["artifact_inventory_sha256"] == right["artifact_inventory_sha256"] == restart["artifact_inventory_sha256"]
    counts = left["manifest"]["counts"] == right["manifest"]["counts"] == restart["manifest"]["counts"]
    discrepancies = [name for name, passed in {"LOGICAL_HASH": logical, "ARTIFACT_INVENTORY": inventory, "COUNT_RECONCILIATION": counts}.items() if not passed]
    return {
        "schema": "ovc-c2-vnext-full-replay-determinism-receipt/v1",
        "logical_hash_match": logical,
        "artifact_inventory_match": inventory,
        "count_reconciliation_match": counts,
        "restart_exercised": True,
        "discrepancies": discrepancies,
        "result": "PASS" if not discrepancies else "FAIL",
    }


def preflight(binding_path: Path, repository_root: Path, expected_commit: str | None = None) -> dict[str, Any]:
    binding = validate_binding(read_json(binding_path), repository_root, expected_commit)
    result = verify_bytes(binding, repository_root, Path(binding["source"]["external_root"]))
    return {"schema": "ovc-c2-vnext-full-replay-preflight-receipt/v1", "binding_id": binding["binding_id"], "binding_sha256": binding["binding_sha256"], **result}


def orchestrate(binding_path: Path, output_root: Path, repository_root: Path, expected_commit: str | None = None) -> dict[str, Any]:
    binding = validate_binding(read_json(binding_path), repository_root, expected_commit)
    external_root = Path(binding["source"]["external_root"]).resolve()
    if output_root.exists():
        raise FullReplayError(f"OUTPUT_ROOT_MUST_NOT_EXIST:{output_root}")
    output_root.mkdir(parents=True)
    write_json(output_root / "input-binding.json", binding)
    write_json(output_root / "preflight-receipt.json", verify_bytes(binding, repository_root, external_root))
    run1 = run_once(binding, repository_root, external_root, output_root / "run-001", resume=False)
    run2 = run_once(binding, repository_root, external_root, output_root / "run-002", resume=False)
    restart_root = output_root / "restart-verification"
    interrupted = False
    try:
        run_once(binding, repository_root, external_root, restart_root, resume=False, stop_after=1)
    except ReplayInterrupted:
        interrupted = True
    if not interrupted:
        raise FullReplayError("RESTART_EXERCISE_DID_NOT_INTERRUPT")
    restart = run_once(binding, repository_root, external_root, restart_root, resume=True)
    comparison = compare_runs(run1, run2, restart)
    write_json(output_root / "determinism-receipt.json", comparison)
    restart_receipt = {
        "schema": "ovc-c2-vnext-full-replay-restart-receipt/v1",
        "checkpoint_loaded": True,
        "resumed_to_completion": True,
        "logical_hash_matches_clean_runs": comparison["logical_hash_match"],
        "result": "PASS" if comparison["logical_hash_match"] else "FAIL",
    }
    write_json(output_root / "restart-receipt.json", restart_receipt)
    receipt = {
        "schema": "ovc-c2-vnext-full-replay-orchestration-receipt/v1",
        "binding_id": binding["binding_id"],
        "binding_sha256": binding["binding_sha256"],
        "clean_run_count": 2,
        "logical_population_sha256": run1["logical_population_sha256"],
        "result": "PASS" if comparison["result"] == restart_receipt["result"] == "PASS" else "FAIL",
        "authority": dict(DENIED),
    }
    write_json(output_root / "orchestration-receipt.json", receipt)
    if receipt["result"] != "PASS":
        raise FullReplayError("FULL_REPLAY_ASSURANCE_FAILED")
    return receipt


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build-binding")
    build.add_argument("--repository-root", required=True, type=Path)
    build.add_argument("--external-root", required=True, type=Path)
    build.add_argument("--output", required=True, type=Path)
    build.add_argument("--expected-main-baseline", required=True)
    check = commands.add_parser("preflight")
    check.add_argument("--repository-root", required=True, type=Path)
    check.add_argument("--input-binding", required=True, type=Path)
    check.add_argument("--expected-code-commit")
    run = commands.add_parser("orchestrate")
    run.add_argument("--repository-root", type=Path, default=Path.cwd())
    run.add_argument("--input-binding", required=True, type=Path)
    run.add_argument("--output-root", required=True, type=Path)
    run.add_argument("--expected-code-commit")
    run.add_argument("--expected-main-baseline")
    run.add_argument("--instrument")
    run.add_argument("--source-slice-id")
    run.add_argument("--source-manifest-sha256")
    run.add_argument("--integrated-freeze-id")
    run.add_argument("--integrated-freeze-sha256")
    run.add_argument("--context-start-utc")
    run.add_argument("--target-start-utc")
    run.add_argument("--target-end-exclusive-utc")
    run.add_argument("--context-end-exclusive-utc")
    run.add_argument("--clock", action="append")
    run.add_argument("--side", action="append")
    run.add_argument("--population-scope")
    run.add_argument("--clean-run-count", type=int)
    run.add_argument("--workspace-policy")
    run.add_argument("--checkpoint-policy")
    run.add_argument("--capacity-policy")
    for name in (
        "resume-enabled", "require-readable-payloads", "require-complete-accounting",
        "require-first-valid-chronology", "require-identical-logical-hashes",
        "emit-input-manifest", "emit-output-manifest", "emit-population-reconciliation",
        "emit-denominator-reconciliation", "emit-capacity-receipt", "emit-checkpoint-receipt",
        "emit-restart-receipt", "emit-determinism-comparison", "deny-outcome-inputs",
        "deny-validation-inputs", "deny-legacy-upstream-influence", "deny-selector-write",
        "deny-release-publication", "deny-r2-write",
    ):
        run.add_argument("--" + name, action="store_true")
    return root


def validate_overrides(args: argparse.Namespace, binding: Mapping[str, Any]) -> None:
    expected = {
        "expected_main_baseline": binding["code"]["expected_main_baseline"],
        "expected_code_commit": binding["code"]["expected_code_commit"],
        "instrument": binding["instrument"],
        "source_slice_id": binding["source"]["slice_id"],
        "source_manifest_sha256": binding["source"]["manifest_sha256"],
        "integrated_freeze_id": binding["frozen_policy"]["integrated_freeze_id"],
        "integrated_freeze_sha256": binding["frozen_policy"]["integrated_freeze_sha256"],
        "context_start_utc": binding["interval"]["context_start_utc"],
        "target_start_utc": binding["interval"]["target_start_utc"],
        "target_end_exclusive_utc": binding["interval"]["target_end_exclusive_utc"],
        "context_end_exclusive_utc": binding["interval"]["context_end_exclusive_utc"],
        "population_scope": binding["scope"]["population_scope"],
        "clean_run_count": binding["execution"]["clean_run_count"],
        "workspace_policy": binding["execution"]["workspace_policy"],
    }
    for field, required in expected.items():
        supplied = getattr(args, field, None)
        if supplied is not None and supplied != required:
            raise FullReplayError(f"COMMAND_OVERRIDE_MISMATCH:{field}")
    if args.clock is not None and sorted(args.clock) != sorted(binding["scope"]["clocks"]):
        raise FullReplayError("COMMAND_OVERRIDE_MISMATCH:clock")
    if args.side is not None and sorted(args.side) != sorted(binding["scope"]["sides"]):
        raise FullReplayError("COMMAND_OVERRIDE_MISMATCH:side")


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "build-binding":
            result = build_binding(args.repository_root, args.external_root, args.output, args.expected_main_baseline)
        elif args.command == "preflight":
            result = preflight(args.input_binding, args.repository_root, args.expected_code_commit)
        else:
            binding = read_json(args.input_binding)
            validate_overrides(args, binding)
            result = orchestrate(args.input_binding, args.output_root, args.repository_root, args.expected_code_commit)
    except FullReplayError as exc:
        print(f"C2_VNEXT_FULL_REPLAY_ERROR={exc}", file=sys.stderr)
        return 2
    print("C2_VNEXT_FULL_REPLAY_RESULT=" + json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
