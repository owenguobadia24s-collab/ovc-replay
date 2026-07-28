from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping

PROGRAMME_ID = "OVC-C1-WICK-BALANCE-CORRECTIVE-PROGRAMME-0.1"
SOURCE = {
    "artifact_id": 8634383302,
    "artifact_name": "c2-g4-exact-parent-replay-output",
    "artifact_archive_sha256": "b8f993f733aed75e488aa60883f00a53596c15e5cd6c14edb787fc3bc12df62f",
    "workflow_run_id": 30210057332,
    "workflow_commit": "4fb06b4d2b13bdf737446cb619e548eb987aeab1",
    "replay_receipt_sha256": "27aac06a35a56518eab67027272238c7bd265161b552823b5ab59d0547d13018",
    "intake_receipt_sha256": "4d519786ce8cc138a88924d1d2ec7de37caabad2ea83e021b403f91c4266d21b",
}
EXPECTED_TOTALS = {
    "files": 24,
    "bytes": 872_839_722,
    "states": 404_434,
    "transitions": 323_910,
}
ROLES: dict[str, dict[str, Any]] = {
    "discovery": {
        "role": "DISCOVERY",
        "c1_v1_release": "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1",
        "c1_v1_manifest": "MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1.r1",
        "c1_v2_release": "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2",
        "c1_v2_manifest": "MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2.r1",
        "c1_v2_manifest_logical_sha256": "c9b2eaa826419a510504c016d99072c6015c337a5c2ef435252d5f6ff1db93bf",
        "c1_v2_manifest_file_sha256": "708025a0f96db4649996bc1201da258f76c048723cf29b0c82725a19ba6418a9",
        "c1_record_count": 159_892,
        "c1_record_files": 144,
        "c2_v1_release": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1",
        "c2_v1_manifest": "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1.r1",
        "c2_v1_manifest_sha256": "c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33",
        "c2_v2_release": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2",
        "c2_v2_manifest": "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2.r1",
        "state_records": 303_856,
        "transition_records": 245_752,
        "opt_a_release": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
        "opt_a_manifest": "MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r2",
        "opt_a_manifest_sha256": "0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c",
    },
    "development": {
        "role": "DEVELOPMENT",
        "c1_v1_release": "OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1",
        "c1_v1_manifest": "MANIFEST.C1.OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1.r1",
        "c1_v2_release": "OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2",
        "c1_v2_manifest": "MANIFEST.C1.OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2.r1",
        "c1_v2_manifest_logical_sha256": "e4f1a2d0af7064837003f1c7b56156966aba3b035cc9a7b8ebbdc8b6b181d73f",
        "c1_v2_manifest_file_sha256": "56c42c1d34d77670ffec25dcf86da6bd7726017c133f1bd9e4f4be2aba23633e",
        "c1_record_count": 52_872,
        "c1_record_files": 48,
        "c2_v1_release": "OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1",
        "c2_v1_manifest": "MANIFEST.C2.OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1.r1",
        "c2_v1_manifest_sha256": "8a37e931ac003e88c8e1b3c4f8a1849e947f86f47e982e00ca4723e53fd9586e",
        "c2_v2_release": "OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v2",
        "c2_v2_manifest": "MANIFEST.C2.OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v2.r1",
        "state_records": 100_578,
        "transition_records": 78_158,
        "opt_a_release": "OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
        "opt_a_manifest": "MANIFEST.OPT-A.GBPUSD.DEVELOPMENT.2024.v2.r2",
        "opt_a_manifest_sha256": "25e1be8a7edb0e96017c45bf35f4e788345f94b22a8ed9bb0874c86338ba64cc",
    },
}


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def stable_id(prefix: str, value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def safe_relative(raw: Any) -> PurePosixPath:
    if not isinstance(raw, str) or not raw:
        raise RuntimeError("INVALID_MANIFEST_PATH")
    path = PurePosixPath(raw)
    if path.is_absolute() or "." in path.parts or ".." in path.parts or "\\" in raw:
        raise RuntimeError(f"UNSAFE_MANIFEST_PATH:{raw}")
    return path


def locate_payload(root: Path, relative: PurePosixPath) -> Path:
    direct = root / Path(*relative.parts)
    under_files = root / "files" / Path(*relative.parts)
    if direct.is_file() and not direct.is_symlink():
        return direct
    if under_files.is_file() and not under_files.is_symlink():
        return under_files
    raise RuntimeError(f"MISSING_C1_PAYLOAD:{relative.as_posix()}")


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"INVALID_JSONL:{path}:{line_number}") from exc
            if not isinstance(value, dict):
                raise RuntimeError(f"NON_OBJECT_JSONL:{path}:{line_number}")
            yield value


