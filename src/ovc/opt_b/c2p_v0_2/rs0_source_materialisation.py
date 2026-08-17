from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
from datetime import datetime, timedelta, timezone
import gc
import gzip
from hashlib import sha256
import json
from pathlib import Path
import resource
from typing import Any, Iterable, Mapping

from ovc.opt_b.c2_vnext import real_source_materialisation as c2rm
from ovc.opt_b.c2e_v2 import source_replay as c2e
from ovc.opt_b.c2e_v2.candidate import build_candidate
from ovc.opt_b.c2e_v2.lifecycle import EpisodeEngine
from ovc.opt_b.c2e_v2.resolver import resolve_candidates

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


def run_current_c2e_side(materialisation: Mapping[str, Any], pack: Mapping[str, Any], *, side: str, source_build_commit: str) -> c2e.ReplayResult:
    engine = EpisodeEngine(str(pack["boundary_pack_id"]))
    frame_index: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []
    blocked_candidates: list[dict[str, Any]] = []
    counters = {name: 0 for name in ("birth", "continuation", "phase_mutation", "re_parent", "censor_gap", "censor_release_end", "legacy_disagreements", "candidate_not_evaluable", "resolver_conflicts")}
    bundles = [dict(row) for row in materialisation["bundles"]]
    _require(bool(bundles), f"C2E_SIDE_POPULATION_EMPTY:{side}")
    _require({str(row["side"]) for row in bundles} == {side}, f"C2E_SIDE_SCOPE_DRIFT:{side}")
    bundles.sort(key=lambda row: (row["first_valid_time"], row["observation_id"]))

    previous: dict[str, Any] | None = None
    active_episode_id: str | None = None
    phase_state: dict[str, tuple[str, list[str]]] = {}
    for bundle in bundles:
        frame = c2e.build_frame(
            bundle,
            predecessor_observation_id=previous["identity"]["observation_id"] if previous else None,
            observations=materialisation["observations"],
            parent_observations=materialisation["parent_observations"],
            profiles=materialisation["profiles"],
            memberships=materialisation["memberships"],
            contexts=materialisation["contexts"],
            levels=materialisation["levels"],
            containers=materialisation["containers"],
            relation_sets=materialisation["relation_sets"],
            materialisation_manifest=materialisation["manifest"],
            source_build_commit=source_build_commit,
        )
        frame_index.append({
            "schema": "c2e_input_frame_index/v0_1",
            "frame_id": frame["frame_id"],
            "logical_hash": frame["logical_hash"],
            "lineage_hash": frame["lineage_hash"],
            "observation_id": frame["identity"]["observation_id"],
            "side": side,
            "first_valid_time": frame["chronology"]["first_valid_time"],
            "continuity_segment_id": frame["chronology"]["continuity_segment_id"],
            "predecessor_observation_id": frame["chronology"].get("predecessor_observation_id"),
            "structural_signature_sha256": frame["comparison"]["structural_signature_sha256"],
            "parent_signature_sha256": frame["comparison"]["parent_signature_sha256"],
            "context_bundle_id": frame["context"].get("context_resolution_bundle_id"),
            "source_relation_set_count": sum(1 for item in frame["lineage"]["parent_record_ids"] if str(item).startswith("C2.RELATION.SET.")),
            "authority": "INACTIVE_NONCANONICAL_SHADOW",
        })
        corrected = c2e.evaluate_boundary_predicates_v2(frame, previous)
        legacy = c2e.evaluate_legacy_predicates(frame, previous)
        if corrected != legacy:
            counters["legacy_disagreements"] += 1
            disagreements.append({
                "schema": "c2e_boundary_disagreement/v0_1",
                "side": side,
                "frame_id": frame["frame_id"],
                "first_valid_time": frame["chronology"]["first_valid_time"],
                "corrected_matched_rules": [rule_id for rule_id in c2e.RULE_IDS if corrected[rule_id]],
                "legacy_matched_rules": [rule_id for rule_id in c2e.RULE_IDS if legacy[rule_id]],
                "authority": "COMPARATOR_ONLY",
            })
        candidates = []
        for rule_id in c2e.RULE_IDS:
            candidate = build_candidate(c2e._rule(pack, rule_id), frame, matched=corrected[rule_id], effective_time=frame["chronology"]["first_valid_time"])
            if candidate is not None:
                if not candidate["evaluable"]:
                    counters["candidate_not_evaluable"] += 1
                    blocked_candidates.append(candidate)
                candidates.append(candidate)
        resolved = resolve_candidates(pack, candidates)
        if resolved["status"] != "RESOLVED":
            counters["resolver_conflicts"] += 1
            raise RS0SourceMaterialisationError(f"BOUNDARY_RESOLUTION_CONFLICT:{side}:{frame['frame_id']}:{resolved['reason_codes']}")
        actions: list[str] = []
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
            actions.append(action)
        evaluations.append({
            "schema": "c2e_boundary_evaluation/v0_2",
            "side": side,
            "frame_id": frame["frame_id"],
            "first_valid_time": frame["chronology"]["first_valid_time"],
            "matched_rules": [rule_id for rule_id in c2e.RULE_IDS if corrected[rule_id]],
            "resolved_actions": actions,
            "blocked_candidate_ids": [candidate["candidate_id"] for candidate in candidates if not candidate["evaluable"]],
            "authority": "INACTIVE_NONCANONICAL_SHADOW",
        })
        previous = frame

    _require(previous is not None and active_episode_id is not None, f"SIDE_POPULATION_EMPTY_OR_UNOWNED:{side}")
    release = build_candidate(c2e._rule(pack, c2e.RULE_IDS[1]), previous, matched=True, effective_time=TARGET_END)
    _require(release is not None and release["evaluable"], "RELEASE_END_CANDIDATE_NOT_EVALUABLE")
    engine.censor(episode_id=active_episode_id, candidate_id=release["candidate_id"], reason="CENSOR_RELEASE_END", effective_time=TARGET_END, first_valid_time=TARGET_END)
    counters["censor_release_end"] += 1
    evaluations.append({
        "schema": "c2e_boundary_evaluation/v0_2",
        "side": side,
        "frame_id": previous["frame_id"],
        "first_valid_time": TARGET_END,
        "matched_rules": [c2e.RULE_IDS[1]],
        "resolved_actions": ["CENSOR_RELEASE_END"],
        "blocked_candidate_ids": [],
        "authority": "INACTIVE_NONCANONICAL_SHADOW",
    })
    membership_count = sum(1 for record in engine.stream.records if record.get("schema") == "c2e_membership_delta/v0_2")
    _require(membership_count == len(bundles), f"MEMBERSHIP_COUNT_RECONCILIATION_FAILED:{side}:{membership_count}:{len(bundles)}")
    for episode_id in sorted(engine.genesis):
        engine.stream.append(engine.snapshot(episode_id, as_of_time=TARGET_END, first_valid_time=TARGET_END))
    _require(counters["birth"] == len(engine.genesis), f"BIRTH_EPISODE_COUNT_MISMATCH:{side}")
    _require(counters["censor_release_end"] == 1, f"RELEASE_END_SIDE_COUNT_MISMATCH:{side}")
    enforce_capacity(f"C2E_REPLAY_{side}")
    return c2e.ReplayResult(frame_index, evaluations, list(engine.stream.records), disagreements, blocked_candidates, counters)


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
        level_id = str(level["level_id"]); fvt = bundle_fvt.get(level_id) or str(level["first_valid_time"])
        yield {
            "schema": ROW_SCHEMA, "source_role": "C2_VNEXT", "instrument": INSTRUMENT, "side": side, "clock": "15M",
            "first_valid_time": fvt, "evaluation_cutoff": fvt, "source_record_id": level_id, "source_record_kind": "C2_LEVEL",
            "structural_role_id": str(level.get("level_type") or "LEVEL"), "geometry_kind_id": "POINT",
            "geometry_signature": {"horizon_id": level.get("horizon_id"), "level_type": level.get("level_type"), "value": level.get("value"), "origin": level.get("origin"), "structural_depth": level.get("structural_depth")},
            "relation_topology": sorted(relation_topology.get(level_id, set())), "c2_package_id": C2_PACKAGE_ID,
            "c2_package_sha256": C2_PACKAGE_SHA256, "authority": "INACTIVE_NONCANONICAL_READ_ONLY_RS0_SOURCE",
        }
    for container in side_data["containers"]:
        container_id = str(container["container_id"]); fvt = bundle_fvt.get(container_id) or str(container["first_valid_time"])
        yield {
            "schema": ROW_SCHEMA, "source_role": "C2_VNEXT", "instrument": INSTRUMENT, "side": side, "clock": "15M",
            "first_valid_time": fvt, "evaluation_cutoff": fvt, "source_record_id": container_id, "source_record_kind": "C2_CONTAINER",
            "structural_role_id": str(container.get("kind") or "CONTAINER"), "geometry_kind_id": "INTERVAL",
            "geometry_signature": {"horizon_id": container.get("horizon_id"), "kind": container.get("kind"), "lower_value": container.get("lower_value"), "upper_value": container.get("upper_value"), "centre": container.get("centre"), "width": container.get("width"), "origin": container.get("origin"), "structural_depth": container.get("structural_depth")},
            "relation_topology": sorted(relation_topology.get(container_id, set())), "c2_package_id": C2_PACKAGE_ID,
            "c2_package_sha256": C2_PACKAGE_SHA256, "authority": "INACTIVE_NONCANONICAL_READ_ONLY_RS0_SOURCE",
        }
    for observation in side_data["complete2h"]:
        fvt = str(observation["first_valid_time"])
        yield {
            "schema": ROW_SCHEMA, "source_role": "C2_VNEXT", "instrument": INSTRUMENT, "side": side, "clock": "2H_A_L",
            "first_valid_time": fvt, "evaluation_cutoff": fvt, "source_record_id": str(observation["observation_id"]),
            "source_record_kind": "C2_PARENT_OBSERVATION", "structural_role_id": "PARENT_CONTEXT_OBSERVATION", "geometry_kind_id": "BAR",
            "geometry_signature": {"interval_start": observation["interval_start"], "interval_end": observation["interval_end"], "open": observation.get("open"), "high": observation.get("high"), "low": observation.get("low"), "close": observation.get("close")},
            "relation_topology": [], "c2_package_id": C2_PACKAGE_ID, "c2_package_sha256": C2_PACKAGE_SHA256,
            "authority": "INACTIVE_NONCANONICAL_READ_ONLY_RS0_SOURCE",
        }


