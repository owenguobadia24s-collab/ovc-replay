from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RECEIPT = ROOT / "docs/programmes/lsiac-v0-1/rrscg-core-wp5/RRSCG_CORE_G5_TERMINAL_MERGE_RECEIPT_v0_1.json"
STATE = ROOT / "records/research_operations/lsiac/LSIAC_PROGRAMME_STATE_v0_31.json"
POINTER = ROOT / "records/research_operations/lsiac/CURRENT_STATE_POINTER.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_terminal_receipt_binds_exact_primary_head_merge_and_assurance():
    receipt = _load(RECEIPT)
    assert receipt["primary_pr"] == 1442
    assert receipt["tested_main_base"] == "242b865e2b0c9789032721634a7dc837f448dd2a"
    assert receipt["final_assurance_head"] == "9f9f6435c59ea82dd8ef5e7d9f2a69fd0440d777"
    assert receipt["squash_merge_commit"] == "a13b4dc64eb7d22f8fec14c524f19d1f3fc3660e"
    assert receipt["assurance"]["tests_workflow"]["canonical_population_count"] == 5550
    assert all(item["result"] == "PASS" for item in receipt["assurance"]["canonical_shards"])
    assert receipt["assurance"]["siq_ready"]["result"] == "PASS"
    assert receipt["assurance"]["merge_readiness"]["result"] == "PASS"
    assert receipt["assurance"]["unresolved_review_threads"] == 0


def test_terminal_state_is_effective_bounded_and_has_no_successor():
    state = _load(STATE)
    pointer = _load(POINTER)
    assert state["status"] == pointer["status"] == "COMPLETED"
    assert state["terminal_state"] == "RRSCG_CORE_COMPLETE_REPOSITORY_EFFECTIVE"
    assert state["merge_commit"] == pointer["primary_merge_commit"]
    assert state["next_packet"] == pointer["next_packet"] == "NONE_RRSCG_CORE_COMPLETE"
    assert state["next_action"] == "PROGRAMME_COMPLETED_NO_NEXT_PACKET"
    assert state["capability_state"] == "INACTIVE"
    assert state["real_source_execution"] == "NOT_AUTHORISED_NOT_PERFORMED"
    assert state["validation"] == "LOCKED_UNCONSUMED"
    assert state["blockers"] == []
    assert state["authority_delta"] == "NONE"


def test_terminal_receipt_preserves_exact_external_source_identity_without_invented_drive_id():
    source = _load(RECEIPT)["external_source_binding"]
    assert source["d10_package_sha256"] == "6b58e9edbb16dd5f8e6f182d0af82c46279a28fc030b4d560bcd69635729515f"
    assert source["d10_release_bundle_sha256"] == "092bf144b38f84a43946d36a15d0905c2bce7f51e7ca815e6814eae361d1ad67"
    assert source["d10_release_binding_sha256"] == "cb2315d01379138c1f62d6b1cacc89d9b1314bf2532602e264b7d223a27bf099"
    assert source["drive_file_id"] == "NOT_EXPOSED_BY_MOUNTED_FILESYSTEM"
