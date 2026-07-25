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


def stream_check(path: Path, *, expected_rows: int, state_stream: bool = False) -> dict[str, object]:
    rows = 0
    close_times: set[str] = set()
    prohibited = {"return", "mfe", "mae", "profit", "win", "loss", "trade", "execution"}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rows += 1
            if row.get("state_contract_version") not in (None, "B-STATE-0.3a"):
                raise ValueError(f"wrong contract version in {path.name}")
            lowered = {key.lower() for key in row}
            if lowered.intersection(prohibited):
                raise ValueError(f"prohibited outcome/execution field in {path.name}")
            if state_stream:
                close_time = row["close_time"]
                if close_time in close_times:
                    raise ValueError(f"duplicate close_time in {path.name}")
                close_times.add(close_time)
                inventory = row["acceptance_relation_inventory"]
                if "semantic_state" in inventory:
                    raise ValueError(f"categorical acceptance state leaked into {path.name}")
                if row.get("location_state") is not None:
                    raise ValueError(f"legacy location state leaked into {path.name}")
    if rows != expected_rows:
        raise ValueError(f"row-count mismatch in {path.name}: {rows} != {expected_rows}")
    return {
        "path": path.name,
        "rows": rows,
        "unique_close_times": len(close_times),
        "gzip_integrity": "PASS",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--determinism-root", type=Path)
    args = parser.parse_args()
    root = args.release_root.resolve()
    manifest = json.loads((root / "B_STATE_0_3A_REPLAY_MANIFEST.json").read_text(encoding="utf-8"))
    expected_manifest_hash = manifest["manifest_hash"]
    core = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if canonical_hash(core) != expected_manifest_hash:
        raise ValueError("manifest self-hash mismatch")

    artifact_checks = []
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        actual = sha256(path)
        if actual != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {path.name}")
        artifact_checks.append({"path": path.name, "sha256": actual, "status": "PASS"})

    stream_checks = []
    for timeframe in ("15M", "2H"):
        result = manifest["results"][timeframe]["v03a"]
        suffix = timeframe.lower()
        stream_checks.append(
            stream_check(
                root / f"acceptance_relation_state_stream_{suffix}.jsonl.gz",
                expected_rows=result["state_records"],
                state_stream=True,
            )
        )
        stream_checks.append(
            stream_check(
                root / f"acceptance_relation_transition_records_{suffix}.jsonl.gz",
                expected_rows=result["transition_records"],
            )
        )
        stream_checks.append(
            stream_check(
                root / f"acceptance_relation_change_records_{suffix}.jsonl.gz",
                expected_rows=result["relation_change_records"],
            )
        )
        if not manifest["results"][timeframe]["unchanged_axis_comparison"]["all_unchanged_axes_match"]:
            raise ValueError(f"non-acceptance axis mismatch in {timeframe}")

    determinism: dict[str, object] = {"checked": False}
    if args.determinism_root:
        prior = json.loads(
            (args.determinism_root.resolve() / "B_STATE_0_3A_REPLAY_MANIFEST.json").read_text(encoding="utf-8")
        )
        comparisons = {}
        for timeframe in ("15M", "2H"):
            current = manifest["results"][timeframe]["v03a"]
            earlier = prior["results"][timeframe]["v03a"]
            for field in (
                "state_stream_canonical_jsonl_hash",
                "transition_stream_canonical_jsonl_hash",
                "relation_change_stream_canonical_jsonl_hash",
            ):
                key = f"{timeframe}:{field}"
                comparisons[key] = current[field] == earlier[field]
        if not all(comparisons.values()):
            raise ValueError("independent replay determinism mismatch")
        determinism = {"checked": True, "all_canonical_hashes_match": True, "comparisons": comparisons}

    result = {
        "status": "PASS",
        "validated_manifest_hash": expected_manifest_hash,
        "artifact_checks": artifact_checks,
        "stream_checks": stream_checks,
        "determinism": determinism,
        "semantic_controls": {
            "categorical_acceptance_state_absent": True,
            "non_acceptance_axes_match_v03": True,
            "outcome_execution_fields_absent": True,
        },
        "authority_boundary": "Validation covers structural OPT-B replay only; no outcome, edge or execution authority.",
    }
    (root / "B_STATE_0_3A_VALIDATION.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# B-STATE-0.3a Validation",
        "",
        "**Status:** `PASS`  ",
        f"**Validated manifest:** `{expected_manifest_hash}`  ",
        f"**Manifest-bound artifacts:** `{len(artifact_checks)}`  ",
        f"**Independent replay determinism:** `{'PASS' if determinism['checked'] else 'NOT RUN'}`",
        "",
        "Every gzip stream decompressed fully, every declared artifact hash matched, state rows were unique by close time, record counts matched the manifest, categorical acceptance did not leak into the relation inventory, frozen non-acceptance axes matched v0.3, and no outcome or execution fields entered the replay.",
    ]
    (root / "B_STATE_0_3A_VALIDATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "manifest_hash": expected_manifest_hash}, sort_keys=True))


if __name__ == "__main__":
    main()
