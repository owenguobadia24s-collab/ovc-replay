from __future__ import annotations

import argparse
import json

from ovc.opt_a.provider_population import build_population_plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exclude", action="append", default=[])
    arguments = parser.parse_args()
    excluded = set(arguments.exclude)
    plan = build_population_plan()
    months = [month for month in plan["months"] if month not in excluded]
    print(json.dumps({"year_month": months}, separators=(",", ":")))
