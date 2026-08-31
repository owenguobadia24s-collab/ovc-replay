from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

from ovc.development.skills.registry import validate_against_schema
from ovc.research_operations.c2_csm_reference import (
    ACTIVE_C2_AUTHORITY,
    GENERATION_ID,
    SOURCE_SHA256,
    C2CSMReferenceEngine,
    ReferenceBar,
    ReferenceEngineError,
    newEngineR4,
    stepR4,
)
from ovc.research_operations.c2_csm_reference.engine import (
    ETR_BOTH_CONTRACTION,
    ETR_BOTH_EXPANSION,
    ETRC_COMPOUND_EXPANSION,
    ETR_DOWN_SHIFT,
    ETR_EVALUABILITY_GAINED,
    ETR_EVALUABILITY_LOST,
    ETR_IDENTITY_CHANGE_SAME_GEOMETRY,
    ETR_LOWER_CONTRACTION,
    ETR_LOWER_EXPANSION,
    ETR_OTHER,
    ETR_UP_SHIFT,
    ETR_UPPER_CONTRACTION,
    ETR_UPPER_EXPANSION,
    INT_REL_UNKNOWN,
    LIFE_ACTIVE,
    LIFE_RETIRED,
    SLOG_TRIG_FINAL,
    SNAP_COMPLETE,
)

ROOT = Path(__file__).resolve().parents[3]


def _bars(*, window_complete: bool = True) -> list[ReferenceBar]:
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
            window_complete=window_complete and index == 20,
            checkpoint_every=5,
        )
        for index in range(21)
    ]


def _run(bars: list[ReferenceBar]) -> C2CSMReferenceEngine:
    engine = C2CSMReferenceEngine()
    for bar in bars:
        engine.step(bar)
    return engine


def test_generation_and_authority_are_exactly_bound() -> None:
    contract = json.loads(
        (ROOT / "contracts/research_operations/c2_csm_reference/C2CSM_REFERENCE_GENERATION_CONTRACT_v0_1.json").read_text(encoding="utf-8")
    )
    assert GENERATION_ID == contract["generation_id"] == "P3-R5-T2-S2"
    assert SOURCE_SHA256 == contract["source_binding"]["sha256"]
    assert ACTIVE_C2_AUTHORITY == contract["active_c2_authority"] == "NONE"


def test_generation_manifest_validates_and_keeps_parity_pending() -> None:
    manifest = json.loads(
        (ROOT / "records/research_operations/c2_csm_reference/C2CSM_REFERENCE_GENERATION_MANIFEST_v0_1.json").read_text(encoding="utf-8")
    )
    schema = json.loads(
        (ROOT / "schemas/research_operations/c2_csm_reference/c2_csm_reference_generation_manifest_v0_1.schema.json").read_text(encoding="utf-8")
    )
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    validate_against_schema(manifest, schema)
    assert manifest["status"] == "IMPLEMENTED_EXACT_SOURCE_BOUND_PARITY_PENDING_WP3"
    assert manifest["parity"]["historical_fixture_replay"] == "PENDING_WP3_RAW_CASE_INPUTS_UNAVAILABLE"
    assert manifest["parity"]["reference_complete_claimed"] is False
    assert manifest["active_c2_authority"] == "NONE"


def test_generation_manifest_binds_exact_implementation_file_hashes() -> None:
    manifest = json.loads(
        (ROOT / "records/research_operations/c2_csm_reference/C2CSM_REFERENCE_GENERATION_MANIFEST_v0_1.json").read_text(encoding="utf-8")
    )
    for relative_path, expected in manifest["implementation"]["file_sha256"].items():
        assert hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest() == expected


def test_strict_formation_and_same_cutoff_lifecycle_order() -> None:
    engine = C2CSMReferenceEngine()
    steps = [engine.step(bar) for bar in _bars()[:14]]
    r1 = engine.state.r3.r2.r1
    assert steps[6].r3.r2.r1.high_event is True
    assert steps[6].r3.r2.r1.low_event is True
    assert steps[6].r3.r2.r1.high_new_id == 1
    assert steps[6].r3.r2.r1.low_new_id == 2
    assert steps[13].r3.r2.r1.high_event is True
    assert steps[13].r3.r2.r1.dormant_this_bar == 1
    assert steps[13].r3.r2.r1.retired_this_bar == 1
    assert r1.life_id == [1, 2, 3]
    assert r1.life_state == [LIFE_RETIRED, LIFE_ACTIVE, LIFE_ACTIVE]
    assert r1.life_dormant_bar[0] == 13
    assert r1.life_retired_bar[0] == 13
    assert r1.life_retired_by_id[0] == 3


def test_role_atomic_compound_and_snapshot_outputs_match_source_order() -> None:
    engine = _run(_bars())
    r4 = engine.state
    r3 = r4.r3
    r2 = r3.r2
    assert r2.env_upper_price == 12
    assert r2.env_lower_price == -2
    assert r3.etr_class_ledger == [
        ETR_EVALUABILITY_GAINED,
        ETR_UPPER_EXPANSION,
        ETR_LOWER_EXPANSION,
    ]
    assert r3.etr_compound_class_ledger == [ETRC_COMPOUND_EXPANSION]
    assert r3.etr_compound_upper_leg_count_ledger == [1]
    assert r3.etr_compound_lower_leg_count_ledger == [1]
    assert r4.snap_status == SNAP_COMPLETE
    assert r4.snap_integrity_pass is True
    assert r4.slog_trigger[-1] == "FORM+LIFE+ROLE+CMP+OPEN+FINAL"
    assert r4.slog_trigger_mask[-1] & SLOG_TRIG_FINAL
    assert r4.slog_record_id == list(range(1, len(r4.slog_record_id) + 1))


