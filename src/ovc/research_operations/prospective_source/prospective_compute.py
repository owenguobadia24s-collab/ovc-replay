from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ovc.opt_b.c1.builder import build as build_c1
from ovc.opt_b.c1.formulas import FORMULA_REGISTRY_ID
from ovc.opt_b.c1.serialization import to_dict as c1_to_dict
from ovc.opt_b.c2.engine import C2ScopeEngine
from ovc.opt_b.c2.replay import FirstValidParentResolver

from . import dukascopy_intake as intake
from .aggregation import aggregate_m1
from .binding import ACTIVE_C2_RELEASE, build_replay_binding, validate_non_activating
from .models import ProspectiveBar, SourceBar, canonical_hash, parse_utc


SLICE_ID = "RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1"
SOURCE_START = "2026-06-22T00:00:00Z"
SOURCE_END = "2026-06-25T00:00:00Z"
SOURCE_MANIFEST_LOGICAL_SHA256 = (
    "429b7b568b7a43d04893c1873773f0b1b567730f2d5d4122d6a1c06dd40e3e41"
)
SOURCE_MANIFEST_FILE_SHA256 = (
    "8509b6cc66814663786e429e6ba1dc0c3497482fc6ac8ceb016cfc1867ec78eb"
)
RPS_G2_MERGE = "dde4ce967b65f373db9c3150a92d93b02326047a"
AUTHORITY_GATE = "RPS-G2"
OPERATION_MODE = "TIME_GATED_REPLAY"
DERIVED_AUTHORITY = "TIME_GATED_REPLAY_DERIVED"
PRICE_SET_ID = "RPS.PRICESET.GBPUSD.20260622_20260625.v1"
SOURCE_MANIFEST_ID = f"RPS.SOURCE-MANIFEST.{SOURCE_MANIFEST_LOGICAL_SHA256[:24]}"
C1_SET_ID = "RPS.C1SET.GBPUSD.20260622_20260625.v1"
C1_MANIFEST_ID = f"RPS.C1MANIFEST.{canonical_hash({'source': SOURCE_MANIFEST_LOGICAL_SHA256, 'formula': FORMULA_REGISTRY_ID})[:24]}"
EXPANDED_OUTPUT_LIMIT = 100 * 1024 * 1024
EXPECTED_COUNTS = {
    "15M": {"total": 288, "complete": 271, "unavailable": 17},
    "2H_A_L": {"total": 36, "complete": 30, "unavailable": 6},
}