def _record_id(record: Mapping[str, Any]) -> str:
    for field in ("episode_id", "snapshot_id", "phase_segment_id", "boundary_event_id", "membership_delta_id", "lineage_edge_id", "stream_manifest_id", "checkpoint_id"):
        if field in record: return str(record[field])
    return hash_obj(record)


def _record_fvt(record: Mapping[str, Any]) -> str:
    for field in ("first_valid_time", "known_at", "as_of_time"):
        value = record.get(field)
        if value: return str(value)
    return TARGET_END


def _c2e_source_rows(result: c2e.ReplayResult, side: str) -> Iterable[dict[str, Any]]:
    for record in result.records:
        schema = str(record.get("schema") or "UNKNOWN"); fvt = _record_fvt(record)
        effective_start = record.get("effective_start") or record.get("effective_time") or record.get("start_time")
        effective_end = record.get("effective_end") or record.get("end_time") or record.get("terminated_at")
        yield {
            "schema": ROW_SCHEMA, "source_role": "C2E_V0_2", "instrument": INSTRUMENT, "side": side, "clock": "15M",
            "first_valid_time": fvt, "evaluation_cutoff": fvt, "source_record_id": _record_id(record), "source_record_kind": schema,
            "structural_role_id": schema.replace("c2e_", "").replace("/v0_2", "").upper(), "geometry_kind_id": "TEMPORAL",
            "geometry_signature": {"episode_id": record.get("episode_id"), "effective_start": effective_start, "effective_end": effective_end, "status": record.get("status"), "phase_type": record.get("phase_type"), "boundary_event_type": record.get("event_type") or record.get("reason")},
            "relation_topology": sorted(str(value) for key, value in record.items() if key in {"parent_episode_id", "child_episode_id", "source_episode_id", "target_episode_id"} and value is not None),
            "c2e_boundary_pack_id": C2E_BOUNDARY_PACK_ID, "c2e_boundary_pack_sha256": C2E_BOUNDARY_PACK_SHA256,
            "authority": "INACTIVE_NONCANONICAL_READ_ONLY_RS0_SOURCE",
        }


