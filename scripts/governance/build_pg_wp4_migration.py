from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.programme_genesis import build_snapshot_from_registry, load_migration_source_registry, write_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the PG-WP4 provisional programme migration snapshot.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("registries/governance/programme_genesis/MIGRATION_SOURCE_REGISTRY_v0_1.json"),
        help="Migration source registry, relative to root unless absolute",
    )
    parser.add_argument("--output", type=Path, required=True, help="Output snapshot path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    registry_path = args.registry if args.registry.is_absolute() else root / args.registry
    output_path = args.output if args.output.is_absolute() else root / args.output
    registry = load_migration_source_registry(registry_path)
    snapshot = build_snapshot_from_registry(root, registry)
    write_snapshot(output_path, snapshot)
    summary = {
        "status": snapshot["status"],
        "record_count": snapshot["record_count"],
        "unique_programme_count": snapshot["unique_programme_count"],
        "blocking_conflict_count": snapshot["blocking_conflict_count"],
        "warning_count": len([item for item in snapshot["conflict_ledger"] if item["severity"] == "WARN"]),
        "snapshot_sha256": snapshot["snapshot_sha256"],
        "output": output_path.as_posix(),
        "authority_effect": snapshot["authority_effect"],
        "import_status": snapshot["import_status"],
    }
    print(json.dumps(summary, sort_keys=True))
    return 0 if snapshot["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
