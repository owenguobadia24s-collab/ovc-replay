from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.opt_a.provider_population import aggregate_month_summaries, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summaries-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    paths = sorted(arguments.summaries_root.rglob("*.json"))
    document = aggregate_month_summaries(paths)
    write_json(arguments.output, document)
    print(json.dumps(document, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