def verify_c1_v2(root: Path, cfg: Mapping[str, Any]) -> dict[str, str]:
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"MISSING_C1_V2_MANIFEST:{root}")
    raw = manifest_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != cfg["c1_v2_manifest_file_sha256"]:
        raise RuntimeError(f"C1_V2_MANIFEST_FILE_SHA_MISMATCH:{cfg['role']}")
    manifest = json.loads(raw)
    if manifest.get("release_id") != cfg["c1_v2_release"]:
        raise RuntimeError(f"C1_V2_RELEASE_MISMATCH:{cfg['role']}")
    if manifest.get("manifest_id") != cfg["c1_v2_manifest"]:
        raise RuntimeError(f"C1_V2_MANIFEST_ID_MISMATCH:{cfg['role']}")
    logical = dict(manifest)
    declared_logical = logical.pop("manifest_sha256", None)
    if hashlib.sha256(canonical_bytes(logical)).hexdigest() != declared_logical:
        raise RuntimeError(f"C1_V2_MANIFEST_SELF_HASH_MISMATCH:{cfg['role']}")
    if declared_logical != cfg["c1_v2_manifest_logical_sha256"]:
        raise RuntimeError(f"C1_V2_MANIFEST_LOGICAL_SHA_MISMATCH:{cfg['role']}")
    if manifest.get("formula_registry_id") != "C1.FORMULAS.v0.1":
        raise RuntimeError(f"C1_V2_FORMULA_REGISTRY_MISMATCH:{cfg['role']}")
    if manifest.get("implementation_id") != "C1.IMPLEMENTATION.v0.2":
        raise RuntimeError(f"C1_V2_IMPLEMENTATION_MISMATCH:{cfg['role']}")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != cfg["c1_record_files"]:
        raise RuntimeError(f"C1_V2_FILE_COUNT_MISMATCH:{cfg['role']}")

    parents: dict[str, str] = {}
    count = 0
    for item in files:
        relative = safe_relative(item.get("path"))
        if not relative.as_posix().startswith("records/"):
            raise RuntimeError(f"C1_V2_NON_RECORD_PAYLOAD:{relative}")
        path = locate_payload(root, relative)
        if path.stat().st_size != int(item.get("size_bytes", -1)) or sha_file(path) != item.get("sha256"):
            raise RuntimeError(f"C1_V2_PAYLOAD_MISMATCH:{cfg['role']}:{relative}")
        shard_count = 0
        for record in read_jsonl(path):
            record_id = record.get("record_id")
            source_bar_id = record.get("source_bar_id")
            if not isinstance(record_id, str) or not record_id.startswith("c1:"):
                raise RuntimeError(f"INVALID_C1_RECORD_ID:{cfg['role']}:{relative}")
            if not isinstance(source_bar_id, str) or not source_bar_id.startswith("opt-a:"):
                raise RuntimeError(f"INVALID_C1_SOURCE_BAR_ID:{cfg['role']}:{relative}")
            if record_id in parents:
                raise RuntimeError(f"DUPLICATE_C1_RECORD_ID:{cfg['role']}:{record_id}")
            if record.get("role") != cfg["role"]:
                raise RuntimeError(f"C1_ROLE_MISMATCH:{cfg['role']}:{record_id}")
            if record.get("parent_release_id") != cfg["opt_a_release"]:
                raise RuntimeError(f"C1_OPT_A_RELEASE_MISMATCH:{cfg['role']}:{record_id}")
            if record.get("parent_manifest_id") != cfg["opt_a_manifest"]:
                raise RuntimeError(f"C1_OPT_A_MANIFEST_MISMATCH:{cfg['role']}:{record_id}")
            if record.get("parent_manifest_sha256") != cfg["opt_a_manifest_sha256"]:
                raise RuntimeError(f"C1_OPT_A_HASH_MISMATCH:{cfg['role']}:{record_id}")
            parents[record_id] = source_bar_id
            count += 1
            shard_count += 1
        if shard_count != int(item.get("record_count", -1)):
            raise RuntimeError(f"C1_SHARD_RECORD_COUNT_MISMATCH:{cfg['role']}:{relative}")
    if count != cfg["c1_record_count"] or manifest.get("record_count") != count:
        raise RuntimeError(f"C1_V2_TOTAL_RECORD_COUNT_MISMATCH:{cfg['role']}:{count}")
    return parents


def source_root(root: Path) -> Path:
    for candidate in (root / "c2-g4-output", root):
        if (candidate / "WP5_LOCAL_REPLAY_RECEIPT.json").is_file():
            return candidate
    raise RuntimeError(f"C2_V1_SOURCE_ROOT_NOT_FOUND:{root}")


