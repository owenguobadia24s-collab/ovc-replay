#!/usr/bin/env python3
"""Run one local copy-only DA-WP5 compact evidence export."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.development.evidence_export import (  # noqa: E402
    EvidenceExportError,
    build_plan,
    execute_export,
    load_profile,
    load_request,
)

DEFAULT_PROFILE = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_EVIDENCE_EXPORT_PROFILE_v0_1.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--external-root", type=Path)
    return parser.parse_args()


def resolve_external_root(argument: Path | None) -> Path:
    if argument is not None:
        return argument
    configured = os.environ.get("OVC_EXTERNAL_ARTIFACT_ROOT")
    if not configured:
        raise EvidenceExportError(
            "EXTERNAL_ROOT_REQUIRED",
            "provide --external-root or set OVC_EXTERNAL_ARTIFACT_ROOT",
        )
    return Path(configured)


def main() -> int:
    args = parse_args()
    try:
        profile = load_profile(args.profile)
        request = load_request(args.request)
        plan = build_plan(args.repository_root, resolve_external_root(args.external_root), request, profile)
        result = execute_export(plan)
    except EvidenceExportError as exc:
        print(json.dumps({"status": "BLOCK", "code": exc.code}, sort_keys=True, separators=(",", ":")), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
