from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

import pytest

from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime import _hash, run_empirical_runtime
from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_indexed import (
    EVIDENCE_CONTRACT_ID,
    RUNTIME_GENERATION_ID,
    RS0IndexedRuntimeError,
    materialize_outcome_result,
    necessary_match_key,
    run_indexed_empirical_runtime,
)
from ovc.opt_b.c2p_v0_2.rs0_empirical_semantics import normalize_candidate_source_row


DEPENDENCIES = {"entries": []}
SPECS = [
    {
        "candidate_id": "C2P2-PS0-OP-A-STRICT-CONTINUITY-v3",
        "semantic_candidate_id": "C2P2-PS0-OP-A-STRICT-CONTINUITY-v2",
        "activation_eligible": False,
    },
    {
        "candidate_id": "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v3",
        "semantic_candidate_id": "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v2",
        "activation_eligible": False,
    },
    {
        "candidate_id": "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v3",
        "semantic_candidate_id": "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v2",
        "activation_eligible": False,
    },
]
DECISION_EQUIVALENCE_FIELDS = (
    "object_pack_candidate_id",
    "candidate_id",
    "eligible_assertion_ids",
    "eligible_tracklet_ids",
    "terminal_decision",
    "resulting_subject_id",
    "first_valid_time",
    "evaluation_cutoff",
)


def level_row(
    ordinal: int,
    *,
    level_type: str = "SWING_HIGH",
    value: str = "1.2500",
    topology: tuple[str, ...] = ("REL-A",),
    source_id: str | None = None,
    at: datetime | None = None,
) -> dict:
    stamp = at or datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * ordinal)
    iso = stamp.isoformat().replace("+00:00", "Z")
    return {
        "schema": "ovc-c2p2-rs0-source-row/v1",
        "source_role": "C2_VNEXT",
        "source_record_id": source_id or f"ROW-{ordinal:06d}",
        "source_record_kind": "C2_LEVEL",
        "instrument": "GBPUSD",
        "side": "ASK",
        "clock": "15M",
        "first_valid_time": iso,
        "evaluation_cutoff": iso,
        "geometry_signature": {
            "horizon_id": "H15",
            "level_type": level_type,
            "value": value,
            "origin": "TEST",
            "structural_depth": 1,
        },
        "relation_topology": list(topology),
    }


def canonical(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda row: (row["first_valid_time"], row["source_record_id"]))


def decision_projection(rows: list[dict]) -> list[dict]:
    return [
        {key: row[key] for key in DECISION_EQUIVALENCE_FIELDS}
        for row in rows
    ]


def assert_outcome_equivalent(reference: dict, indexed: dict) -> None:
    assert indexed["processed_source_record_ids"] == reference["processed_source_record_ids"]
    assert indexed["last_stream_order_key"] == reference["last_stream_order_key"]
    assert indexed["candidates"] == reference["candidates"]
    assert indexed["tracklets"] == reference["tracklets"]
    assert indexed["object_assertions"] == reference["object_assertions"]
    assert indexed["indexes"] == reference["indexes"]
    assert decision_projection(indexed["match_decisions"]) == decision_projection(reference["match_decisions"])
    assert indexed["runtime_generation_id"] == RUNTIME_GENERATION_ID
    assert indexed["evidence_contract_id"] == EVIDENCE_CONTRACT_ID
    assert indexed["selection_state"] == "UNSELECTED_RESEARCH_CANDIDATE"
    assert indexed["activation_state"] == "NONE"
    assert indexed["real_source_launch"] == "FORBIDDEN_BY_AUTHORITY"