def _write_rows(path: Path, rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    write, close = _writer(path)
    for row in rows: write(row)
    info = close(); _require(info["row_count"] > 0, f"RS0_SOURCE_PROJECTION_EMPTY:{path.name}")
    return info


def _write_json(path: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(dict(value)) + b"\n"; path.write_bytes(data)
    return {"relative_path": path.name, "sha256": sha256(data).hexdigest(), "size_bytes": len(data), "row_count": 1}


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
        side_data = build_current_c2_side(side, rows15, rows2h)
        del rows15, rows2h; gc.collect(); enforce_capacity(f"C2_VNEXT_READY_{side}")

        c2_info = _write_rows(out_dir / f"c2-vnext-rs0-source-{side.lower()}.jsonl", _c2_source_rows(side_data, side))
        c2_info["role"] = "C2_VNEXT"; source_files.append(c2_info); source_row_counts["C2_VNEXT"] += int(c2_info["row_count"])
        side_materialisation = _side_materialisation(side_data)
        c2e_result = run_current_c2e_side(side_materialisation, pack, side=side, source_build_commit=source_build_commit)
        c2e_info = _write_rows(out_dir / f"c2e-v0-2-rs0-source-{side.lower()}.jsonl", _c2e_source_rows(c2e_result, side))
        c2e_info["role"] = "C2E_V0_2"; source_files.append(c2e_info); source_row_counts["C2E_V0_2"] += int(c2e_info["row_count"])
        side_receipts[side] = {
            "c1_15m_rows": len(side_data["complete15"]), "c1_2h_rows": len(side_data["complete2h"]),
            "target_bundles": len(side_materialisation["bundles"]), "c2_levels": len(side_data["levels"]),
            "c2_containers": len(side_data["containers"]), "c2e_stream_records": len(c2e_result.records),
            "c2e_counters": dict(c2e_result.counters), "peak_rss_bytes_after_side": peak_rss_bytes(),
        }
        del side_data, side_materialisation, c2e_result; gc.collect(); enforce_capacity(f"SIDE_COMPLETE_{side}")

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
