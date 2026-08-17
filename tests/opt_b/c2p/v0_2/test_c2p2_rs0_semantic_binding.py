from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from ovc.opt_b.c2p_v0_2.rs0_empirical_semantics import (
    RS0SemanticError,
    c2e_dependency_disposition,
    evaluate_pair,
    normalize_candidate_source_row,
)

ROOT = Path(__file__).resolve().parents[4]
REG = ROOT / "registries/opt_b/c2p/v0_2/research"
RS0 = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0"
PS0 = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-ps0"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _logical_hash(record: dict, field: str) -> str:
    payload = {key: value for key, value in record.items() if key != field}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(raw).hexdigest()


def _candidate_hash(candidate: dict) -> str:
    payload = {key: value for key, value in candidate.items() if key != "candidate_logical_hash"}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(raw).hexdigest()


def _level(*, record_id: str, value: float, topology: list[str] | None = None, level_type: str = "RANGE_HIGH") -> dict:
    return {
        "schema": "ovc-c2p2-rs0-source-row/v1",
        "source_role": "C2_VNEXT",
        "instrument": "GBPUSD",
        "side": "BID",
        "clock": "15M",
        "first_valid_time": "2021-01-01T00:15:00Z" if record_id == "L1" else "2021-01-01T00:30:00Z",
        "evaluation_cutoff": "2021-01-01T00:15:00Z" if record_id == "L1" else "2021-01-01T00:30:00Z",
        "source_record_id": record_id,
        "source_record_kind": "C2_LEVEL",
        "structural_role_id": level_type,
        "geometry_kind_id": "POINT",
        "geometry_signature": {
            "horizon_id": "H4",
            "level_type": level_type,
            "value": value,
            "origin": "C2AR",
            "structural_depth": None,
        },
        "relation_topology": topology or ["ABOVE"],
    }


def _container(*, record_id: str, lower: float, upper: float) -> dict:
    return {
        "schema": "ovc-c2p2-rs0-source-row/v1",
        "source_role": "C2_VNEXT",
        "instrument": "GBPUSD",
        "side": "ASK",
        "clock": "15M",
        "first_valid_time": "2021-01-01T00:15:00Z" if record_id == "C1" else "2021-01-01T00:30:00Z",
        "evaluation_cutoff": "2021-01-01T00:15:00Z" if record_id == "C1" else "2021-01-01T00:30:00Z",
        "source_record_id": record_id,
        "source_record_kind": "C2_CONTAINER",
        "structural_role_id": "TRAILING_RANGE",
        "geometry_kind_id": "INTERVAL",
        "geometry_signature": {
            "horizon_id": "H4",
            "kind": "TRAILING_RANGE",
            "lower_value": lower,
            "upper_value": upper,
            "centre": (lower + upper) / 2,
            "width": upper - lower,
            "origin": "C2AR",
            "structural_depth": 1,
        },
        "relation_topology": ["INSIDE"],
    }


def test_all_semantic_artifact_hashes_and_successor_candidate_hashes_are_exact() -> None:
    geometry = _read(REG / "C2P2_RS0_EMPIRICAL_GEOMETRY_COMPATIBILITY_v0_1.json")
    c2e = _read(REG / "C2P2_RS0_C2E_DEPENDENCY_ROLE_REGISTRY_v0_1.json")
    binding = _read(REG / "C2P2_RS0_EMPIRICAL_SEMANTICS_BINDING_v0_1.json")
    candidates = _read(PS0 / "C2P2_PS0_OBJECTPACK_CANDIDATES_v0_2.json")
    currentness = _read(RS0 / "C2P2_RS0_CANDIDATE_CURRENTNESS_v0_1.json")

    assert geometry["logical_sha256"] == _logical_hash(geometry, "logical_sha256")
    assert c2e["logical_sha256"] == _logical_hash(c2e, "logical_sha256")
    assert binding["logical_sha256"] == _logical_hash(binding, "logical_sha256")
    assert candidates["generation_logical_sha256"] == _logical_hash(candidates, "generation_logical_sha256")
    assert currentness["logical_sha256"] == _logical_hash(currentness, "logical_sha256")
    for candidate in candidates["candidates"]:
        assert candidate["candidate_logical_hash"] == _candidate_hash(candidate)

    assert candidates["grun_currentness"]["fresh_grun_required"] is True
    assert currentness["identity_change"] is True
    assert currentness["old_grun_token_disposition"] == "PRESERVED_UNCONSUMED_NOT_APPLICABLE_TO_SUCCESSOR_GENERATION"
    assert candidates["active_object_pack_id"] is None
    assert candidates["selection_state"] == "NONE_SELECTED"


