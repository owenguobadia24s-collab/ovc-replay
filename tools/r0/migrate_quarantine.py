from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

BASELINE = "c0ad7ba22618babdde731e2a338f68f688d4210c"
PACKET_ROOT = Path("docs/history/repository-freezes/ovc-replay-v1-c0ad7ba")
CLASSIFICATION_PATH = PACKET_ROOT / "TRACKED_FILE_CLASSIFICATION.json"
MOVE_PLAN_PATH = PACKET_ROOT / "QUARANTINE_MOVE_PLAN.json"
QUARANTINE_ROOT = Path("legacy/quarantine/abcd-engine-v1-c0ad7ba")


def _run(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_plan(classification: dict[str, Any], move_plan: dict[str, Any]) -> list[dict[str, Any]]:
    if classification.get("baseline_commit") != BASELINE:
        raise SystemExit("classification baseline does not match approved freeze")
    if move_plan.get("baseline_commit") != BASELINE:
        raise SystemExit("move-plan baseline does not match approved freeze")
    if classification.get("counts", {}).get("UNRESOLVED") != 0:
        raise SystemExit("classification contains unresolved paths")
    if move_plan.get("moves_executed") is not False:
        raise SystemExit("move plan is not in the approved unexecuted state")
    if move_plan.get("quarantine_root") != QUARANTINE_ROOT.as_posix():
        raise SystemExit("unexpected quarantine root")

    classified_moves = {
        record["path"]: record
        for record in classification["records"]
        if record["classification"] == "MOVE_TO_QUARANTINE"
    }
    records = move_plan.get("records", [])
    if len(records) != 106 or len(classified_moves) != 106:
        raise SystemExit("R0-3 requires exactly 106 approved moves")

    seen_sources: set[str] = set()
    seen_targets: set[str] = set()
    for record in records:
        source = record["source_path"]
        target = record["target_path"]
        if source in seen_sources or target in seen_targets:
            raise SystemExit(f"duplicate move path: {source} -> {target}")
        seen_sources.add(source)
        seen_targets.add(target)
        classified = classified_moves.get(source)
        if classified is None:
            raise SystemExit(f"move not present in classification: {source}")
        if target != classified["target_path"]:
            raise SystemExit(f"target mismatch for {source}")
        if record["git_blob_sha1"] != classified["git_blob_sha1"]:
            raise SystemExit(f"blob mismatch in packet for {source}")
        if not target.startswith(QUARANTINE_ROOT.as_posix() + "/"):
            raise SystemExit(f"target escapes quarantine root: {target}")
    return records


def _verify_completed(move_plan: dict[str, Any]) -> None:
    validation = _read_json(PACKET_ROOT / "R0_3_VALIDATION.json")
    if validation.get("result") != "PASS" or validation.get("executed_move_count") != 106:
        raise SystemExit("completed migration lacks a passing validation packet")
    records = move_plan.get("records", [])
    if len(records) != 106:
        raise SystemExit("completed migration does not contain 106 move records")
    for record in records:
        source = Path(record["source_path"])
        target = Path(record["target_path"])
        if source.exists():
            raise SystemExit(f"quarantined source unexpectedly restored: {source}")
        if not target.is_file():
            raise SystemExit(f"quarantine target missing: {target}")
        if _run("git", "hash-object", "--", target.as_posix()) != record["git_blob_sha1"]:
            raise SystemExit(f"quarantine blob drift detected: {target}")
    print("R0-3 already complete; verified 106 quarantined paths and unchanged blobs")


def migrate() -> None:
    classification = _read_json(CLASSIFICATION_PATH)
    move_plan = _read_json(MOVE_PLAN_PATH)
    if move_plan.get("moves_executed") is True:
        _verify_completed(move_plan)
        return
    records = _validate_plan(classification, move_plan)

    manifest_records: list[dict[str, Any]] = []
    for record in records:
        source = Path(record["source_path"])
        target = Path(record["target_path"])
        if not source.is_file():
            raise SystemExit(f"approved source missing: {source}")
        if target.exists():
            raise SystemExit(f"quarantine target already exists: {target}")

        actual_blob = _run("git", "hash-object", "--", source.as_posix())
        if actual_blob != record["git_blob_sha1"]:
            raise SystemExit(f"source blob changed since freeze: {source}")

        classified = next(item for item in classification["records"] if item["path"] == source.as_posix())
        if _sha256(source) != classified["sha256"]:
            raise SystemExit(f"source SHA-256 changed since freeze: {source}")

        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call(["git", "mv", "--", source.as_posix(), target.as_posix()])
        moved_blob = _run("git", "hash-object", "--", target.as_posix())
        if moved_blob != record["git_blob_sha1"]:
            raise SystemExit(f"moved blob differs from frozen source: {target}")

        manifest_records.append(
            {
                "source_path": source.as_posix(),
                "target_path": target.as_posix(),
                "git_blob_sha1": moved_blob,
                "sha256": classified["sha256"],
                "size_bytes": classified["size_bytes"],
                "classification_rule_id": classified["rule_id"],
            }
        )

    source_remaining = [record["source_path"] for record in records if Path(record["source_path"]).exists()]
    target_missing = [record["target_path"] for record in records if not Path(record["target_path"]).is_file()]
    if source_remaining or target_missing:
        raise SystemExit("post-move source/target invariant failed")

    QUARANTINE_ROOT.mkdir(parents=True, exist_ok=True)
    _write_json(
        QUARANTINE_ROOT / "QUARANTINE_MANIFEST.json",
        {
            "schema": "ovc-r0-quarantine-manifest/v1",
            "baseline_commit": BASELINE,
            "classification_sha256": move_plan["classification_sha256"],
            "authority_state": "HISTORICAL_QUARANTINED",
            "move_count": len(manifest_records),
            "records": manifest_records,
        },
    )

    with (QUARANTINE_ROOT / "ORIGINAL_PATH_CROSSWALK.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source_path", "target_path", "git_blob_sha1", "sha256", "size_bytes"],
        )
        writer.writeheader()
        for record in manifest_records:
            writer.writerow({key: record[key] for key in writer.fieldnames})

    (QUARANTINE_ROOT / "AUTHORITY_DENYLIST.yaml").write_text(
        "authority_state: HISTORICAL_QUARANTINED\n"
        "package_discovery: EXCLUDED\n"
        "test_discovery: EXCLUDED\n"
        "selector_eligibility: DENIED\n"
        "runtime_imports: DENIED\n"
        "release_parent_eligibility: DENIED\n"
        "rollback_target: DENIED\n"
        "discovery_seed_eligibility: DENIED\n",
        encoding="utf-8",
    )
    (QUARANTINE_ROOT / "QUARANTINE_README.md").write_text(
        "# Historical ABCD Engine Quarantine\n\n"
        f"This directory contains {len(manifest_records)} exact Git moves from the frozen repository baseline "
        f"`{BASELINE}`. File bytes are unchanged; original and quarantine paths are recorded in "
        "`QUARANTINE_MANIFEST.json` and `ORIGINAL_PATH_CROSSWALK.csv`.\n\n"
        "These files exist only for historical audit, source crosswalks, defect-fixture derivation and legacy-result "
        "reference. They are not active packages, tests, selectors, release parents, rollback targets, parameter "
        "sources or discovery seeds. Historical release records remain under `docs/history/` and were not moved.\n",
        encoding="utf-8",
    )

    move_plan["moves_executed"] = True
    move_plan["execution_state"] = "EXACT_PATHS_MOVED_TO_HISTORICAL_QUARANTINE"
    move_plan["executed_move_count"] = len(manifest_records)
    move_plan["quarantine_manifest"] = (QUARANTINE_ROOT / "QUARANTINE_MANIFEST.json").as_posix()
    _write_json(MOVE_PLAN_PATH, move_plan)

    classification["decision_state"] = "CLASSIFIED_AND_QUARANTINED"
    classification["move_operations_executed"] = len(manifest_records)
    _write_json(CLASSIFICATION_PATH, classification)

    _write_json(
        PACKET_ROOT / "R0_3_VALIDATION.json",
        {
            "baseline_commit": BASELINE,
            "approved_move_count": 106,
            "executed_move_count": len(manifest_records),
            "source_paths_remaining": 0,
            "quarantine_targets_missing": 0,
            "duplicate_source_paths": 0,
            "duplicate_target_paths": 0,
            "blob_identity_verified": True,
            "sha256_identity_verified": True,
            "historical_release_tree_moved": False,
            "result": "PASS",
        },
    )
    (PACKET_ROOT / "R0_3_QUARANTINE_MIGRATION_SUMMARY.md").write_text(
        "# R0-3 Exact-Path Quarantine Migration\n\n"
        f"- Approved moves: **{len(manifest_records)}**\n"
        f"- Executed moves: **{len(manifest_records)}**\n"
        "- Source paths remaining: **0**\n"
        "- Missing quarantine targets: **0**\n"
        "- Byte identity: **PASS**\n"
        "- Git blob identity: **PASS**\n"
        "- Historical `docs/history/` release records moved: **0**\n"
        "- Authority state: `HISTORICAL_QUARANTINED`\n\n"
        "No provider intake, R2 publication, selector activation or new market authority was introduced.\n\n"
        "**R0-3 structural result: PASS**\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate"])
    args = parser.parse_args()
    if args.command == "migrate":
        migrate()
