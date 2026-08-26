from __future__ import annotations

import json
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256

ROOT = Path(__file__).resolve().parents[3]
G3 = ROOT / "docs/programmes/grt-v0-2/g3"
AUTH = ROOT / "registries/authority"
IMPL = ROOT / "registries/implementation/grt_v0_2"
GOV = ROOT / "registries/governance/grt_v0_2"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def assert_hashed(record):
    payload = dict(record)
    observed = payload.pop("logical_sha256")
    assert observed == canonical_sha256(payload)


def test_operator_rollback_decision_is_exact_and_source_bound():
    decision = load(G3 / "GRT2_G3_ROLLBACK_OPERATOR_DECISION.json")
    assert_hashed(decision)
    assert decision["decision"] == "PASS"
    assert decision["operator_instruction"] == "OVC APPROVE GRT2-G3 ROLLBACK TO LIMITED_NEW_ARTIFACT_ENFORCEMENT"
    assert decision["approved_authority_delta"]["enforcement"]["transition"] == "FULL_GRT_EXACT_TO_LIMITED_NEW_ARTIFACT_ENFORCEMENT"
    assert decision["approved_authority_delta"]["debt_floor"]["preserve_generations"] == [0, 1, 2]


def test_current_authority_requires_limited_enforcement_and_no_floor_advancement():
    authority = load(AUTH / "GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_3.json")
    assert_hashed(authority)
    assert authority["enforcement_mode"] == "LIMITED_NEW_ARTIFACT_ENFORCEMENT"
    assert authority["full_grt_exact_required"] is False
    assert authority["ordinary_packet_debt_floor_generation_required"] is False
    assert authority["debt_floor_current_pointer_status"] == "HISTORICAL_NON_ENFORCING_DO_NOT_ADVANCE"
    assert authority["g3_status"] == "ROLLED_BACK_TO_G2_5_LIMITED_ENFORCEMENT"


def test_debtfloor_g0_g1_g2_and_pointer_remain_historical_bytes():
    expected = {
        0: "2c2152397e1ac5ace98b3363ca39c84f5d5a5dadbc6243e73cbd1fba15413c8b",
        1: "4fdfaf281720232dbb0fd6c9496b2849d26f1e7107d559bba0e6efc51fe02d27",
        2: "cc79b13935e91775165d10903126cb7909a0ec78eeb6ddd7d6692e36a7e8bedb",
    }
    for generation, floor_hash in expected.items():
        floor = load(GOV / f"debt_floors/GRT_DEBT_FLOOR_G{generation}.json")
        assert floor["generation"] == generation
        assert floor["floor_hash"] == floor_hash
    pointer = load(GOV / "GRT_DEBT_FLOOR_CURRENT.json")
    assert pointer["generation"] == 2
    assert pointer["floor_hash"] == expected[2]
    assert pointer["definition"].endswith("GRT_DEBT_FLOOR_G2.json")


def test_current_programme_state_and_pointer_expose_completed_resume_without_wp5_start():
    state = load(IMPL / "OVC_GRT2_STATE_v0_20_G3_ROLLBACK_COMPLETED.json")
    assert_hashed(state)
    pointer = load(IMPL / "CURRENT_STATE_POINTER.json")
    assert pointer["current_state"].endswith("OVC_GRT2_STATE_v0_20_G3_ROLLBACK_COMPLETED.json")
    assert pointer["status"] == "COMPLETED"
    assert pointer["operator_decision_required"] is False
    assert state["status"] == "COMPLETED"
    assert state["active_enforcement"] == "LIMITED_NEW_ARTIFACT_ENFORCEMENT"
    assert state["ordinary_packet_debt_floor_generation_required"] is False
    assert state["wp5_status"] == "NOT_STARTED"
    assert "RESUME_ORDINARY_DEVELOPMENT_UNDER_LIMITED_ENFORCEMENT" in state["next_action"]


def test_permanent_integration_lane_retains_siq_but_not_full_grt_exact():
    workflow = (ROOT / ".github/workflows/ovc-tiered-tests.yml").read_text(encoding="utf-8")
    assert "group: ovc-main-integration-lane-v1" in workflow
    assert "Run mandatory SIQ/PDC exact-final assurance inside lease" in workflow
    assert "timeout-minutes: 10" in workflow
    assert "Run required GRT-EXACT against the exact late-bound integration tree" not in workflow
    assert "Run lightweight GRT integration readiness" not in workflow
    assert "grt_exact_proof_id" not in workflow


def test_floor_preparation_is_compatibility_no_write_only():
    script = (ROOT / "scripts/governance/grt_v0_2/prepare_next_debt_floor.py").read_text(encoding="utf-8")
    assert "DISABLED_BY_GRT2_G3_ROLLBACK" in script
    assert '"floor_mutation_required": False' in script
    assert '"ordinary_packet_debt_floor_generation_required": False' in script
    assert "floor_path.write_text" not in script
    assert "POINTER.write_text" not in script


def test_limited_candidate_runtime_is_bound_to_current_rollback_authority():
    script = (ROOT / "scripts/governance/grt_v0_2/reconcile_g2_5_pilot.py").read_text(encoding="utf-8")
    assert "GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_3.json" in script
    assert "ROLLED_BACK_TO_G2_5_LIMITED_ENFORCEMENT" in script
    assert "ordinary_packet_debt_floor_generation_required" in script


def test_qa_has_no_warning_or_unresolved_issue():
    qa = load(G3 / "GRT2_G3_ROLLBACK_QA_PACKET.json")
    assert_hashed(qa)
    assert qa["recommendation"] == "PASS"
    assert qa["warnings"] == []
    assert qa["unresolved_issues"] == []
