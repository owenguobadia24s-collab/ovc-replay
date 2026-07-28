from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import time
import tracemalloc
import unittest
from copy import deepcopy
from pathlib import Path

from ovc.research_operations.v0_3.c1_index import build_c1_indexes

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = ROOT / "fixtures" / "research_operations" / "v0_3" / "wp1_c1_index_cases.json"
REGISTRY_PATH = ROOT / "registries" / "opt_b" / "c1" / "C1_FORMULA_REGISTRY_v0_1.yaml"
FAMILY_COUNTS = [
    ("DISCOVERY", "15M", "BID", 71982),
    ("DISCOVERY", "15M", "ASK", 71982),
    ("DISCOVERY", "2H_A_L", "BID", 7964),
    ("DISCOVERY", "2H_A_L", "ASK", 7964),
    ("DEVELOPMENT", "15M", "BID", 23853),
    ("DEVELOPMENT", "15M", "ASK", 23853),
    ("DEVELOPMENT", "2H_A_L", "BID", 2583),
    ("DEVELOPMENT", "2H_A_L", "ASK", 2583),
]


def inputs():
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    registry_text = REGISTRY_PATH.read_text(encoding="utf-8")
    registry_sha = hashlib.sha256(registry_text.encode("utf-8")).hexdigest()
    releases = deepcopy(fixture["releases"])
    for release in releases:
        release["formula_registry_sha256"] = registry_sha
    return registry_text, releases


def headers(reverse: bool = False):
    _, releases = inputs()
    release_by_role = {release["role"]: release for release in releases}
    families = list(reversed(FAMILY_COUNTS)) if reverse else FAMILY_COUNTS
    for role, clock, side, count in families:
        release = release_by_role[role]
        for offset in range(count):
            token = f"{role}|{clock}|{side}|{offset}"
            yield {
                "record_id": "c1:" + hashlib.sha256(token.encode()).hexdigest(),
                "role": role,
                "release_id": release["release_id"],
                "manifest_sha256": release["manifest_sha256"],
                "clock": clock,
                "side": side,
                "schema_version": "0.1",
                "formula_registry_id": "C1.FORMULAS.v0.1",
                "null_reasons": {"close_change": "NO_PRIOR_BAR"} if offset == 0 else {},
                "source_hash": hashlib.sha256((token + "|source").encode()).hexdigest(),
            }


class C1IndexPerformanceTests(unittest.TestCase):
    def test_declared_full_corpus_shape_is_bounded_and_reproducible(self) -> None:
        registry_text, releases = inputs()
        tracemalloc.start()
        start = time.perf_counter()
        first = build_c1_indexes(
            releases=releases,
            formula_registry_text=registry_text,
            record_headers=headers(),
        )
        wall = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        rerun_start = time.perf_counter()
        second = build_c1_indexes(
            releases=list(reversed(releases)),
            formula_registry_text=registry_text,
            record_headers=headers(reverse=True),
        )
        rerun_wall = time.perf_counter() - rerun_start
        self.assertEqual(first["logical_index_sha256"], second["logical_index_sha256"])
        self.assertLessEqual(wall, 300.0)
        self.assertLessEqual(rerun_wall, 300.0)

        identity = {
            "machine": platform.node() or "github-hosted-runner",
            "python_version": platform.python_version(),
            "operating_system": platform.platform(),
            "corpus_type": "DECLARED_FULL_CORPUS_SHAPE",
            "record_count": 212764,
            "record_file_count": 192,
            "formula_count": 18,
            "logical_index_sha256": first["logical_index_sha256"],
        }
        benchmark_id = "RO3-C1-BENCH-" + hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:20]
        report = {
            "schema": "ovc-ro3-c1-index-benchmark/v1",
            "benchmark_id": benchmark_id,
            **identity,
            "wall_time_seconds": round(wall, 6),
            "rerun_wall_time_seconds": round(rerun_wall, 6),
            "peak_memory_bytes": peak,
            "records_per_second": round(212764 / wall, 3),
            "soft_target_seconds": 300,
            "soft_target_result": "PASS",
            "reproducibility": "PASS_IDENTICAL_RERUN",
            "writes": "NONE",
        }
        print("RO3_BENCHMARK=" + json.dumps(report, sort_keys=True, separators=(",", ":")))
        output = os.environ.get("RO3_BENCHMARK_OUTPUT")
        if output:
            Path(output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.assertGreater(report["records_per_second"], 0)
        self.assertEqual(sys.version_info.major, 3)


if __name__ == "__main__":
    unittest.main()
