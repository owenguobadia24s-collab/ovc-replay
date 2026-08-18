from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP0 = ROOT / "docs/releases/development-skills-v0-3/cers-conformance/cers-wp0"


def _load(path: str | Path):
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    return json.loads(p.read_text(encoding="utf-8"))


def _canonical_id(value: dict) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_cers_wp0_freezes_current_control_plane_without_authority_expansion():
    freeze = _load(WP0 / "CERS_WP0_SOURCE_AUTHORITY_FREEZE_v0_1.json")
    assert freeze["packet_id"] == "CERS-WP0"
    assert freeze["status"] == "FROZEN_FOR_WP0_QUALIFICATION"
    assert freeze["observed_main"]["commit"] == "17c2aac536893005fc07f4ec1717d04b6b2f9177"
    assert freeze["observed_main"]["tree"] == "5643bf72e0ca54169737474a5ce5437d3c651709"
    by_id = {row["id"]: row for row in freeze["current_control_bindings"]}
    assert by_id["DEFAULT_EXECUTION_SUBSTRATE"]["status"] == "ACTIVE"
    assert by_id["DEFAULT_EXECUTION_SUBSTRATE"]["controller"] == "DSAI_VIT_PHYSICAL_CONTROLLER"
    assert by_id["DEFAULT_EXECUTION_SUBSTRATE"]["physical_gateway"] == "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY"
    assert by_id["DEFAULT_EXECUTION_SUBSTRATE"]["parallel_physical_merge"] is False
    assert by_id["DSAI3V_ASYNC_ASSURANCE_LIVE_AUTHORITY_v0_1"]["authority_status"] == "ACTIVE"
    assert by_id["DSAI3V_VIT_CURRENT_STATE"]["vit_live_physical_main_control"] == "ACTIVE_GENERAL_ALREADY_AUTHORISED_AUTO_EXECUTABLE_POPULATION"
    assert by_id["GRT_V0_2_CURRENT_STATE"]["status"] == "QA_REVIEW"
    assert by_id["GRT_V0_2_CURRENT_STATE"]["active_enforcement"] == "LIMITED_NEW_ARTIFACT_ENFORCEMENT"
    assert by_id["GRT_V0_2_CURRENT_STATE"]["g3_status"] == "NOT_AUTHORISED_READINESS_EVIDENCE_INCOMPLETE"
    assert by_id["PRVITR_TERMINAL_STATE"]["live_authoritative_path"] == "PRVITR_CORRECTED_LIVE_ADMISSION"
    assert by_id["VIT_PLACEMENT_PREDECESSOR_RESOLUTION"]["lower_pr_number_fifo"] is False
    assert by_id["VIT_PLACEMENT_PREDECESSOR_RESOLUTION"]["policy"] == "EXACT_VIT_PLACEMENT_TRAIN_PREDECESSOR"
    assert by_id["VIT_COMPLETION_POLICY"]["administrative_closeout_packet"] == "REJECT_NEW_PERMANENT_PACKET"
    assert by_id["VIT_COMPLETION_POLICY"]["post_merge_fact_route"] == "PHYSICAL_MATERIALISATION_RECEIPT_PACKET_COMPLETION_RECEIPT"
    assert by_id["PRVITR_LIVE_ADMISSION"]["single_physical_writer"] is True
    assert freeze["live_dispatch"]["status"] == "DENIED_PENDING_CERS-G-LIVE-DISPATCH"
    assert freeze["live_dispatch"]["worker_capability_binding"] == "NONE_ADMITTED_FOR_LIVE_CERS_DISPATCH"
    assert freeze["live_dispatch"]["new_writer_identity"] == "NONE_GRANTED"
    assert freeze["live_dispatch"]["agent_write_authority"] == "NONE"


def test_cers_wp0_registered_root_census_is_exact_and_fail_closed():
    census = _load(WP0 / "CERS_WP0_PROGRAMME_ROOT_CENSUS_v0_1.json")
    policy = census["discovery_policy"]
    assert policy["mode"] == "REGISTERED_EXACT_ROOTS_ONLY"
    assert policy["branch_heuristics"] is False
    assert policy["pr_title_or_body_heuristics"] is False
    assert policy["workflow_name_heuristics"] is False
    assert policy["chat_state_discovery"] is False
    assert policy["historical_fallback_for_current_state"] is False
    assert policy["unknown_or_unregistered_root"] == "NON_DISPATCHABLE_DENY"
    root_ids = {row["root_id"] for row in census["registered_roots"]}
    assert root_ids == {"CERS", "DSAI3V_VIT", "DSAI3V_ASYNC_ASSURANCE", "DSAI2_ORCH345", "GRT_V0_2", "PRVITR"}
    assert census["dispatch_eligibility"]["registered_root_is_sufficient"] is False
    assert census["dispatch_eligibility"]["unknown_root"] == "DENY"


