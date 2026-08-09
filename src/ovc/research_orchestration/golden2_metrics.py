from __future__ import annotations

from typing import Any

from ovc.research_orchestration.telemetry import build_telemetry_receipt

RUN_ID = "IROF.RUN.GOLDEN2.WEEK.v0_1"


def telemetry(stage_id: str, *, wall: float | None, cpu: float | None, objects: int, pairs: int = 0) -> dict[str, Any]:
    throughput = (objects / wall) if wall is not None and wall > 0 else None
    values = {
        "wall_seconds": (wall, "seconds"),
        "cpu_seconds": (cpu, "seconds"),
        "core_seconds": (cpu, "core_seconds"),
        "peak_rss_bytes": (None, "bytes"),
        "worker_count": (1, "workers"),
        "bytes_read": (None, "bytes"),
        "bytes_written": (None, "bytes"),
        "persistent_bytes": (None, "bytes"),
        "temporary_bytes": (None, "bytes"),
        "object_count": (objects, "objects"),
        "pair_count": (pairs, "pairs"),
        "tile_count": (0, "tiles"),
        "configuration_count": (1, "configurations"),
        "throughput_per_second": (throughput, "objects_per_second"),
        "cache_hit_count": (0, "hits"),
        "cache_miss_count": (0, "misses"),
        "restart_count": (0, "restarts"),
    }
    return build_telemetry_receipt(run_id=RUN_ID, stage_id=stage_id, values=values).to_dict()
