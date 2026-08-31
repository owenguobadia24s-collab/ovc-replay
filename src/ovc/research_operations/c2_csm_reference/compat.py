from __future__ import annotations

from .engine import C2CSMReferenceEngine
from .models import FormationLifecycleStep, R2Step, R3Step, R4Step, ReferenceBar

Engine = C2CSMReferenceEngine
EngineR2 = C2CSMReferenceEngine
EngineR3 = C2CSMReferenceEngine
EngineR4 = C2CSMReferenceEngine


def newEngine() -> Engine:
    return C2CSMReferenceEngine()


def newEngineR2() -> EngineR2:
    return C2CSMReferenceEngine()


def newEngineR3() -> EngineR3:
    return C2CSMReferenceEngine()


def newEngineR4() -> EngineR4:
    return C2CSMReferenceEngine()


def reset(engine: Engine) -> None:
    engine.reset()


def resetR2(engine: EngineR2) -> None:
    engine.reset()


def resetR3(engine: EngineR3) -> None:
    engine.reset()


def resetR4(engine: EngineR4) -> None:
    engine.reset()


def _bar(
    *, enabled: bool, logic_enabled: bool, in_lab_window: bool, first_lab_bar: bool,
    chart_gap: bool, segment_obs: int, bar_index: int, source_high: float | None,
    source_low: float | None, source_close: float | None, sequence: int = 0,
    cutoff_ms: int | None = None, window_complete: bool = False,
    checkpoint_every: int = 0, record_relation_only: bool = False,
    record_interaction_only: bool = False, mintick: float | None = None,
) -> ReferenceBar:
    return ReferenceBar(
        enabled=enabled,
        logic_enabled=logic_enabled,
        in_lab_window=in_lab_window,
        first_lab_bar=first_lab_bar,
        chart_gap=chart_gap,
        segment_obs=segment_obs,
        bar_index=bar_index,
        source_high=source_high,
        source_low=source_low,
        source_close=source_close,
        sequence=sequence,
        cutoff_ms=cutoff_ms,
        mintick=mintick,
        window_complete=window_complete,
        checkpoint_every=checkpoint_every,
        record_relation_only=record_relation_only,
        record_interaction_only=record_interaction_only,
    )


def step(
    engine: Engine, enabled: bool, logic_enabled: bool, in_lab_window: bool,
    first_lab_bar: bool, chart_gap: bool, segment_obs: int, bar_index: int,
    source_high: float | None, source_low: float | None, source_close: float | None,
) -> FormationLifecycleStep:
    bar = _bar(
        enabled=enabled, logic_enabled=logic_enabled, in_lab_window=in_lab_window,
        first_lab_bar=first_lab_bar, chart_gap=chart_gap, segment_obs=segment_obs,
        bar_index=bar_index, source_high=source_high, source_low=source_low,
        source_close=source_close,
    )
    engine._validate_bar(bar)
    if enabled and first_lab_bar:
        engine.reset()
    return engine._step_r1(bar)


def stepR2(
    engine: EngineR2, enabled: bool, logic_enabled: bool, in_lab_window: bool,
    first_lab_bar: bool, chart_gap: bool, segment_obs: int, bar_index: int,
    source_high: float | None, source_low: float | None, source_close: float | None,
    *, mintick: float | None = None,
) -> R2Step:
    bar = _bar(
        enabled=enabled, logic_enabled=logic_enabled, in_lab_window=in_lab_window,
        first_lab_bar=first_lab_bar, chart_gap=chart_gap, segment_obs=segment_obs,
        bar_index=bar_index, source_high=source_high, source_low=source_low,
        source_close=source_close, mintick=mintick,
    )
    engine._validate_bar(bar)
    if enabled and first_lab_bar:
        engine.reset()
    return engine._step_r2(bar, engine._step_r1(bar))


def stepR3(
    engine: EngineR3, enabled: bool, logic_enabled: bool, in_lab_window: bool,
    first_lab_bar: bool, chart_gap: bool, segment_obs: int, bar_index: int,
    source_high: float | None, source_low: float | None, source_close: float | None,
    *, mintick: float | None = None,
) -> R3Step:
    bar = _bar(
        enabled=enabled, logic_enabled=logic_enabled, in_lab_window=in_lab_window,
        first_lab_bar=first_lab_bar, chart_gap=chart_gap, segment_obs=segment_obs,
        bar_index=bar_index, source_high=source_high, source_low=source_low,
        source_close=source_close, mintick=mintick,
    )
    engine._validate_bar(bar)
    if enabled and first_lab_bar:
        engine.reset()
    r1_step = engine._step_r1(bar)
    return engine._step_r3(bar, engine._step_r2(bar, r1_step))


def stepR4(
    engine: EngineR4, enabled: bool, logic_enabled: bool, in_lab_window: bool,
    first_lab_bar: bool, chart_gap: bool, segment_obs: int, bar_index: int,
    source_high: float | None, source_low: float | None, source_close: float | None,
    sequence: int, cutoff_ms: int | None, window_complete: bool,
    checkpoint_every: int, record_relation_only: bool, record_interaction_only: bool,
    *, mintick: float | None = None,
) -> R4Step:
    return engine.step(_bar(
        enabled=enabled, logic_enabled=logic_enabled, in_lab_window=in_lab_window,
        first_lab_bar=first_lab_bar, chart_gap=chart_gap, segment_obs=segment_obs,
        bar_index=bar_index, source_high=source_high, source_low=source_low,
        source_close=source_close, sequence=sequence, cutoff_ms=cutoff_ms,
        window_complete=window_complete, checkpoint_every=checkpoint_every,
        record_relation_only=record_relation_only,
        record_interaction_only=record_interaction_only, mintick=mintick,
    ))
