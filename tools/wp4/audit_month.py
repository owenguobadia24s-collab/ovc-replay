from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.opt_a.provider_population import audit_month_workspace


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--year-month", required=True)
    arguments = parser.parse_args()
    summary = audit_month_workspace(arguments.workspace, arguments.year_month)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
