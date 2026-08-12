from __future__ import annotations

import json
from pathlib import Path

from ovc.opt_b.esl.c3_reference import measure_reference_vertical_path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "fixtures/opt_b/esl/wp3/bootstrap_c2_input.json"


def test_wp4_reference_performance_calibration_probe():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    measurement = measure_reference_vertical_path(source["c2_observation"], source["profile_outputs"], source_generation_id=source["source_generation_id"], repetitions=200, warmup=20)
    raise AssertionError("ESLI_WP4_CALIBRATION=" + json.dumps(measurement, sort_keys=True, separators=(",", ":")))
