from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.rccr.closeout import (
    RCCRCloseoutError,
    build_rebuild_restart_receipt,
    reconcile_source_frontier,
    validate_terminal_authority,
)

ROOT = Path(__file__).resolve().parents[3]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def source_inputs():
    return (
        load("docs/releases/rccr-v0-1/rccri-wp6b/RCCRI_WP6B_SOURCE_ADMISSION_MANIFEST.json"),
        load("docs/releases/rccr-v0-1/rccri-wp6b/RCCRBootstrapManifest.BROAD_WAVE_1.json"),
        load("registries/implementation/rccr_v0_1/CURRENT_STATE_POINTER.json"),
    )


def test_wp7b_merge_receipt_proves_exact_tree_materialisation():
    receipt = load("docs/releases/rccr-v0-1/rccri-wp7b/RCCRI_WP7B_MERGE_RECEIPT.json")
    assert receipt["decision"] == "PASS"
    assert receipt["squash_merge_commit"] == "f8711a2fa0d643c87abb45a0985bf526c0f9915a"
    assert receipt["qualified_result_tree"] == receipt["physical_post_merge_tree"] == "7b367c4a9a900cf8ec75154d03bf0e99f7868624"
    assert receipt["authority_delta"] == "NONE"
    assert receipt["next_packet"] == "RCCRI-WP8"


def test_wp8_merge_receipt_proves_terminal_physical_materialisation():
    receipt = load("docs/releases/rccr-v0-1/rccri-wp8/RCCRI_WP8_MERGE_RECEIPT.json")
    assert receipt["decision"] == "PASS"
    assert receipt["candidate_head"] == "78518c97f6fbb8dbbae7b229e03ee8d767e40544"
    assert receipt["squash_merge_commit"] == "43c053822e4a3cd0e7c04fc4a0760879ef84290a"
    assert receipt["qualified_result_tree"] == receipt["physical_post_merge_tree"] == "6ef70fb8095c3a8074587b5900e791ae98043db9"
    assert receipt["tree_equivalence"] == "PASS"
    assert receipt["authority_delta"] == "NONE"
    assert receipt["terminal_state"] == "RCCR_V0_1_IMPLEMENTED_NON_AUTHORITATIVE_SYNTHESIS"
    assert receipt["next_packet"] is None
    assert receipt["next_operator_gate"] is None


def test_source_frontier_reconciliation_is_exact_allowlist_and_authority_preserving():
    admission, wave, pointer = source_inputs()
    rebuilt = reconcile_source_frontier(admission_manifest=admission, bootstrap_wave=wave, current_pointer=pointer)
    recorded = load("docs/releases/rccr-v0-1/rccri-wp8/RCCRI_WP8_SOURCE_FRONTIER_RECONCILIATION.json")
    assert recorded["status"] == "PASS"
    assert recorded["admission_mode"] == "EXACT_ID_ALLOWLIST_ONLY"
    assert recorded["admitted_source_count"] == len(rebuilt["admitted_source_ids"]) == 6
    assert recorded["excluded_source_count"] == len(rebuilt["excluded_source_ids"]) == 6
    assert recorded["admitted_source_ids"] == rebuilt["admitted_source_ids"]
    assert recorded["excluded_source_ids"] == rebuilt["excluded_source_ids"]
    assert recorded["arbitrary_repository_scan"] is False
    assert recorded["owner_authority_frontier"] == rebuilt["owner_authority_frontier"]
    assert recorded["rccr_consumption_boundary"] == rebuilt["rccr_consumption_boundary"]
    assert recorded["authority_effect"] == rebuilt["authority_effect"] == "NONE"


