from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from ovc.development.identity import canonical_json_bytes, canonical_sha256
from .registry import RegistryValidationError, load_and_validate_registries


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ovc skills-registry")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--root", type=Path, default=Path.cwd())
    canon = sub.add_parser("canonicalize")
    canon.add_argument("path", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "validate":
            result = load_and_validate_registries(args.root)
            print(json.dumps(result, sort_keys=True, separators=(",", ":")))
            return 0
        value = json.loads(args.path.read_text(encoding="utf-8"))
        payload = canonical_json_bytes(value)
        print(payload.decode("utf-8"))
        print(canonical_sha256(value, role="DSAI_CANONICAL_JSON"))
        return 0
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RegistryValidationError) as exc:
        print(json.dumps({"status":"BLOCK","reason":str(exc)}, sort_keys=True, separators=(",", ":")))
        return 2
