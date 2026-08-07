from __future__ import annotations

import json
import os
from pathlib import Path
import resource
import tempfile
import time

from ovc.opt_b.srfd.capacity import _fixture_representations
from ovc.opt_b.srfd.capacity_v2 import validate_feasibility_bridge_receipt
from ovc.opt_b.srfd.distance import DistanceSpec
from ovc.opt_b.srfd.distance_optimized import batch_compute_prepared, deterministic_parallel_tiles
from ovc.opt_b.srfd.distance_surface import TileHeader, coefficient_width, compact_pair_coefficients, write_exact_tile
from ovc.opt_b.srfd.serialization import canonical_json_bytes, logical_sha256


ROOT = Path(__file__).resolve().parents[2]
H0_PATH = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g8r-wp0/SRFDI_G8R_WP0_H0_ENVIRONMENT_RECEIPT.json"


def rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value * 1024) if value < 10_000_000 else int(value)


def measure_n(n: int) -> dict[str, object]:
    records = _fixture_representations(n, 5)
    spec = DistanceSpec("G8R.BRIDGE.L1.v1", "L1_TYPED", tuple(f"d{i}" for i in range(5)), precision_places=12)
    cpu0 = time.process_time(); wall0 = time.perf_counter()
    coefficients, reference = compact_pair_coefficients(records, spec)
    ref_wall = time.perf_counter() - wall0; ref_cpu = time.process_time() - cpu0
    ref_bytes = sum(len(canonical_json_bytes(item)) for item in reference)
    ref_rss = rss_bytes()

    cpu1 = time.process_time(); wall1 = time.perf_counter()
    optimized = batch_compute_prepared(records, spec)
    opt_wall = time.perf_counter() - wall1; opt_cpu = time.process_time() - cpu1
    opt_rss = rss_bytes()
    equivalent = reference == optimized

    worker_measurements: dict[str, object] = {}
    for workers in (1, 2, 4):
        start = time.perf_counter()
        parallel = deterministic_parallel_tiles(records, spec, tile_pair_count=max(64, len(coefficients) // 8 or 1), worker_count=workers)
        elapsed = time.perf_counter() - start
        worker_measurements[str(workers)] = {"wall_seconds": elapsed, "logical_equivalence": parallel == reference}

    width = coefficient_width(coefficients)
    return {
        "n": n,
        "pair_count": len(coefficients),
        "reference": {"wall_seconds": ref_wall, "cpu_seconds": ref_cpu, "peak_rss_bytes": ref_rss, "logical_json_bytes": ref_bytes},
        "optimized": {"wall_seconds": opt_wall, "cpu_seconds": opt_cpu, "peak_rss_bytes": opt_rss, "fixed_width_bytes": len(coefficients) * width, "coefficient_width": width},
        "logical_equivalence": equivalent,
        "worker_sweep": worker_measurements,
        "marginal_improvement_factor": ref_wall / opt_wall if opt_wall else float("inf"),
    }


def measure_io(root: Path) -> dict[str, object]:
    receipts: list[dict[str, object]] = []
    for count in (64_000, 256_000, 1_000_000):
        coefficients = (0,) * count
        header = TileHeader("G8R.TILE.v1", "big", 8, 12, "POP", "DOMAIN", "SPEC", 0, count, count)
        path = root / f"tile-{count}.bin"
        start = time.perf_counter(); receipt = write_exact_tile(path, header, coefficients); elapsed = time.perf_counter() - start
        receipts.append({"pair_count": count, "payload_bytes": receipt.payload_bytes, "write_seconds": elapsed, "write_mib_per_second": (receipt.payload_bytes / 1048576) / elapsed if elapsed else None, "content_hash": receipt.content_hash})
    return {"schema":"ovc-srfdi-g8r-storage-io-capacity-receipt/v1","measurement_class":"MEASURED","tile_ladder":receipts,"logical_hash":logical_sha256(receipts)}


def main() -> int:
    output = Path(os.environ.get("G8R_BRIDGE_OUTPUT", "g8r-bridge-evidence")); output.mkdir(parents=True, exist_ok=True)
    h0 = json.loads(H0_PATH.read_text(encoding="utf-8"))
    p0 = measure_n(64); p1 = measure_n(256)
    with tempfile.TemporaryDirectory(prefix="g8r-io-") as tmp:
        io_receipt = measure_io(Path(tmp))
    if not p0["logical_equivalence"] or not p1["logical_equivalence"] or not all(item["logical_equivalence"] for item in p1["worker_sweep"].values()):
        disposition = "IMPLAUSIBLE"
    elif float(p1["marginal_improvement_factor"]) >= 1.0:
        disposition = "PLAUSIBLE"
    else:
        disposition = "INDETERMINATE"
    p1_ref = p1["reference"]; p1_opt = p1["optimized"]
    bridge = {
        "schema":"ovc-srfdi-g8r-feasibility-bridge-receipt/v1",
        "environment_fingerprint":h0["environment_fingerprint"],
        "baseline_component_id":"B0_CURRENT_JSON_REFERENCE",
        "candidate_component_id":"B2_PREPARED_STDLIB_EXACT",
        "population":{"P0":{"n":64},"P1":{"n":256}},
        "backend":"PYTHON_STDLIB_EXACT",
        "before_wall_seconds":p1_ref["wall_seconds"],
        "after_wall_seconds":p1_opt["wall_seconds"],
        "before_cpu_seconds":p1_ref["cpu_seconds"],
        "after_cpu_seconds":p1_opt["cpu_seconds"],
        "before_peak_rss_bytes":p1_ref["peak_rss_bytes"],
        "after_peak_rss_bytes":p1_opt["peak_rss_bytes"],
        "before_external_bytes":p1_ref["logical_json_bytes"],
        "after_external_bytes":p1_opt["fixed_width_bytes"],
        "storage_read_seconds":0.0,
        "storage_write_seconds":sum(item["write_seconds"] for item in io_receipt["tile_ladder"]),
        "cache_state":"COLD",
        "logical_equivalence":bool(p1["logical_equivalence"]),
        "marginal_improvement_factor":p1["marginal_improvement_factor"],
        "remaining_bottleneck":"FAMILY_METHOD_OPTIMIZATION_NOT_YET_AUTHORISED",
        "bounded_forecast":{"P2":"EXTRAPOLATED_FROM_P1_PAIRWISE_ONLY","P3":"EXTRAPOLATED_FROM_P1_PAIRWISE_ONLY","P4":"EXTRAPOLATED_FROM_P1_PAIRWISE_ONLY"},
        "disposition":disposition,
        "rungs":{"P0":p0,"P1":p1},
        "numpy":{"state":"CANDIDATE_UNADMITTED","present_on_h0":h0["candidate_backend"]["numpy"]["present"]},
        "no_multiplicative_speedup_claim":True,
        "june_market_records_read":False,"validation_consumed":False
    }
    validate_feasibility_bridge_receipt(bridge)
    bridge["logical_hash"] = logical_sha256(bridge)
    (output / "FEASIBILITY_BRIDGE_RECEIPT.json").write_text(json.dumps(bridge, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    (output / "STORAGE_IO_CAPACITY_RECEIPT.json").write_text(json.dumps(io_receipt, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(f"G8R_BRIDGE_DISPOSITION={disposition}")
    print(f"G8R_BRIDGE_FACTOR={p1['marginal_improvement_factor']}")
    print(f"G8R_BRIDGE_LOGICAL_HASH={bridge['logical_hash']}")
    print(f"G8R_IO_LOGICAL_HASH={io_receipt['logical_hash']}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
