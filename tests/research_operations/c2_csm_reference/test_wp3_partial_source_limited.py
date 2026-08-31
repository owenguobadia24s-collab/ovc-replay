from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys

from ovc.research_operations.c2_csm_reference import (
    C2CSMReferenceEngine,
    ReferenceBar,
    newEngineR4,
    stepR4,
)


ROOT = Path(__file__).resolve().parents[3]


def _bars() -> list[ReferenceBar]:
    highs = [1, 2, 3, 10, 4, 5, 6, 7, 8, 9, 12, 10, 11, 11.5] + [11] * 7
    lows = [9, 8, 7, 0, 6, 5, 4] + [5] * 7 + [0, -0.5, -1, -2, -1.5, -1, -0.5]
    closes = [5.0] * 21
    closes[13] = 11.0
    closes[20] = -1.0
    return [
        ReferenceBar(
            enabled=True,
            logic_enabled=True,
            in_lab_window=True,
            first_lab_bar=index == 0,
            chart_gap=False,
            segment_obs=index + 1,
            bar_index=index,
            source_high=float(highs[index]),
            source_low=float(lows[index]),
            source_close=closes[index],
            sequence=index + 1,
            cutoff_ms=1_700_000_000_000 + index,
            mintick=0.5,
            window_complete=index == 20,
            checkpoint_every=5,
        )
        for index in range(21)
    ]


def _run(bars: list[ReferenceBar]) -> C2CSMReferenceEngine:
    engine = C2CSMReferenceEngine()
    for bar in bars:
        engine.step(bar)
    return engine


def _step_compat(engine: C2CSMReferenceEngine, bar: ReferenceBar) -> None:
    stepR4(
        engine,
        bar.enabled,
        bar.logic_enabled,
        bar.in_lab_window,
        bar.first_lab_bar,
        bar.chart_gap,
        bar.segment_obs,
        bar.bar_index,
        bar.source_high,
        bar.source_low,
        bar.source_close,
        bar.sequence,
        bar.cutoff_ms,
        bar.window_complete,
        bar.checkpoint_every,
        bar.record_relation_only,
        bar.record_interaction_only,
        mintick=bar.mintick,
    )


def _clean_process(payload: dict) -> bytes:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-m", "ovc.research_operations.c2_csm_reference.cli"],
        input=json.dumps(payload).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        env=environment,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8")
    return completed.stdout


def test_every_admissible_checkpoint_cut_is_logically_and_byte_identical() -> None:
    bars = _bars()
    uninterrupted = _run(bars)
    expected_output = uninterrupted.typed_output_bytes()
    expected_checkpoint = uninterrupted.checkpoint_bytes()
    for cut in range(1, len(bars)):
        prefix = _run(bars[:cut])
        restarted = C2CSMReferenceEngine.from_checkpoint(prefix.checkpoint_bytes())
        for bar in bars[cut:]:
            restarted.step(bar)
        assert restarted.typed_output_bytes() == expected_output
        assert restarted.checkpoint_bytes() == expected_checkpoint


def test_clean_process_checkpoint_restart_matches_uninterrupted_bytes() -> None:
    bars = _bars()
    expected = _run(bars).typed_output_bytes()
    for cut in (1, 7, 14, 20):
        checkpoint = _run(bars[:cut]).checkpoint()
        actual = _clean_process(
            {
                "checkpoint": checkpoint,
                "bars": [asdict(bar) for bar in bars[cut:]],
            }
        )
        assert actual == expected


def test_c2lib_engine_r4_surface_matches_primary_api_after_every_step() -> None:
    direct = C2CSMReferenceEngine()
    compatible = newEngineR4()
    for bar in _bars():
        direct.step(bar)
        _step_compat(compatible, bar)
        assert compatible.typed_output_bytes() == direct.typed_output_bytes()
        assert compatible.checkpoint_bytes() == direct.checkpoint_bytes()


def test_repeated_serialization_preserves_identity_and_authority_firewall() -> None:
    engine = _run(_bars())
    first = engine.typed_output()
    assert engine.typed_output_bytes() == engine.typed_output_bytes()
    assert first == engine.typed_output()
    assert first["output_id"] == engine.typed_output()["output_id"]
    assert first["active_c2_authority"] == "NONE"
    assert first["role"] == "DESCRIPTIVE_REFERENCE_CONFORMANCE_ONLY"
