from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import pytest

from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime import run_empirical_runtime
from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_source_order import (
    SOURCE_ORDER_ADAPTER_ID,
    canonicalize_equal_time_groups,
    merge_source_streams_with_tie_canonicalization,
)
from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_streaming import (
    RS0SpooledRuntimeError,
    materialize_reference_result,
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
    *,
    first_valid_time: str,
    source_record_id: str,
    side: str = "BID",
    value: str = "1.2500",
) -> dict:
    return {
        "schema": "ovc-c2p2-rs0-source-row/v1",
        "source_role": "C2_VNEXT",
        "instrument": "GBPUSD",
        "side": side,
        "clock": "15M",
        "first_valid_time": first_valid_time,
        "evaluation_cutoff": first_valid_time,
        "source_record_id": source_record_id,
        "source_record_kind": "C2_LEVEL",
        "geometry_signature": {
            "horizon_id": "H4",
            "level_type": "RANGE_HIGH",
            "value": value,
            "origin": "C2AR",
            "structural_depth": None,
        },
        "relation_topology": ["ABOVE"],
    }


def _adversarial_streams() -> list[list[dict]]:
    return [
        [
            _level(first_valid_time="2021-01-01T00:00:00Z", source_record_id="BID-Z"),
            _level(first_valid_time="2021-01-01T00:00:00Z", source_record_id="BID-A"),
            _level(first_valid_time="2021-01-01T00:15:00Z", source_record_id="BID-C"),
            _level(first_valid_time="2021-01-01T00:15:00Z", source_record_id="BID-B"),
        ],
        [
            _level(first_valid_time="2021-01-01T00:00:00Z", source_record_id="ASK-Z", side="ASK"),
            _level(first_valid_time="2021-01-01T00:00:00Z", source_record_id="ASK-A", side="ASK"),
            _level(first_valid_time="2021-01-01T00:15:00Z", source_record_id="ASK-C", side="ASK"),
            _level(first_valid_time="2021-01-01T00:15:00Z", source_record_id="ASK-B", side="ASK"),
        ],
    ]


@pytest.mark.parametrize("letter", ["A", "B", "C"])
def test_equal_time_unsorted_ties_are_exact_reference_equivalent(
    letter: str, tmp_path: Path
) -> None:
    streams = _adversarial_streams()
    reference_rows = [row for stream in streams for row in stream]
    reference = run_empirical_runtime(reference_rows, _spec(letter), REGISTRY)

    recovered = merge_source_streams_with_tie_canonicalization(streams)
    manifest = run_spooled_empirical_runtime(
        recovered,
        _spec(letter),
        REGISTRY,
        work_dir=tmp_path / letter,
        checkpoint_cadence=2,
    )

    assert materialize_reference_result(tmp_path / letter) == reference
    assert manifest["selection_state"] == "UNSELECTED_RESEARCH_CANDIDATE"
    assert manifest["activation_state"] == "NONE"
    assert manifest["real_source_launch"] == "NOT_AUTHORISED_BY_RUNTIME"
    assert SOURCE_ORDER_ADAPTER_ID.endswith("_v0_2")


def test_source_order_recovery_preserves_every_row_without_mutation() -> None:
    streams = _adversarial_streams()
    before = Counter(
        json.dumps(row, sort_keys=True, separators=(",", ":"))
        for stream in streams
        for row in stream
    )
    after_rows = list(merge_source_streams_with_tie_canonicalization(streams))
    after = Counter(
        json.dumps(row, sort_keys=True, separators=(",", ":"))
        for row in after_rows
    )

    assert before == after
    keys = [(row["first_valid_time"], row["source_record_id"]) for row in after_rows]
    assert keys == sorted(keys)
    assert len(keys) == len(set(row["source_record_id"] for row in after_rows))


def test_equal_time_group_is_buffered_locally_not_population_materialized() -> None:
    consumed = 0

    def stream():
        nonlocal consumed
        rows = [
            _level(first_valid_time="2021-01-01T00:00:00Z", source_record_id="Z"),
            _level(first_valid_time="2021-01-01T00:00:00Z", source_record_id="A"),
            _level(first_valid_time="2021-01-01T00:15:00Z", source_record_id="C"),
            _level(first_valid_time="2021-01-01T00:30:00Z", source_record_id="D"),
        ]
        for row in rows:
            consumed += 1
            yield row

    iterator = canonicalize_equal_time_groups(stream())
    first = next(iterator)

    assert first["source_record_id"] == "A"
    assert consumed == 3


def test_genuinely_decreasing_first_valid_time_fails_closed() -> None:
    stream = [
        _level(first_valid_time="2021-01-01T00:15:00Z", source_record_id="A"),
        _level(first_valid_time="2021-01-01T00:00:00Z", source_record_id="B"),
    ]
    with pytest.raises(RS0SpooledRuntimeError, match="FIRST_VALID_TIME_DECREASING"):
        list(canonicalize_equal_time_groups(stream))


def test_duplicate_equal_time_source_id_fails_closed() -> None:
    duplicate = _level(
        first_valid_time="2021-01-01T00:00:00Z",
        source_record_id="DUP",
    )
    with pytest.raises(RS0SpooledRuntimeError, match="DUPLICATE_OR_NONUNIQUE_ID"):
        list(canonicalize_equal_time_groups([duplicate, dict(duplicate)]))


def test_cross_time_duplicate_id_remains_runtime_fail_closed(tmp_path: Path) -> None:
    rows = [
        _level(first_valid_time="2021-01-01T00:00:00Z", source_record_id="DUP"),
        _level(first_valid_time="2021-01-01T00:15:00Z", source_record_id="DUP"),
    ]
    with pytest.raises(RS0SpooledRuntimeError, match="DUPLICATE_SOURCE_RECORD"):
        run_spooled_empirical_runtime(
            merge_source_streams_with_tie_canonicalization([rows]),
            _spec("A"),
            REGISTRY,
            work_dir=tmp_path,
        )
