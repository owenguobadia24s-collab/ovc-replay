from __future__ import annotations

import json
from pathlib import Path

from ovc.opt_b.c2p_v0_2 import rs0_source_materialisation as source
from ovc.opt_b.c2p_v0_2.rs0_execution import iter_verified_rows, validate_locator
from ovc.opt_b.c2_vnext import real_source_materialisation as c2rm
from ovc.opt_b.c2e_v2.models import build_record
from ovc.opt_b.c2e_v2.projection import project_episode

ROOT = Path(__file__).resolve().parents[4]


def test_operator_pass_is_narrow_and_materialisation_remains_frozen_after_successor_block() -> None:
    decision = json.loads((ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_SOURCE_MATERIALISATION_OPERATOR_DECISION_v0_1.json").read_text())
    closeout = json.loads((ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_CURRENT_SOURCE_MATERIALISATION_CLOSEOUT_v0_1.json").read_text())
    state = json.loads((ROOT / "registries/implementation/c2p_v0_2/C2P2_RS0_EXECUTION_STATE_v0_1.json").read_text())
    assert decision["decision"] == "PASS"
    assert decision["approved_delta"]["authority_class"] == "BOUNDED_READ_ONLY_CURRENT_SOURCE_MATERIALISATION"
    assert decision["approved_delta"]["output"] == "INACTIVE_NONCANONICAL_READ_ONLY_RS0_SOURCE"
    assert any("Legacy OPT-B.C2" in row for row in decision["conditions"])

    assert closeout["packet_id"] == "C2P2-RS0-CURRENT-SOURCE-MATERIALISATION"
    assert closeout["status"] == "COMPLETED"
    assert closeout["next_packet"] == "C2P2-RS0-EXECUTION"
    assert closeout["workflow"]["run_id"] == 32010902424
    assert closeout["materialisation"]["logical_sha256"] == "f7e772ca550fe9b1fb69c45ceca6e55f48da3b9cc02d88bb7b8dd1b74dd6766b"

    assert state["packet_id"] == "C2P2-RS0-EXECUTION"
    assert state["status"] == "BLOCKED"
    assert state["current_source_materialisation"]["workflow_run_id"] == 32010902424
    assert state["current_source_materialisation"]["logical_sha256"] == closeout["materialisation"]["logical_sha256"]
    assert state["run_authority_consumed"] is False
    assert state["run_count_remaining"] == 1
    assert state["f0_a"] == "HOLD_UNCHANGED"
    assert state["validation"] == "LOCKED_UNCONSUMED"


def test_scoped_current_c2_binding_restores_historical_june_defaults() -> None:
    keys = ("CONTEXT_START", "CONTEXT_END", "TARGET_START", "TARGET_END", "PARTITION_ID", "C1_RELEASE_ID", "MATERIALISATION_ID")
    before = {key: getattr(c2rm, key) for key in keys}
    with source._c2_scope():
        assert c2rm.CONTEXT_START == source.TARGET_START
        assert c2rm.CONTEXT_END == source.TARGET_END
        assert c2rm.C1_RELEASE_ID == source.C1_RELEASE_ID
        assert c2rm.MATERIALISATION_ID == source.MATERIALISATION_ID
        assert c2rm.PARTITION_ID == source.MATERIALISATION_ID
    assert {key: getattr(c2rm, key) for key in keys} == before


def test_projection_is_rs0_adapter_valid_and_preserves_c2_c2e_roles(tmp_path: Path) -> None:
    side_data = {
        "relations": [{"object_id": "L1", "topology": "ABOVE"}, {"object_id": "C1", "topology": "INSIDE"}],
        "bundles": [{"first_valid_time": "2021-01-01T00:15:00Z", "level_ids": ["L1"], "container_ids": ["C1"]}],
        "levels": [{"level_id": "L1", "first_valid_time": "2021-01-01T00:15:00Z", "level_type": "RANGE_HIGH", "horizon_id": "H4", "value": 1.25, "origin": "TEST", "structural_depth": None}],
        "containers": [{"container_id": "C1", "first_valid_time": "2021-01-01T00:15:00Z", "kind": "TRAILING_RANGE", "horizon_id": "H4", "lower_value": 1.2, "upper_value": 1.3, "centre": 1.25, "width": 0.1, "origin": "TEST", "structural_depth": None}],
        "complete2h": [{"observation_id": "P1", "first_valid_time": "2021-01-01T02:00:00Z", "interval_start": "2021-01-01T00:00:00Z", "interval_end": "2021-01-01T02:00:00Z", "open": 1.2, "high": 1.3, "low": 1.1, "close": 1.25}],
    }
    c2_path = tmp_path / "c2.jsonl"
    c2_info = source._write_rows(c2_path, source._c2_source_rows(side_data, "BID"))
    c2_info["role"] = "C2_VNEXT"
    assert c2_info["row_count"] == 3

    c2e_path = tmp_path / "c2e.jsonl"
    c2e_row = {
        "schema": source.ROW_SCHEMA,
        "source_role": "C2E_V0_2",
        "instrument": "GBPUSD",
        "side": "BID",
        "clock": "15M",
        "first_valid_time": "2021-01-01T00:15:00Z",
        "evaluation_cutoff": "2021-01-01T00:15:00Z",
        "source_record_id": "E1",
        "structural_role_id": "EPISODE",
        "geometry_kind_id": "TEMPORAL",
        "geometry_signature": {"episode_id": "EP1"},
        "relation_topology": [],
    }
    c2e_info = source._write_rows(c2e_path, [c2e_row])
    c2e_info["role"] = "C2E_V0_2"

    locator = {
        "schema": source.LOCATOR_SCHEMA,
        "instrument": "GBPUSD",
        "sides": ["BID", "ASK"],
        "clocks": ["15M", "2H_A_L"],
        "interval": source.INTERVAL,
        "sources": [c2_info, c2e_info],
    }
    verified = validate_locator(locator, tmp_path)
    assert {row.role for row in verified} == {"C2_VNEXT", "C2E_V0_2"}
    for item in verified:
        rows = list(iter_verified_rows(tmp_path / item.relative_path, expected_role=item.role))
        assert len(rows) == item.row_count
        assert all("validation" not in row and "outcome" not in row for row in rows)


def test_capacity_and_identity_bindings_are_exact() -> None:
    assert source.PEAK_MEMORY_LIMIT_BYTES == 1_160_593_408
    assert source.EXTERNAL_STORAGE_LIMIT_BYTES == 6_411_935_744
    assert source.C2_PACKAGE_SHA256 == "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3"
    assert source.C2E_BOUNDARY_PACK_SHA256 == "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"
    assert source.OPT_A_MANIFEST_SHA256 == "0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c"


def test_dedicated_materialisation_workflow_is_non_pr_and_branch_bounded() -> None:
    text = (ROOT / ".github/workflows/c2p2-rs0-current-source-materialisation.yml").read_text(encoding="utf-8")
    assert "pull_request:" not in text
    assert "push:" in text
    assert "build/c2p2-rs0-current-source-materialisation-20260817" in text


def test_streaming_episode_projection_matches_reference_projection() -> None:
    projected_rows: list[dict] = []
    stream = source._StreamingSemanticStream(side="BID", write_source_row=projected_rows.append)
    genesis = build_record("episode_genesis", {
        "boundary_pack_id": source.C2E_BOUNDARY_PACK_ID,
        "source_release_id": source.MATERIALISATION_ID,
        "instrument_id": "GBPUSD",
        "side": "BID",
        "scope_id": "LOCAL_15M",
        "scale_id": "15M",
        "birth_frame_id": "FRAME.1",
        "birth_boundary_rule_id": "RULE.BIRTH",
        "birth_effective_time": "2021-01-01T00:15:00Z",
        "first_valid_time": "2021-01-01T00:15:00Z",
        "authority": "INACTIVE_NONCANONICAL_SHADOW",
    })
    episode_id = genesis["episode_id"]
    birth_event = build_record("boundary_event", {
        "episode_ids": [episode_id], "candidate_ids": ["CAND.1"], "lifecycle_action": "BIRTH", "priority_class": 8,
        "compatibility_disposition": "ORDERED_BY_PRIORITY", "effective_time": "2021-01-01T00:15:00Z",
        "confirmation_time": "2021-01-01T00:15:00Z", "first_valid_time": "2021-01-01T00:15:00Z",
        "collision_disposition": "NONE", "reason_codes": [], "authority": "INACTIVE_NONCANONICAL_SHADOW",
    })
    membership = build_record("membership_delta", {
        "episode_id": episode_id, "frame_id": "FRAME.1", "operation": "ADD", "boundary_event_id": birth_event["boundary_event_id"],
        "effective_time": "2021-01-01T00:15:00Z", "first_valid_time": "2021-01-01T00:15:00Z",
        "authority": "INACTIVE_NONCANONICAL_SHADOW",
    })
    phase = build_record("phase_segment", {
        "episode_id": episode_id, "phase_type": "STRUCTURAL_SIGNATURE_INTERVAL", "start_time": "2021-01-01T00:15:00Z",
        "end_time": "2021-01-01T00:30:00Z", "first_valid_time": "2021-01-01T00:30:00Z", "source_record_ids": ["R1"],
        "authority": "INACTIVE_NONCANONICAL_SHADOW",
    })
    censor = build_record("boundary_event", {
        "episode_ids": [episode_id], "candidate_ids": ["CAND.2"], "lifecycle_action": "CENSOR_RELEASE_END", "priority_class": 2,
        "compatibility_disposition": "ORDERED_BY_PRIORITY", "effective_time": "2021-01-01T00:30:00Z",
        "confirmation_time": "2021-01-01T00:30:00Z", "first_valid_time": "2021-01-01T00:30:00Z",
        "collision_disposition": "NONE", "reason_codes": ["C2E_RELEASE_END_CENSORED"], "authority": "INACTIVE_NONCANONICAL_SHADOW",
    })
    records = [genesis, birth_event, membership, phase, censor]
    for record in records:
        stream.append(record)
    expected = project_episode(episode_id, records, as_of_time="2021-01-01T00:30:00Z", first_valid_time="2021-01-01T00:30:00Z")
    actual = stream.snapshot_record(episode_id, as_of_time="2021-01-01T00:30:00Z", first_valid_time="2021-01-01T00:30:00Z")
    assert actual == expected
    stream.append(actual)
    assert stream.membership_count == 1
    assert stream.record_count == 6
    assert len(projected_rows) == 6