@pytest.mark.parametrize("spec", SPECS, ids=["A", "B", "C"])
def test_a_b_c_terminal_and_lifecycle_outcomes_match_frozen_reference(tmp_path: Path, spec: dict) -> None:
    rows = canonical([
        level_row(0, value="1.2500"),
        level_row(1, value="1.2500"),
        level_row(2, value="1.2500"),
        level_row(3, level_type="SWING_LOW", value="1.2400", topology=("REL-B",)),
        level_row(4, value="1.2500"),
        level_row(5, level_type="SWING_LOW", value="1.2400", topology=("REL-B",)),
        level_row(6, level_type="SWING_LOW", value="1.2400", topology=("REL-B",)),
        level_row(7, level_type="SWING_LOW", value="1.2400", topology=("REL-B",)),
    ])
    reference = run_empirical_runtime(rows, spec, DEPENDENCIES)
    work = tmp_path / spec["candidate_id"]
    manifest = run_indexed_empirical_runtime(rows, spec, DEPENDENCIES, work_dir=work, checkpoint_cadence=2)
    indexed = materialize_outcome_result(work)
    assert_outcome_equivalent(reference, indexed)
    assert manifest["counts"]["negative_coverage_certificates"] == len(rows)
    assert manifest["real_source_launch"] == "FORBIDDEN_BY_AUTHORITY"


def test_candidate_a_unique_density_replaces_quadratic_negative_vectors_with_linear_certificates(tmp_path: Path) -> None:
    spec = SPECS[0]
    n = 256
    rows = canonical([level_row(i, value=f"{1 + i / 100000:.5f}") for i in range(n)])
    reference = run_empirical_runtime(rows, spec, DEPENDENCIES)
    expected_vectors = n * (n - 1) // 2
    assert len(reference["evidence_vectors"]) == expected_vectors

    work = tmp_path / "indexed-unique"
    manifest = run_indexed_empirical_runtime(rows, spec, DEPENDENCIES, work_dir=work, checkpoint_cadence=32)
    indexed = materialize_outcome_result(work)
    assert_outcome_equivalent(reference, indexed)
    assert manifest["counts"]["evaluated_pair_vectors"] == 0
    assert manifest["counts"]["negative_coverage_certificates"] == n
    last = indexed["negative_coverage_certificates"][-1]
    assert last["open_tracklets"]["scope_total"] == n - 1
    assert last["open_tracklets"]["examined"] == 0
    assert last["open_tracklets"]["pruned_by_necessary_key_or_global_blocker"] == n - 1


@pytest.mark.parametrize("blocker_kind", ["discontinuity", "terminal_break"])
def test_global_breaks_preserve_reference_censoring_and_terminal_outcomes(tmp_path: Path, blocker_kind: str) -> None:
    spec = SPECS[0]
    rows = canonical([
        level_row(0, value="1.2500"),
        level_row(1, level_type="SWING_LOW", value="1.2400", topology=("REL-B",)),
        level_row(2, value="1.2500"),
    ])
    target = rows[-1]["source_record_id"]
    kwargs = (
        {"explicit_discontinuity_source_ids": [target]}
        if blocker_kind == "discontinuity"
        else {"prior_terminal_break_source_ids": [target]}
    )
    reference = run_empirical_runtime(rows, spec, DEPENDENCIES, **kwargs)
    work = tmp_path / blocker_kind
    run_indexed_empirical_runtime(rows, spec, DEPENDENCIES, work_dir=work, **kwargs)
    indexed = materialize_outcome_result(work)
    assert_outcome_equivalent(reference, indexed)
    certificate = indexed["negative_coverage_certificates"][-1]
    assert certificate["global_blocker"] in {
        "RS0_EXPLICIT_SOURCE_DISCONTINUITY",
        "RS0_PRIOR_TERMINAL_BREAK",
    }
    assert certificate["open_tracklets"]["examined"] == 0


