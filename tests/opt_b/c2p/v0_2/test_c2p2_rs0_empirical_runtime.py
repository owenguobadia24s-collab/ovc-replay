from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

import pytest

from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime import (
    RS0EmpiricalRuntimeError,
    run_comparative_set,
    run_empirical_runtime,
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


def _level(index: int, *, value: str = "1.2500", topology: str = "ABOVE") -> dict:
    return {
        "schema": "ovc-c2p2-rs0-source-row/v1",
        "source_role": "C2_VNEXT",
        "instrument": "GBPUSD",
        "side": "BID",
        "clock": "15M",
        "first_valid_time": f"2021-01-01T{index // 60:02d}:{index % 60:02d}:00Z",
        "evaluation_cutoff": f"2021-01-01T{index // 60:02d}:{index % 60:02d}:00Z",
        "source_record_id": f"L{index:04d}",
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


def _rehash_checkpoint(state: dict) -> None:
    payload = {key: value for key, value in state.items() if key != "checkpoint_sha256"}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    state["checkpoint_sha256"] = sha256(raw).hexdigest()


def test_exact_a_runtime_materialises_candidate_tracklet_genesis_and_update() -> None:
    result = run_empirical_runtime([_level(i) for i in range(1, 5)], _spec("A"), REGISTRY)

    assert len(result["candidates"]) == 4
    assert [row["terminal_decision"] for row in result["match_decisions"]] == [
        "NEW_TRACKLET", "TRACKLET_UPDATE", "GENESIS", "UPDATE"
    ]
    assert len(result["tracklets"]) == 1
    assert result["tracklets"][0]["state"] == "CONFIRMED"
    assert len(result["object_assertions"]) == 1
    assertion = result["object_assertions"][0]
    assert assertion["observation_count"] == 4
    assert assertion["activation_state"] == "NONE"
    assert result["selection_state"] == "UNSELECTED_RESEARCH_CANDIDATE"
    assert result["real_source_launch"] == "NOT_AUTHORISED_BY_RUNTIME"


def test_a_and_b_discriminate_moving_geometry_without_numeric_threshold() -> None:
    rows = [_level(i, value=f"1.25{i:02d}") for i in range(1, 5)]
    strict = run_empirical_runtime(rows, _spec("A"), REGISTRY)
    relational = run_empirical_runtime(rows, _spec("B"), REGISTRY)

    assert len(strict["object_assertions"]) == 0
    assert len(strict["tracklets"]) == 4
    assert len(relational["object_assertions"]) == 1
    assert relational["object_assertions"][0]["observation_count"] == 4
    vectors = relational["evidence_vectors"]
    assert vectors
    assert all(row["numeric_residual_policy"] == "EVIDENCE_ONLY_NO_PASS_THRESHOLD" for row in vectors)
    assert all("score" not in row and "rank" not in row for row in vectors)


def test_current_c_runtime_uses_lawful_c2_only_route() -> None:
    rows = [_level(i, value=f"1.25{i:02d}", topology="ABOVE" if i < 3 else "BELOW") for i in range(1, 5)]
    result = run_empirical_runtime(rows, _spec("C"), REGISTRY)

    assert len(result["object_assertions"]) == 1
    assert all(
        vector["c2e_dependency_disposition"] == "NOT_APPLICABLE_C2_ONLY"
        for vector in result["evidence_vectors"]
    )


def test_explicit_discontinuity_censors_open_tracklet_and_opens_new_identity_path() -> None:
    rows = [_level(i) for i in range(1, 4)]
    result = run_empirical_runtime(
        rows,
        _spec("A"),
        REGISTRY,
        explicit_discontinuity_source_ids={"L0003"},
    )

    assert [row["state"] for row in result["tracklets"]] == ["CENSORED", "OPEN"]
    assert result["tracklets"][0]["reason_codes"] == ["RS0_EXPLICIT_SOURCE_DISCONTINUITY"]
    assert len(result["object_assertions"]) == 0
    assert result["match_decisions"][-1]["terminal_decision"] == "NEW_TRACKLET"


def test_restart_checkpoint_and_replay_are_byte_deterministic() -> None:
    rows = [_level(i, value=f"1.25{i:02d}") for i in range(1, 7)]
    one_shot = run_empirical_runtime(rows, _spec("B"), REGISTRY)
    first = run_empirical_runtime(rows[:2], _spec("B"), REGISTRY)
    restarted = run_empirical_runtime(rows[2:], _spec("B"), REGISTRY, initial_state=first)
    replayed = run_empirical_runtime(rows, _spec("B"), REGISTRY)

    assert restarted == one_shot == replayed
    corrupt = deepcopy(first)
    corrupt["selection_state"] = "SELECTED"
    with pytest.raises(RS0EmpiricalRuntimeError, match="CHECKPOINT_HASH_MISMATCH"):
        run_empirical_runtime(rows[2:], _spec("B"), REGISTRY, initial_state=corrupt)


def test_equal_lawful_assertions_remain_ambiguous_without_tie_break() -> None:
    base = run_empirical_runtime([_level(i) for i in range(1, 4)], _spec("A"), REGISTRY)
    second = deepcopy(base["object_assertions"][0])
    second["object_assertion_id"] = "b" * 64
    base["object_assertions"].append(second)
    scope_key = next(iter(base["indexes"]["assertion_ids_by_scope"]))
    base["indexes"]["assertion_ids_by_scope"][scope_key].append(second["object_assertion_id"])
    base["indexes"]["assertion_ids_by_scope"][scope_key].sort()
    _rehash_checkpoint(base)

    result = run_empirical_runtime([_level(4)], _spec("A"), REGISTRY, initial_state=base)
    decision = result["match_decisions"][-1]
    assert decision["terminal_decision"] == "AMBIGUOUS"
    assert decision["eligible_assertion_ids"] == sorted([
        base["object_assertions"][0]["object_assertion_id"], "b" * 64
    ])
    assert all(assertion["observation_count"] == 3 for assertion in result["object_assertions"])
    assert decision["resulting_subject_id"] is None


def test_comparative_runtime_has_no_winner_activation_or_real_source_authority() -> None:
    result = run_comparative_set(
        [_level(i, value=f"1.25{i:02d}") for i in range(1, 5)],
        [_spec("C"), _spec("A"), _spec("B")],
        REGISTRY,
    )

    assert result["selection_state"] == "COMPARATIVE_SET_ONLY_NO_WINNER"
    assert result["active_object_pack_id"] is None
    assert result["real_source_launch"] == "NOT_AUTHORISED_BY_RUNTIME"
    assert len(result["candidate_results"]) == 3
    assert all(row["activation_state"] == "NONE" for row in result["candidate_results"])


def test_runtime_fails_closed_on_forbidden_duplicate_nonmonotonic_or_activation_inputs() -> None:
    forbidden = _level(1)
    forbidden["geometry_signature"]["nested"] = {"outcome": "FORBIDDEN"}
    with pytest.raises(ValueError, match="RS0_FORBIDDEN_IDENTITY_FIELD"):
        run_empirical_runtime([forbidden], _spec("A"), REGISTRY)

    with pytest.raises(RS0EmpiricalRuntimeError, match="DUPLICATE_SOURCE_RECORD"):
        run_empirical_runtime([_level(1), _level(1)], _spec("A"), REGISTRY)

    first = run_empirical_runtime([_level(2)], _spec("A"), REGISTRY)
    with pytest.raises(RS0EmpiricalRuntimeError, match="NONMONOTONIC_RESTART_STREAM"):
        run_empirical_runtime([_level(1)], _spec("A"), REGISTRY, initial_state=first)

    active = _spec("A")
    active["activation_eligible"] = True
    with pytest.raises(RS0EmpiricalRuntimeError, match="ACTIVATION_FORBIDDEN"):
        run_empirical_runtime([_level(1)], active, REGISTRY)


def test_deterministic_scope_indexes_are_exact_and_capacity_fixture_is_complete() -> None:
    rows = [_level(i, value=f"{1 + i / 100000:.5f}") for i in range(1, 301)]
    result = run_empirical_runtime(rows, _spec("B"), REGISTRY)

    assertion_ids = sorted(row["object_assertion_id"] for row in result["object_assertions"])
    indexed_ids = sorted(
        value
        for values in result["indexes"]["assertion_ids_by_scope"].values()
        for value in values
    )
    assert indexed_ids == assertion_ids
    assert len(result["processed_source_record_ids"]) == 300
    assert len(result["candidates"]) == 300
    assert result["checkpoint_sha256"] == run_empirical_runtime(rows, _spec("B"), REGISTRY)["checkpoint_sha256"]
