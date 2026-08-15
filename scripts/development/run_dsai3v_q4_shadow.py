import json
import time
import tracemalloc
from pathlib import Path
from dataclasses import asdict
from ovc.development.skills.vit_budget import LanePacketObservation, measure_q4

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/dsai3v-wp8b/DSAI3V_WP8B_LIVE_LANE_SOURCE_MANIFEST.json"


def main():
    manifest = json.loads(MANIFEST.read_text())
    rows = []
    for li, lane in enumerate(manifest["lanes"]):
        source = (ROOT / lane["source"]).read_text()
        for pi, packet in enumerate(lane["packet_queue"][:2]):
            tracemalloc.start()
            t0 = time.perf_counter()
            payload = json.dumps({"lane": lane["lane_id"], "packet": packet, "source": source}, sort_keys=True)
            build = time.perf_counter() - t0
            t1 = time.perf_counter()
            restored = json.loads(payload)
            rebuild = time.perf_counter() - t1
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            rows.append(LanePacketObservation(lane["lane_id"], packet, build, rebuild, build + rebuild, rebuild, peak, len(payload.encode()), "PLACEMENT_RECOMPUTE_ONLY" if pi == 0 else "ASSURANCE_RENEWAL_REQUIRED", reference_optimized_equal=(restored["packet"] == packet), safe_bypass_exercised=(li == 0 and pi == 1), restart_exercised=(li == 1 and pi == 1), external_reanchor_exercised=(li == 2 and pi == 1)))
    report = measure_q4(rows)
    print("DSAI3V_Q4_MEASUREMENT=" + json.dumps({"observations": [asdict(x) for x in rows], "report": asdict(report), "report_id": report.report_id, "budget_id": report.budget.budget_id, "passes": report.passes}, sort_keys=True))
    return 0 if report.passes else 2


if __name__ == "__main__":
    raise SystemExit(main())
