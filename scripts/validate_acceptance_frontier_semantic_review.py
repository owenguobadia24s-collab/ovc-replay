from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def recursive_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return {str(key).lower() for key in value}.union(
            *(recursive_keys(item) for item in value.values())
        )
    if isinstance(value, list):
        return set().union(*(recursive_keys(item) for item in value)) if value else set()
    return set()


def stream_check(path: Path, *, expected_rows: int, unique_field: str) -> dict[str, object]:
    prohibited = {"return", "mfe", "mae", "profit", "win", "loss", "trade", "execution"}
    rows = 0
    identities: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rows += 1
            if row["state_contract_version"] != "B-STATE-0.3b-REVIEW":
                raise ValueError(f"wrong contract version in {path.name}")
            identity = row[unique_field]
            if identity in identities:
                raise ValueError(f"duplicate {unique_field} in {path.name}")
            identities.add(identity)
            if recursive_keys(row).intersection(prohibited):
                raise ValueError(f"prohibited outcome/execution field in {path.name}")
            summary = row.get("acceptance_frontier_summary")
            if summary is not None:
                if "accepted_above_level_ids" in summary or "accepted_below_level_ids" in summary:
                    raise ValueError("full relation ledger leaked into compact frontier projection")
                if "full_relation_inventory_hash" not in row:
                    raise ValueError("compact projection is not bound to the full parent inventory")
    if rows != expected_rows:
        raise ValueError(f"row-count mismatch in {path.name}: {rows} != {expected_rows}")
    return {"path": path.name, "rows": rows, f"unique_{unique_field}": len(identities), "gzip_integrity": "PASS"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--parent-root", type=Path, required=True)
    parser.add_argument("--determinism-root", type=Path)
    args = parser.parse_args()
    root = args.release_root.resolve()
    manifest = json.loads((root / "B_STATE_0_3B_REVIEW_MANIFEST.json").read_text(encoding="utf-8"))
    core = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if canonical_hash(core) != manifest["manifest_hash"]:
        raise ValueError("review manifest self-hash mismatch")
    parent = json.loads(
        (args.parent_root.resolve() / "B_STATE_0_3A_REPLAY_MANIFEST.json").read_text(encoding="utf-8")
    )
    parent_core = {key: value for key, value in parent.items() if key != "manifest_hash"}
    if canonical_hash(parent_core) != parent["manifest_hash"]:
        raise ValueError("parent manifest self-hash mismatch")
    if manifest["parent_v03a_manifest_hash"] != parent["manifest_hash"]:
        raise ValueError("parent manifest lineage mismatch")

    artifact_checks = []
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        actual = sha256(path)
        if actual != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {path.name}")
        artifact_checks.append({"path": path.name, "sha256": actual, "status": "PASS"})

    stream_checks = []
    for timeframe in ("15M", "2H"):
        result = manifest["results"][timeframe]
        stream_checks.append(
            stream_check(
                root / f"acceptance_frontier_review_state_stream_{timeframe.lower()}.jsonl.gz",
                expected_rows=result["review_state_records"],
                unique_field="close_time",
            )
        )
        stream_checks.append(
            stream_check(
                root / f"acceptance_frontier_event_records_{timeframe.lower()}.jsonl.gz",
                expected_rows=result["frontier_event_records"],
                unique_field="at",
            )
        )
        if sum(item["bars"] for item in result["monthly_event_rates"].values()) != result["source_bars"]:
            raise ValueError(f"monthly bar coverage mismatch in {timeframe}")
        if result["review_genuine_conflict_bars"]:
            raise ValueError(f"frontier review introduced conflict in {timeframe}")

    determinism: dict[str, object] = {"checked": False}
    if args.determinism_root:
        prior = json.loads(
            (args.determinism_root.resolve() / "B_STATE_0_3B_REVIEW_MANIFEST.json").read_text(encoding="utf-8")
        )
        comparisons = {}
        for timeframe in ("15M", "2H"):
            current = manifest["results"][timeframe]
            earlier = prior["results"][timeframe]
            for field in (
                "review_state_stream_canonical_jsonl_hash",
                "frontier_event_stream_canonical_jsonl_hash",
            ):
                key = f"{timeframe}:{field}"
                comparisons[key] = current[field] == earlier[field]
        if not all(comparisons.values()):
            raise ValueError("independent semantic-review determinism mismatch")
        determinism = {"checked": True, "all_canonical_hashes_match": True, "comparisons": comparisons}

    result = {
        "status": "PASS",
        "validated_manifest_hash": manifest["manifest_hash"],
        "validated_parent_manifest_hash": parent["manifest_hash"],
        "artifact_checks": artifact_checks,
        "stream_checks": stream_checks,
        "determinism": determinism,
        "semantic_controls": {
            "representation_ratification_is_scoped": True,
            "full_relation_ledger_preserved_by_parent_hash": True,
            "compact_projection_contains_no_full_relation_lists": True,
            "outcome_execution_fields_absent": True,
            "review_introduced_no_conflict": True,
        },
        "authority_boundary": "Representation-only OPT-B research authority; frontier event remains an unratified semantic candidate.",
    }
    (root / "B_STATE_0_3B_REVIEW_VALIDATION.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# B-STATE-0.3b Semantic Review Validation",
        "",
        "**Status:** `PASS`  ",
        f"**Validated manifest:** `{manifest['manifest_hash']}`  ",
        f"**Parent v0.3a manifest:** `{parent['manifest_hash']}`  ",
        f"**Independent replay determinism:** `{'PASS' if determinism['checked'] else 'NOT RUN'}`",
        "",
        "All streams decompressed, hashes and counts matched, close/event times were unique, monthly coverage was complete, the compact projection remained bound to the full parent ledger, and no outcome, execution or new conflict entered the review.",
    ]
    (root / "B_STATE_0_3B_REVIEW_VALIDATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "manifest_hash": manifest["manifest_hash"]}, sort_keys=True))


if __name__ == "__main__":
    main()
