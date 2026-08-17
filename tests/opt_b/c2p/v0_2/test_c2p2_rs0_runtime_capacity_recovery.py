from __future__ import annotations

from pathlib import Path

import pytest

from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime import run_empirical_runtime
from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_streaming import (
    ADAPTER_ID,
    RS0SpooledRuntimeError,
    materialize_reference_result,
    merge_canonical_source_streams,
    run_spooled_empirical_runtime,
)


REGISTRY = {
    "schema": "ovc-c2p2-rs0-c2e-dependency-role-registry/v1",
    "entries": [],
    "current_declared_episode_relative_roles": [],
}


def _spec(letter: str) -> dict:
    names = {
        "A": "STRICT-CONTINUITY",
        "B": "RELATIONAL-CONTINUITY",
        "C": "EPISODE-ENRICHED-CONTINUITY",
    }
    stem = names[letter]
    return {
        "candidate_id": f"C2P2-PS0-OP-{letter}-{stem}-v3",
        "semantic_candidate_id": f"C2P2-PS0-OP-{letter}-{stem}-v2",
        "activation_eligible": False,
    }


def _level(
    index: int,
    *,
    value: str = "1.2500",
    topology: str = "ABOVE",
    side: str = "BID",
) -> dict:
    return {
        "schema": "ovc-c2p2-rs0-source-row/v1",
        "source_role": "C2_VNEXT",
        "instrument": "GBPUSD",
        "side": side,
        "clock": "15M",
        "first_valid_time": f"2021-01-01T{index // 60:02d}:{index % 60:02d}:00Z",
        "evaluation_cutoff": f"2021-01-01T{index // 60:02d}:{index % 60:02d}:00Z",
        "source_record_id": f"{side[0]}L{index:04d}",
        "source_record_kind": "C2_LEVEL",
        "geometry_signature": {
            "horizon_id": "H4",
            "level_type": "RANGE_HIGH",
            "value": value,
            "origin": "C2AR",
            "structural_depth": None,
        },
        "relation_topology": [topology],
    }


@pytest.mark.parametrize("letter", ["A", "B", "C"])
def test_spooled_adapter_is_exact_reference_equivalent(letter: str, tmp_path: Path) -> None:
    rows = [
        _level(i, value=f"1.25{i:02d}", topology="ABOVE" if i < 4 else "BELOW")
        for i in range(1, 7)
    ]
    reference = run_empirical_runtime(rows, _spec(letter), REGISTRY)
    manifest = run_spooled_empirical_runtime(
        rows,
        _spec(letter),
        REGISTRY,
        work_dir=tmp_path,
        checkpoint_cadence=2,
    )
    materialized = materialize_reference_result(tmp_path)

    assert materialized == reference
    assert manifest["adapter_id"] == ADAPTER_ID
    assert manifest["runtime_binding_id"] == reference["runtime_binding_id"]
    assert manifest["selection_state"] == "UNSELECTED_RESEARCH_CANDIDATE"
    assert manifest["activation_state"] == "NONE"
    assert manifest["real_source_launch"] == "NOT_AUTHORISED_BY_RUNTIME"
    assert manifest["scientific_effect"] == "NONE_FROM_ADAPTER"


def test_canonical_merge_preserves_one_shot_reference_sort_order(tmp_path: Path) -> None:
    odd = [_level(i, value="1.2500") for i in (1, 3, 5)]
    even = [_level(i, value="1.2500") for i in (2, 4, 6)]
    reference = run_empirical_runtime(odd + even, _spec("A"), REGISTRY)

    merged = merge_canonical_source_streams([odd, even])
    run_spooled_empirical_runtime(
        merged,
        _spec("A"),
        REGISTRY,
        work_dir=tmp_path,
        checkpoint_cadence=2,
    )
    assert materialize_reference_result(tmp_path) == reference


def test_spooled_adapter_preserves_discontinuity_semantics(tmp_path: Path) -> None:
    rows = [_level(i) for i in range(1, 5)]
    source_id = rows[2]["source_record_id"]
    reference = run_empirical_runtime(
        rows,
        _spec("A"),
        REGISTRY,
        explicit_discontinuity_source_ids={source_id},
    )
    run_spooled_empirical_runtime(
        rows,
        _spec("A"),
        REGISTRY,
        work_dir=tmp_path,
        explicit_discontinuity_source_ids={source_id},
        checkpoint_cadence=1,
    )
    assert materialize_reference_result(tmp_path) == reference


def test_spooled_adapter_fails_closed_on_nonmonotonic_or_duplicate_stream(tmp_path: Path) -> None:
    with pytest.raises(RS0SpooledRuntimeError, match="NONMONOTONIC"):
        run_spooled_empirical_runtime(
            [_level(2), _level(1)],
            _spec("A"),
            REGISTRY,
            work_dir=tmp_path / "nonmonotonic",
        )

    duplicate = _level(1)
    later_duplicate = _level(2)
    later_duplicate["source_record_id"] = duplicate["source_record_id"]
    with pytest.raises(RS0SpooledRuntimeError, match="DUPLICATE_SOURCE_RECORD"):
        run_spooled_empirical_runtime(
            [duplicate, later_duplicate],
            _spec("A"),
            REGISTRY,
            work_dir=tmp_path / "duplicate",
        )


def test_source_merge_fails_closed_when_an_input_stream_is_not_canonical() -> None:
    with pytest.raises(RS0SpooledRuntimeError, match="SOURCE_STREAM_NONMONOTONIC"):
        list(merge_canonical_source_streams([[_level(2), _level(1)]]))
