"""Build the exact source-free C2S-SPTOI WP11 pre-GREAL packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.research_operations.spto.pre_greal import build_pre_greal_packet


DEFAULT_OUTPUT = Path(
    "docs/programmes/c2s-sptoi-v0-1/wp11/"
    "C2S_SPTOI_WP11_PRE_GREAL_OPERATOR_PACKET_v0_1.json"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_pre_greal_packet(root), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
