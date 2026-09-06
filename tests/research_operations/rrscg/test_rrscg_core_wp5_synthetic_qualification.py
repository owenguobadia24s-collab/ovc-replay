from __future__ import annotations

import dataclasses
import json
import os
import sys
import time
from pathlib import Path

import pytest

from ovc.research_operations.rrscg.qualification import (
    QualificationError,
    generate_synthetic_cases,
    merge_qualification_records,
    qualification_content_hash,
    reconcile_denominators,
    run_synthetic_cases,
)
from ovc.research_orchestration.checkpoint import assert_fresh_resume_equivalent

ROOT = Path(__file__).resolve().parents[3]
QUALIFICATION_MANIFEST = ROOT / "fixtures/research_operations/rrscg/rrscg_core_wp5_qualification_manifest_v0_1.json"


def _manifest():
    return json.loads(QUALIFICATION_MANIFEST.read_text(encoding="utf-8"))


def _resident_bytes() -> int:
    """Return process resident memory without adding a runtime dependency."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        ctypes.windll.kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        process = ctypes.windll.kernel32.GetCurrentProcess()
        get_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_memory_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
        get_memory_info.restype = wintypes.BOOL
        if not get_memory_info(process, ctypes.byref(counters), counters.cb):
            raise OSError("GetProcessMemoryInfo failed")
        return int(counters.WorkingSetSize)

    import resource

    rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return rss if sys.platform == "darwin" else rss * 1024


def test_deterministic_replay_and_chunk_equivalence():
    cases = generate_synthetic_cases(1024)
    one = run_synthetic_cases(cases, chunk_size=1024)
    repeated = run_synthetic_cases(cases, chunk_size=1024)
    chunked = run_synthetic_cases(cases, chunk_size=37)
    assert one == repeated == chunked
    assert qualification_content_hash(one) == qualification_content_hash(repeated) == qualification_content_hash(chunked)
    assert qualification_content_hash(one) == _manifest()["synthetic_runs"]["cases_1024"]["content_sha256"]


def test_order_independence_and_exact_chronology_recovery():
    cases = generate_synthetic_cases(513)
    forward = run_synthetic_cases(cases, chunk_size=64)
    reverse = run_synthetic_cases(reversed(cases), chunk_size=29)
    assert forward == reverse
    assert [record.source_sequence_index for record in forward] == list(range(513))
    assert [record.first_valid_time for record in forward] == sorted(record.first_valid_time for record in forward)


def test_checkpoint_restart_equivalence_reuses_existing_irof_identity_assertion():
    cases = generate_synthetic_cases(777)
    fresh = run_synthetic_cases(cases, chunk_size=128)
    first = run_synthetic_cases(cases[:333], chunk_size=41)
    resumed = run_synthetic_cases(cases[333:], chunk_size=53)
    merged = merge_qualification_records(first, resumed)
    fresh_hash = qualification_content_hash(fresh)
    resumed_hash = qualification_content_hash(merged)
    assert_fresh_resume_equivalent(fresh_hash, qualification_content_hash(run_synthetic_cases(cases)), resumed_hash)
    assert fresh == merged


def test_denominator_reconciliation_and_reducer_scope():
    records = run_synthetic_cases(generate_synthetic_cases(3068), chunk_size=211)
    receipt = reconcile_denominators(records, expected_count=3068)
    assert receipt.status == "PASS"
    assert receipt.record_count == receipt.unique_case_count == receipt.unique_sequence_count == 3068
    assert receipt.r2_resolved_count == receipt.d9_resolved_count == receipt.d10_resolved_count
    assert receipt.d10_affected_count > 0
    expected = _manifest()["synthetic_runs"]["cases_3068"]
    assert qualification_content_hash(records) == expected["content_sha256"]
    assert receipt.to_dict() == expected["denominator_reconciliation"]
    for record in records:
        if record.d10_resolution_tier != record.d9_resolution_tier:
            assert record.d9_resolution_tier == "MINIMAL_CONSTRAINT"
            assert record.d10_resolution_tier == "C_LAST_FAMILY_CONSENSUS"
            assert set(record.d10_selected_frontier).issubset(record.r2_selected_frontier)


def test_duplicate_and_tampered_inputs_fail_closed():
    cases = generate_synthetic_cases(3)
    with pytest.raises(QualificationError, match="DUPLICATE_SYNTHETIC_CASE_ID"):
        run_synthetic_cases((cases[0], dataclasses.replace(cases[0], source_sequence_index=99)))
    with pytest.raises(QualificationError, match="DUPLICATE_SOURCE_SEQUENCE_INDEX"):
        run_synthetic_cases((cases[0], dataclasses.replace(cases[1], source_sequence_index=0)))
    with pytest.raises(QualificationError, match="CHUNK_SIZE"):
        run_synthetic_cases(cases, chunk_size=0)


def test_bounded_20k_single_clock_capacity():
    resident_before = _resident_bytes()
    started = time.perf_counter()
    records = run_synthetic_cases(generate_synthetic_cases(20_000), chunk_size=512)
    elapsed = time.perf_counter() - started
    resident_growth = max(0, _resident_bytes() - resident_before)
    receipt = reconcile_denominators(records, expected_count=20_000)
    assert receipt.status == "PASS"
    expected = _manifest()["synthetic_runs"]["cases_20000"]
    assert qualification_content_hash(records) == expected["content_sha256"]
    assert receipt.to_dict() == expected["denominator_reconciliation"]
    assert elapsed < 60.0
    assert resident_growth < 512 * 1024 * 1024
