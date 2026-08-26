from __future__ import annotations
import json
from pathlib import Path
from ovc.programme_genesis.grt_v0_2.debt import validate_debt_floor
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256

ROOT = Path(__file__).resolve().parents[3]
G3 = ROOT / "docs/programmes/grt-v0-2/g3"
GOV = ROOT / "registries/governance/grt_v0_2"


def load(path):
    return json.loads(path.read_text())


def check(record):
    payload = dict(record)
    observed = payload.pop("logical_sha256")
    assert observed == canonical_sha256(payload)


def test_terminal_supersession_operator_pass_remains_immutable_history():
    decision = load(G3 / "GRT2_G3_OPERATOR_DECISION.json")
    check(decision)
    assert decision["operator_instruction"] == "OVC APPROVE GRT2-G3 TERMINAL SUPERSESSION PASS"
    assert decision["approved_terminal_decision_identity"] == "401b6ab70f3f6ee977766176f12336c7ba1c3f263375e64012d4cec9124b8f49"
    assert decision["approved_authority_delta"]["debt_floor"]["floor_hash"] == "2c2152397e1ac5ace98b3363ca39c84f5d5a5dadbc6243e73cbd1fba15413c8b"


def test_generation_zero_floor_remains_exact_historical_approved_object():
    decision = load(G3 / "GRT2_G3_TERMINAL_SUPERSESSION_DECISION.json")
    proposed = dict(decision["proposed_replacement_generation_0_floor"])
    proposed.pop("member_count")
    proposed.pop("status")
    active = load(GOV / "debt_floors/GRT_DEBT_FLOOR_G0.json")
    assert active == proposed
    validate_debt_floor(active)
    assert len(active["open_grandfathered_findings"]) == 1648
    assert active["floor_hash"] == "2c2152397e1ac5ace98b3363ca39c84f5d5a5dadbc6243e73cbd1fba15413c8b"


def test_historical_full_exact_authority_is_preserved_but_superseded_by_rollback():
    historical = load(ROOT / "registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_2.json")
    check(historical)
    assert historical["enforcement_mode"] == "FULL_GRT_EXACT"
    assert historical["constitution_status"] == "ACTIVE"
    assert historical["no_new_hygiene_debt_required"] is True
    current = load(ROOT / "registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_3.json")
    check(current)
    assert current["supersedes_authority"].endswith("GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_2.json")
    assert current["enforcement_mode"] == "LIMITED_NEW_ARTIFACT_ENFORCEMENT"
    assert current["full_grt_exact_required"] is False
    assert current["ordinary_packet_debt_floor_generation_required"] is False


def test_activation_state_and_g4_history_remain_preserved():
    state = load(ROOT / "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_17_SUPERSEDING_ACTIVATION.json")
    check(state)
    assert state["next_packet"] == "GRT2-WP4" and state["next_gate"] == "GRT2-G4"
    assert state["current_projection_status"] == "PRE_G3_POINTER_INTENTIONALLY_PRESERVED_AS_INHERITED_STALE_STATE_FOR_WP4_WAVE_A"
    rollback = load(ROOT / "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_19_G3_ROLLBACK_LIMITED_ENFORCEMENT.json")
    check(rollback)
    assert rollback["g4_status"] == "HISTORICAL_COMPLETED"
    assert rollback["wp5_status"] == "NOT_STARTED"


def test_historical_revalidation_remains_but_current_serialized_lane_no_longer_requires_grt_exact():
    revalidation = load(G3 / "GRT2_G3_ACTIVATION_REVALIDATION.json")
    check(revalidation)
    assert revalidation["approved_floor_member_count"] == 1648
    assert revalidation["approved_missing_from_current_count"] == 0
    assert revalidation["current_not_in_approved_count"] == 0
    assert revalidation["b0_exact"] is True
    assert revalidation["unresolved_lineage_count"] == 0
    workflow = (ROOT / ".github/workflows/ovc-tiered-tests.yml").read_text()
    assert "group: ovc-main-integration-lane-v1" in workflow
    assert "Run mandatory SIQ/PDC exact-final assurance inside lease" in workflow
    assert "Run required GRT-EXACT against the exact late-bound integration tree" not in workflow
    assert "Run lightweight GRT integration readiness" not in workflow
