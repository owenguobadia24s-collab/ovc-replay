#!/usr/bin/env python3
"""Run a profile-bound read-only OVC artifact preflight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.development.artifacts import ArtifactRef  # noqa: E402
from ovc.development.preflight import DestinationCheck, PreflightRequest, run_preflight  # noqa: E402
from ovc.development.profiles import load_profile  # noqa: E402


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact_ref(row: dict[str, Any]) -> ArtifactRef:
    allowed = {"logical_name", "relative_path", "size_bytes", "sha256", "schema_id", "media_type", "identity_policy"}
    unknown = set(row) - allowed
    if unknown:
        raise ValueError(f"unknown artifact-ref fields: {sorted(unknown)}")
    return ArtifactRef(
        logical_name=row["logical_name"],
        relative_path=row["relative_path"],
        size_bytes=row["size_bytes"],
        sha256=row["sha256"],
        schema_id=row.get("schema_id"),
        media_type=row.get("media_type", "application/octet-stream"),
        identity_policy=row.get("identity_policy", "EXACT_FILE"),
    )


def _destination(row: dict[str, Any]) -> DestinationCheck:
    if set(row) - {"logical_name", "relative_path", "policy"}:
        raise ValueError("unknown destination fields")
    return DestinationCheck(row["logical_name"], row["relative_path"], row.get("policy", "ABSENT_OR_EMPTY"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--refs", type=Path, required=True, help="JSON array of exact artifact references")
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--destination-root", type=Path, required=True)
    parser.add_argument("--destinations", type=Path, help="Optional JSON array of destination checks")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        profile = load_profile(args.profile)
        raw_refs = _load_json(args.refs)
        if not isinstance(raw_refs, list):
            raise ValueError("refs root must be an array")
        refs = tuple(_artifact_ref(row) for row in raw_refs)
        destinations: tuple[DestinationCheck, ...] = ()
        if args.destinations:
            raw_destinations = _load_json(args.destinations)
            if not isinstance(raw_destinations, list):
                raise ValueError("destinations root must be an array")
            destinations = tuple(_destination(row) for row in raw_destinations)
        receipt = run_preflight(args.input_root, args.destination_root, PreflightRequest(profile, refs, destinations))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCK", "reason": "PREFLIGHT_REQUEST_INVALID", "detail": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