def test_forced_equal_lawful_tracklet_ambiguity_matches_reference(tmp_path: Path) -> None:
    spec = SPECS[0]
    first = level_row(0, value="1.2500")
    second = level_row(1, value="1.2500")

    reference_state = run_empirical_runtime([first], spec, DEPENDENCIES)
    clone = deepcopy(reference_state["tracklets"][0])
    clone["tracklet_id"] = "SYNTHETIC-EQUAL-LAWFUL-COMPETITOR"
    reference_state["tracklets"].append(clone)
    scope_key = next(iter(reference_state["indexes"]["open_tracklet_ids_by_scope"]))
    reference_state["indexes"]["open_tracklet_ids_by_scope"][scope_key].append(clone["tracklet_id"])
    reference_state["indexes"]["open_tracklet_ids_by_scope"][scope_key].sort()
    reference_state["checkpoint_sha256"] = _hash({
        key: value for key, value in reference_state.items() if key != "checkpoint_sha256"
    })
    reference = run_empirical_runtime([second], spec, DEPENDENCIES, initial_state=reference_state)

    work = tmp_path / "ambiguous"
    run_indexed_empirical_runtime([first], spec, DEPENDENCIES, work_dir=work)
    material = normalize_candidate_source_row(first)
    match_key = necessary_match_key(spec["semantic_candidate_id"], material)
    database = work / "runtime-indexed.sqlite3"
    with sqlite3.connect(database) as connection:
        original = connection.execute(
            "SELECT value_json, scope_key FROM tracklets ORDER BY ordinal LIMIT 1"
        ).fetchone()
        injected = json.loads(original[0])
        injected["tracklet_id"] = clone["tracklet_id"]
        connection.execute(
            "INSERT INTO tracklets(tracklet_id, ordinal, scope_key, match_key, state, value_json) VALUES (?, ?, ?, ?, 'OPEN', ?)",
            (clone["tracklet_id"], 1, original[1], match_key, json.dumps(injected, sort_keys=True, separators=(",", ":"))),
        )
        connection.commit()
    run_indexed_empirical_runtime([second], spec, DEPENDENCIES, work_dir=work, resume=True)
    indexed = materialize_outcome_result(work)
    assert_outcome_equivalent(reference, indexed)
    assert indexed["match_decisions"][-1]["terminal_decision"] == "AMBIGUOUS"
    assert sorted(indexed["match_decisions"][-1]["eligible_tracklet_ids"]) == sorted([
        reference_state["tracklets"][0]["tracklet_id"], clone["tracklet_id"]
    ])


def test_restart_is_deterministic_and_duplicate_nonmonotonic_streams_fail_closed(tmp_path: Path) -> None:
    spec = SPECS[0]
    rows = canonical([
        level_row(0, value="1.2500"),
        level_row(1, value="1.2500"),
        level_row(2, value="1.2500"),
        level_row(3, level_type="SWING_LOW", value="1.2400"),
        level_row(4, level_type="SWING_LOW", value="1.2400"),
    ])
    one_shot = tmp_path / "one-shot"
    restarted = tmp_path / "restarted"
    run_indexed_empirical_runtime(rows, spec, DEPENDENCIES, work_dir=one_shot)
    run_indexed_empirical_runtime(rows[:2], spec, DEPENDENCIES, work_dir=restarted)
    run_indexed_empirical_runtime(rows[2:], spec, DEPENDENCIES, work_dir=restarted, resume=True)
    assert materialize_outcome_result(one_shot) == materialize_outcome_result(restarted)

    duplicate = tmp_path / "duplicate"
    run_indexed_empirical_runtime(rows[:1], spec, DEPENDENCIES, work_dir=duplicate)
    with pytest.raises(RS0IndexedRuntimeError, match="DUPLICATE_SOURCE_RECORD"):
        run_indexed_empirical_runtime(rows[:1], spec, DEPENDENCIES, work_dir=duplicate, resume=True)

    equal_time = datetime(2024, 2, 1, tzinfo=timezone.utc)
    canonical_equal = [
        level_row(0, source_id="EQ-A", at=equal_time, value="1.2500"),
        level_row(1, source_id="EQ-B", at=equal_time, value="1.2500"),
    ]
    equal_work = tmp_path / "equal-time"
    run_indexed_empirical_runtime(canonical_equal, spec, DEPENDENCIES, work_dir=equal_work)
    assert materialize_outcome_result(equal_work)["processed_source_record_ids"] == ["EQ-A", "EQ-B"]

    bad = tmp_path / "nonmonotonic"
    with pytest.raises(RS0IndexedRuntimeError, match="NONMONOTONIC"):
        run_indexed_empirical_runtime(list(reversed(canonical_equal)), spec, DEPENDENCIES, work_dir=bad)


def test_nonempty_dependency_registry_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(RS0IndexedRuntimeError, match="FROZEN_EMPTY_C2E"):
        run_indexed_empirical_runtime(
            [level_row(0)],
            SPECS[2],
            {"entries": [{"structural_role_id": "LEVEL"}]},
            work_dir=tmp_path / "bad-dependency",
        )
