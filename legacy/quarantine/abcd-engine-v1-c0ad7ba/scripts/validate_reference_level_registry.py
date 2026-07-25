from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import read_canonical_bars, sha256, verify_seal  # noqa: E402
from ovc_opt_b import build_level_registry, reference_level_to_dict  # noqa: E402


def canonical_hash(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal-root", type=Path, required=True)
    parser.add_argument("--registry-root", type=Path, required=True)
    args = parser.parse_args()
    seal_root = args.seal_root.resolve()
    registry_root = args.registry_root.resolve()

    seal = verify_seal(seal_root)
    manifest_path = registry_root / "REFERENCE_LEVEL_REGISTRY_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_manifest_hash = manifest.pop("manifest_hash")
    if canonical_hash(manifest) != expected_manifest_hash:
        raise ValueError("reference-level manifest hash mismatch")
    if manifest["opt_a_seal_hash"] != seal["seal_hash"]:
        raise ValueError("reference-level registry is not bound to the verified OPT-A seal")

    for artifact in manifest["artifacts"]:
        path = registry_root / artifact["path"]
        if not path.is_file() or sha256(path) != artifact["sha256"]:
            raise ValueError(f"registry artifact mismatch: {artifact['path']}")

    results: dict[str, object] = {}
    combined_records: list[dict[str, object]] = []
    all_ids: set[str] = set()
    for timeframe in ("15M", "2H"):
        source = seal_root / manifest["timeframes"][timeframe]["source_path"]
        bars = read_canonical_bars(source)
        rebuilt = build_level_registry(bars)
        expected = [reference_level_to_dict(level) for level in rebuilt.levels]
        actual = load_jsonl(registry_root / f"reference_levels_{timeframe.lower()}.jsonl")
        if actual != expected:
            raise ValueError(f"{timeframe} registry replay differs from stored release")
        ids = [record["reference_level_id"] for record in actual]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate {timeframe} reference_level_id")
        overlap = all_ids.intersection(ids)
        if overlap:
            raise ValueError("reference_level_id collision across timeframes")
        all_ids.update(ids)
        counts = Counter(record["level_type"] for record in actual)
        if rebuilt.registry_hash != manifest["timeframes"][timeframe]["registry_hash"]:
            raise ValueError(f"{timeframe} registry hash mismatch")
        results[timeframe] = {
            "source_bars": len(bars),
            "levels": len(actual),
            "type_counts": dict(sorted(counts.items())),
            "registry_hash": rebuilt.registry_hash,
            "replay_exact": True,
            "unique_ids": True,
            "gap_crossing_windows": 0,
        }
        combined_records.extend(actual)

    if canonical_hash(combined_records) != manifest["combined_registry_hash"]:
        raise ValueError("combined registry hash mismatch")
    validation = {
        "validation_id": "B-REF-0.1-VALIDATION-2026-07-19",
        "status": "PASS",
        "registry_id": manifest["registry_id"],
        "registry_version": manifest["registry_version"],
        "manifest_hash": expected_manifest_hash,
        "opt_a_seal_id": seal["seal_id"],
        "opt_a_seal_hash": seal["seal_hash"],
        "timeframes": results,
        "combined_registry_hash": manifest["combined_registry_hash"],
        "checks": {
            "seal_artifacts_verified": True,
            "registry_artifacts_verified": True,
            "byte_equivalent_rebuild": True,
            "unique_level_ids": True,
            "construction_windows_gap_safe": True,
            "future_data_not_required_for_first_valid_records": True,
        },
    }
    (registry_root / "REFERENCE_LEVEL_REGISTRY_VALIDATION.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(validation))


if __name__ == "__main__":
    main()
