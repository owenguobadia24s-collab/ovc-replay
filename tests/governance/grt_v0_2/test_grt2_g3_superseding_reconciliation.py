from __future__ import annotations

import json
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.debt import B0_MEMBER_COUNT, B0_MEMBERSHIP_SHA256, validate_debt_floor
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256
from ovc.development.skills.vit_core import DependencyFrontier, IntegrationAuthorityManifest

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs/programmes/grt-v0-2/g3/superseding"

def load(name: str) -> dict:
    return json.loads((BASE / name).read_text(encoding="utf-8"))

def assert_hash(record: dict) -> None:
    payload = dict(record); actual = payload.pop("logical_sha256"); assert actual == canonical_sha256(payload)

def test_superseding_reconciliation_is_exact_and_authority_inert() -> None:
    evidence = load("GRT2_G3_SUPERSEDING_READINESS_RECONCILIATION_EVIDENCE.json")
    qa = load("GRT2_G3_SUPERSEDING_READINESS_RECONCILIATION_QA_PACKET.json")
    packet = load("GRT2_G3_SUPERSEDING_READINESS_RECONCILIATION_PACKET.json")
    for record in (evidence, qa, packet): assert_hash(record)
    assert evidence["current_protected_main"] == {"commit": "a22b6171d5acf8d06145e6e26516d78b06c55406", "tree": "f1f137a20c170a265eae222ae0dffd757eafee88"}
    assert evidence["historical_decision_preservation"]["previous_operator_pass_status"] == "RECEIVED_UNCONSUMED_EXACT_APPROVED_FLOOR_STALE"
    assert evidence["b0_integrity"]["exact"] is True
    assert evidence["b0_integrity"]["member_count"] == B0_MEMBER_COUNT
    assert evidence["b0_integrity"]["membership_sha256"] == B0_MEMBERSHIP_SHA256
    assert evidence["current_census"]["finding_count"] == 1640
    assert evidence["current_census"]["not_evaluable"] == []
    assert evidence["current_census"]["adapter_errors"] == []
    assert all(evidence["readiness_conditions"].values())
    rec = evidence["old_to_current_reconciliation"]
    assert rec["classification"]["forbidden_new_or_recurrent_debt"] == 0
    assert rec["classification"]["unlawfully_expanded_baseline_debt"] == 0
    assert qa["qa_disposition"] == "PASS" and qa["unresolved_issues"] == []
    assert packet["authority_delta"] == "NONE" and packet["next_packet"] == "GRT2-G3-SUPERSEDING-GATE-READY-MATERIALISATION"

def test_candidate_floor_seed_is_new_valid_and_inactive() -> None:
    floor = load("GRT2_G3_SUPERSEDING_CANDIDATE_DEBT_FLOOR_GENERATION_0_SEED.json")
    validate_debt_floor(floor)
    assert floor["floor_hash"] == "0ffcef46d02f7cb5929531076824d4966ad5216a3a6ae2af0d4f3c6239d820db"
    assert len(floor["open_grandfathered_findings"]) == 1640
    evidence = load("GRT2_G3_SUPERSEDING_READINESS_RECONCILIATION_EVIDENCE.json")
    assert evidence["candidate_floor_seed"]["status"] == "INACTIVE_CANDIDATE_SEED_FOR_FINAL_GATE_READY_REVALIDATION"
    assert evidence["historical_decision_preservation"]["former_floor"]["floor_hash"] == "f008cbad6bbb891b18f615aa91f9981fbf71ec874972630d8c6eb38ae1642ba9"

def test_superseding_reconciliation_bindings_are_exact_and_reserved() -> None:
    a = load("GRT2_G3_SUPERSEDING_READINESS_AUTHORITY_MANIFEST.json")
    f = load("GRT2_G3_SUPERSEDING_READINESS_DEPENDENCY_FRONTIER.json")
    authority = IntegrationAuthorityManifest(**{**a["authority_manifest"], "authority_sources": tuple(a["authority_manifest"]["authority_sources"]), "reserved_boundaries": tuple(a["authority_manifest"]["reserved_boundaries"])})
    frontier = DependencyFrontier(**{**f["dependency_frontier"], "dependencies": tuple(f["dependency_frontier"]["dependencies"]), "owner_bindings": tuple(f["dependency_frontier"]["owner_bindings"])})
    assert authority.logical_id == a["authority_manifest_id"]
    assert frontier.logical_id == f["dependency_frontier_id"]
    assert authority.authority_delta == "NONE_SUPERSEDING_READINESS_RECONCILIATION_ONLY"
    assert "GRT2-G3_OPERATOR_DECISION" in authority.reserved_boundaries
    assert "PGN_NATIVE_ADOPTION" in authority.reserved_boundaries
