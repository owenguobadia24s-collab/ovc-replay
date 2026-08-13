from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.constitution import (
    REGISTRY_DIR,
    build_registry_bundle,
    validate_committed_bundle,
)
from ovc.programme_genesis.grt_v0_2.serialization import canonical_json_v1_bytes


def _write_bundle(repository_root: Path) -> None:
    output_dir = repository_root / REGISTRY_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, record in build_registry_bundle(repository_root).items():
        (output_dir / name).write_bytes(canonical_json_v1_bytes(record) + b"\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or verify the inactive GRT v0.2 WP1 Repository Constitution bundle."
    )
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify committed schemas/registries without rewriting them.",
    )
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    if not args.check:
        _write_bundle(root)
    receipt = validate_committed_bundle(root)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
