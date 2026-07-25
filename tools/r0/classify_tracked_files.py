from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

BASELINE_COMMIT = "c0ad7ba22618babdde731e2a338f68f688d4210c"
QUARANTINE_ROOT = "legacy/quarantine/abcd-engine-v1-c0ad7ba"
CLASSIFICATIONS = {
    "RETAIN_ACTIVE",
    "RETAIN_HISTORICAL",
    "MOVE_TO_QUARANTINE",
    "REBUILD_V2",
    "REMOVE_GENERATED",
    "UNRESOLVED",
}

ROOT_RETAIN_ACTIVE = {
    ".gitattributes",
    ".gitignore",
    "CONTRIBUTING.md",
    "LICENSE",
    "LICENSE.md",
}
ROOT_REBUILD_V2 = {"README.md", "pyproject.toml"}
ACTIVE_DOCS = {
    "artifacts/README.md",
    "data/EXTERNAL_DEPENDENCIES.md",
    "data/README.md",
    "docs/EVIDENCE_STORE.md",
}
REBUILD_DOCS = {"docs/CURRENT_STATUS.md"}
ACTIVE_TESTS = {"tests/test_evidence_store.py"}


def _classify(path: str) -> tuple[str, str, str]:
    """Return classification, rule ID and a concise authority rationale."""
    if path in ROOT_RETAIN_ACTIVE:
        return (
            "RETAIN_ACTIVE",
            "R0C-ROOT-GENERAL",
            "Repository-level control or contribution file remains valid for the v2 foundation.",
        )
    if path in ROOT_REBUILD_V2:
        return (
            "REBUILD_V2",
            "R0C-ROOT-SEMANTIC",
            "Active repository metadata must be rewritten to describe the v2 discovery foundation.",
        )
    if path.startswith(".github/"):
        return (
            "RETAIN_ACTIVE",
            "R0C-GITHUB-CONTROL",
            "Repository automation remains active unless separately superseded by a reviewed workflow change.",
        )
    if path in ACTIVE_DOCS:
        return (
            "RETAIN_ACTIVE",
            "R0C-EVIDENCE-BOUNDARY",
            "Evidence-store or Git/external-artifact boundary documentation remains authoritative infrastructure.",
        )
    if path in REBUILD_DOCS:
        return (
            "REBUILD_V2",
            "R0C-CURRENT-STATUS",
            "Current-status authority must be replaced atomically during the v2 scaffold packet.",
        )
    if path == "docs/IMPORT_PROVENANCE.md":
        return (
            "RETAIN_HISTORICAL",
            "R0C-IMPORT-PROVENANCE",
            "Import provenance remains an immutable historical court record and grants no active model authority.",
        )
    if path.startswith("docs/history/"):
        return (
            "RETAIN_HISTORICAL",
            "R0C-HISTORY",
            "Historical releases, decisions and evidence remain in place and immutable.",
        )
    if path.startswith("docs/architecture/"):
        return (
            "RETAIN_HISTORICAL",
            "R0C-ARCHITECTURE-HISTORY",
            "Prior architecture and development summaries remain source material, not active implementation authority.",
        )
    if path.startswith("docs/"):
        return (
            "RETAIN_HISTORICAL",
            "R0C-DOC-CONSERVATIVE",
            "Legacy documentation is retained for audit and crosswalk use without active selector or runtime authority.",
        )
    if path.startswith("src/ovc_evidence_store/"):
        return (
            "RETAIN_ACTIVE",
            "R0C-EVIDENCE-STORE",
            "The tested deterministic manifest, immutable upload and byte-verification package remains active infrastructure.",
        )
    if path in ACTIVE_TESTS:
        return (
            "RETAIN_ACTIVE",
            "R0C-EVIDENCE-STORE-TEST",
            "The evidence-store regression suite remains required for the v2 foundation.",
        )
    if path.startswith("contracts/"):
        return (
            "MOVE_TO_QUARANTINE",
            "R0C-LEGACY-CONTRACT",
            "Current contracts encode the superseded mixed ABCD authority and must leave the active contract namespace.",
        )
    if path.startswith("scripts/"):
        return (
            "MOVE_TO_QUARANTINE",
            "R0C-LEGACY-SCRIPT",
            "Current scripts execute or validate the superseded ABCD discovery and evidence programme.",
        )
    if path.startswith("src/"):
        return (
            "MOVE_TO_QUARANTINE",
            "R0C-LEGACY-SOURCE",
            "All source packages except ovc_evidence_store belong to the superseded engine and cannot remain importable.",
        )
    if path.startswith("tests/"):
        return (
            "MOVE_TO_QUARANTINE",
            "R0C-LEGACY-TEST",
            "Tests tied to the superseded ABCD engine move with that implementation and are excluded from active discovery.",
        )
    if path.startswith(("schemas/", "schema/", "registries/", "registry/", "config/", "configs/", "fixtures/", "examples/")):
        return (
            "MOVE_TO_QUARANTINE",
            "R0C-LEGACY-SUPPORT",
            "Supporting model artifacts are coupled to the superseded engine and must be rebuilt in explicit v2 namespaces.",
        )
    if path.startswith("notebooks/"):
        return (
            "RETAIN_HISTORICAL",
            "R0C-NOTEBOOK-HISTORY",
            "Research notebooks are preserved as historical observations but cannot supply active facts or discovery seeds.",
        )
    if "/" not in path:
        return (
            "RETAIN_ACTIVE",
            "R0C-ROOT-FALLBACK",
            "Unrecognised root control file is retained; runtime authority still requires an explicit v2 registry entry.",
        )
    return (
        "MOVE_TO_QUARANTINE",
        "R0C-CONSERVATIVE-QUARANTINE",
        "Unrecognised non-historical subtree is conservatively removed from the active tree pending a future explicit rebuild decision.",
    )


