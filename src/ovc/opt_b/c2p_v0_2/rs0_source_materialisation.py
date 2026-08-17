from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
import csv
from datetime import datetime, timedelta, timezone
import gc
import gzip
from hashlib import sha256
import json
from pathlib import Path
import resource
from typing import Any, Iterable, Iterator, Mapping

from ovc.opt_b.c2_vnext import real_source_materialisation as c2rm
from ovc.opt_b.c2e_v2 import source_replay as c2e
from ovc.opt_b.c2e_v2.candidate import build_candidate
from ovc.opt_b.c2e_v2.lifecycle import EpisodeEngine
from ovc.opt_b.c2e_v2.models import build_record
from ovc.opt_b.c2e_v2.resolver import resolve_candidates
from ovc.opt_b.c2e_v2.stream import AppendOnlyStream, StreamError

SCHEMA = "ovc-c2p2-rs0-current-source-materialisation/v1"
LOCATOR_SCHEMA = "ovc-c2p2-rs0-source-locator/v1"
ROW_SCHEMA = "ovc-c2p2-rs0-source-row/v1"
PROGRAMME_ID = "OVC-C2P2-RS0-SHADOW-EVIDENCE-v0.1"
PACKET_ID = "C2P2-RS0-CURRENT-SOURCE-MATERIALISATION"
MATERIALISATION_ID = "C2P2.RS0.CURRENT.C2VNEXT.C2E.2021_2023.v1"

TARGET_START = "2021-01-01T00:00:00Z"
TARGET_END = "2024-01-01T00:00:00Z"
INTERVAL = "[2021-01-01T00:00:00Z,2024-01-01T00:00:00Z)"
INSTRUMENT = "GBPUSD"
SIDES = ("BID", "ASK")
CLOCKS = ("15M", "2H_A_L")

C1_RELEASE_ID = "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2"
C1_MANIFEST_ID = "MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2.r1"
C1_SOURCE_COMMIT = "f30efb0ef8b72cb2e43ccb242c479932a6ee8387"
C1_IMPLEMENTATION_ID = "C1.IMPLEMENTATION.v0.2"
OPT_A_RELEASE_ID = "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2"
OPT_A_MANIFEST_ID = "MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r2"
OPT_A_MANIFEST_SHA256 = "0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c"
OPT_A_SOURCE_COMMIT = "8c4c6c70da6f3f8b400d06df990500702813ff39"

C2_PACKAGE_ID = "C2AR.INTEGRATED.SHADOW.PACKAGE.v1"
C2_PACKAGE_SHA256 = "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3"
C2E_BOUNDARY_PACK_ID = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
C2E_BOUNDARY_PACK_SHA256 = "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"

PEAK_MEMORY_LIMIT_BYTES = 1_160_593_408
EXTERNAL_STORAGE_LIMIT_BYTES = 6_411_935_744


class RS0SourceMaterialisationError(RuntimeError):
    pass


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise RS0SourceMaterialisationError(marker)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def hash_obj(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value * 1024 if value < 10_000_000_000 else value


def enforce_capacity(stage: str) -> None:
    rss = peak_rss_bytes()
    if rss > PEAK_MEMORY_LIMIT_BYTES:
        raise RS0SourceMaterialisationError(
            f"CAPACITY_EXCEEDED:{stage}:peak_rss_bytes={rss}:limit={PEAK_MEMORY_LIMIT_BYTES}"
        )


def _parse_ms(value: Any) -> datetime:
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _duration(clock: str) -> timedelta:
    if clock == "15M":
        return timedelta(minutes=15)
    if clock == "2H_A_L":
        return timedelta(hours=2)
    raise RS0SourceMaterialisationError(f"UNSUPPORTED_CLOCK:{clock}")


def _load_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _manifest_index(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["path"]): dict(row) for row in rows}


def verify_artifact_roots(c1_root: Path, opt_a_root: Path) -> dict[str, Any]:
    c1_descriptor = _load_json(c1_root / "release-descriptor.json")
    _require(c1_descriptor.get("release_id") == C1_RELEASE_ID, "C1_RELEASE_ID_DRIFT")
    _require(c1_descriptor.get("manifest_id") == C1_MANIFEST_ID, "C1_MANIFEST_ID_DRIFT")
    _require(c1_descriptor.get("source_commit") == C1_SOURCE_COMMIT, "C1_SOURCE_COMMIT_DRIFT")
    _require(c1_descriptor.get("implementation_id") == C1_IMPLEMENTATION_ID, "C1_IMPLEMENTATION_ID_DRIFT")
    _require(c1_descriptor.get("role") == "DISCOVERY", "C1_ROLE_DRIFT")
    _require(c1_descriptor.get("validation_consumption") == "LOCKED_UNCONSUMED", "C1_VALIDATION_STATE_DRIFT")

    c1_manifest = _load_json(c1_root / "manifest.json")
    _require(int(c1_manifest.get("file_count", -1)) == 144, "C1_FILE_COUNT_DRIFT")
    c1_files = _manifest_index(c1_manifest.get("files", []))
    relevant_c1 = {
        path: meta for path, meta in c1_files.items()
        if path.startswith("records/15M/") or path.startswith("records/2H_A_L/")
    }
    _require(len(relevant_c1) == 144, "C1_RELEVANT_FILE_COUNT_DRIFT")

    opt_a_descriptor = _load_json(opt_a_root / "release-descriptor.json")
    _require(opt_a_descriptor.get("release_id") == OPT_A_RELEASE_ID, "OPT_A_RELEASE_ID_DRIFT")
    _require(opt_a_descriptor.get("source_commit") == OPT_A_SOURCE_COMMIT, "OPT_A_SOURCE_COMMIT_DRIFT")
    _require(opt_a_descriptor.get("role") == "DISCOVERY", "OPT_A_ROLE_DRIFT")
    _require(opt_a_descriptor.get("lifecycle_state") == "RELEASE_FROZEN", "OPT_A_FREEZE_STATE_DRIFT")

    opt_a_inventory = _load_json(opt_a_root / "release-inventory.json")
    opt_a_files = _manifest_index(opt_a_inventory.get("files", []))
    relevant_opt_a = {
        path: meta for path, meta in opt_a_files.items()
        if path.startswith("canonical/15M/") or path.startswith("canonical/2H_A_L/")
    }
    _require(len(relevant_opt_a) == 144, "OPT_A_RELEVANT_FILE_COUNT_DRIFT")
    return {
        "c1_descriptor": c1_descriptor,
        "c1_manifest": c1_manifest,
        "c1_files": relevant_c1,
        "opt_a_descriptor": opt_a_descriptor,
        "opt_a_inventory": opt_a_inventory,
        "opt_a_files": relevant_opt_a,
    }


def _verify_file(path: Path, expected: Mapping[str, Any], marker: str) -> None:
    _require(path.is_file(), f"{marker}_MISSING:{path}")
    _require(path.stat().st_size == int(expected["size_bytes"]), f"{marker}_SIZE_DRIFT:{path}")
    _require(hash_file(path) == str(expected["sha256"]), f"{marker}_HASH_DRIFT:{path}")


