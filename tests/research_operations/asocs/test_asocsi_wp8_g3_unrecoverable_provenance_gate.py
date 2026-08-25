from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"

def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def test_unrecoverable_provenance_gate_preserves_frozen_scientific_record() -> None:
    evidence = _json(WP8 / "ASOCSI_WP8_G3_UNRECOVERABLE_PROVENANCE_EVIDENCE_v0_1.json")
    gate = _json(WP8 / "ASOCSI_G6_PROVENANCE_SUPERSESSION_GATE_PACKET_v0_1.json")
    assert evidence["meaning_bearing_change"] is False
    assert evidence["residual_provenance"]["classification"] == "PROPOSED_UNRECOVERABLE_PROVENANCE"
    assert evidence["residual_provenance"]["preserved_frozen_receipts"]["census_sha256"] == "c49f34e7af19f0110d24377a54ab8f0bd3fb183e83e924de07bf39cd586de2c7"
    assert evidence["residual_provenance"]["preserved_frozen_receipts"]["compact_manifest_sha256"] == "b8b4caeca0c9e234339c07053bac6c65040d0cb14c9abfca08590526e5b4a3da"
    assert evidence["exact_reproduction"]["observation_trace_sha256"] == "22c856efdd24083d5339d2082ad9714597e326a6f40655bfb82b0afa9899f7dc"
    assert evidence["exact_reproduction"]["ordered_trace_ids_sha256"] == "bcd571f567068035592bb0d868747cfe85e8aaa01155b1fa8c798f488f6ef0d7"
    assert len(evidence["exact_reproduction"]["checkpoints"]) == 4
    assert gate["recommended_decision"] == "PASS"
    assert gate["proposed_delta"]["class"] == "OPERATOR_REQUIRED_ACCEPTANCE_CONDITION_SUPERSESSION"

def test_gate_preparation_does_not_self_grant_reveal_or_semantic_authority() -> None:
    authority = _json(WP8 / "ASOCSI_WP8_G3_UNRECOVERABLE_PROVENANCE_AUTHORITY_v0_1.json")
    qa = _json(WP8 / "ASOCSI_WP8_G3_UNRECOVERABLE_PROVENANCE_QA_v0_1.json")
    pointer = _json(ROOT / "registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json")
    state = _json(ROOT / pointer["current_state"])
    non_grants = set(authority["non_grants"])
    assert authority["authority_delta"] == "NONE"
    assert {"SUPERSEDE_EXACT_MANIFEST_REPRODUCTION_REQUIREMENT","START_STAGE1_REVEAL","SEMANTIC_REMEDIATION","REPLACE_OR_REWRITE_FROZEN_G3"}.issubset(non_grants)
    assert qa["qa_recommendation"] == "PASS_TO_OPERATOR_GATE"
    assert state["status"] == "GATE_READY"
    assert state["authority_required"] == "OPERATOR_REQUIRED"
    assert state["preserved"]["stage1_reveal_started"] is False
    assert pointer["next_packet"] == "ASOCSI-G6-PROVENANCE-SUPERSESSION-OPERATOR-DECISION"
