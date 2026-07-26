from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ovc.opt_b.c2.replay import DEVELOPMENT_RELEASE, DISCOVERY_RELEASE, ReplayError, run_role_replay


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded OPT-B.C2 v2 WP5 replay from exact C1 JSONL exports.")
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    discovery = args.release_root / "discovery" / "c1_records.jsonl"
    development = args.release_root / "development" / "c1_records.jsonl"
    missing = [str(path) for path in (discovery, development) if not path.is_file()]
    if missing:
        print(json.dumps({"status": "BLOCKED_MISSING_C1_RELEASE_ROOT", "missing": missing}, indent=2))
        return 2

    try:
        summaries = [
            run_role_replay(role="DISCOVERY", release_id=DISCOVERY_RELEASE, input_path=discovery, output_dir=args.output_root),
            run_role_replay(role="DEVELOPMENT", release_id=DEVELOPMENT_RELEASE, input_path=development, output_dir=args.output_root),
        ]
    except ReplayError as exc:
        print(json.dumps({"status": "BLOCKED_REPLAY_ERROR", "error": str(exc)}, indent=2))
        return 3

    receipt = {
        "schema": "ovc-opt-b-c2-wp5-local-replay/v1",
        "status": "PASS_LOCAL_REPLAY",
        "roles": [summary.__dict__ for summary in summaries],
        "outputs": {
            path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
            for path in sorted(args.output_root.glob("*.jsonl"))
        },
        "validation_consumption": "LOCKED_UNCONSUMED",
        "probability": "NONE",
        "trading": "NONE",
        "execution": "NONE",
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "WP5_LOCAL_REPLAY_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