def test_rebuild_restart_receipt_is_order_invariant_and_fail_closed():
    pilot = load("records/research_operations/rccr/v0_1/RCCRBootstrapManifest/rccr__RCCRBootstrapManifest__f64578daa0a45984c7b5677831a5e2a09a452fa4ac1664f9d71fe10d930acbf0.json")
    capability = load("docs/releases/rccr-v0-1/rccri-wp7a/CapabilityWithoutDemandReadModel.json")
    posture = load("docs/releases/rccr-v0-1/rccri-wp7a/PortfolioPostureSummary.json")
    admission, wave, pointer = source_inputs()
    reconciliation = reconcile_source_frontier(admission_manifest=admission, bootstrap_wave=wave, current_pointer=pointer)
    durable = [pilot, {"record_type": "SOURCE_ADMISSION", "source_ids": reconciliation["admitted_source_ids"], "authority_effect": "NONE"}]
    a = build_rebuild_restart_receipt(durable_records=durable, read_models=[capability, posture], source_reconciliation=reconciliation)
    b = build_rebuild_restart_receipt(durable_records=list(reversed(durable)), read_models=[posture, capability], source_reconciliation=reconciliation)
    assert a == b
    assert a["restart_semantics"] == "CLEAN_REBUILD_FROM_DURABLE_INPUTS"
    assert a["write_routes"] == "DENIED"
    assert a["authority_effect"] == "NONE"
    with pytest.raises(RCCRCloseoutError):
        build_rebuild_restart_receipt(durable_records=[{"authority_effect": "GRANTED"}], read_models=[capability], source_reconciliation=reconciliation)


def test_terminal_authority_validation_preserves_owner_and_validation_denials():
    pointer = load("registries/implementation/rccr_v0_1/CURRENT_STATE_POINTER.json")
    validate_terminal_authority(pointer)
    assert pointer["status"] == "COMPLETED"
    assert pointer["current_state"] == "RCCR_V0_1_STATE_v0_17.json"
    assert pointer["current_packet"] == "RCCRI-WP8"
    assert pointer["current_gate"] == "RCCRI-G8"
    assert pointer["gate_status"] == "PASS_DELEGATED_COMPLETED"
    assert pointer["last_completed_packet"] == "RCCRI-WP8"
    assert pointer["last_merge_commit"] == "43c053822e4a3cd0e7c04fc4a0760879ef84290a"
    assert pointer["owner_authority_frontier"]["validation"]["state"] == "LOCKED_UNCONSUMED"
    assert pointer["rccr_consumption_boundary"]["owner_capability_activation"] == "DENIED"
    assert pointer["rccr_consumption_boundary"]["validation_consumption"] == "DENIED"
    assert pointer["next_packet"] is None
    assert pointer["next_operator_gate"] is None
    assert pointer["authority_effect"] == "NONE"


def test_v0_2_backlog_is_non_ranked_non_promoting_and_source_bound():
    backlog = load("docs/releases/rccr-v0-1/rccri-wp8/RCCR_V0_2_CANDIDATE_BACKLOG.json")
    assert backlog["ranking"] == "NONE"
    assert backlog["promotion_authority"] == "NONE"
    assert len(backlog["candidates"]) == 5
    assert all(item["status"] == "FUTURE_CANDIDATE_ONLY" for item in backlog["candidates"])
    assert all(item["authority_effect"] == "NONE" for item in backlog["candidates"])
    assert backlog["authority_effect"] == "NONE"


def test_wp8_authority_and_dependency_manifests_bind_terminal_non_authority():
    authority = load("docs/releases/rccr-v0-1/rccri-wp8/RCCRI_WP8_AUTHORITY_MANIFEST.json")
    dependency = load("docs/releases/rccr-v0-1/rccri-wp8/RCCRI_WP8_DEPENDENCY_FRONTIER.json")
    assert authority["manifest_id"] == "e61804e79484c9e0230edc544c3a2da137c86a8e3bd7e09cac1342bdcd5bf6ff"
    assert authority["hash_basis"]["authority_delta"] == "NONE"
    assert authority["hash_basis"]["terminal_target"] == "RCCR_V0_1_IMPLEMENTED_NON_AUTHORITATIVE_SYNTHESIS"
    assert dependency["frontier_id"] == "63cabbf80ac93e1d062e6e046cc08579d282bacfe69d570ac84fef51049b947a"
    assert dependency["hash_basis"]["next_packet"] is None
    assert dependency["hash_basis"]["terminal_state"] == "RCCR_V0_1_IMPLEMENTED_NON_AUTHORITATIVE_SYNTHESIS"
