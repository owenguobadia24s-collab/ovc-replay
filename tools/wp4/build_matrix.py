from __future__ import annotations

import json

from ovc.opt_a.provider_population import build_population_plan


if __name__ == "__main__":
    plan = build_population_plan()
    print(json.dumps({"year_month": plan["months"]}, separators=(",", ":")))