def test_source_normalization_is_exact_and_context_or_c2e_cannot_become_base_candidate() -> None:
    level = normalize_candidate_source_row(_level(record_id="L1", value=1.25))
    assert level["structural_role_id"] == "LEVEL"
    assert level["geometry_kind_id"] == "POINT_REFERENCE"
    assert level["owner_geometry_class"] == {
        "horizon_id": "H4",
        "level_type": "RANGE_HIGH",
        "origin": "C2AR",
        "structural_depth": None,
    }

    container = normalize_candidate_source_row(_container(record_id="C1", lower=1.20, upper=1.30))
    assert container["structural_role_id"] == "RANGE"
    assert container["geometry_kind_id"] == "INTERVAL"
    assert container["owner_geometry_class"]["kind"] == "TRAILING_RANGE"

    parent = _level(record_id="P1", value=1.25)
    parent["source_record_kind"] = "C2_PARENT_OBSERVATION"
    parent["clock"] = "2H_A_L"
    with pytest.raises(RS0SemanticError, match="RS0_BASE_CANDIDATE_SOURCE_FORBIDDEN"):
        normalize_candidate_source_row(parent)

    c2e = _level(record_id="E1", value=1.25)
    c2e["source_role"] = "C2E_V0_2"
    with pytest.raises(RS0SemanticError, match="RS0_BASE_CANDIDATE_REQUIRES_C2_VNEXT"):
        normalize_candidate_source_row(c2e)


def test_a_b_c_discriminate_exact_geometry_relational_evolution_and_current_c2_only_route() -> None:
    registry = _read(REG / "C2P2_RS0_C2E_DEPENDENCY_ROLE_REGISTRY_v0_1.json")
    old = normalize_candidate_source_row(_level(record_id="L1", value=1.25, topology=["ABOVE"]))
    moved = normalize_candidate_source_row(_level(record_id="L2", value=1.255, topology=["ABOVE"]))

    a = evaluate_pair("C2P2-PS0-OP-A-STRICT-CONTINUITY-v2", old, moved, registry)
    b = evaluate_pair("C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v2", old, moved, registry)
    c = evaluate_pair("C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v2", old, moved, registry)

    assert a["same_object_pair_supported"] is False
    assert a["predicate_results"]["same_geometry_signature"] is False
    assert b["same_object_pair_supported"] is True
    assert b["geometry_residuals"]["value"] == "0.005"
    assert b["numeric_residual_policy"] == "EVIDENCE_ONLY_NO_PASS_THRESHOLD"
    assert c["same_object_pair_supported"] is True
    assert c["c2e_dependency_disposition"] == "NOT_APPLICABLE_C2_ONLY"

    changed_topology = normalize_candidate_source_row(_level(record_id="L2", value=1.255, topology=["BELOW"]))
    b2 = evaluate_pair("C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v2", old, changed_topology, registry)
    c2 = evaluate_pair("C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v2", old, changed_topology, registry)
    assert b2["predicate_results"]["same_relation_topology"] is False
    assert b2["same_object_pair_supported"] is False
    assert c2["same_object_pair_supported"] is True


