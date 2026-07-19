from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from itertools import zip_longest
from pathlib import Path


CONTRACT_VERSION = "B-STATE-0.3b"
RATIFICATION_ID = "B-STATE-0.3b-FRONTIER-ACTIVE-RESEARCH"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def verify_manifest(root: Path, name: str) -> dict[str, object]:
    manifest = json.loads((root / name).read_text(encoding="utf-8"))
    core = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if canonical_hash(core) != manifest["manifest_hash"]:
        raise ValueError(f"manifest self-hash mismatch: {name}")
    return manifest


def recursive_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key).lower() for key in value}
        for item in value.values():
            keys.update(recursive_keys(item))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(recursive_keys(item))
        return keys
    return set()


def stream_check(
    path: Path,
    *,
    expected_rows: int,
    identity_fields: tuple[str, ...],
) -> tuple[dict[str, object], set[tuple[object, ...]]]:
    prohibited = {"return", "mfe", "mae", "profit", "win", "loss", "trade", "execution"}
    identities: set[tuple[object, ...]] = set()
    rows = 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rows += 1
            if row["state_contract_version"] != CONTRACT_VERSION:
                raise ValueError(f"wrong contract version in {path.name}")
            if row["ratification_id"] != RATIFICATION_ID:
                raise ValueError(f"wrong ratification ID in {path.name}")
            identity = tuple(row[field] for field in identity_fields)
            if identity in identities:
                raise ValueError(f"duplicate identity in {path.name}: {identity}")
            identities.add(identity)
            if recursive_keys(row).intersection(prohibited):
                raise ValueError(f"outcome/execution field in {path.name}")
            summary = row.get("acceptance_frontier_summary")
            if summary is not None:
                if "accepted_above_level_ids" in summary or "accepted_below_level_ids" in summary:
                    raise ValueError("full relation inventory leaked into compact projection")
                if "full_relation_inventory_hash" not in row:
                    raise ValueError("compact row lacks full-ledger binding")
    if rows != expected_rows:
        raise ValueError(f"row-count mismatch in {path.name}: {rows} != {expected_rows}")
    return (
        {"path": path.name, "rows": rows, "unique_identities": len(identities), "gzip_integrity": "PASS"},
        identities,
    )