def hydrate_rows(
    c1_root: Path,
    opt_a_root: Path,
    indexes: Mapping[str, Any],
    *,
    side: str,
    clock: str,
) -> list[dict[str, Any]]:
    prefix = f"records/{clock}/{side}/"
    c1_items = sorted((path, meta) for path, meta in indexes["c1_files"].items() if path.startswith(prefix))
    _require(len(c1_items) == 36, f"C1_MONTH_SHARD_COUNT_DRIFT:{clock}:{side}:{len(c1_items)}")
    result: list[dict[str, Any]] = []
    observed_record_count = 0
    for c1_rel, c1_meta in c1_items:
        c1_path = c1_root / c1_rel
        _verify_file(c1_path, c1_meta, "C1_SHARD")
        with gzip.open(c1_path, "rt", encoding="utf-8") as handle:
            c1_rows = [json.loads(line) for line in handle if line.strip()]
        _require(len(c1_rows) == int(c1_meta["record_count"]), f"C1_SHARD_RECORD_COUNT_DRIFT:{c1_rel}")
        _require(bool(c1_rows), f"C1_SHARD_EMPTY:{c1_rel}")
        source_paths = {str(row.get("source_path")) for row in c1_rows}
        _require(len(source_paths) == 1, f"C1_SOURCE_PATH_MULTIPLE:{c1_rel}")
        opt_a_rel = next(iter(source_paths))
        _require(opt_a_rel in indexes["opt_a_files"], f"OPT_A_PARENT_NOT_IN_INVENTORY:{opt_a_rel}")
        opt_a_path = opt_a_root / opt_a_rel
        _verify_file(opt_a_path, indexes["opt_a_files"][opt_a_rel], "OPT_A_SHARD")
        with opt_a_path.open("r", encoding="utf-8", newline="") as handle:
            price_rows = {int(row["timestamp"]): row for row in csv.DictReader(handle)}
        _require(len(price_rows) == len(c1_rows), f"C1_OPT_A_ROW_COUNT_MISMATCH:{c1_rel}")
        for c1_row in c1_rows:
            _require(c1_row.get("schema") == "ovc-c1-bar-primitives/v0.1", "C1_ROW_SCHEMA_DRIFT")
            _require(c1_row.get("instrument") == INSTRUMENT, "C1_INSTRUMENT_DRIFT")
            _require(c1_row.get("price_side") == side, "C1_SIDE_DRIFT")
            _require(c1_row.get("clock") == clock, "C1_CLOCK_DRIFT")
            _require(c1_row.get("role") == "DISCOVERY", "C1_ROW_ROLE_DRIFT")
            _require(c1_row.get("parent_release_id") == OPT_A_RELEASE_ID, "C1_PARENT_RELEASE_DRIFT")
            _require(c1_row.get("parent_manifest_id") == OPT_A_MANIFEST_ID, "C1_PARENT_MANIFEST_ID_DRIFT")
            _require(c1_row.get("parent_manifest_sha256") == OPT_A_MANIFEST_SHA256, "C1_PARENT_MANIFEST_HASH_DRIFT")
            timestamp_ms = int(c1_row["timestamp_ms"])
            price_row = price_rows.get(timestamp_ms)
            _require(price_row is not None, f"OPT_A_TIMESTAMP_NOT_FOUND:{c1_rel}:{timestamp_ms}")
            open_time_dt = _parse_ms(timestamp_ms)
            close_time_dt = open_time_dt + _duration(clock)
            open_time = _iso(open_time_dt)
            close_time = _iso(close_time_dt)
            _require(TARGET_START <= open_time < TARGET_END, f"C1_ROW_OUTSIDE_FROZEN_INTERVAL:{open_time}")
            result.append({
                "open_time": open_time,
                "close_time": close_time,
                "clock": clock,
                "side": side,
                "c1_record_id": str(c1_row["record_id"]),
                "opt_a_release_id": OPT_A_RELEASE_ID,
                "source_bar_id": str(c1_row["source_bar_id"]),
                "c1_release_id": C1_RELEASE_ID,
                "quality_state": "COMPLETE",
                "prices": {
                    "open": str(price_row["open"]),
                    "high": str(price_row["high"]),
                    "low": str(price_row["low"]),
                    "close": str(price_row["close"]),
                },
                "target_eligible": True,
                "source_path": opt_a_rel,
                "source_manifest_sha256": OPT_A_MANIFEST_SHA256,
            })
            observed_record_count += 1
    result.sort(key=lambda row: (row["open_time"], row["c1_record_id"]))
    _require(observed_record_count == sum(int(meta["record_count"]) for _, meta in c1_items), "C1_RECORD_TOTAL_DRIFT")
    return result


@contextmanager
def _c2_scope():
    overrides = {
        "CONTEXT_START": TARGET_START,
        "CONTEXT_END": TARGET_END,
        "TARGET_START": TARGET_START,
        "TARGET_END": TARGET_END,
        "INSTRUMENT": INSTRUMENT,
        "PARTITION_ID": MATERIALISATION_ID,
        "C1_RELEASE_ID": C1_RELEASE_ID,
        "C1_MANIFEST_ID": C1_MANIFEST_ID,
        "SOURCE_SLICE_ID": OPT_A_RELEASE_ID,
        "SOURCE_MANIFEST_SHA256": OPT_A_MANIFEST_SHA256,
        "MATERIALISATION_ID": MATERIALISATION_ID,
    }
    original = {key: getattr(c2rm, key) for key in overrides}
    try:
        for key, value in overrides.items():
            setattr(c2rm, key, value)
        yield
    finally:
        for key, value in original.items():
            setattr(c2rm, key, value)


def build_current_c2_side(side: str, rows15: list[dict[str, Any]], rows2h: list[dict[str, Any]]) -> dict[str, Any]:
    with _c2_scope():
        result = c2rm.build_side(side, rows15, rows2h)
    enforce_capacity(f"C2_VNEXT_BUILD_{side}")
    return result