class ComputeError(RuntimeError):
    pass


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def logical_sha(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ComputeError(f"refusing to overwrite derived evidence: {path}")
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, values: Iterable[Mapping[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ComputeError(f"refusing to overwrite derived output: {path}")
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for value in values:
            handle.write(
                json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
            )
            count += 1
    return count


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
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ComputeError("unable to resolve repository state") from exc
    if branch != "main":
        raise ComputeError("RPS-WP3 local execution requires the main branch")
    if changes:
        raise ComputeError("RPS-WP3 local execution requires a clean tracked worktree")
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise ComputeError("invalid repository commit identity")
    return branch, commit


def external_root(repository_root: Path, environ: Mapping[str, str]) -> Path:
    try:
        return intake._resolve_root(repository_root, environ)
    except intake.IntakeError as exc:
        raise ComputeError(str(exc)) from exc


def evidence_index_path(repository_root: Path) -> Path:
    return (
        repository_root
        / "docs"
        / "releases"
        / "prospective-source-v0-1"
        / "rps-wp2"
        / "RPS_WP2_COMPACT_EVIDENCE_INDEX.json"
    )


def load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ComputeError(f"{code}:{path}") from exc
    if not isinstance(value, dict):
        raise ComputeError(f"{code}:{path}")
    return value


def load_evidence_index(repository_root: Path) -> dict[str, Any]:
    value = load_json(evidence_index_path(repository_root), "INVALID_EVIDENCE_INDEX")
    if value.get("slice_id") != SLICE_ID:
        raise ComputeError("evidence index slice identity mismatch")
    if value.get("coverage_state") != "GAPPED":
        raise ComputeError("evidence index coverage state mismatch")
    if value.get("manifest_logical_sha256") != SOURCE_MANIFEST_LOGICAL_SHA256:
        raise ComputeError("evidence index manifest logical hash mismatch")
    if value.get("manifest_file_sha256") != SOURCE_MANIFEST_FILE_SHA256:
        raise ComputeError("evidence index manifest file hash mismatch")
    return value


def safe_file(root: Path, relative: str) -> Path:
    candidate = root / Path(relative)
    if candidate.is_symlink() or not candidate.is_file():
        raise ComputeError(f"required regular source file unavailable: {relative}")
    resolved_root = root.resolve(strict=True)
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ComputeError(f"source file escapes frozen slice: {relative}") from exc
    return resolved


def verify_frozen_source(
    repository_root: Path,
    environ: Mapping[str, str],
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    index = load_evidence_index(repository_root)
    root = external_root(repository_root, environ) / "prospective-source" / "intake" / SLICE_ID
    if not root.is_dir():
        raise ComputeError(f"accepted frozen source slice unavailable: {root}")

    compact = {item["name"]: item for item in index["compact_files"]}
    for name, item in compact.items():
        relative = name if name == "source-slice-manifest.json" else f"receipts/{name}"
        path = safe_file(root, relative)
        if path.stat().st_size != int(item["size_bytes"]):
            raise ComputeError(f"compact evidence size mismatch: {name}")
        if sha_file(path) != item["sha256"]:
            raise ComputeError(f"compact evidence SHA-256 mismatch: {name}")

    manifest_path = safe_file(root, "source-slice-manifest.json")
    manifest = load_json(manifest_path, "INVALID_SOURCE_MANIFEST")
    logical = dict(manifest)
    claimed = logical.pop("manifest_sha256", None)
    if claimed != logical_sha(logical) or claimed != SOURCE_MANIFEST_LOGICAL_SHA256:
        raise ComputeError("source manifest logical SHA-256 mismatch")
    if sha_file(manifest_path) != SOURCE_MANIFEST_FILE_SHA256:
        raise ComputeError("source manifest file SHA-256 mismatch")
    required_manifest = {
        "slice_id": SLICE_ID,
        "coverage_state": "GAPPED",
        "frozen": True,
        "release_status": "NOT_A_RELEASE",
        "selector_eligibility": "NONE",
        "r2_publication": "DENIED",
        "source_window_start_utc": SOURCE_START,
        "source_window_end_utc": SOURCE_END,
    }
    for key, expected in required_manifest.items():
        if manifest.get(key) != expected:
            raise ComputeError(f"source manifest authority mismatch: {key}")

    inventory = load_json(
        safe_file(root, "receipts/source-object-inventory.json"),
        "INVALID_SOURCE_OBJECT_INVENTORY",
    )
    if inventory.get("slice_id") != SLICE_ID or inventory.get("source_object_count") != 4:
        raise ComputeError("source-object inventory identity mismatch")
    expected = {
        item["object_id"]: item
        for item in index["source_objects"]
    }
    observed = {
        item["object_id"]: item
        for item in inventory.get("source_objects", [])
    }
    if set(observed) != set(expected):
        raise ComputeError("source-object identity inventory mismatch")
    for object_id, item in expected.items():
        actual = observed[object_id]
        for field in (
            "clock",
            "side",
            "relative_path",
            "row_count",
            "size_bytes",
            "sha256",
            "schema_fingerprint",
            "first_timestamp_utc",
            "last_timestamp_utc",
        ):
            if actual.get(field) != item.get(field):
                raise ComputeError(f"source-object metadata mismatch: {object_id}:{field}")
        path = safe_file(root, str(item["relative_path"]))
        if path.stat().st_size != int(item["size_bytes"]):
            raise ComputeError(f"source-object size mismatch: {object_id}")
        if sha_file(path) != item["sha256"]:
            raise ComputeError(f"source-object SHA-256 mismatch: {object_id}")
    return root, index, inventory


def parse_m1(
    source_root: Path,
    item: Mapping[str, Any],
) -> list[SourceBar]:
    path = safe_file(source_root, str(item["relative_path"]))
    side = str(item["side"])
    source_object_id = str(item["object_id"])
    result: list[SourceBar] = []
    previous: datetime | None = None
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != intake.ORDERED_COLUMNS:
                raise ComputeError(f"unexpected source CSV columns: {path}")
            for row_number, row in enumerate(reader, 2):
                try:
                    timestamp_ms = int(row["timestamp"])
                    timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
                    values = {
                        name: Decimal(str(row[name]))
                        for name in ("open", "high", "low", "close", "volume")
                    }
                except (ValueError, InvalidOperation, TypeError, KeyError) as exc:
                    raise ComputeError(f"invalid M1 row:{path}:{row_number}") from exc
                if previous is not None and timestamp <= previous:
                    raise ComputeError(f"non-monotonic M1 row:{path}:{row_number}")
                if values["volume"] < 0:
                    raise ComputeError(f"negative M1 volume:{path}:{row_number}")
                if values["high"] < max(values["open"], values["close"]):
                    raise ComputeError(f"invalid M1 high:{path}:{row_number}")
                if values["low"] > min(values["open"], values["close"]):
                    raise ComputeError(f"invalid M1 low:{path}:{row_number}")
                identity = {
                    "source_object_id": source_object_id,
                    "timestamp_ms": timestamp_ms,
                    "side": side,
                }
                result.append(
                    SourceBar(
                        object_id=f"RPS.M1BAR.{canonical_hash(identity)[:24]}",
                        timestamp_utc=utc(timestamp),
                        side=side,
                        open=values["open"],
                        high=values["high"],
                        low=values["low"],
                        close=values["close"],
                        volume=values["volume"],
                    )
                )
                previous = timestamp
    except OSError as exc:
        raise ComputeError(f"unable to read M1 source object: {path}") from exc
    if len(result) != int(item["row_count"]):
        raise ComputeError(f"M1 row-count mismatch: {source_object_id}")
    if not result:
        raise ComputeError(f"empty M1 source object: {source_object_id}")
    if result[0].timestamp_utc != item["first_timestamp_utc"]:
        raise ComputeError(f"M1 first timestamp mismatch: {source_object_id}")
    if result[-1].timestamp_utc != item["last_timestamp_utc"]:
        raise ComputeError(f"M1 last timestamp mismatch: {source_object_id}")
    return result


def build_bars(
    source_root: Path,
    inventory: Mapping[str, Any],
) -> tuple[dict[tuple[str, str], list[ProspectiveBar]], dict[str, str]]:
    m1_items = {
        str(item["side"]): item
        for item in inventory["source_objects"]
        if item["clock"] == "M1"
    }
    if set(m1_items) != {"BID", "ASK"}:
        raise ComputeError("exact M1 BID/ASK source objects are required")
    built: dict[tuple[str, str], list[ProspectiveBar]] = {}
    source_object_ids = {
        side: str(item["object_id"])
        for side, item in m1_items.items()
    }
    for side in ("BID", "ASK"):
        rows = parse_m1(source_root, m1_items[side])
        for clock in ("15M", "2H_A_L"):
            bars = aggregate_m1(
                rows,
                clock=clock,
                side=side,
                admissible_cutoff_utc=SOURCE_END,
            )
            expected = EXPECTED_COUNTS[clock]
            complete = sum(item.quality_state == "COMPLETE" for item in bars)
            unavailable = sum(
                item.quality_state == "QUARANTINED_INCOMPLETE_PARENT_SET"
                for item in bars
            )
            if (
                len(bars) != expected["total"]
                or complete != expected["complete"]
                or unavailable != expected["unavailable"]
            ):
                raise ComputeError(
                    f"coverage propagation mismatch:{clock}:{side}:"
                    f"{len(bars)}:{complete}:{unavailable}"
                )
            built[(clock, side)] = bars
    return built, source_object_ids


def prospective_price_payload(
    bar: ProspectiveBar,
    source_object_id: str,
) -> dict[str, Any]:
    if bar.quality_state != "COMPLETE" or None in (
        bar.open,
        bar.high,
        bar.low,
        bar.close,
        bar.volume,
    ):
        raise ComputeError("incomplete parent cannot enter C1")
    source_bar_id = f"rps-price:{canonical_hash(bar.logical_dict())}"
    return {
        "operation_mode": OPERATION_MODE,
        "release_id": PRICE_SET_ID,
        "manifest_id": SOURCE_MANIFEST_ID,
        "research_role": "DISCOVERY",
        "instrument_id": "GBPUSD",
        "clock_id": bar.clock,
        "price_side": bar.side,
        "source_bar_id": source_bar_id,
        "open_time": bar.start_utc,
        "close_time": bar.end_utc,
        "first_valid_time": bar.end_utc,
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
        "price_increment": "0.00001",
        "admissibility": "HANDOFF_ELIGIBLE",
        "quality_state": "COMPLETE",
        "synthetic": False,
        "selector_state": "NONE",
        "authority_state": DERIVED_AUTHORITY,
        "validation_consumption_state": "DENIED",
        "release_membership": False,
        "parent_source_object_ids": [source_object_id],
        "parent_m1_bar_ids": list(bar.parent_source_object_ids),
    }


def build_c1_records(
    bars: Sequence[ProspectiveBar],
    source_object_id: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    prior_payload: dict[str, Any] | None = None
    for bar in sorted(bars, key=lambda item: item.start_utc):
        if bar.quality_state != "COMPLETE":
            continue
        current = prospective_price_payload(bar, source_object_id)
        result = build_c1(current, prior_payload)
        c1 = c1_to_dict(result)
        joined = {
            "c1_record_id": c1["record_id"],
            "c1_release_id": C1_SET_ID,
            "c1_manifest_id": C1_MANIFEST_ID,
            "opt_a_release_id": PRICE_SET_ID,
            "opt_a_manifest_id": SOURCE_MANIFEST_ID,
            "opt_a_manifest_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
            "role": "DISCOVERY",
            "authority_state": DERIVED_AUTHORITY,
            "instrument": "GBPUSD",
            "clock": bar.clock,
            "side": bar.side,
            "open_time": bar.start_utc,
            "close_time": bar.end_utc,
            "first_valid_time": bar.end_utc,
            "source_path": f"prospective-bars/{bar.clock}/{bar.side}/{bar.bar_id}",
            "source_bar_id": current["source_bar_id"],
            "measurements": c1["measurements"],
            "categorical": c1["categorical"],
            "null_reasons": c1["null_reasons"],
            "quality_state": "COMPLETE",
            "prices": {
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
            },
            "formula_registry_id": FORMULA_REGISTRY_ID,
            "source_slice_id": SLICE_ID,
            "source_manifest_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
            "parent_m1_bar_ids": list(bar.parent_source_object_ids),
            "operation_mode": OPERATION_MODE,
            "release_membership": False,
            "selector_eligibility": "NONE",
            "r2_publication": "DENIED",
            "validation_consumption": "DENIED",
            "live_prospective_append": "DENIED",
        }
        records.append(joined)
        prior_payload = current
    return records


def process_scope(
    records: Sequence[Mapping[str, Any]],
    *,
    scope: str,
    parent_resolver: FirstValidParentResolver | None = None,
    collect_levels: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[tuple[str, tuple[dict[str, Any], ...]]]]:
    engine = C2ScopeEngine(scope)
    states: list[dict[str, Any]] = []
    transitions: list[dict[str, Any]] = []
    snapshots: list[tuple[str, tuple[dict[str, Any], ...]]] = []
    for record in records:
        result = engine.process(
            record,
            parent_levels=parent_resolver(record) if parent_resolver else (),
        )
        state = dict(result.state)
        state.update(
            {
                "role": "DISCOVERY",
                "active_c2_model_release_id": ACTIVE_C2_RELEASE,
                "operation_mode": OPERATION_MODE,
                "source_slice_id": SLICE_ID,
                "release_membership": False,
                "live_prospective_append": "DENIED",
            }
        )
        states.append(state)
        if result.transition is not None:
            transition = dict(result.transition)
            transition.update(
                {
                    "role": "DISCOVERY",
                    "clock": record["clock"],
                    "side": record["side"],
                    "evaluation_scope_id": scope,
                    "active_c2_model_release_id": ACTIVE_C2_RELEASE,
                    "operation_mode": OPERATION_MODE,
                    "source_slice_id": SLICE_ID,
                    "release_membership": False,
                    "live_prospective_append": "DENIED",
                }
            )
            transitions.append(transition)
        if collect_levels:
            snapshots.append((str(state["first_valid_time"]), result.levels))
    return states, transitions, snapshots


def build_c2_outputs(
    c1: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]],
) -> dict[tuple[str, str, str], tuple[list[dict[str, Any]], list[dict[str, Any]]]]:
    outputs: dict[
        tuple[str, str, str],
        tuple[list[dict[str, Any]], list[dict[str, Any]]],
    ] = {}
    for side in ("BID", "ASK"):
        two_h_scope = "GBPUSD-2H-A-L-LOCAL-v0.1"
        states, transitions, snapshots = process_scope(
            c1[("2H_A_L", side)],
            scope=two_h_scope,
            collect_levels=True,
        )
        outputs[("2H_A_L", side, two_h_scope)] = (states, transitions)

        local_scope = "GBPUSD-15M-LOCAL-v0.1"
        states, transitions, _ = process_scope(
            c1[("15M", side)],
            scope=local_scope,
        )
        outputs[("15M", side, local_scope)] = (states, transitions)

        combined_scope = "GBPUSD-15M-WITH-2H-PARENT-v0.1"
        states, transitions, _ = process_scope(
            c1[("15M", side)],
            scope=combined_scope,
            parent_resolver=FirstValidParentResolver(snapshots),
        )
        outputs[("15M", side, combined_scope)] = (states, transitions)
    return outputs


def file_inventory(root: Path, paths: Sequence[Path]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        result.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha_file(path),
            }
        )
    return result


def workspace_size(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def quarantine_staging(staging: Path, reason: str) -> Path | None:
    if not staging.exists():
        return None
    root = staging.parent / "quarantine"
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"RPS-WP3.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.{uuid.uuid4().hex[:8]}"
    try:
        write_json(
            staging / "failure-receipt.json",
            {
                "schema": "ovc-rps-wp3-compute-failure/v1",
                "slice_id": SLICE_ID,
                "reason": reason,
                "provider_network_access_performed": False,
                "release_mutation_performed": False,
                "live_prospective_append_performed": False,
            },
        )
    except Exception:
        pass
    staging.rename(target)
    return target


def preflight(
    repository_root: Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    branch, commit = repository_state(repository_root)
    source_root, index, inventory = verify_frozen_source(repository_root, values)
    compute_root = external_root(repository_root, values) / "prospective-source" / "compute"
    return {
        "status": "READY_FOR_LOCAL_DERIVED_COMPUTE",
        "authority_gate": AUTHORITY_GATE,
        "slice_id": SLICE_ID,
        "coverage_state": "GAPPED",
        "repository_branch": branch,
        "code_commit": commit,
        "source_manifest_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
        "source_object_count": inventory["source_object_count"],
        "m1_rows_per_side": index["accepted_source"] ["m1_rows_per_side"] if "accepted_source" in index else 4285,
        "admissible_cutoff_utc": SOURCE_END,
        "operation_mode": OPERATION_MODE,
        "provider_network_access_performed": False,
        "output_root_exists": compute_root.exists(),
        "source_root_verified": source_root.is_dir(),
        "release_status": "NOT_A_RELEASE",
        "selector_eligibility": "NONE",
        "r2_publication": "DENIED",
        "validation_consumption": "DENIED",
        "live_prospective_append": "DENIED",
    }


def execute(
    repository_root: Path,
    *,
    authority_gate: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    if authority_gate != AUTHORITY_GATE:
        raise ComputeError(f"exact delegated authority binding required: --gate {AUTHORITY_GATE}")
    if truthy(values.get("CI")) or truthy(values.get("GITHUB_ACTIONS")):
        raise ComputeError("RPS-WP3 external derived compute is prohibited in CI")
    _, code_commit = repository_state(repository_root)
    source_root, index, inventory = verify_frozen_source(repository_root, values)
    compute_root = external_root(repository_root, values) / "prospective-source" / "compute"
    compute_root.mkdir(parents=True, exist_ok=True)
    staging = compute_root / f".RPS-WP3.staging.{uuid.uuid4().hex}"
    staging.mkdir(parents=False, exist_ok=False)
    try:
        bars, source_object_ids = build_bars(source_root, inventory)
        data_paths: list[Path] = []
        for (clock, side), items in sorted(bars.items()):
            path = staging / "bars" / clock / f"{side}.jsonl"
            write_jsonl(path, [item.logical_dict() for item in items])
            data_paths.append(path)

        c1_records: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for (clock, side), items in sorted(bars.items()):
            records = build_c1_records(items, source_object_ids[side])
            expected = EXPECTED_COUNTS[clock]["complete"]
            if len(records) != expected:
                raise ComputeError(f"C1 complete-parent count mismatch:{clock}:{side}")
            c1_records[(clock, side)] = records
            path = staging / "c1" / clock / f"{side}.jsonl"
            write_jsonl(path, records)
            data_paths.append(path)

        c2_outputs = build_c2_outputs(c1_records)
        state_count = transition_count = 0
        for (clock, side, scope), (states, transitions) in sorted(c2_outputs.items()):
            slug = scope.replace(".", "_")
            state_path = staging / "c2" / "states" / clock / side / f"{slug}.jsonl"
            transition_path = staging / "c2" / "transitions" / clock / side / f"{slug}.jsonl"
            state_count += write_jsonl(state_path, states)
            transition_count += write_jsonl(transition_path, transitions)
            data_paths.extend((state_path, transition_path))

        coverage = {
            "schema": "ovc-rps-wp3-derived-coverage/v1",
            "slice_id": SLICE_ID,
            "coverage_state": "GAPPED",
            "results": [
                {
                    "clock": clock,
                    **EXPECTED_COUNTS[clock],
                    "incomplete_parent_policy": "EXCLUDE_NO_SYNTHESIS",
                }
                for clock in ("15M", "2H_A_L")
            ],
            "c1_record_count": sum(len(items) for items in c1_records.values()),
            "c2_state_count": state_count,
            "c2_transition_count": transition_count,
            "repair_performed": False,
            "forward_fill_performed": False,
            "interpolation_performed": False,
            "synthesis_performed": False,
            "incomplete_parent_consumption": "DENIED",
            "qa_state": "PASS_GAPPED_EXCLUSION",
        }
        coverage_path = staging / "qa" / "coverage.json"
        write_json(coverage_path, coverage)
        data_paths.append(coverage_path)

        payload_inventory = file_inventory(staging, data_paths)
        output_manifest_body = {
            "schema": "ovc-rps-wp3-output-manifest/v1",
            "slice_id": SLICE_ID,
            "source_manifest_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
            "operation_mode": OPERATION_MODE,
            "admissible_cutoff_utc": SOURCE_END,
            "active_c2_model_release_id": ACTIVE_C2_RELEASE,
            "code_commit": code_commit,
            "files": payload_inventory,
            "file_count": len(payload_inventory),
            "release_status": "NOT_A_RELEASE",
            "selector_eligibility": "NONE",
            "r2_publication": "DENIED",
            "validation_consumption": "DENIED",
            "live_prospective_append": "DENIED",
        }
        output_manifest_sha = logical_sha(output_manifest_body)
        output_manifest = {
            **output_manifest_body,
            "output_manifest_sha256": output_manifest_sha,
        }
        output_manifest_path = staging / "output-manifest.json"
        write_json(output_manifest_path, output_manifest)

        run_identity = {
            "slice_id": SLICE_ID,
            "source_manifest_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
            "code_commit": code_commit,
            "operation_mode": OPERATION_MODE,
            "admissible_cutoff_utc": SOURCE_END,
            "output_manifest_sha256": output_manifest_sha,
        }
        run_id = f"RPS.RUN.{canonical_hash(run_identity)[:24]}"
        compute_run = {
            "run_id": run_id,
            "source_slice_id": SLICE_ID,
            "source_manifest_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
            "code_commit": code_commit,
            "operation_mode": OPERATION_MODE,
            "admissible_cutoff_utc": SOURCE_END,
            "output_manifest_sha256": output_manifest_sha,
            "status": "COMPLETE",
        }
        compute_run_path = staging / "prospective-compute-run.json"
        write_json(compute_run_path, compute_run)

        binding = build_replay_binding(
            source_slice_id=SLICE_ID,
            source_manifest_sha256=SOURCE_MANIFEST_LOGICAL_SHA256,
            compute_run_id=run_id,
            eligible_data_through_utc=SOURCE_END,
            deterministic_replay=True,
            lineage_complete=True,
            gap_state="GAPPED_EXPLICIT_INCOMPLETE_PARENT_EXCLUSION",
        )
        validate_non_activating(binding)
        binding_value = {
            **binding.as_dict(),
            "operation_mode": OPERATION_MODE,
            "source_coverage_state": "GAPPED",
            "status": "ACCEPTED_FOR_REPLAY_CANDIDATE",
            "live_prospective_append": "DENIED",
            "active_research_triage": False,
            "write_authority": False,
        }
        binding_path = staging / "prospective-source-binding.json"
        write_json(binding_path, binding_value)

        receipt = {
            "schema": "ovc-rps-wp3-compute-receipt/v1",
            "run_id": run_id,
            "binding_id": binding.binding_id,
            "slice_id": SLICE_ID,
            "source_manifest_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
            "output_manifest_sha256": output_manifest_sha,
            "output_manifest_file_sha256": sha_file(output_manifest_path),
            "compute_run_file_sha256": sha_file(compute_run_path),
            "binding_file_sha256": sha_file(binding_path),
            "code_commit": code_commit,
            "operation_mode": OPERATION_MODE,
            "admissible_cutoff_utc": SOURCE_END,
            "c1_record_count": coverage["c1_record_count"],
            "c2_state_count": state_count,
            "c2_transition_count": transition_count,
            "deterministic_replay": True,
            "lineage_complete": True,
            "provider_network_access_performed": False,
            "release_status": "NOT_A_RELEASE",
            "selector_eligibility": "NONE",
            "r2_publication": "DENIED",
            "validation_consumption": "DENIED",
            "live_prospective_append": "DENIED",
            "active_research_triage": False,
            "write_authority": False,
            "status": "COMPLETE_LOCAL_CANDIDATE",
        }
        receipt_path = staging / "compute-receipt.json"
        write_json(receipt_path, receipt)

        if workspace_size(staging) > EXPANDED_OUTPUT_LIMIT:
            raise ComputeError("RPS-WP3 expanded output limit exceeded")
        final = compute_root / run_id
        if final.exists():
            raise ComputeError(f"refusing to overwrite existing compute run: {final}")
        staging.rename(final)
        return {
            "status": "COMPLETE_LOCAL_PROSPECTIVE_COMPUTE_CANDIDATE",
            "run_id": run_id,
            "binding_id": binding.binding_id,
            "slice_id": SLICE_ID,
            "source_manifest_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
            "output_manifest_sha256": output_manifest_sha,
            "code_commit": code_commit,
            "operation_mode": OPERATION_MODE,
            "coverage_state": "GAPPED",
            "c1_record_count": coverage["c1_record_count"],
            "c2_state_count": state_count,
            "c2_transition_count": transition_count,
            "provider_network_access_performed": False,
            "release_status": "NOT_A_RELEASE",
            "selector_eligibility": "NONE",
            "r2_publication": "DENIED",
            "validation_consumption": "DENIED",
            "live_prospective_append": "DENIED",
            "active_research_triage": False,
            "write_authority": False,
        }
    except Exception as exc:
        quarantined = quarantine_staging(staging, str(exc))
        suffix = f"; staging quarantined at {quarantined}" if quarantined else ""
        if isinstance(exc, ComputeError):
            raise ComputeError(str(exc) + suffix) from exc
        raise ComputeError(f"unexpected RPS-WP3 compute failure: {exc}{suffix}") from exc


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Operator-local RPS-WP3 derived 15M/2H C1/C2 compute and exact source binding."
    )
    result.add_argument("command", choices=("preflight", "execute"))
    result.add_argument("--repository-root", type=Path, default=Path.cwd())
    result.add_argument("--gate", default=None)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        repository_root = arguments.repository_root.resolve(strict=True)
        if arguments.command == "preflight":
            result = preflight(repository_root)
        else:
            result = execute(
                repository_root,
                authority_gate=arguments.gate or "",
            )
    except ComputeError as exc:
        print(f"RPS-WP3 compute blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