def verify_c2_v1_source(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    replay_path = root / "WP5_LOCAL_REPLAY_RECEIPT.json"
    intake_path = root / "WP5_CANONICAL_INTAKE_RECEIPT.json"
    if sha_file(replay_path) != SOURCE["replay_receipt_sha256"]:
        raise RuntimeError("C2_V1_REPLAY_RECEIPT_SHA_MISMATCH")
    if sha_file(intake_path) != SOURCE["intake_receipt_sha256"]:
        raise RuntimeError("C2_V1_INTAKE_RECEIPT_SHA_MISMATCH")
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    if replay.get("status") != "PASS_LOCAL_REPLAY":
        raise RuntimeError("C2_V1_SOURCE_REPLAY_NOT_PASS")
    for key, expected in {
        "validation_consumption": "LOCKED_UNCONSUMED",
        "probability": "NONE",
        "exposure": "NONE",
        "trading": "NONE",
        "execution": "NONE",
    }.items():
        if replay.get(key) != expected:
            raise RuntimeError(f"C2_V1_SOURCE_AUTHORITY_MISMATCH:{key}")
    outputs = replay.get("outputs")
    if not isinstance(outputs, dict):
        raise RuntimeError("C2_V1_OUTPUT_INVENTORY_MISSING")
    if len(outputs) != EXPECTED_TOTALS["files"] or sum(int(x["bytes"]) for x in outputs.values()) != EXPECTED_TOTALS["bytes"]:
        raise RuntimeError("C2_V1_OUTPUT_TOTAL_MISMATCH")
    actual = {
        path.relative_to(root).as_posix()
        for folder in (root / "states", root / "transitions")
        for path in folder.rglob("*.jsonl")
    }
    if actual != set(outputs):
        raise RuntimeError("C2_V1_OUTPUT_PATH_SET_MISMATCH")
    for relative, item in outputs.items():
        path = root / relative
        if path.stat().st_size != int(item["bytes"]) or sha_file(path) != item["sha256"]:
            raise RuntimeError(f"C2_V1_OUTPUT_BYTE_MISMATCH:{relative}")
    return replay, intake


def state_identity(row: Mapping[str, Any], c1_release_id: str) -> dict[str, Any]:
    return {
        "c1_record_id": row["parent_c1_record_id"],
        "source_bar_id": row["parent_opt_a_bar_id"],
        "c1_release_id": c1_release_id,
        "opt_a_release_id": row["opt_a_release_id"],
        "first_valid_time": row["first_valid_time"],
        "clock": row["clock"],
        "side": row["side"],
        "evaluation_scope_id": row["evaluation_scope_id"],
        "parameter_pack_id": row["parameter_pack_id"],
        "axes": row["axes"],
    }


def semantic_state(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: row[key]
        for key in (
            "parent_c1_record_id",
            "parent_opt_a_bar_id",
            "opt_a_release_id",
            "opt_a_manifest_id",
            "first_valid_time",
            "clock",
            "side",
            "evaluation_scope_id",
            "parameter_pack_id",
            "axes",
            "level_ids",
            "container_ids",
            "relation_set_id",
            "persistence",
            "continuity",
            "role",
        )
    }


def semantic_transition(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: row[key]
        for key in (
            "changed_axes",
            "first_valid_time",
            "status",
            "role",
            "clock",
            "side",
            "evaluation_scope_id",
        )
    }


def transform_states(
    source: Path,
    target: Path,
    cfg: Mapping[str, Any],
    parents: Mapping[str, str],
) -> tuple[int, dict[str, str], int]:
    target.parent.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    count = 0
    unchanged_ids = 0
    with source.open("r", encoding="utf-8", newline="") as read, target.open("w", encoding="utf-8", newline="\n") as write:
        for line_number, line in enumerate(read, 1):
            if not line.endswith("\n"):
                raise RuntimeError(f"UNTERMINATED_C2_STATE:{source}:{line_number}")
            old = json.loads(line)
            if old.get("role") != cfg["role"]:
                raise RuntimeError(f"C2_STATE_ROLE_MISMATCH:{source}:{line_number}")
            if old.get("c1_release_id") != cfg["c1_v1_release"] or old.get("c1_manifest_id") != cfg["c1_v1_manifest"]:
                raise RuntimeError(f"C2_STATE_OLD_C1_BINDING_MISMATCH:{source}:{line_number}")
            if old.get("opt_a_release_id") != cfg["opt_a_release"] or old.get("opt_a_manifest_id") != cfg["opt_a_manifest"]:
                raise RuntimeError(f"C2_STATE_OPT_A_BINDING_MISMATCH:{source}:{line_number}")
            parent_id = old.get("parent_c1_record_id")
            if parents.get(parent_id) != old.get("parent_opt_a_bar_id"):
                raise RuntimeError(f"C2_STATE_C1_V2_PARENT_MISSING_OR_MISMATCH:{source}:{line_number}")
            old_expected = stable_id("c2-state", state_identity(old, cfg["c1_v1_release"]))
            if old.get("c2_state_id") != old_expected:
                raise RuntimeError(f"C2_STATE_V1_IDENTITY_MISMATCH:{source}:{line_number}")
            new = dict(old)
            new["c1_release_id"] = cfg["c1_v2_release"]
            new["c1_manifest_id"] = cfg["c1_v2_manifest"]
            new_id = stable_id("c2-state", state_identity(new, cfg["c1_v2_release"]))
            new["c2_state_id"] = new_id
            if semantic_state(new) != semantic_state(old):
                raise RuntimeError(f"C2_STATE_SEMANTIC_DRIFT:{source}:{line_number}")
            if new_id == old["c2_state_id"]:
                unchanged_ids += 1
            if old["c2_state_id"] in mapping:
                raise RuntimeError(f"DUPLICATE_C2_STATE_ID:{source}:{line_number}")
            mapping[old["c2_state_id"]] = new_id
            write.write(json.dumps(new, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n")
            count += 1
    return count, mapping, unchanged_ids


def transform_transitions(
    source: Path,
    target: Path,
    cfg: Mapping[str, Any],
    state_map: Mapping[str, str],
) -> tuple[int, int]:
    target.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    unchanged_ids = 0
    with source.open("r", encoding="utf-8", newline="") as read, target.open("w", encoding="utf-8", newline="\n") as write:
        for line_number, line in enumerate(read, 1):
            if not line.endswith("\n"):
                raise RuntimeError(f"UNTERMINATED_C2_TRANSITION:{source}:{line_number}")
            old = json.loads(line)
            if old.get("role") != cfg["role"]:
                raise RuntimeError(f"C2_TRANSITION_ROLE_MISMATCH:{source}:{line_number}")
            old_identity = {
                "from": old["from_state_id"],
                "to": old["to_state_id"],
                "changed_axes": sorted(old["changed_axes"]),
                "first_valid_time": old["first_valid_time"],
            }
            if old.get("c2_transition_id") != stable_id("c2-transition", old_identity):
                raise RuntimeError(f"C2_TRANSITION_V1_IDENTITY_MISMATCH:{source}:{line_number}")
            try:
                new_from = state_map[old["from_state_id"]]
                new_to = state_map[old["to_state_id"]]
            except KeyError as exc:
                raise RuntimeError(f"C2_TRANSITION_ENDPOINT_NOT_REPLAYED:{source}:{line_number}") from exc
            new = dict(old)
            new["from_state_id"] = new_from
            new["to_state_id"] = new_to
            new_identity = {
                "from": new_from,
                "to": new_to,
                "changed_axes": sorted(new["changed_axes"]),
                "first_valid_time": new["first_valid_time"],
            }
            new_id = stable_id("c2-transition", new_identity)
            new["c2_transition_id"] = new_id
            if semantic_transition(new) != semantic_transition(old):
                raise RuntimeError(f"C2_TRANSITION_SEMANTIC_DRIFT:{source}:{line_number}")
            if new_id == old["c2_transition_id"]:
                unchanged_ids += 1
            write.write(json.dumps(new, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n")
            count += 1
    return count, unchanged_ids


def replay_identity_once(
    source: Path,
    target: Path,
    parent_maps: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    if target.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_REPLAY:{target}")
    target.mkdir(parents=True)
    totals = {"state_records": 0, "transition_records": 0, "unchanged_state_ids": 0, "unchanged_transition_ids": 0}
    roles: dict[str, dict[str, Any]] = {}
    for role_key, cfg in ROLES.items():
        state_map: dict[str, str] = {}
        role_stats = {"state_records": 0, "transition_records": 0, "state_files": 0, "transition_files": 0}
        state_paths = sorted((source / "states" / role_key).rglob("*.jsonl"))
        transition_paths = sorted((source / "transitions" / role_key).rglob("*.jsonl"))
        if len(state_paths) != 6 or len(transition_paths) != 6:
            raise RuntimeError(f"C2_ROLE_FILE_COUNT_MISMATCH:{cfg['role']}")
        for old_path in state_paths:
            rel = old_path.relative_to(source)
            new_path = target / rel
            count, mapping, unchanged = transform_states(old_path, new_path, cfg, parent_maps[role_key])
            if set(state_map) & set(mapping):
                raise RuntimeError(f"DUPLICATE_C2_STATE_ID_ACROSS_FILES:{cfg['role']}")
            state_map.update(mapping)
            role_stats["state_records"] += count
            role_stats["state_files"] += 1
            totals["unchanged_state_ids"] += unchanged
        for old_path in transition_paths:
            rel = old_path.relative_to(source)
            new_path = target / rel
            count, unchanged = transform_transitions(old_path, new_path, cfg, state_map)
            role_stats["transition_records"] += count
            role_stats["transition_files"] += 1
            totals["unchanged_transition_ids"] += unchanged
        if role_stats["state_records"] != cfg["state_records"] or role_stats["transition_records"] != cfg["transition_records"]:
            raise RuntimeError(f"C2_ROLE_RECORD_COUNT_MISMATCH:{cfg['role']}:{role_stats}")
        roles[role_key] = role_stats
        totals["state_records"] += role_stats["state_records"]
        totals["transition_records"] += role_stats["transition_records"]
    if totals["state_records"] != EXPECTED_TOTALS["states"] or totals["transition_records"] != EXPECTED_TOTALS["transitions"]:
        raise RuntimeError(f"C2_TOTAL_RECORD_COUNT_MISMATCH:{totals}")
    if totals["unchanged_state_ids"] or totals["unchanged_transition_ids"]:
        raise RuntimeError(f"C2_IDENTITY_DID_NOT_CHANGE:{totals}")
    return {"roles": roles, **totals}


def inventory(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha_file(path),
        }
        for path in sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(root).as_posix())
    ]


def stream_record_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def build_candidate(
    role_key: str,
    replay_root: Path,
    source_root_path: Path,
    output_root: Path,
    source_commit: str,
    replay_summary: Mapping[str, Any],
) -> dict[str, Any]:
    cfg = ROLES[role_key]
    root = output_root / role_key
    if root.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_CANDIDATE:{root}")
    root.mkdir(parents=True)
    files: list[dict[str, Any]] = []
    for kind in ("states", "transitions"):
        for source_path in sorted((replay_root / kind / role_key).rglob("*.jsonl")):
            relative = Path(kind) / source_path.relative_to(replay_root / kind / role_key)
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, target)
            files.append(
                {
                    "path": relative.as_posix(),
                    "size_bytes": target.stat().st_size,
                    "sha256": sha_file(target),
                    "record_type": "STATE" if kind == "states" else "TRANSITION",
                    "record_count": stream_record_count(target),
                }
            )
    source_dir = root / "source"
    source_dir.mkdir(parents=True)
    for name in ("WP5_LOCAL_REPLAY_RECEIPT.json", "WP5_CANONICAL_INTAKE_RECEIPT.json"):
        target = source_dir / name
        shutil.copyfile(source_root_path / name, target)
        files.append({"path": f"source/{name}", "size_bytes": target.stat().st_size, "sha256": sha_file(target)})
    binding = {
        "schema": "ovc-c1c-g5-c2-identity-replay-source-binding/v1",
        "programme_id": PROGRAMME_ID,
        "gate_id": "C1C-G5",
        "source": SOURCE,
        "source_c2_release_id": cfg["c2_v1_release"],
        "source_c2_manifest_id": cfg["c2_v1_manifest"],
        "source_c2_manifest_sha256": cfg["c2_v1_manifest_sha256"],
        "parent_c1_v2_release_id": cfg["c1_v2_release"],
        "parent_c1_v2_manifest_id": cfg["c1_v2_manifest"],
        "parent_c1_v2_manifest_logical_sha256": cfg["c1_v2_manifest_logical_sha256"],
        "parent_c1_v2_manifest_file_sha256": cfg["c1_v2_manifest_file_sha256"],
        "identity_replay_rule": "PRESERVE_ALL_C2_SEMANTIC_VALUES_REBIND_EXACT_C1_V2_PARENT_AND_RECOMPUTE_C2_STATE_TRANSITION_IDENTITIES",
        "source_commit": source_commit,
    }
    write_json(source_dir / "C1C_G5_SOURCE_BINDING.json", binding)
    files.append({"path": "source/C1C_G5_SOURCE_BINDING.json", "size_bytes": (source_dir / "C1C_G5_SOURCE_BINDING.json").stat().st_size, "sha256": sha_file(source_dir / "C1C_G5_SOURCE_BINDING.json")})

    role_summary = replay_summary["roles"][role_key]
    descriptor = {
        "schema": "ovc-c1c-g5-c2-corrective-release-descriptor/v1",
        "programme_id": PROGRAMME_ID,
        "gate_id": "C1C-G5",
        "release_id": cfg["c2_v2_release"],
        "manifest_id": cfg["c2_v2_manifest"],
        "role": cfg["role"],
        "supersedes_release_id": cfg["c2_v1_release"],
        "parent_opt_a_release_id": cfg["opt_a_release"],
        "parent_opt_a_manifest_id": cfg["opt_a_manifest"],
        "parent_opt_a_manifest_sha256": cfg["opt_a_manifest_sha256"],
        "parent_c1_release_id": cfg["c1_v2_release"],
        "parent_c1_manifest_id": cfg["c1_v2_manifest"],
        "parent_c1_manifest_sha256": cfg["c1_v2_manifest_logical_sha256"],
        "source_c2_release_id": cfg["c2_v1_release"],
        "source_c2_manifest_id": cfg["c2_v1_manifest"],
        "source_c2_manifest_sha256": cfg["c2_v1_manifest_sha256"],
        "lifecycle_state": "RELEASE_FROZEN_LOCAL_CANDIDATE",
        "authority_state": "CANDIDATE",
        "availability_state": "LOCAL_ONLY",
        "active_selector": False,
        "publication_status": "NOT_ATTEMPTED",
        "identity_replay": True,
        "semantic_equivalence": "PASS_ZERO_STATE_OR_TRANSITION_VALUE_DRIFT",
        "state_file_count": role_summary["state_files"],
        "transition_file_count": role_summary["transition_files"],
        "state_record_count": role_summary["state_records"],
        "transition_record_count": role_summary["transition_records"],
        "validation_consumption": "LOCKED_UNCONSUMED",
        "semantic_promotion": "NONE",
        "threshold_change": "NONE",
        "probability_authority": "NONE",
        "risk_authority": "NONE",
        "exposure_authority": "NONE",
        "trading_authority": "NONE",
        "execution_authority": "NONE",
    }
    write_json(root / "release-descriptor.json", descriptor)
    files.append({"path": "release-descriptor.json", "size_bytes": (root / "release-descriptor.json").stat().st_size, "sha256": sha_file(root / "release-descriptor.json")})

    qa = {
        "schema": "ovc-c1c-g5-c2-qa-summary/v1",
        "programme_id": PROGRAMME_ID,
        "gate_id": "C1C-G5",
        "release_id": cfg["c2_v2_release"],
        "status": "PASS",
        "checks": [
            {"check_id": "C1C-G5-C2-01", "status": "PASS", "result": "EXACT_C1_V2_PARENT_FULL_BYTE_VERIFIED"},
            {"check_id": "C1C-G5-C2-02", "status": "PASS", "result": "EXACT_C2_V1_SOURCE_ARTIFACT_FULL_BYTE_VERIFIED"},
            {"check_id": "C1C-G5-C2-03", "status": "PASS", "result": "ALL_C2_PARENT_C1_RECORD_IDS_RESOLVE_TO_C1_V2"},
            {"check_id": "C1C-G5-C2-04", "status": "PASS", "result": "ZERO_STATE_SEMANTIC_DRIFT"},
            {"check_id": "C1C-G5-C2-05", "status": "PASS", "result": "ZERO_TRANSITION_SEMANTIC_DRIFT"},
            {"check_id": "C1C-G5-C2-06", "status": "PASS", "result": "ALL_STATE_AND_TRANSITION_IDENTITIES_RECOMPUTED"},
            {"check_id": "C1C-G5-C2-07", "status": "PASS", "result": "TWO_INDEPENDENT_BYTE_IDENTICAL_MATERIALIZATIONS"},
            {"check_id": "C1C-G5-C2-08", "status": "PASS", "result": "VALIDATION_LOCKED_UNCONSUMED"},
        ],
        "blocking_issues": 0,
        "unresolved_issues": 0,
    }
    write_json(root / "qa/C1C_G5_QA_SUMMARY.json", qa)
    write_json(root / "qa/C1C_G5_ISSUE_LEDGER.json", {"schema": "ovc-c1c-g5-issue-ledger/v1", "gate_id": "C1C-G5", "release_id": cfg["c2_v2_release"], "issues": [], "issue_count": 0, "open_issue_count": 0})
    for relative in ("qa/C1C_G5_QA_SUMMARY.json", "qa/C1C_G5_ISSUE_LEDGER.json"):
        path = root / relative
        files.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha_file(path)})

    manifest_body = {
        "schema": "ovc-c1c-g5-c2-release-manifest/v1",
        "manifest_id": cfg["c2_v2_manifest"],
        "release_id": cfg["c2_v2_release"],
        "source_commit": source_commit,
        "parent_manifests": [
            {"layer": "OPT-A", "release_id": cfg["opt_a_release"], "manifest_id": cfg["opt_a_manifest"], "manifest_sha256": cfg["opt_a_manifest_sha256"]},
            {"layer": "OPT-B.C1", "release_id": cfg["c1_v2_release"], "manifest_id": cfg["c1_v2_manifest"], "manifest_sha256": cfg["c1_v2_manifest_logical_sha256"], "manifest_file_sha256": cfg["c1_v2_manifest_file_sha256"]},
            {"layer": "OPT-B.C2.SOURCE", "release_id": cfg["c2_v1_release"], "manifest_id": cfg["c2_v1_manifest"], "manifest_sha256": cfg["c2_v1_manifest_sha256"]},
        ],
        "files": sorted(files, key=lambda item: item["path"]),
        "file_count": len(files),
        "total_bytes": sum(int(item["size_bytes"]) for item in files),
        "state_record_count": role_summary["state_records"],
        "transition_record_count": role_summary["transition_records"],
        "selector_eligibility": "APPROVED_PENDING_FULL_REMOTE_VERIFICATION_AND_COORDINATED_C1C_G4_G5_TRANSACTION",
        "validation_consumption": "LOCKED_UNCONSUMED",
    }
    manifest = {**manifest_body, "manifest_sha256": hashlib.sha256(canonical_bytes(manifest_body)).hexdigest()}
    write_json(root / "manifest.json", manifest)
    expected = hashlib.sha256(canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_sha256"})).hexdigest()
    if expected != manifest["manifest_sha256"]:
        raise RuntimeError(f"C2_V2_MANIFEST_SELF_HASH_FAILURE:{cfg['role']}")
    return {
        "role": cfg["role"],
        "release_id": cfg["c2_v2_release"],
        "manifest_id": cfg["c2_v2_manifest"],
        "manifest_sha256": manifest["manifest_sha256"],
        "manifest_file_sha256": sha_file(root / "manifest.json"),
        "manifest_bound_file_count": len(files),
        "manifest_bound_bytes": manifest_body["total_bytes"],
        "state_record_count": role_summary["state_records"],
        "transition_record_count": role_summary["transition_records"],
    }


def run_command(*args: str) -> None:
    subprocess.run(args, check=True)


def remote_listing(prefix: str) -> set[str]:
    result = subprocess.run(
        ["rclone", "lsf", "--recursive", "--s3-no-check-bucket", prefix],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"REMOTE_PREFLIGHT_ERROR:{prefix}:{result.stderr.strip()}")
    return {line.rstrip("/") for line in result.stdout.splitlines() if line and not line.endswith("/")}


def stream_remote_hash(remote: str) -> tuple[int, str]:
    process = subprocess.Popen(["rclone", "cat", "--s3-no-check-bucket", remote], stdout=subprocess.PIPE)
    if process.stdout is None:
        raise RuntimeError(f"REMOTE_STREAM_UNAVAILABLE:{remote}")
    digest = hashlib.sha256()
    size = 0
    while True:
        block = process.stdout.read(1024 * 1024)
        if not block:
            break
        size += len(block)
        digest.update(block)
    code = process.wait()
    if code:
        raise RuntimeError(f"REMOTE_READ_FAILED:{remote}:{code}")
    return size, digest.hexdigest()


def publish_candidate(root: Path, candidate: Mapping[str, Any], bucket: str) -> dict[str, Any]:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prefix = f"{bucket}/{candidate['release_id']}/{candidate['manifest_id']}"
    expected = {str(item["path"]) for item in manifest["files"]} | {"manifest.json"}
    existing = remote_listing(prefix)
    if existing and existing != expected:
        missing = sorted(expected - existing)[:5]
        extra = sorted(existing - expected)[:5]
        raise RuntimeError(f"REMOTE_COLLISION:{candidate['role']}:missing={missing}:extra={extra}")
    mode = "EXACT_EXISTING_REVERIFY" if existing else "ABSENT_PUBLISH"
    if not existing:
        for item in manifest["files"]:
            run_command("rclone", "copyto", "--immutable", "--s3-no-check-bucket", str(root / item["path"]), f"{prefix}/{item['path']}")
        run_command("rclone", "copyto", "--immutable", "--s3-no-check-bucket", str(manifest_path), f"{prefix}/manifest.json")
    objects: list[dict[str, Any]] = []
    for item in manifest["files"]:
        remote = f"{prefix}/{item['path']}"
        size, digest = stream_remote_hash(remote)
        if size != int(item["size_bytes"]) or digest != item["sha256"]:
            raise RuntimeError(f"REMOTE_BYTE_MISMATCH:{remote}")
        objects.append({"key": remote.split(":", 1)[1], "size_bytes": size, "sha256": digest})
    manifest_remote = f"{prefix}/manifest.json"
    size, digest = stream_remote_hash(manifest_remote)
    if size != manifest_path.stat().st_size or digest != candidate["manifest_file_sha256"]:
        raise RuntimeError(f"REMOTE_MANIFEST_MISMATCH:{candidate['role']}")
    objects.append({"key": manifest_remote.split(":", 1)[1], "size_bytes": size, "sha256": digest, "completion_marker": True})
    return {
        **candidate,
        "publication_mode": mode,
        "remote_prefix": prefix.split(":", 1)[1] + "/",
        "remote_object_count": len(objects),
        "remote_verified_bytes": sum(int(item["size_bytes"]) for item in objects),
        "remote_verified": True,
        "objects": objects,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute C1C-G5 deterministic C2 v2 identity replay and optional R2 publication.")
    parser.add_argument("--c1-root", type=Path, required=True)
    parser.add_argument("--c2-v1-artifact-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--workflow-run-id", type=int, default=0)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--bucket", default="ovc_r2:ovc-evidence/canonical/releases")
    args = parser.parse_args()

    if args.output_root.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_OUTPUT:{args.output_root}")
    args.output_root.mkdir(parents=True)
    source = source_root(args.c2_v1_artifact_root)
    source_replay, _ = verify_c2_v1_source(source)
    parent_maps = {
        role_key: verify_c1_v2(args.c1_root / role_key, cfg)
        for role_key, cfg in ROLES.items()
    }

    replay_a = args.output_root / "replay-a"
    replay_b = args.output_root / "replay-b"
    summary_a = replay_identity_once(source, replay_a, parent_maps)
    summary_b = replay_identity_once(source, replay_b, parent_maps)
    inventory_a = inventory(replay_a)
    inventory_b = inventory(replay_b)
    if inventory_a != inventory_b or summary_a != summary_b:
        raise RuntimeError("C2_V2_DETERMINISTIC_REPLAY_MISMATCH")
    replay_tree_sha256 = hashlib.sha256(canonical_bytes(inventory_a)).hexdigest()

    candidate_root = args.output_root / "candidates"
    candidates = [
        build_candidate(role_key, replay_a, source, candidate_root, args.source_commit, summary_a)
        for role_key in ("discovery", "development")
    ]
    candidate_tree_sha256 = hashlib.sha256(canonical_bytes(inventory(candidate_root))).hexdigest()

    local_receipt = {
        "schema": "ovc-c1c-g5-c2-v2-local-identity-replay/v1",
        "programme_id": PROGRAMME_ID,
        "gate_id": "C1C-G5",
        "status": "PASS_LOCAL_C2_V2_IDENTITY_REPLAY_ZERO_SEMANTIC_DRIFT",
        "source_commit": args.source_commit,
        "source_c2_v1": SOURCE,
        "source_replay_receipt": source_replay,
        "source_intake_receipt_sha256": SOURCE["intake_receipt_sha256"],
        "c1_v2_parent_counts": {key: len(value) for key, value in parent_maps.items()},
        "replay": summary_a,
        "deterministic_output_equivalence": "PASS_TWO_INDEPENDENT_BYTE_IDENTICAL_MATERIALIZATIONS",
        "replay_tree_sha256": replay_tree_sha256,
        "candidate_tree_sha256": candidate_tree_sha256,
        "candidates": candidates,
        "semantic_state_drift_count": 0,
        "semantic_transition_drift_count": 0,
        "validation_consumption": "LOCKED_UNCONSUMED",
        "semantic_promotion": "NONE",
        "threshold_change": "NONE",
        "probability": "NONE",
        "risk": "NONE",
        "exposure": "NONE",
        "trading": "NONE",
        "execution": "NONE",
    }
    write_json(args.output_root / "evidence/C1C_G5_LOCAL_REPLAY_RECEIPT.json", local_receipt)

    if not args.publish:
        print(json.dumps({"status": local_receipt["status"], "replay_tree_sha256": replay_tree_sha256, "candidate_tree_sha256": candidate_tree_sha256}, indent=2, sort_keys=True))
        return 0

    published = [
        publish_candidate(candidate_root / role_key, candidate, args.bucket)
        for role_key, candidate in zip(("discovery", "development"), candidates)
    ]
    receipt = {
        "schema": "ovc-c1c-g5-c2-v2-publication-verification/v1",
        "programme_id": PROGRAMME_ID,
        "gate_id": "C1C-G5",
        "decision": "PASS",
        "status": "PASS_C2_V2_IDENTITY_REPLAY_PUBLICATION_FULL_REMOTE_BYTE_VERIFICATION",
        "workflow_run_id": args.workflow_run_id or int(os.environ.get("GITHUB_RUN_ID", "0")),
        "workflow_commit": args.source_commit,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_c2_v1": SOURCE,
        "source_c1_v2_publication_workflow_run_id": 30384400312,
        "source_c1_v2_remote_object_count": 194,
        "source_c1_v2_remote_verified_bytes": 36_206_001,
        "replay_tree_sha256": replay_tree_sha256,
        "candidate_tree_sha256": candidate_tree_sha256,
        "deterministic_output_equivalence": "PASS_TWO_INDEPENDENT_BYTE_IDENTICAL_MATERIALIZATIONS",
        "semantic_state_drift_count": 0,
        "semantic_transition_drift_count": 0,
        "state_record_count": summary_a["state_records"],
        "transition_record_count": summary_a["transition_records"],
        "release_count": len(published),
        "remote_object_count": sum(int(item["remote_object_count"]) for item in published),
        "remote_verified_bytes_including_manifests": sum(int(item["remote_verified_bytes"]) for item in published),
        "publication_order": "PAYLOAD_FIRST_MANIFEST_LAST",
        "releases": published,
        "c1_selector_change": "PENDING_COORDINATED_C1C_G4_G5_REPOSITORY_TRANSACTION",
        "c2_selector_change": "PENDING_COORDINATED_C1C_G4_G5_REPOSITORY_TRANSACTION",
        "pilot_action": "PENDING_APPEND_ONLY_SUPERSESSION_AND_RERUN",
        "canonical_pattern_discovery_append": "DENIED",
        "validation_consumption": "LOCKED_UNCONSUMED",
        "semantic_promotion": "NONE",
        "family_promotion": "NONE",
        "novelty_promotion": "NONE",
        "threshold_change": "NONE",
        "probability": "NONE",
        "risk": "NONE",
        "exposure": "NONE",
        "trading": "NONE",
        "execution": "NONE",
        "agent_write": "NONE",
    }
    write_json(args.output_root / "evidence/C1C_G5_C2_V2_REMOTE_VERIFICATION_RECEIPT.json", receipt)
    print(json.dumps({
        "status": receipt["status"],
        "workflow_run_id": receipt["workflow_run_id"],
        "state_records": receipt["state_record_count"],
        "transition_records": receipt["transition_record_count"],
        "remote_objects": receipt["remote_object_count"],
        "remote_bytes": receipt["remote_verified_bytes_including_manifests"],
        "releases": [
            {"role": item["role"], "release_id": item["release_id"], "manifest_id": item["manifest_id"], "manifest_sha256": item["manifest_sha256"], "manifest_file_sha256": item["manifest_file_sha256"]}
            for item in published
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