def _canonical_json(document: Any) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path}")
    return value


def build_classification(inventory_path: Path, hashes_path: Path) -> dict[str, Any]:
    inventory = _load(inventory_path)
    hashes = _load(hashes_path)
    if inventory.get("baseline_commit") != BASELINE_COMMIT:
        raise ValueError("inventory baseline does not match approved R0 baseline")
    if hashes.get("baseline_commit") != BASELINE_COMMIT:
        raise ValueError("hash ledger baseline does not match approved R0 baseline")

    inventory_files = inventory.get("files")
    hash_files = hashes.get("files")
    if not isinstance(inventory_files, list) or not isinstance(hash_files, list):
        raise ValueError("inventory and hash ledgers must contain file lists")

    hash_by_path = {item["path"]: item for item in hash_files}
    if len(hash_by_path) != len(hash_files):
        raise ValueError("duplicate path in hash ledger")

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in inventory_files:
        path = item["path"]
        PurePosixPath(path)
        if path in seen:
            raise ValueError(f"duplicate inventory path: {path}")
        seen.add(path)
        hash_item = hash_by_path.get(path)
        if hash_item is None:
            raise ValueError(f"path missing from hash ledger: {path}")
        for field in ("git_blob_sha1", "size_bytes"):
            if item[field] != hash_item[field]:
                raise ValueError(f"inventory/hash mismatch for {path}: {field}")

        classification, rule_id, rationale = _classify(path)
        if classification not in CLASSIFICATIONS:
            raise AssertionError(f"unknown classification {classification}")
        target_path: str | None
        if classification == "MOVE_TO_QUARANTINE":
            target_path = f"{QUARANTINE_ROOT}/{path}"
        elif classification == "REMOVE_GENERATED":
            target_path = None
        else:
            target_path = path
        rows.append(
            {
                "classification": classification,
                "git_blob_sha1": item["git_blob_sha1"],
                "mode": item["mode"],
                "path": path,
                "rationale": rationale,
                "rule_id": rule_id,
                "sha256": hash_item["sha256"],
                "size_bytes": item["size_bytes"],
                "target_path": target_path,
            }
        )

    if set(hash_by_path) != seen:
        extra = sorted(set(hash_by_path) - seen)
        raise ValueError(f"hash ledger contains paths absent from inventory: {extra[:5]}")
    rows.sort(key=lambda row: row["path"].encode("utf-8"))
    counts = Counter(row["classification"] for row in rows)
    if len(rows) != inventory.get("file_count") or len(rows) != hashes.get("file_count"):
        raise ValueError("classified count does not match frozen ledger count")
    if counts["UNRESOLVED"]:
        raise ValueError("R0-2 cannot pass with unresolved classifications")

    return {
        "baseline_commit": BASELINE_COMMIT,
        "classification_schema": "ovc-r0-tracked-file-classification/v1",
        "classified_file_count": len(rows),
        "counts": {name: counts.get(name, 0) for name in sorted(CLASSIFICATIONS)},
        "decision_state": "CLASSIFIED_NO_MOVES_EXECUTED",
        "quarantine_root": QUARANTINE_ROOT,
        "records": rows,
        "rules_version": "R0C-0.1",
    }