def test_gap_censors_relation_without_interpolation_or_synthetic_event() -> None:
    bars = _bars(window_complete=False)[:8]
    engine = _run(bars)
    before_events = engine.state.r3.r2.int_event_total
    gap = ReferenceBar(
        enabled=True,
        logic_enabled=True,
        in_lab_window=True,
        first_lab_bar=False,
        chart_gap=True,
        segment_obs=1,
        bar_index=8,
        source_high=20,
        source_low=-20,
        source_close=20,
        sequence=9,
        cutoff_ms=1_700_000_000_008,
    )
    engine.step(gap)
    assert engine.state.r3.r2.int_event_total == before_events
    assert set(engine.state.r3.r2.int_last_relation) == {INT_REL_UNKNOWN}
    resumed = deepcopy(gap)
    resumed.chart_gap = False
    resumed.segment_obs = 2
    resumed.bar_index = 9
    resumed.sequence = 10
    engine.step(resumed)
    assert engine.state.r3.r2.int_event_total == before_events
    assert INT_REL_UNKNOWN not in engine.state.r3.r2.int_last_relation


def test_checkpoint_restart_and_fresh_replay_are_byte_identical() -> None:
    bars = _bars()
    uninterrupted = _run(bars)
    prefix = _run(bars[:14])
    restarted = C2CSMReferenceEngine.from_checkpoint(prefix.checkpoint_bytes())
    for bar in bars[14:]:
        restarted.step(bar)
    fresh = _run(bars)
    assert restarted.typed_output_bytes() == uninterrupted.typed_output_bytes()
    assert fresh.typed_output_bytes() == uninterrupted.typed_output_bytes()
    assert restarted.checkpoint_bytes() == uninterrupted.checkpoint_bytes()


def test_clean_process_replay_is_byte_identical() -> None:
    bars = _bars()
    expected = _run(bars).typed_output_bytes()
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-m", "ovc.research_operations.c2_csm_reference.cli"],
        input=json.dumps({"bars": [asdict(bar) for bar in bars]}).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        env=environment,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8")
    assert completed.stdout == expected


def test_historical_engine_r4_typed_call_surface_matches_primary_api() -> None:
    direct = _run(_bars())
    compatible = newEngineR4()
    for bar in _bars():
        stepR4(
            compatible,
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
    assert compatible.typed_output_bytes() == direct.typed_output_bytes()


def test_typed_output_is_deterministic_and_explicitly_non_authoritative() -> None:
    engine = _run(_bars())
    first = engine.typed_output()
    second = engine.typed_output()
    assert first == second
    assert first["role"] == "DESCRIPTIVE_REFERENCE_CONFORMANCE_ONLY"
    assert first["active_c2_authority"] == "NONE"
    assert first["generation_id"] == "P3-R5-T2-S2"
    assert first["source_sha256"] == SOURCE_SHA256
    assert first["output_id"] == second["output_id"]


def test_checkpoint_rejects_corruption_and_authority_promotion() -> None:
    payload = _run(_bars()[:8]).checkpoint()
    corrupt = deepcopy(payload)
    corrupt["state"]["snap_sequence"] = 999
    with pytest.raises(ReferenceEngineError, match="identity mismatch"):
        C2CSMReferenceEngine.from_checkpoint(corrupt)
    promoted = deepcopy(payload)
    promoted["active_c2_authority"] = "OWNER"
    promoted.pop("checkpoint_id")
    from ovc.research_operations.canonical import canonical_sha256

    promoted["checkpoint_id"] = canonical_sha256(promoted)
    with pytest.raises(ReferenceEngineError, match="authority boundary"):
        C2CSMReferenceEngine.from_checkpoint(promoted)


def test_logic_enabled_requires_complete_source_clock() -> None:
    bar = _bars()[0]
    bar.source_close = None
    with pytest.raises(ReferenceEngineError, match="logic_enabled"):
        C2CSMReferenceEngine().step(bar)


@pytest.mark.parametrize(
    ("current_upper", "current_lower", "expected"),
    [
        (10, 0, ETR_IDENTITY_CHANGE_SAME_GEOMETRY),
        (12, 0, ETR_UPPER_EXPANSION),
        (10, -2, ETR_LOWER_EXPANSION),
        (8, 0, ETR_UPPER_CONTRACTION),
        (10, 2, ETR_LOWER_CONTRACTION),
        (12, -2, ETR_BOTH_EXPANSION),
        (8, 2, ETR_BOTH_CONTRACTION),
        (12, 2, ETR_UP_SHIFT),
        (8, -2, ETR_DOWN_SHIFT),
    ],
)
def test_atomic_classification_preserves_enum_and_value_order(
    current_upper: float, current_lower: float, expected: int
) -> None:
    engine = C2CSMReferenceEngine()
    engine.state.r3.etr_prev_upper = 10
    engine.state.r3.etr_prev_lower = 0
    engine.state.r3.r2.env_upper_price = current_upper
    engine.state.r3.r2.env_lower_price = current_lower
    assert engine._classify_atomic(True, True) == expected
    assert engine._classify_atomic(False, True) == ETR_EVALUABILITY_GAINED
    assert engine._classify_atomic(True, False) == ETR_EVALUABILITY_LOST
    assert engine._classify_atomic(False, False) == ETR_OTHER


def test_strict_p3_rejects_tied_candidate() -> None:
    bars = _bars(window_complete=False)[:7]
    bars[0].source_high = 10
    engine = _run(bars)
    assert engine.state.r3.r2.r1.life_id == [1]
    assert engine.state.r3.r2.r1.life_kind == [-1]