def test_container_numeric_evolution_is_residual_evidence_not_identity_threshold() -> None:
    registry = _read(REG / "C2P2_RS0_C2E_DEPENDENCY_ROLE_REGISTRY_v0_1.json")
    old = normalize_candidate_source_row(_container(record_id="C1", lower=1.20, upper=1.30))
    moved = normalize_candidate_source_row(_container(record_id="C2", lower=1.21, upper=1.32))
    result = evaluate_pair("C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v2", old, moved, registry)
    assert result["same_object_pair_supported"] is True
    assert result["numeric_residual_policy"] == "EVIDENCE_ONLY_NO_PASS_THRESHOLD"
    assert set(result["geometry_residuals"]) == {"centre", "lower_value", "upper_value", "width"}


def test_c2e_dependency_registry_has_zero_current_episode_relative_roles_and_future_unbound_role_fails_closed() -> None:
    registry = _read(REG / "C2P2_RS0_C2E_DEPENDENCY_ROLE_REGISTRY_v0_1.json")
    assert registry["entries"] == []
    assert registry["current_declared_episode_relative_roles"] == []
    assert c2e_dependency_disposition("LEVEL", registry) == "NOT_APPLICABLE_C2_ONLY"
    future = dict(registry)
    future["entries"] = [{"structural_role_id": "EPISODE_RELATIVE_LEVEL", "execution_mode": "PENDING"}]
    with pytest.raises(RS0SemanticError, match="RS0_C2E_DEPENDENCY_ROLE_UNBOUND"):
        c2e_dependency_disposition("EPISODE_RELATIVE_LEVEL", future)


def test_explicit_discontinuity_breaks_continuity_without_inventing_elapsed_time_threshold() -> None:
    registry = _read(REG / "C2P2_RS0_C2E_DEPENDENCY_ROLE_REGISTRY_v0_1.json")
    old = normalize_candidate_source_row(_level(record_id="L1", value=1.25))
    moved = normalize_candidate_source_row(_level(record_id="L2", value=1.25))
    result = evaluate_pair(
        "C2P2-PS0-OP-A-STRICT-CONTINUITY-v2",
        old,
        moved,
        registry,
        explicit_discontinuity=True,
    )
    assert result["predicate_results"]["chronology_contiguous"] is False
    binding = _read(REG / "C2P2_RS0_EMPIRICAL_SEMANTICS_BINDING_v0_1.json")
    assert binding["common_identity_mechanics"]["chronology"]["numeric_elapsed_time_threshold"] is None


def test_forbidden_future_or_outcome_inputs_fail_closed() -> None:
    row = _level(record_id="L1", value=1.25)
    row["outcome"] = "UP"
    with pytest.raises(RS0SemanticError, match="RS0_FORBIDDEN_IDENTITY_FIELD:outcome"):
        normalize_candidate_source_row(row)


def test_programme_state_preserves_no_winner_unconsumed_old_grun_and_runtime_continuation_only() -> None:
    execution = _read(ROOT / "registries/implementation/c2p_v0_2/C2P2_RS0_EXECUTION_STATE_v0_1.json")
    programme = _read(ROOT / "registries/implementation/c2p_v0_2/C2P2_RS0_STATE_v0_1.json")
    assert execution["packet_id"] == "C2P2-RS0-OBJECTPACK-SEMANTIC-BINDING"
    assert execution["run_authority_consumed"] is False
    assert execution["run_count_remaining"] == 1
    assert execution["fresh_grun_required_before_real_source_launch"] is True
    assert execution["next_packet"] == "C2P2-RS0-EMPIRICAL-RUNTIME-CLOSEOUT"
    assert programme["selection_state"] == "COMPARATIVE_SET_ONLY_NO_WINNER"
    assert programme["authority"]["active_object_pack"] is None
    assert programme["authority"]["validation"] == "LOCKED_UNCONSUMED"
    assert programme["authority"]["successor_candidate_real_source_launch"] == "DENIED_UNTIL_FRESH_GRUN_PASS"
