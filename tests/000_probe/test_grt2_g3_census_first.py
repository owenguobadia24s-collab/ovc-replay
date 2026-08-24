from __future__ import annotations

import importlib.util
from pathlib import Path

PROBE = Path(__file__).resolve().parents[1] / "test_000_grt2_g3_superseding_census_probe.py"
spec = importlib.util.spec_from_file_location("grt2_g3_fast_probe", PROBE)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_grt2_g3_census_probe_first() -> None:
    module.test_probe()
