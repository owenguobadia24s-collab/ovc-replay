from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import pytest

from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime import run_empirical_runtime
from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_source_order import (
    BASE_CANDIDATE_SOURCE_KINDS,
    CONTEXT_ONLY_SOURCE_KINDS,
    SOURCE_ORDER_ADAPTER_ID,
    canonicalize_equal_time_groups,
    inspect_source_kind_segments,
    merge_source_factories_with_kind_segmentation,
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


def _row(
    *,
    first_valid_time: str,
    source_record_id: str,
    source_record_kind: str,
    side: str = "BID",
) -> dict:
    if source_record_kind == "C2_LEVEL":
        geometry_signature = {
            "horizon_id": "H4",
            "level_type": "RANGE_HIGH",
            "value": "1.2500",
            "origin": "C2AR",
            "structural_depth": None,
        }
        clock = "15M"
    elif source_record_kind == "C2_CONTAINER":
        geometry_signature = {
            "horizon_id": "H4",
            "kind": "RANGE",
            "lower_value": "1.2400",
            "upper_value": "1.2600",
            "centre": "1.2500",
            "width": "0.0200",
            "origin": "C2AR",
            "structural_depth": None,
        }
        clock = "15M"
    elif source_record_kind == "C2_PARENT_OBSERVATION":
        geometry_signature = {
            "interval_start": first_valid_time,
            "interval_end": first_valid_time,
            "open": "1.2500",
            "high": "1.2600",
            "low": "1.2400",
            "close": "1.2550",
        }
        clock = "2H_A_L"
    else:
        raise AssertionError(source_record_kind)
    return {
        "schema": "ovc-c2p2-rs0-source-row/v1",
        "source_role": "C2_VNEXT",
        "instrument": "GBPUSD",
        "side": side,
        "clock": clock,
        "first_valid_time": first_valid_time,
        "evaluation_cutoff": first_valid_time,
        "source_record_id": source_record_id,
        "source_record_kind": source_record_kind,
        "geometry_signature": geometry_signature,
        "relation_topology": [],
    }


def _envelope(side: str, prefix: str) -> list[dict]:
    rows: list[dict] = []
    for kind, kind_prefix in (
        ("C2_LEVEL", "L"),
        ("C2_CONTAINER", "C"),
        ("C2_PARENT_OBSERVATION", "P"),
    ):
        rows.extend(
            [
                _row(
                    first_valid_time="2021-01-01T00:00:00Z",
                    source_record_id=f"{prefix}-{kind_prefix}-Z",
                    source_record_kind=kind,
                    side=side,
                ),
                _row(
                    first_valid_time="2021-01-01T00:00:00Z",
                    source_record_id=f"{prefix}-{kind_prefix}-A",
                    source_record_kind=kind,
                    side=side,
                ),
                _row(
                    first_valid_time="2021-01-01T00:15:00Z",
                    source_record_id=f"{prefix}-{kind_prefix}-C",
                    source_record_kind=kind,
                    side=side,
                ),
                _row(
                    first_valid_time="2021-01-01T00:15:00Z",
                    source_record_id=f"{prefix}-{kind_prefix}-B",
                    source_record_kind=kind,
                    side=side,
                ),
            ]
        )
    return rows


def _adversarial_envelopes() -> list[list[dict]]:
    return [_envelope("BID", "BID"), _envelope("ASK", "ASK")]


def _base_candidate_rows(envelopes: list[list[dict]]) -> list[dict]:
    allowed = set(BASE_CANDIDATE_SOURCE_KINDS)
    return [
        row
        for envelope in envelopes
        for row in envelope
        if row["source_record_kind"] in allowed
    ]


@pytest.mark.parametrize("letter", ["A", "B", "C"])
def test_segmented_equal_time_recovery_is_exact_reference_equivalent(
    letter: str, tmp_path: Path
) -> None:
    envelopes = _adversarial_envelopes()
    reference = run_empirical_runtime(_base_candidate_rows(envelopes), _spec(letter), REGISTRY)

    factories = [(lambda rows=envelope: iter(rows)) for envelope in envelopes]
    recovered = merge_source_factories_with_kind_segmentation(factories)
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


def test_source_kind_segment_inspection_preserves_context_without_promoting_it() -> None:
    envelope = _envelope("BID", "BID")
    receipt = inspect_source_kind_segments(envelope)

    assert receipt["observed_kinds"] == [
        "C2_LEVEL",
        "C2_CONTAINER",
        "C2_PARENT_OBSERVATION",
    ]
    assert receipt["base_candidate_kinds"] == list(BASE_CANDIDATE_SOURCE_KINDS)
    assert receipt["context_only_kinds"] == list(CONTEXT_ONLY_SOURCE_KINDS)
    assert receipt["base_candidate_rows"] == 8
    assert receipt["context_only_rows"] == 4
    assert receipt["raw_rows"] == 12
    assert receipt["segment_transitions"] == [
        {"from": "C2_LEVEL", "to": "C2_CONTAINER"},
        {"from": "C2_CONTAINER", "to": "C2_PARENT_OBSERVATION"},
    ]
    assert receipt["boundary_time_decreases"] == 2
    assert receipt["within_kind_time_decreases"] == 0


def test_recovery_preserves_all_source_rows_and_projects_exact_base_candidate_subset() -> None:
    envelopes = _adversarial_envelopes()
    raw_before = Counter(
        json.dumps(row, sort_keys=True, separators=(",", ":"))
        for envelope in envelopes
        for row in envelope
    )
    assert sum(raw_before.values()) == 24

    factories = [(lambda rows=envelope: iter(rows)) for envelope in envelopes]
    recovered_rows = list(merge_source_factories_with_kind_segmentation(factories))
    expected_base = Counter(
        json.dumps(row, sort_keys=True, separators=(",", ":"))
        for row in _base_candidate_rows(envelopes)
    )
    observed_base = Counter(
        json.dumps(row, sort_keys=True, separators=(",", ":"))
        for row in recovered_rows
    )

    assert observed_base == expected_base
    assert all(
        row["source_record_kind"] in BASE_CANDIDATE_SOURCE_KINDS
        for row in recovered_rows
    )
    assert len(recovered_rows) == 16
    keys = [(row["first_valid_time"], row["source_record_id"]) for row in recovered_rows]
    assert keys == sorted(keys)
    assert len(keys) == len(set(row["source_record_id"] for row in recovered_rows))


def test_equal_time_group_is_buffered_locally_not_population_materialized() -> None:
    consumed = 0

    def stream():
        nonlocal consumed
        rows = [
            _row(
                first_valid_time="2021-01-01T00:00:00Z",
                source_record_id="Z",
                source_record_kind="C2_LEVEL",
            ),
            _row(
                first_valid_time="2021-01-01T00:00:00Z",
                source_record_id="A",
                source_record_kind="C2_LEVEL",
            ),
            _row(
                first_valid_time="2021-01-01T00:15:00Z",
                source_record_id="C",
                source_record_kind="C2_LEVEL",
            ),
            _row(
                first_valid_time="2021-01-01T00:30:00Z",
                source_record_id="D",
                source_record_kind="C2_LEVEL",
            ),
        ]
        for row in rows:
            consumed += 1
            yield row

    iterator = canonicalize_equal_time_groups(stream())
    first = next(iterator)

    assert first["source_record_id"] == "A"
    assert consumed == 3


def test_genuinely_decreasing_time_within_kind_fails_closed() -> None:
    stream = [
        _row(
            first_valid_time="2021-01-01T00:15:00Z",
            source_record_id="A",
            source_record_kind="C2_LEVEL",
        ),
        _row(
            first_valid_time="2021-01-01T00:00:00Z",
            source_record_id="B",
            source_record_kind="C2_LEVEL",
        ),
    ]
    with pytest.raises(
        RS0SpooledRuntimeError,
        match="FIRST_VALID_TIME_DECREASING_WITHIN_KIND",
    ):
        inspect_source_kind_segments(stream)


def test_source_kind_reentry_fails_closed() -> None:
    stream = [
        _row(
            first_valid_time="2021-01-01T00:00:00Z",
            source_record_id="L1",
            source_record_kind="C2_LEVEL",
        ),
        _row(
            first_valid_time="2021-01-01T00:00:00Z",
            source_record_id="C1",
            source_record_kind="C2_CONTAINER",
        ),
        _row(
            first_valid_time="2021-01-01T00:15:00Z",
            source_record_id="L2",
            source_record_kind="C2_LEVEL",
        ),
    ]
    with pytest.raises(RS0SpooledRuntimeError, match="KIND_SEGMENT_REENTRY"):
        inspect_source_kind_segments(stream)


def test_duplicate_equal_time_source_id_fails_closed() -> None:
    duplicate = _row(
        first_valid_time="2021-01-01T00:00:00Z",
        source_record_id="DUP",
        source_record_kind="C2_LEVEL",
    )
    with pytest.raises(RS0SpooledRuntimeError, match="DUPLICATE_OR_NONUNIQUE_ID"):
        list(canonicalize_equal_time_groups([duplicate, dict(duplicate)]))


def test_cross_time_duplicate_id_remains_runtime_fail_closed(tmp_path: Path) -> None:
    rows = [
        _row(
            first_valid_time="2021-01-01T00:00:00Z",
            source_record_id="DUP",
            source_record_kind="C2_LEVEL",
        ),
        _row(
            first_valid_time="2021-01-01T00:15:00Z",
            source_record_id="DUP",
            source_record_kind="C2_LEVEL",
        ),
    ]
    factories = [lambda: iter(rows)]
    with pytest.raises(RS0SpooledRuntimeError, match="DUPLICATE_SOURCE_RECORD"):
        run_spooled_empirical_runtime(
            merge_source_factories_with_kind_segmentation(factories),
            _spec("A"),
            REGISTRY,
            work_dir=tmp_path,
        )