def write_outputs(document: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_text = _canonical_json(document)
    (output_dir / "TRACKED_FILE_CLASSIFICATION.json").write_text(json_text, encoding="utf-8")

    fields = [
        "path",
        "classification",
        "target_path",
        "rule_id",
        "rationale",
        "mode",
        "size_bytes",
        "git_blob_sha1",
        "sha256",
    ]
    with (output_dir / "TRACKED_FILE_CLASSIFICATION.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in document["records"]:
            writer.writerow({field: row.get(field) for field in fields})

    move_records = [row for row in document["records"] if row["classification"] == "MOVE_TO_QUARANTINE"]
    move_plan = {
        "baseline_commit": BASELINE_COMMIT,
        "classification_sha256": hashlib.sha256(json_text.encode("utf-8")).hexdigest(),
        "move_count": len(move_records),
        "moves_executed": False,
        "quarantine_root": QUARANTINE_ROOT,
        "records": [
            {
                "git_blob_sha1": row["git_blob_sha1"],
                "source_path": row["path"],
                "target_path": row["target_path"],
            }
            for row in move_records
        ],
    }
    (output_dir / "QUARANTINE_MOVE_PLAN.json").write_text(_canonical_json(move_plan), encoding="utf-8")

    counts = document["counts"]
    total_bytes = Counter()
    for row in document["records"]:
        total_bytes[row["classification"]] += row["size_bytes"]
    summary = [
        "# R0-2 Tracked-File Classification Summary",
        "",
        f"- Baseline: `{BASELINE_COMMIT}`",
        f"- Files classified: **{document['classified_file_count']}**",
        "- Unresolved files: **0**",
        "- Files moved in R0-2: **0**",
        f"- Quarantine destination reserved: `{QUARANTINE_ROOT}/`",
        "- Decision state: `CLASSIFIED_NO_MOVES_EXECUTED`",
        "",
        "| Classification | Files | Frozen blob bytes | R0-2 consequence |",
        "|---|---:|---:|---|",
    ]
    consequences = {
        "RETAIN_ACTIVE": "Remain in the active tree as infrastructure or repository control.",
        "RETAIN_HISTORICAL": "Remain immutable and addressable without active model authority.",
        "MOVE_TO_QUARANTINE": "Approved for an exact-path move during R0-3; not moved yet.",
        "REBUILD_V2": "Stay in place until replaced atomically by the v2 scaffold.",
        "REMOVE_GENERATED": "Approved for removal only during a later bounded packet.",
        "UNRESOLVED": "Blocks progression.",
    }
    for name in sorted(CLASSIFICATIONS):
        summary.append(
            f"| `{name}` | {counts[name]} | {total_bytes[name]} | {consequences[name]} |"
        )
    summary.extend(
        [
            "",
            "## Classification principles",
            "",
            "- `docs/history/` and prior architecture records remain historical court records and are not moved.",
            "- `src/ovc_evidence_store/`, its test and evidence-store boundary documentation remain active infrastructure.",
            "- Existing ABCD contracts, source packages, scripts and associated tests are assigned to quarantine.",
            "- `README.md`, `pyproject.toml` and `docs/CURRENT_STATUS.md` are marked for atomic v2 rewrite rather than deletion.",
            "- No old story, threshold, state, outcome or candidate receives active authority through retention.",
            "",
            "## R0-2 result",
            "",
            "**PASS — every frozen baseline file has exactly one classification and no repository path was moved.**",
            "",
        ]
    )
    (output_dir / "CLASSIFICATION_SUMMARY.md").write_text("\n".join(summary), encoding="utf-8")

    validation = {
        "baseline_commit": BASELINE_COMMIT,
        "classification_sha256": hashlib.sha256(json_text.encode("utf-8")).hexdigest(),
        "classified_file_count": document["classified_file_count"],
        "counts_sum": sum(document["counts"].values()),
        "duplicate_source_paths": 0,
        "duplicate_quarantine_targets": len(move_records)
        - len({row["target_path"] for row in move_records}),
        "move_operations_executed": 0,
        "result": "PASS",
        "unresolved_count": document["counts"]["UNRESOLVED"],
    }
    if validation["duplicate_quarantine_targets"] != 0:
        raise ValueError("duplicate quarantine targets generated")
    (output_dir / "R0_2_VALIDATION.json").write_text(_canonical_json(validation), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify every file in the frozen R0 baseline")
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--hashes", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    document = build_classification(args.inventory, args.hashes)
    write_outputs(document, args.output_dir)
    print(json.dumps(document["counts"], sort_keys=True))
    print(f"classified {document['classified_file_count']} files; unresolved=0; moves_executed=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