def cross_check_parent(state_path: Path, parent_path: Path) -> dict[str, int]:
    rows = hashes = axes = 0
    with gzip.open(state_path, "rt", encoding="utf-8") as state_handle:
        with gzip.open(parent_path, "rt", encoding="utf-8") as parent_handle:
            for state_line, parent_line in zip_longest(state_handle, parent_handle):
                if state_line is None or parent_line is None:
                    raise ValueError("ratified/parent row cardinality mismatch")
                state = json.loads(state_line)
                parent = json.loads(parent_line)
                rows += 1
                if state["close_time"] != parent["close_time"]:
                    raise ValueError("ratified/parent timestamp mismatch")
                if state["parent_v03a_state_record_id"] != parent["state_record_id"]:
                    raise ValueError("ratified/parent record lineage mismatch")
                if state["full_relation_inventory_hash"] != canonical_hash(parent["acceptance_relation_inventory"]):
                    raise ValueError("ratified compact projection/full inventory mismatch")
                hashes += 1
                for field in (
                    "displacement_state",
                    "compression_state",
                    "interaction_state",
                    "interaction_components",
                    "quality_state",
                ):
                    if state[field] != parent[field]:
                        raise ValueError(f"ratified non-acceptance axis mismatch: {field}")
                axes += 1
    return {"rows": rows, "parent_inventory_hash_matches": hashes, "non_acceptance_axis_matches": axes}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--parent-root", type=Path, required=True)
    parser.add_argument("--determinism-root", type=Path)
    args = parser.parse_args()
    root = args.release_root.resolve()
    review_root = args.review_root.resolve()
    parent_root = args.parent_root.resolve()
    manifest = verify_manifest(root, "B_STATE_0_3B_RATIFIED_MANIFEST.json")
    review = verify_manifest(review_root, "B_STATE_0_3B_REVIEW_MANIFEST.json")
    parent = verify_manifest(parent_root, "B_STATE_0_3A_REPLAY_MANIFEST.json")
    if manifest["semantic_review_manifest_hash"] != review["manifest_hash"]:
        raise ValueError("ratified/review manifest lineage mismatch")
    if manifest["parent_v03a_manifest_hash"] != parent["manifest_hash"]:
        raise ValueError("ratified/parent manifest lineage mismatch")

    artifact_checks = []
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        actual = sha256(path)
        if actual != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {path.name}")
        artifact_checks.append({"path": path.name, "sha256": actual, "status": "PASS"})

    stream_checks = []
    lineage_checks = {}
    for timeframe in ("15M", "2H"):
        result = manifest["results"][timeframe]
        suffix = timeframe.lower()
        state_result, state_ids = stream_check(
            root / f"ratified_parallel_axis_state_stream_{suffix}.jsonl.gz",
            expected_rows=result["state_records"],
            identity_fields=("close_time",),
        )
        event_result, event_ids = stream_check(
            root / f"ratified_acceptance_frontier_events_{suffix}.jsonl.gz",
            expected_rows=result["acceptance_event_records"],
            identity_fields=("at",),
        )
        transition_result, _ = stream_check(
            root / f"ratified_parallel_axis_transitions_{suffix}.jsonl.gz",
            expected_rows=result["transition_records"],
            identity_fields=("at", "axis"),
        )
        if not {item for item in event_ids}.issubset({item for item in state_ids}):
            raise ValueError(f"event times are not a subset of state times in {timeframe}")
        stream_checks.extend((state_result, event_result, transition_result))
        lineage_checks[timeframe] = cross_check_parent(
            root / f"ratified_parallel_axis_state_stream_{suffix}.jsonl.gz",
            parent_root / f"acceptance_relation_state_stream_{suffix}.jsonl.gz",
        )
        if result["genuine_conflict_bars"]:
            raise ValueError(f"ratified state contains conflict in {timeframe}")

    determinism: dict[str, object] = {"checked": False}
    if args.determinism_root:
        prior = verify_manifest(args.determinism_root.resolve(), "B_STATE_0_3B_RATIFIED_MANIFEST.json")
        comparisons = {}
        for timeframe in ("15M", "2H"):
            current = manifest["results"][timeframe]
            earlier = prior["results"][timeframe]
            for field in (
                "state_stream_canonical_jsonl_hash",
                "event_stream_canonical_jsonl_hash",
                "transition_stream_canonical_jsonl_hash",
            ):
                key = f"{timeframe}:{field}"
                comparisons[key] = current[field] == earlier[field]
        if not all(comparisons.values()):
            raise ValueError("ratified release determinism mismatch")
        determinism = {"checked": True, "all_canonical_hashes_match": True, "comparisons": comparisons}

    result = {
        "status": "PASS",
        "validated_manifest_hash": manifest["manifest_hash"],
        "validated_review_manifest_hash": review["manifest_hash"],
        "validated_parent_manifest_hash": parent["manifest_hash"],
        "artifact_checks": artifact_checks,
        "stream_checks": stream_checks,
        "lineage_checks": lineage_checks,
        "determinism": determinism,
        "authority_boundary": "Ratified descriptive OPT-B research state only; no outcome, edge, risk, production or execution authority.",
    }
    (root / "B_STATE_0_3B_RATIFIED_VALIDATION.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# B-STATE-0.3b Ratified Release Validation",
        "",
        "**Status:** `PASS`  ",
        f"**Validated manifest:** `{manifest['manifest_hash']}`  ",
        f"**Independent determinism:** `{'PASS' if determinism['checked'] else 'NOT RUN'}`",
        "",
        "Every artifact, gzip stream, row count, identity, parent-inventory hash, non-acceptance axis and canonical replay hash passed. No outcome, execution or genuine-conflict record entered the ratified state release.",
    ]
    (root / "B_STATE_0_3B_RATIFIED_VALIDATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "manifest_hash": manifest["manifest_hash"]}, sort_keys=True))


if __name__ == "__main__":
    main()