def test_cers_wp0_sources_preserve_existing_controller_gateway_and_frozen_denial():
    freeze = _load(WP0 / "CERS_WP0_SOURCE_AUTHORITY_FREEZE_v0_1.json")
    default = _load("registries/authority/DEFAULT_EXECUTION_SUBSTRATE.json")
    async_live = _load("registries/authority/DSAI3V_ASYNC_ASSURANCE_LIVE_AUTHORITY_v0_1.json")
    exclusivity = _load("registries/development/skills/VIT_PHYSICAL_MAIN_EXCLUSIVITY_v0_1.json")
    wp0_state = _load("registries/implementation/dsai3v_cers_v0_1/OVC_DSAI3V_CERS_STATE_v0_4.json")
    assert default["status"] == "ACTIVE"
    assert default["controller"] == "DSAI_VIT_PHYSICAL_CONTROLLER"
    assert default["execution_policy"]["physical_gateway"] == "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY"
    assert default["execution_policy"]["parallel_physical_merge"] is False
    assert async_live["authority_status"] == "ACTIVE"
    assert async_live["provider_write_or_merge"] is False
    assert async_live["new_writer_identity"] == "NONE"
    assert async_live["parallel_physical_merge"] is False
    assert exclusivity["exclusive_writer_identity"] == "DSAI_VIT_PHYSICAL_CONTROLLER"
    assert exclusivity["physical_gateway"] == "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY"
    assert exclusivity["parallel_physical_merge"] is False
    assert wp0_state["live_unattended_dispatch"] == "DENIED_PENDING_CERS-G-LIVE-DISPATCH"
    assert freeze["conclusion"] == "WP0_IMPLEMENTATION_AUTHORITY_CURRENT_LIVE_DISPATCH_REMAINS_DENIED"


def test_cers_wp0_programme_state_does_not_claim_runtime_or_live_dispatch():
    state = _load("registries/implementation/dsai3v_cers_v0_1/OVC_DSAI3V_CERS_STATE_v0_4.json")
    assert state["packet_id"] == "CERS-WP0"
    assert state["status"] == "QA_REVIEW"
    assert state["authority_delta"] == "NONE"
    assert state["runtime_authority"] == "NOT_IMPLEMENTED"
    assert state["new_writer_identity"] == "NONE_GRANTED"
    assert state["worker_binding"] == "NONE_ADMITTED_FOR_LIVE_CERS_DISPATCH"
    assert state["live_unattended_dispatch"] == "DENIED_PENDING_CERS-G-LIVE-DISPATCH"
    assert state["parallel_physical_merge"] is False
    gate = next(row for row in state["packet_register"] if row["packet_id"] == "CERS-G-LIVE-DISPATCH")
    assert gate["authority_required"] == "OPERATOR_REQUIRED"


def test_cers_wp0_authority_manifest_and_dependency_frontier_are_exact():
    authority = _load(WP0 / "CERS_WP0_AUTHORITY_MANIFEST_v0_1.json")
    frontier = _load(WP0 / "CERS_WP0_DEPENDENCY_FRONTIER_v0_1.json")
    packet = _load(WP0 / "CERS_WP0_IMPLEMENTATION_PACKET_v0_1.json")
    assert _canonical_id(authority) == packet["authority_manifest_id"] == "7318a8673c96822145c659d45dd7bebe3678e2fe7989d02ef01f41d27446cd10"
    assert _canonical_id(frontier) == packet["dependency_frontier_id"] == "fda0e3bfc91b5ba58c75950c75a201c486512c15a06d618f1c8ca0ca636d96c2"
    assert authority["authority_class"] == "AUTO_EXECUTABLE"
    assert authority["authority_delta"] == "NONE"
    assert "CERS_UNATTENDED_WRITE_CAPABLE_DISPATCH" in authority["denied"]
    assert frontier["observations"]["grt_is_cers_wp0_prerequisite"] is False
    assert frontier["observations"]["vit_predecessor_resolution"] == "PLACEMENT_TRAIN_PREDECESSOR_NOT_PR_NUMBER_FIFO"
    assert frontier["observations"]["administrative_closeout_route"] == "PHYSICAL_MATERIALISATION_RECEIPT_PACKET_COMPLETION_RECEIPT"
    assert frontier["blockers"] == []
