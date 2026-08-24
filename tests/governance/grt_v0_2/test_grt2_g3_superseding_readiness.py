from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET_ROOT = ROOT / "docs/programmes/grt-v0-2/g3/superseding"
STATE_ROOT = ROOT / "registries/implementation/grt_v0_2"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _logical_sha(payload: dict) -> str:
    body = {key: value for key, value in payload.items() if key != "logical_sha256"}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _canonical_sha(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def test_grt2_g3_superseding_readiness_reconciliation_is_exact_and_authority_inert() -> None:
    manifest = _load(PACKET_ROOT / "GRT2_G3_SUPERSEDING_READINESS_AUTHORITY_MANIFEST.json")
    frontier = _load(PACKET_ROOT / "GRT2_G3_SUPERSEDING_READINESS_DEPENDENCY_FRONTIER.json")
    evidence = _load(PACKET_ROOT / "GRT2_G3_SUPERSEDING_READINESS_RECONCILIATION_EVIDENCE.json")
    qa = _load(PACKET_ROOT / "GRT2_G3_SUPERSEDING_READINESS_QA_PACKET.json")
    decision = _load(PACKET_ROOT / "GRT2_G3_SUPERSEDING_READINESS_DELEGATED_DECISION.json")
    receipt = _load(PACKET_ROOT / "GRT2_G3_SUPERSEDING_READINESS_COMPLETION_RECEIPT.json")
    state = _load(STATE_ROOT / "OVC_GRT2_STATE_v0_16_SUPERSEDING_READINESS_RECONCILIATION_COMPLETED.json")
    pointer = _load(STATE_ROOT / "CURRENT_STATE_POINTER.json")
    old_floor = _load(ROOT / "docs/programmes/grt-v0-2/g3/GRT2_G3_PROPOSED_DEBT_FLOOR_GENERATION_0.json")
    constitution = _load(ROOT / "registries/governance/grt_v0_2/GRT_REPOSITORY_CONSTITUTION_v0_2.json")
    authority = _load(ROOT / "registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_1.json")
    pgn = _load(ROOT / "registries/governance/programme_genesis/OVC_PGN_PORTFOLIO_LEDGER_v0_2.json")

    assert _canonical_sha(manifest) == "b8d884e9fa40aafd7db280d1acb35525419d09141295b7b527a44591f1b2b9d2"
    assert _canonical_sha(frontier) == "7ff6eeaa524ad9a49b661ee9fd3582bdd590df9b6397c125db350e1d3e4549b4"
    for packet in (evidence, qa, decision, receipt, state):
        assert packet["logical_sha256"] == _logical_sha(packet)

    assert evidence["logical_sha256"] == "54e58cdfc87f6969930d1cbe1ee13acfc2f2e037091f02aaf39f8ca5ae724551"
    assert qa["logical_sha256"] == "63a110b48978be2dcb166700be7fca90865ea6f5bac9ef08a8369b37d0ba5a7a"
    assert decision["logical_sha256"] == "83037480e7e51f73e17f3856d345dd3ea76588df37247c9f4c0fdc1a64bc71e0"
    assert receipt["logical_sha256"] == "1d533382862b7f68c46926fa76d602088fdd7a9bbab4b4c9e7f6c10758e56428"
    assert state["logical_sha256"] == "365514ffce4bdf8ba209ccfb4f79a08c1b4e60222c6bd6892d253ca67f0f1f5b"

    assert old_floor["floor_hash"] == "f008cbad6bbb891b18f615aa91f9981fbf71ec874972630d8c6eb38ae1642ba9"
    assert len(old_floor["open_grandfathered_findings"]) == 1628
    assert evidence["previous_g3"]["operator_decision"] == "PASS_RECEIVED_UNCONSUMED"
    assert evidence["previous_g3"]["authority_consumed"] == "NONE"

    current = evidence["exact_current_baseline"]
    assert current["commit"] == "4aac7376e60525b0c86b9f4577ce32790b0d98de"
    assert current["tree"] == "f887aa0d709b723aa7b92abbc8a2e6ba0930cdf3"
    assert current["full_tree_component_count"] == 7571
    assert current["evaluation_count"] == 12362
    assert current["finding_count"] == 1638
    assert current["snapshot_hash"] == "907ff285e2a27678893b80670aef67d427f829884ad15d96a74766e30efbb842"
    assert current["not_evaluable_count"] == 0
    assert current["adapter_error_count"] == 0
    assert len(current["rule_family_coverage"]) == 10
    assert set(current["rule_family_coverage"].values()) == {"EVALUATED"}

    b0 = evidence["b0_integrity"]
    assert b0 == {
        "exact": True,
        "lineage_status": "PASS",
        "member_count": 569,
        "membership_sha256": "3587c224c07360751923e5718c5bedb432ce4a5c8cccd4061f73dd53ef07de5d",
        "unresolved_lineage_count": 0,
    }
    observer = evidence["observer_transition"]
    assert observer["current_observer_condition_count"] == 2163
    assert observer["source_classified_condition_count"] == 2163
    assert observer["unresolved_current_condition_count"] == 0
    assert observer["transition_new_debt_count"] == 0
    assert observer["stable_expanded_count"] == 0
    assert observer["stable_material_changed_count"] == 0

    reconciliation = evidence["old_to_current_finding_reconciliation"]
    assert reconciliation["former_count"] == 1628
    assert reconciliation["current_count"] == 1638
    assert reconciliation["unchanged_count"] == 1625
    assert reconciliation["resolved_count"] == 3
    assert reconciliation["added_count"] == 13
    assert reconciliation["net_change"] == 10
    assert reconciliation["extent_dispositions"] == {
        "EXPANDED": 0,
        "MATERIAL_CHANGED": 0,
        "NOT_COMPARABLE": 0,
        "REDUCED": 0,
        "UNCHANGED": 1625,
    }
    assert reconciliation["identity_replacements"] == 1
    assert reconciliation["genuinely_new_actionable_findings_relative_to_former_floor"] == 12
    assert reconciliation["forbidden_new_or_recurrent_debt"] == 0
    assert reconciliation["unlawful_baseline_expansion"] == 0

    floor = evidence["provisional_replacement_floor_on_exact_baseline"]
    assert floor["generation"] == 0
    assert floor["count"] == 1638
    assert floor["floor_hash"] == "3aac9f9128345aa53776f7cbf9e28fe060e5ab27ea143959490f7ebf80ff3cbb"
    assert floor["status"] == "CANDIDATE_ONLY_REQUIRES_POST_INTEGRATION_EXACT_REBUILD"
    assert floor["old_floor_mutated"] is False

    artifact = evidence["external_artifact"]
    assert artifact["workflow_run_id"] == 32774766087
    assert artifact["artifact_id"] == 9537555078
    assert artifact["artifact_digest"] == "sha256:c705efda7d5afe76e40afc3056fa9b54db52e60477fd7f2b6e7cc2a2f487e3a3"
    assert artifact["evidence_logical_sha256"] == "4ee0147f6733dcc7b034b6e72be7d31036438b7e214075ccf978688d54030b1e"

    assert qa["disposition"] == "PASS"
    assert qa["warnings"] == []
    assert qa["unresolved_issues"] == []
    assert decision["decision"] == "PASS"
    assert decision["authority_effect"] == "NONE"
    assert receipt["status"] == "COMPLETED_PENDING_PHYSICAL_MATERIALISATION"

    assert constitution["canonical_hash"] == "cac9fc5f0e31db08c4c37153c92a214fcc482414421f34d74c594faec65a71b0"
    assert constitution["status"] == "PROPOSED_UNADMITTED"
    assert authority["enforcement_mode"] == "LIMITED_NEW_ARTIFACT_ENFORCEMENT"
    assert authority["g3_status"] == "NOT_AUTHORISED"
    assert pgn["authority"]["native_genesis_adoption"] == "DENIED_PENDING_PGN_G3"

    assert state["status"] == "READY"
    assert state["g3_status"] == "SUPERSEDING_READINESS_RECONCILIATION_COMPLETED_NOT_AUTHORISED"
    assert state["operator_decision_required"] is False
    assert state["next_packet"] == "GRT2-G3-SUPERSEDING-GATE-READY"
    assert pointer["current_state"].endswith("OVC_GRT2_STATE_v0_16_SUPERSEDING_READINESS_RECONCILIATION_COMPLETED.json")
    assert pointer["status"] == "READY"
    assert pointer["next_packet"] == "GRT2-G3-SUPERSEDING-GATE-READY"
    assert pointer["operator_decision_required"] is False
