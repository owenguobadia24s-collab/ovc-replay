from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"
GATE_READY_STATE = ROOT / "records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_24_WP8_G3_PROVENANCE_GATE_READY.json"
POINTER = ROOT / "registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json"

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

def test_gate_preparation_remains_immutable_and_current_state_advances_only_by_operator_pass() -> None:
    authority = _json(WP8 / "ASOCSI_WP8_G3_UNRECOVERABLE_PROVENANCE_AUTHORITY_v0_1.json")
    qa = _json(WP8 / "ASOCSI_WP8_G3_UNRECOVERABLE_PROVENANCE_QA_v0_1.json")
    gate_ready = _json(GATE_READY_STATE)
    pointer = _json(POINTER)
    current = _json(ROOT / pointer["current_state"])
    non_grants = set(authority["non_grants"])

    assert authority["authority_delta"] == "NONE"
    assert {"SUPERSEDE_EXACT_MANIFEST_REPRODUCTION_REQUIREMENT","START_STAGE1_REVEAL","SEMANTIC_REMEDIATION","REPLACE_OR_REWRITE_FROZEN_G3"}.issubset(non_grants)
    assert qa["qa_recommendation"] == "PASS_TO_OPERATOR_GATE"

    # Historical gate preparation never self-granted the reserved decision.
    assert gate_ready["status"] == "GATE_READY"
    assert gate_ready["authority_required"] == "OPERATOR_REQUIRED"
    assert gate_ready["preserved"]["stage1_reveal_started"] is False
    assert gate_ready["next_packet"] == "ASOCSI-G6-PROVENANCE-SUPERSESSION-OPERATOR-DECISION"

    if pointer["current_state"] == str(GATE_READY_STATE.relative_to(ROOT)).replace("\\", "/"):
        assert pointer["status"] == "GATE_READY"
        assert pointer["next_packet"] == "ASOCSI-G6-PROVENANCE-SUPERSESSION-OPERATOR-DECISION"
    else:
        decision = _json(WP8 / "ASOCSI_G6_PROVENANCE_SUPERSESSION_OPERATOR_DECISION_v0_1.json")
        assert current["status"] == "APPROVED"
        assert current["authority_required"] == "SATISFIED_OPERATOR_PASS"
        assert current["gate_id"] == "ASOCSI-G6-PROVENANCE-SUPERSESSION"
        assert current["stage1_reveal_started"] is False
        assert current["human_adjudication_started"] is False
        assert current["preserved"]["unrecoverable_provenance_warning"] is True
        assert decision["decision"] == "PASS" and decision["authority"] == "OPERATOR"
        assert pointer["next_packet"] == "ASOCSI-WP8-STAGE1-HUMAN-FIDELITY-ADJUDICATION"