def _dedupe_profiles(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = dict(raw)
        identity = str(row["profile_output_id"])
        if identity in output:
            _require(canonical_bytes(output[identity]) == canonical_bytes(row), f"PROFILE_ID_CONTENT_COLLISION:{identity}")
        output[identity] = row
    return output


def _side_materialisation(side_data: Mapping[str, Any]) -> dict[str, Any]:
    bundles = [dict(row) for row in side_data["bundles"] if row.get("target_eligible") is True]
    bundles.sort(key=lambda row: (row["first_valid_time"], row["observation_id"]))
    digest = sha256()
    for row in bundles:
        digest.update(canonical_bytes(row)); digest.update(b"\n")
    target_hash = digest.hexdigest()
    manifest_seed = {
        "schema": "ovc-c2p2-rs0-c2-vnext-side-manifest/v1",
        "materialisation_id": MATERIALISATION_ID,
        "side": side_data["side"],
        "c1_release_id": C1_RELEASE_ID,
        "opt_a_release_id": OPT_A_RELEASE_ID,
        "c2_package_id": C2_PACKAGE_ID,
        "c2_package_sha256": C2_PACKAGE_SHA256,
        "target_bundles_sha256": target_hash,
        "target_bundle_count": len(bundles),
        "interval": INTERVAL,
    }
    logical_sha = hash_obj(manifest_seed)
    return {
        "manifest": {**manifest_seed, "logical_sha256": logical_sha, "files": {"target_bundles": {"sha256": target_hash}}},
        "bundles": bundles,
        "observations": {row["observation_id"]: row for row in side_data["complete15"]},
        "parent_observations": {row["observation_id"]: row for row in side_data["complete2h"]},
        "profiles": _dedupe_profiles(side_data["profiles"]),
        "memberships": {row["membership_id"]: row for row in side_data["memberships"]},
        "contexts": {row["bundle_id"]: row for row in side_data["contexts"]},
        "levels": {row["level_id"]: row for row in side_data["levels"]},
        "containers": {row["container_id"]: row for row in side_data["containers"]},
        "relation_sets": {row["relation_set_id"]: row for row in side_data["relation_sets"]},
    }


def _writer(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("wb")
    digest = sha256()
    state = {"count": 0}
    def write(row: Mapping[str, Any]) -> None:
        data = canonical_bytes(dict(row)) + b"\n"
        handle.write(data); digest.update(data); state["count"] += 1
    def close() -> dict[str, Any]:
        handle.close()
        return {"relative_path": path.name, "sha256": digest.hexdigest(), "size_bytes": path.stat().st_size, "row_count": state["count"]}
    return write, close


def _level_source_row(level: Mapping[str, Any], *, side: str, fvt: str, topology: Iterable[str]) -> dict[str, Any]:
    return {
        "schema": ROW_SCHEMA, "source_role": "C2_VNEXT", "instrument": INSTRUMENT, "side": side, "clock": "15M",
        "first_valid_time": fvt, "evaluation_cutoff": fvt, "source_record_id": str(level["level_id"]), "source_record_kind": "C2_LEVEL",
        "structural_role_id": str(level.get("level_type") or "LEVEL"), "geometry_kind_id": "POINT",
        "geometry_signature": {"horizon_id": level.get("horizon_id"), "level_type": level.get("level_type"), "value": level.get("value"), "origin": level.get("origin"), "structural_depth": level.get("structural_depth")},
        "relation_topology": sorted(set(str(item) for item in topology)), "c2_package_id": C2_PACKAGE_ID,
        "c2_package_sha256": C2_PACKAGE_SHA256, "authority": "INACTIVE_NONCANONICAL_READ_ONLY_RS0_SOURCE",
    }


def _container_source_row(container: Mapping[str, Any], *, side: str, fvt: str, topology: Iterable[str]) -> dict[str, Any]:
    return {
        "schema": ROW_SCHEMA, "source_role": "C2_VNEXT", "instrument": INSTRUMENT, "side": side, "clock": "15M",
        "first_valid_time": fvt, "evaluation_cutoff": fvt, "source_record_id": str(container["container_id"]), "source_record_kind": "C2_CONTAINER",
        "structural_role_id": str(container.get("kind") or "CONTAINER"), "geometry_kind_id": "INTERVAL",
        "geometry_signature": {"horizon_id": container.get("horizon_id"), "kind": container.get("kind"), "lower_value": container.get("lower_value"), "upper_value": container.get("upper_value"), "centre": container.get("centre"), "width": container.get("width"), "origin": container.get("origin"), "structural_depth": container.get("structural_depth")},
        "relation_topology": sorted(set(str(item) for item in topology)), "c2_package_id": C2_PACKAGE_ID,
        "c2_package_sha256": C2_PACKAGE_SHA256, "authority": "INACTIVE_NONCANONICAL_READ_ONLY_RS0_SOURCE",
    }


def _parent_source_row(observation: Mapping[str, Any], *, side: str) -> dict[str, Any]:
    fvt = str(observation["first_valid_time"])
    return {
        "schema": ROW_SCHEMA, "source_role": "C2_VNEXT", "instrument": INSTRUMENT, "side": side, "clock": "2H_A_L",
        "first_valid_time": fvt, "evaluation_cutoff": fvt, "source_record_id": str(observation["observation_id"]),
        "source_record_kind": "C2_PARENT_OBSERVATION", "structural_role_id": "PARENT_CONTEXT_OBSERVATION", "geometry_kind_id": "BAR",
        "geometry_signature": {"interval_start": observation["interval_start"], "interval_end": observation["interval_end"], "open": observation.get("open"), "high": observation.get("high"), "low": observation.get("low"), "close": observation.get("close")},
        "relation_topology": [], "c2_package_id": C2_PACKAGE_ID, "c2_package_sha256": C2_PACKAGE_SHA256,
        "authority": "INACTIVE_NONCANONICAL_READ_ONLY_RS0_SOURCE",
    }


def _c2_source_rows(side_data: Mapping[str, Any], side: str) -> Iterable[dict[str, Any]]:
    relation_topology: dict[str, set[str]] = {}
    for relation in side_data["relations"]:
        object_id = relation.get("object_id"); topology = relation.get("topology")
        if object_id is not None and topology is not None:
            relation_topology.setdefault(str(object_id), set()).add(str(topology))
    bundle_fvt: dict[str, str] = {}
    for bundle in side_data["bundles"]:
        fvt = str(bundle["first_valid_time"])
        for object_id in bundle.get("level_ids", []): bundle_fvt[str(object_id)] = fvt
        for object_id in bundle.get("container_ids", []): bundle_fvt[str(object_id)] = fvt
    for level in side_data["levels"]:
        level_id = str(level["level_id"])
        yield _level_source_row(level, side=side, fvt=bundle_fvt.get(level_id) or str(level["first_valid_time"]), topology=relation_topology.get(level_id, set()))
    for container in side_data["containers"]:
        container_id = str(container["container_id"])
        yield _container_source_row(container, side=side, fvt=bundle_fvt.get(container_id) or str(container["first_valid_time"]), topology=relation_topology.get(container_id, set()))
    for observation in side_data["complete2h"]:
        yield _parent_source_row(observation, side=side)


def _record_id(record: Mapping[str, Any]) -> str:
    for field in ("episode_id", "snapshot_id", "phase_segment_id", "boundary_event_id", "membership_delta_id", "lineage_edge_id", "stream_manifest_id", "checkpoint_id", "handoff_id", "remap_record_id"):
        if field in record:
            return str(record[field])
    return hash_obj(record)


def _record_fvt(record: Mapping[str, Any]) -> str:
    for field in ("first_valid_time", "known_at", "as_of_time"):
        value = record.get(field)
        if value:
            return str(value)
    return TARGET_END


def _c2e_source_row(record: Mapping[str, Any], side: str) -> dict[str, Any]:
    schema = str(record.get("schema") or "UNKNOWN")
    fvt = _record_fvt(record)
    effective_start = record.get("effective_start") or record.get("effective_time") or record.get("start_time")
    effective_end = record.get("effective_end") or record.get("end_time") or record.get("terminated_at")
    return {
        "schema": ROW_SCHEMA, "source_role": "C2E_V0_2", "instrument": INSTRUMENT, "side": side, "clock": "15M",
        "first_valid_time": fvt, "evaluation_cutoff": fvt, "source_record_id": _record_id(record), "source_record_kind": schema,
        "structural_role_id": schema.replace("c2e_", "").replace("/v0_2", "").upper(), "geometry_kind_id": "TEMPORAL",
        "geometry_signature": {"episode_id": record.get("episode_id"), "effective_start": effective_start, "effective_end": effective_end, "status": record.get("status"), "phase_type": record.get("phase_type"), "boundary_event_type": record.get("event_type") or record.get("reason")},
        "relation_topology": sorted(str(value) for key, value in record.items() if key in {"parent_episode_id", "child_episode_id", "source_episode_id", "target_episode_id"} and value is not None),
        "c2e_boundary_pack_id": C2E_BOUNDARY_PACK_ID, "c2e_boundary_pack_sha256": C2E_BOUNDARY_PACK_SHA256,
        "authority": "INACTIVE_NONCANONICAL_READ_ONLY_RS0_SOURCE",
    }


def _c2e_source_rows(result: c2e.ReplayResult, side: str) -> Iterable[dict[str, Any]]:
    for record in result.records:
        yield _c2e_source_row(record, side)


def _write_rows(path: Path, rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    write, close = _writer(path)
    for row in rows:
        write(row)
    info = close()
    _require(info["row_count"] > 0, f"RS0_SOURCE_PROJECTION_EMPTY:{path.name}")
    return info


def _write_json(path: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(dict(value)) + b"\n"
    path.write_bytes(data)
    return {"relative_path": path.name, "sha256": sha256(data).hexdigest(), "size_bytes": len(data), "row_count": 1}


def _compact_observation(raw: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "observation_id": raw["observation_id"],
        "first_valid_time": raw["first_valid_time"],
        "interval_start": raw["interval_start"],
        "interval_end": raw["interval_end"],
        "continuity": copy.deepcopy(raw.get("continuity", {})),
        "projection_eligibility": copy.deepcopy(raw.get("projection_eligibility", {})),
    }


def _prepare_streaming_side(side: str, rows15: list[dict[str, Any]], rows2h: list[dict[str, Any]]) -> dict[str, Any]:
    with _c2_scope():
        calendar = c2rm.default_gbpusd_calendar()
        pop15 = c2rm.build_population(
            c2rm.CONTEXT_START, c2rm.CONTEXT_END, instrument=INSTRUMENT, calendar=calendar,
            evidence_rows=[c2rm.c1_to_evidence(row) for row in rows15], sides=(side,),
            lattices=(c2rm.baseline_lattices()[0],), partition_id=MATERIALISATION_ID,
        )
        c1_by_interval15 = {(r["open_time"], r["close_time"], r["side"]): r for r in rows15}
        full15: list[dict[str, Any]] = []
        complete15: list[dict[str, Any]] = []
        target_ids: set[str] = set()
        observations15 = pop15["observations"]
        del pop15
        for position in range(len(observations15)):
            raw = observations15[position]
            full15.append(_compact_observation(raw))
            row = c1_by_interval15.get((raw["interval_start"], raw["interval_end"], raw["side"]))
            if row and raw["projection_eligibility"]["eligible"]:
                obs = c2rm.enrich_observation(raw, row)
                complete15.append(obs)
                if row.get("target_eligible") is True:
                    target_ids.add(str(obs["observation_id"]))
            observations15[position] = None
        del observations15, c1_by_interval15

        evidence2h = [c2rm.c1_to_evidence(row) for row in rows2h]
        slots2h = []
        for row in rows2h:
            start, end = c2rm.parse_time(row["open_time"]), c2rm.parse_time(row["close_time"])
            identity = {"instrument": INSTRUMENT, "side": side, "interval_start": c2rm.iso(start), "interval_end": c2rm.iso(end), "partition_id": MATERIALISATION_ID}
            slots2h.append({"slot_id": c2rm.digest("C2.SLOT", identity), **identity, "expectation": calendar.classify(start, end)})
        two_h_lattice = next(profile for profile in c2rm.baseline_lattices() if profile.interval_minutes == 120)
        full2h = c2rm.assign_continuity(c2rm.bind_evidence(slots2h, evidence2h, lattices=(two_h_lattice,)))
        c1_by_interval2h = {(r["open_time"], r["close_time"], r["side"]): r for r in rows2h}
        complete2h: list[dict[str, Any]] = []
        for raw in full2h:
            row = c1_by_interval2h.get((raw["interval_start"], raw["interval_end"], raw["side"]))
            if row and raw["projection_eligibility"]["eligible"]:
                complete2h.append(c2rm.enrich_observation(raw, row))
        parent_slots = [{
            "observation_id": obs["observation_id"], "interval_start": obs["interval_start"], "interval_end": obs["interval_end"],
            "first_valid_time": obs["first_valid_time"], "status": "COMPLETE", "source_id": obs["lineage"]["c1_record_id"],
            "instrument_id": INSTRUMENT, "side": side, "release_id": C1_RELEASE_ID,
            "calendar_id": calendar.calendar_id, "parent_lattice_id": c2rm.PARENT_LATTICE_ID,
        } for obs in complete2h]
        parent_slot_index = {(item["interval_start"], item["interval_end"]): item for item in parent_slots}
        full_index = {str(obs["observation_id"]): index for index, obs in enumerate(full15)}
        complete_by_id = {str(obs["observation_id"]): obs for obs in complete15}
        horizon_defs = [c2rm.horizon_definition(count) for count in c2rm.HORIZON_COUNTS]
        order = [(str(row["first_valid_time"]), str(row["observation_id"])) for row in complete15]
        _require(order == sorted(order), f"C2_COMPLETE15_ORDER_DRIFT:{side}")
        return {
            "side": side,
            "calendar": calendar,
            "full15": full15,
            "complete15": complete15,
            "complete2h": complete2h,
            "parent_slots": parent_slots,
            "parent_slot_index": parent_slot_index,
            "parent_observations": {str(row["observation_id"]): row for row in complete2h},
            "full_index": full_index,
            "complete_by_id": complete_by_id,
            "horizon_defs": horizon_defs,
            "target_ids": target_ids,
        }


def _iter_streaming_c2_events(prepared: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
    side = str(prepared["side"])
    previous_refs: dict[tuple[str, str], str] = {}
    previous_relations: dict[str, dict[str, Any]] = {}
    previous_segment: Any = None
    with _c2_scope():
        for current in prepared["complete15"]:
            current_id = str(current["observation_id"])
            current_fvt = str(current["first_valid_time"])
            segment = current["continuity"]["segment_id"]
            if segment != previous_segment:
                previous_refs, previous_relations = {}, {}
            previous_segment = segment
            current_levels: list[dict[str, Any]] = []
            current_containers: list[dict[str, Any]] = []
            motion_profiles: list[dict[str, Any]] = []
            current_ref_map: dict[tuple[str, str], str] = {}
            memberships: list[dict[str, Any]] = []
            for definition in prepared["horizon_defs"]:
                horizon = c2rm.fast_horizon(definition, prepared["full15"], prepared["full_index"][current_id])
                memberships.append(horizon)
                price_delta = None
                if horizon["status"] == "COMPUTABLE":
                    member_obs = [prepared["complete_by_id"][str(member_id)] for member_id in horizon["member_observation_ids"]]
                    price_delta = float(current["close"]) - float(member_obs[0]["close"])
                    range_levels = c2rm.build_trailing_range_snapshot(member_obs, horizon_id=definition.horizon_id, clock_id=c2rm.LOCAL_LATTICE_ID)
                    current_levels.extend(range_levels)
                    current_containers.append(c2rm.build_trailing_range_container(range_levels))
                    for level in range_levels:
                        current_ref_map[(definition.horizon_id, str(level["level_type"]))] = str(level["level_id"])
                motion_profiles.append(c2rm.evaluate_motion_profile(
                    c2rm.formula_membership(horizon, current_fvt), price_delta=price_delta, relation_deltas=[], as_of_time=current_fvt,
                ))
            graph = c2rm.build_container_graph(current_containers)
            probe = c2rm.point_probe(value=float(current["close"]), source_record_id=current_id, first_valid_time=current_fvt, probe_label="CLOSE")
            level_relations = [c2rm.relate_point_to_level(probe, item, precision=5) for item in current_levels]
            container_relations = [c2rm.relate_point_to_container(probe, item, precision=5) for item in current_containers]
            sets: list[dict[str, Any]] = []
            if current_levels:
                sets.append(c2rm.build_relation_set(scope_type="LOCAL_LEVELS", subject_observation_id=current_id,
                    candidate_object_ids=[item["level_id"] for item in current_levels], relations=level_relations, exclusions=[], as_of_time=current_fvt))
            if current_containers:
                sets.append(c2rm.build_relation_set(scope_type="LOCAL_MEASUREMENT_CONTAINERS", subject_observation_id=current_id,
                    candidate_object_ids=[item["container_id"] for item in current_containers], relations=container_relations, exclusions=[], as_of_time=current_fvt))
            location = c2rm.evaluate_location_profile(sets, [*level_relations, *container_relations], as_of_time=current_fvt)
            organisation = c2rm.evaluate_organisation_profile(graph, swing_graph=None, as_of_time=current_fvt)
            current_relation_map = {str(relation["object_id"]): relation for relation in level_relations}
            deltas = [c2rm.temporal_relation_delta(previous_relations[object_id], relation)
                      for object_id, relation in current_relation_map.items() if object_id in previous_relations]
            ref_changes = []
            for key, current_level_id in sorted(current_ref_map.items()):
                prior_level_id = previous_refs.get(key)
                if prior_level_id is not None and prior_level_id != current_level_id:
                    ref_changes.append(c2rm.reference_change_record(previous_object_id=prior_level_id, current_object_id=current_level_id,
                        first_valid_time=current_fvt, reason="TRAILING_RANGE_SNAPSHOT_REFRESH"))
            interaction = c2rm.evaluate_interaction_profile(relation_deltas=deltas, crossing_evidence=[], reference_changes=ref_changes, as_of_time=current_fvt)
            previous_refs, previous_relations = current_ref_map, current_relation_map
            local_parent = {"observation_id": current_id, "first_valid_time": current_fvt, "instrument_id": INSTRUMENT,
                "side": side, "release_id": C1_RELEASE_ID, "calendar_id": prepared["calendar"].calendar_id,
                "parent_lattice_id": c2rm.PARENT_LATTICE_ID, "parent_scope_id": "PARENT_2H_A_L"}
            expected_start, expected_end = c2rm.expected_parent_slot(current_fvt)
            parent_candidate = prepared["parent_slot_index"].get((expected_start, expected_end))
            context = c2rm.resolve_parent_context(local_observation=local_parent,
                parent_slots=([parent_candidate] if parent_candidate is not None else []), parent_objects=(), structural_depths=(),
                higher_order_local_objects=(), episode_candidates=(), previous_bundle=None,
                eligible_local_observation_count=len(prepared["complete15"]), registered_closure_count=0, episode_authority=False)
            profiles = [location, *motion_profiles, organisation, interaction]
            bundle = {"schema": "ovc-c2-vnext-observation-materialisation-bundle/v1", "materialisation_id": MATERIALISATION_ID,
                "observation_id": current_id, "first_valid_time": current_fvt, "side": side, "target_eligible": current_id in prepared["target_ids"],
                "horizon_membership_ids": [item["membership_id"] for item in memberships],
                "profile_output_ids": {"LOCATION": [location["profile_output_id"]], "MOTION": [item["profile_output_id"] for item in motion_profiles],
                    "ORGANISATION": [organisation["profile_output_id"]], "INTERACTION": [interaction["profile_output_id"]]},
                "level_ids": [item["level_id"] for item in current_levels], "container_ids": [item["container_id"] for item in current_containers],
                "relation_set_ids": [item["relation_set_id"] for item in sets], "context_bundle_id": context["bundle_id"],
                "fixed_parent_observation_id": context["fixed_parent_observation_link"]["selected_id"],
                "authority": "SHADOW_FROZEN_READ_ONLY_MATERIALISATION_ONLY"}
            yield {
                "observation": current,
                "memberships": memberships,
                "levels": current_levels,
                "containers": current_containers,
                "relations": [*level_relations, *container_relations, *deltas, *ref_changes],
                "direct_relations": [*level_relations, *container_relations],
                "relation_sets": sets,
                "profiles": profiles,
                "context": context,
                "bundle": bundle,
            }


def _streaming_side_manifest(prepared: Mapping[str, Any]) -> dict[str, Any]:
    digest = sha256()
    count = 0
    for index, event in enumerate(_iter_streaming_c2_events(prepared), 1):
        bundle = event["bundle"]
        if bundle.get("target_eligible") is True:
            digest.update(canonical_bytes(bundle)); digest.update(b"\n"); count += 1
        if index % 4096 == 0:
            enforce_capacity(f"C2_VNEXT_MANIFEST_PASS_{prepared['side']}_{index}")
    _require(count > 0, f"C2E_SIDE_POPULATION_EMPTY:{prepared['side']}")
    target_hash = digest.hexdigest()
    manifest_seed = {
        "schema": "ovc-c2p2-rs0-c2-vnext-side-manifest/v1",
        "materialisation_id": MATERIALISATION_ID,
        "side": prepared["side"],
        "c1_release_id": C1_RELEASE_ID,
        "opt_a_release_id": OPT_A_RELEASE_ID,
        "c2_package_id": C2_PACKAGE_ID,
        "c2_package_sha256": C2_PACKAGE_SHA256,
        "target_bundles_sha256": target_hash,
        "target_bundle_count": count,
        "interval": INTERVAL,
    }
    logical_sha = hash_obj(manifest_seed)
    return {**manifest_seed, "logical_sha256": logical_sha, "files": {"target_bundles": {"sha256": target_hash}}}


class _StreamingSemanticStream:
    def __init__(self, *, side: str, write_source_row) -> None:
        self.side = side
        self.write_source_row = write_source_row
        self._ids: set[str] = set()
        self._projection: dict[str, dict[str, Any]] = {}
        self.record_count = 0
        self.membership_count = 0

    def append(self, record: Mapping[str, Any]) -> None:
        item = copy.deepcopy(dict(record))
        try:
            record_id = AppendOnlyStream._record_id(item)
        except StreamError as exc:
            raise RS0SourceMaterialisationError(str(exc)) from exc
        if record_id in self._ids:
            raise RS0SourceMaterialisationError("APPEND_ONLY_DUPLICATE_OR_UPDATE_DENIED")
        if item.get("authority") not in {"INACTIVE_NONCANONICAL_SHADOW", "COMPARISON_ONLY"}:
            raise RS0SourceMaterialisationError("STREAM_AUTHORITY_DENIED")
        self._ids.add(record_id)
        self.record_count += 1
        schema = item.get("schema")
        if schema == "c2e_episode_genesis/v0_2":
            self._projection.setdefault(str(item["episode_id"]), {"members": set(), "phases": set(), "boundaries": set(), "status": "OPEN"})
        elif schema == "c2e_membership_delta/v0_2":
            self.membership_count += 1
            state = self._projection.setdefault(str(item["episode_id"]), {"members": set(), "phases": set(), "boundaries": set(), "status": "OPEN"})
            if item.get("operation") == "ADD":
                state["members"].add(str(item["frame_id"]))
            elif item.get("operation") == "REMOVE_TOPOLOGY_EFFECT":
                state["members"].discard(str(item["frame_id"]))
        elif schema == "c2e_phase_segment/v0_2":
            state = self._projection.setdefault(str(item["episode_id"]), {"members": set(), "phases": set(), "boundaries": set(), "status": "OPEN"})
            state["phases"].add(str(item["phase_segment_id"]))
        elif schema == "c2e_boundary_event/v0_2":
            for episode_id in item.get("episode_ids", []):
                state = self._projection.setdefault(str(episode_id), {"members": set(), "phases": set(), "boundaries": set(), "status": "OPEN"})
                state["boundaries"].add(str(item["boundary_event_id"]))
                action = item.get("lifecycle_action")
                if action in {"CENSOR_GAP", "CENSOR_RELEASE_END"}:
                    state["status"] = "CENSORED"
                elif action == "TERMINATE_CONFLICT":
                    state["status"] = "CONFLICTED"
                elif action == "TERMINATE":
                    state["status"] = "TERMINATED"
        self.write_source_row(_c2e_source_row(item, self.side))

    def snapshot_record(self, episode_id: str, *, as_of_time: str, first_valid_time: str) -> dict[str, Any]:
        state = self._projection.get(episode_id)
        _require(state is not None, f"EPISODE_PROJECTION_NOT_FOUND:{episode_id}")
        return build_record("episode_snapshot", {
            "episode_id": episode_id,
            "as_of_time": as_of_time,
            "first_valid_time": first_valid_time,
            "status": state["status"],
            "member_ids": sorted(state["members"]),
            "phase_segment_ids": sorted(state["phases"]),
            "boundary_event_ids": sorted(state["boundaries"]),
            "authority": "INACTIVE_NONCANONICAL_SHADOW",
        })

    @property
    def records(self) -> list[dict[str, Any]]:
        raise RS0SourceMaterialisationError("STREAMING_RECORD_REHYDRATION_DENIED")

    def update(self, *_args: Any, **_kwargs: Any) -> None:
        raise RS0SourceMaterialisationError("APPEND_ONLY_UPDATE_DENIED")

    def delete(self, *_args: Any, **_kwargs: Any) -> None:
        raise RS0SourceMaterialisationError("APPEND_ONLY_DELETE_DENIED")


def _event_maps(event: Mapping[str, Any], prepared: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "observations": {str(event["observation"]["observation_id"]): event["observation"]},
        "parent_observations": prepared["parent_observations"],
        "profiles": {str(row["profile_output_id"]): row for row in event["profiles"]},
        "memberships": {str(row["membership_id"]): row for row in event["memberships"]},
        "contexts": {str(event["context"]["bundle_id"]): event["context"]},
        "levels": {str(row["level_id"]): row for row in event["levels"]},
        "containers": {str(row["container_id"]): row for row in event["containers"]},
        "relation_sets": {str(row["relation_set_id"]): row for row in event["relation_sets"]},
    }


def _run_streaming_c2e_side(
    prepared: Mapping[str, Any],
    manifest: Mapping[str, Any],
    pack: Mapping[str, Any],
    *,
    side: str,
    source_build_commit: str,
    write_source_row,
) -> dict[str, Any]:
    stream = _StreamingSemanticStream(side=side, write_source_row=write_source_row)
    engine = EpisodeEngine(str(pack["boundary_pack_id"]))
    engine.stream = stream
    counters = {name: 0 for name in ("birth", "continuation", "phase_mutation", "re_parent", "censor_gap", "censor_release_end", "legacy_disagreements", "candidate_not_evaluable", "resolver_conflicts")}
    previous: dict[str, Any] | None = None
    active_episode_id: str | None = None
    phase_state: dict[str, tuple[str, list[str]]] = {}
    target_count = 0
    for index, event in enumerate(_iter_streaming_c2_events(prepared), 1):
        bundle = event["bundle"]
        if bundle.get("target_eligible") is not True:
            continue
        target_count += 1
        maps = _event_maps(event, prepared)
        frame = c2e.build_frame(
            bundle,
            predecessor_observation_id=previous["identity"]["observation_id"] if previous else None,
            observations=maps["observations"], parent_observations=maps["parent_observations"],
            profiles=maps["profiles"], memberships=maps["memberships"], contexts=maps["contexts"],
            levels=maps["levels"], containers=maps["containers"], relation_sets=maps["relation_sets"],
            materialisation_manifest=manifest, source_build_commit=source_build_commit,
        )
        corrected = c2e.evaluate_boundary_predicates_v2(frame, previous)
        legacy = c2e.evaluate_legacy_predicates(frame, previous)
        if corrected != legacy:
            counters["legacy_disagreements"] += 1
        candidates = []
        for rule_id in c2e.RULE_IDS:
            candidate = build_candidate(c2e._rule(pack, rule_id), frame, matched=corrected[rule_id], effective_time=frame["chronology"]["first_valid_time"])
            if candidate is not None:
                if not candidate["evaluable"]:
                    counters["candidate_not_evaluable"] += 1
                candidates.append(candidate)
        resolved = resolve_candidates(pack, candidates)
        if resolved["status"] != "RESOLVED":
            counters["resolver_conflicts"] += 1
            raise RS0SourceMaterialisationError(f"BOUNDARY_RESOLUTION_CONFLICT:{side}:{frame['frame_id']}:{resolved['reason_codes']}")
        for candidate in resolved["resolved"]:
            action = candidate["lifecycle_action"]
            if action == "CENSOR_GAP":
                _require(active_episode_id is not None, "NO_ACTIVE_EPISODE_TO_CENSOR")
                engine.censor(episode_id=active_episode_id, candidate_id=candidate["candidate_id"], reason="CENSOR_GAP", effective_time=candidate["effective_time"], first_valid_time=candidate["first_valid_time"])
                counters["censor_gap"] += 1
                active_episode_id = None
            elif action == "RE_PARENT":
                _require(active_episode_id is not None, "NO_ACTIVE_EPISODE_TO_REPARENT")
                engine.re_parent(episode_id=active_episode_id, candidate_id=candidate["candidate_id"], effective_time=candidate["effective_time"], first_valid_time=candidate["first_valid_time"], reason_codes=["C2E_UPSTREAM_PARENT_SIGNATURE_CHANGE"])
                counters["re_parent"] += 1
            elif action == "PHASE_MUTATION":
                _require(active_episode_id is not None, "NO_ACTIVE_EPISODE_TO_PHASE")
                start_time, source_ids = phase_state[active_episode_id]
                engine.phase_mutation(episode_id=active_episode_id, candidate_id=candidate["candidate_id"], phase_type="STRUCTURAL_SIGNATURE_INTERVAL", start_time=start_time, end_time=candidate["effective_time"], source_record_ids=source_ids, effective_time=candidate["effective_time"], first_valid_time=candidate["first_valid_time"])
                phase_state[active_episode_id] = (candidate["effective_time"], sorted(frame["structural"]["location_record_ids"] + frame["structural"]["motion_record_ids"] + frame["structural"]["organisation_record_ids"] + frame["structural"]["interaction_record_ids"]))
                counters["phase_mutation"] += 1
            elif action == "CONTINUATION":
                _require(active_episode_id is not None, "NO_ACTIVE_EPISODE_TO_CONTINUE")
                engine.continue_episode(episode_id=active_episode_id, frame=frame, candidate_id=candidate["candidate_id"], effective_time=candidate["effective_time"], first_valid_time=candidate["first_valid_time"])
                counters["continuation"] += 1
            elif action == "BIRTH":
                genesis = engine.birth(frame=frame, boundary_rule_id=candidate["boundary_rule_id"], candidate_id=candidate["candidate_id"], effective_time=candidate["effective_time"], first_valid_time=candidate["first_valid_time"])
                active_episode_id = genesis["episode_id"]
                phase_state[active_episode_id] = (candidate["effective_time"], sorted(frame["structural"]["location_record_ids"] + frame["structural"]["motion_record_ids"] + frame["structural"]["organisation_record_ids"] + frame["structural"]["interaction_record_ids"]))
                counters["birth"] += 1
            else:
                raise RS0SourceMaterialisationError(f"UNSUPPORTED_LIFECYCLE_ACTION:{action}")
        previous = frame
        if index % 4096 == 0:
            gc.collect(); enforce_capacity(f"C2E_STREAM_{side}_{index}")
    _require(previous is not None and active_episode_id is not None, f"SIDE_POPULATION_EMPTY_OR_UNOWNED:{side}")
    _require(target_count == int(manifest["target_bundle_count"]), f"TARGET_BUNDLE_COUNT_RECONCILIATION_FAILED:{side}:{target_count}:{manifest['target_bundle_count']}")
    release = build_candidate(c2e._rule(pack, c2e.RULE_IDS[1]), previous, matched=True, effective_time=TARGET_END)
    _require(release is not None and release["evaluable"], "RELEASE_END_CANDIDATE_NOT_EVALUABLE")
    engine.censor(episode_id=active_episode_id, candidate_id=release["candidate_id"], reason="CENSOR_RELEASE_END", effective_time=TARGET_END, first_valid_time=TARGET_END)
    counters["censor_release_end"] += 1
    _require(stream.membership_count == target_count, f"MEMBERSHIP_COUNT_RECONCILIATION_FAILED:{side}:{stream.membership_count}:{target_count}")
    for episode_id in sorted(engine.genesis):
        stream.append(stream.snapshot_record(episode_id, as_of_time=TARGET_END, first_valid_time=TARGET_END))
    _require(counters["birth"] == len(engine.genesis), f"BIRTH_EPISODE_COUNT_MISMATCH:{side}")
    _require(counters["censor_release_end"] == 1, f"RELEASE_END_SIDE_COUNT_MISMATCH:{side}")
    enforce_capacity(f"C2E_STREAM_COMPLETE_{side}")
    return {"counters": counters, "record_count": stream.record_count, "episode_count": len(engine.genesis), "target_count": target_count}


def _append_file(dst_handle, digest, src: Path) -> int:
    size = 0
    with src.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            dst_handle.write(chunk); digest.update(chunk); size += len(chunk)
    return size


def _write_streaming_c2_source(prepared: Mapping[str, Any], out_path: Path) -> tuple[dict[str, Any], dict[str, int]]:
    temp_root = out_path.parent.parent / ".c2p2-rs0-temp"
    temp_root.mkdir(parents=True, exist_ok=True)
    level_path = temp_root / f"{prepared['side'].lower()}-levels.jsonl"
    container_path = temp_root / f"{prepared['side'].lower()}-containers.jsonl"
    level_write, level_close = _writer(level_path)
    container_write, container_close = _writer(container_path)
    for index, event in enumerate(_iter_streaming_c2_events(prepared), 1):
        fvt = str(event["bundle"]["first_valid_time"])
        topology: dict[str, set[str]] = {}
        for relation in event["direct_relations"]:
            object_id = relation.get("object_id"); relation_topology = relation.get("topology")
            if object_id is not None and relation_topology is not None:
                topology.setdefault(str(object_id), set()).add(str(relation_topology))
        for level in event["levels"]:
            level_write(_level_source_row(level, side=str(prepared["side"]), fvt=fvt, topology=topology.get(str(level["level_id"]), set())))
        for container in event["containers"]:
            container_write(_container_source_row(container, side=str(prepared["side"]), fvt=fvt, topology=topology.get(str(container["container_id"]), set())))
        if index % 4096 == 0:
            enforce_capacity(f"C2_SOURCE_STREAM_{prepared['side']}_{index}")
    level_info = level_close(); container_info = container_close()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    digest = sha256(); row_count = int(level_info["row_count"]) + int(container_info["row_count"])
    with out_path.open("wb") as out_handle:
        _append_file(out_handle, digest, level_path)
        _append_file(out_handle, digest, container_path)
        for observation in prepared["complete2h"]:
            data = canonical_bytes(_parent_source_row(observation, side=str(prepared["side"]))) + b"\n"
            out_handle.write(data); digest.update(data); row_count += 1
    info = {"relative_path": out_path.name, "sha256": digest.hexdigest(), "size_bytes": out_path.stat().st_size, "row_count": row_count}
    _require(row_count > 0, f"RS0_SOURCE_PROJECTION_EMPTY:{out_path.name}")
    return info, {"levels": int(level_info["row_count"]), "containers": int(container_info["row_count"])}


def materialise(*, c1_root: Path, opt_a_root: Path, pack_path: Path, out_dir: Path, source_build_commit: str) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    indexes = verify_artifact_roots(c1_root, opt_a_root)
    pack = _load_json(pack_path)
    _require(pack.get("boundary_pack_id") == C2E_BOUNDARY_PACK_ID, "C2E_BOUNDARY_PACK_ID_DRIFT")
    _require(pack.get("logical_sha256") == C2E_BOUNDARY_PACK_SHA256, "C2E_BOUNDARY_PACK_HASH_DRIFT")
    source_files: list[dict[str, Any]] = []
    side_receipts: dict[str, Any] = {}
    source_row_counts = {"C2_VNEXT": 0, "C2E_V0_2": 0}
    for side in SIDES:
        rows15 = hydrate_rows(c1_root, opt_a_root, indexes, side=side, clock="15M")
        rows2h = hydrate_rows(c1_root, opt_a_root, indexes, side=side, clock="2H_A_L")
        enforce_capacity(f"HYDRATED_INPUT_{side}")
        prepared = _prepare_streaming_side(side, rows15, rows2h)
        del rows15, rows2h; gc.collect(); enforce_capacity(f"C2_VNEXT_PREPARED_{side}")
        manifest = _streaming_side_manifest(prepared)
        gc.collect(); enforce_capacity(f"C2_VNEXT_MANIFEST_READY_{side}")
        c2_info, c2_counts = _write_streaming_c2_source(prepared, out_dir / f"c2-vnext-rs0-source-{side.lower()}.jsonl")
        c2_info["role"] = "C2_VNEXT"; source_files.append(c2_info); source_row_counts["C2_VNEXT"] += int(c2_info["row_count"])
        c2e_write, c2e_close = _writer(out_dir / f"c2e-v0-2-rs0-source-{side.lower()}.jsonl")
        c2e_result = _run_streaming_c2e_side(prepared, manifest, pack, side=side, source_build_commit=source_build_commit, write_source_row=c2e_write)
        c2e_info = c2e_close(); _require(c2e_info["row_count"] > 0, f"RS0_SOURCE_PROJECTION_EMPTY:{c2e_info['relative_path']}")
        c2e_info["role"] = "C2E_V0_2"; source_files.append(c2e_info); source_row_counts["C2E_V0_2"] += int(c2e_info["row_count"])
        side_receipts[side] = {
            "c1_15m_rows": len(prepared["complete15"]), "c1_2h_rows": len(prepared["complete2h"]),
            "target_bundles": int(manifest["target_bundle_count"]), "c2_levels": c2_counts["levels"],
            "c2_containers": c2_counts["containers"], "c2e_stream_records": int(c2e_result["record_count"]),
            "c2e_counters": dict(c2e_result["counters"]), "peak_rss_bytes_after_side": peak_rss_bytes(),
        }
        del prepared, manifest, c2e_result; gc.collect(); enforce_capacity(f"SIDE_COMPLETE_{side}")
    locator = {
        "schema": LOCATOR_SCHEMA, "programme_id": PROGRAMME_ID, "packet_id": PACKET_ID, "materialisation_id": MATERIALISATION_ID,
        "instrument": INSTRUMENT, "sides": ["BID", "ASK"], "clocks": ["15M", "2H_A_L"], "interval": INTERVAL,
        "sources": sorted(source_files, key=lambda row: (row["role"], row["relative_path"])),
        "source_binding": {
            "c1_release_id": C1_RELEASE_ID, "c1_manifest_id": C1_MANIFEST_ID, "c1_source_commit": C1_SOURCE_COMMIT,
            "opt_a_release_id": OPT_A_RELEASE_ID, "opt_a_manifest_id": OPT_A_MANIFEST_ID, "opt_a_manifest_sha256": OPT_A_MANIFEST_SHA256,
            "opt_a_source_commit": OPT_A_SOURCE_COMMIT, "c2_package_id": C2_PACKAGE_ID, "c2_package_sha256": C2_PACKAGE_SHA256,
            "c2e_boundary_pack_id": C2E_BOUNDARY_PACK_ID, "c2e_boundary_pack_sha256": C2E_BOUNDARY_PACK_SHA256,
        },
        "authority": "INACTIVE_NONCANONICAL_READ_ONLY_RS0_SOURCE_ONLY", "validation": "LOCKED_UNCONSUMED",
        "sampling": "NONE", "reduced_precision": "NONE", "provider_intake": "NONE_ALREADY_GOVERNED_IMMUTABLE_PARENT_ARTIFACTS_ONLY",
    }
    locator["logical_sha256"] = hash_obj(locator)
    locator_info = _write_json(out_dir / "rs0-source-locator.json", locator)
    total_artifact_bytes = sum(int(item["size_bytes"]) for item in source_files) + int(locator_info["size_bytes"])
    _require(total_artifact_bytes <= EXTERNAL_STORAGE_LIMIT_BYTES, f"CAPACITY_EXCEEDED:artifact_bytes={total_artifact_bytes}:limit={EXTERNAL_STORAGE_LIMIT_BYTES}")
    receipt = {
        "schema": SCHEMA, "programme_id": PROGRAMME_ID, "packet_id": PACKET_ID, "materialisation_id": MATERIALISATION_ID, "status": "PASS",
        "population": {"instrument": INSTRUMENT, "sides": ["BID", "ASK"], "clocks": ["15M", "2H_A_L"], "interval": INTERVAL, "research_role": "DISCOVERY_SHADOW_ONLY"},
        "source_binding": locator["source_binding"], "side_receipts": side_receipts, "source_row_counts": source_row_counts,
        "locator": locator_info, "locator_logical_sha256": locator["logical_sha256"], "total_artifact_bytes": total_artifact_bytes,
        "peak_rss_bytes": peak_rss_bytes(), "capacity_limits": {"peak_memory_limit_bytes": PEAK_MEMORY_LIMIT_BYTES, "external_storage_limit_bytes": EXTERNAL_STORAGE_LIMIT_BYTES, "concurrency_limit": 1},
        "authority": {"c2p_activation": "NONE", "objectpack_selection": "NONE", "ec1_scientific_effect": "NONE", "f0_a": "HOLD_UNCHANGED", "validation": "LOCKED_UNCONSUMED", "publication": "NONE", "probability_risk_exposure_execution": "NONE", "grun_one_run_token_consumed": False},
        "rollback": "Preserve generated inactive evidence; forward-supersede bindings only.",
    }
    receipt["logical_sha256"] = hash_obj(receipt)
    _write_json(out_dir / "current-source-materialisation-receipt.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--c1-root", required=True); parser.add_argument("--opt-a-root", required=True)
    parser.add_argument("--pack", required=True); parser.add_argument("--out", required=True); parser.add_argument("--source-build-commit", required=True)
    args = parser.parse_args()
    receipt = materialise(c1_root=Path(args.c1_root), opt_a_root=Path(args.opt_a_root), pack_path=Path(args.pack), out_dir=Path(args.out), source_build_commit=args.source_build_commit)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
