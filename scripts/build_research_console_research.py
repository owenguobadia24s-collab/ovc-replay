from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.research_operations.console_research_candidate import build_candidate


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the RC-WP3-v0.3 cutoff-safe Research workspace candidate"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(
            "fixtures/research_operations/research_console_v0_3/RC_WP3_RESEARCH_SOURCE_RECORDS.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("var/research_operations/console/research_candidate.json"),
    )
    parser.add_argument(
        "--mode",
        choices=("PROSPECTIVE", "REVIEW"),
        default=None,
        help="Override the source bundle cutoff mode without changing the source record.",
    )
    args = parser.parse_args()

    if not args.source.is_file():
        raise FileNotFoundError(f"Research source bundle unavailable: {args.source}")

    projection = build_candidate(args.source, cutoff_mode=args.mode)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(projection.to_dict(), sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(projection.logical_sha256)
    print("CANDIDATE_ONLY_PENDING_RC_G3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
