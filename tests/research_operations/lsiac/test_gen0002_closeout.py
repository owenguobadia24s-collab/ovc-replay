from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ovc.research_operations.lsiac.gen0002 import audit_frozen_passport_subject_identity

ROOT = Path(__file__).resolve().parents[3]
GEN = ROOT / "docs" / "programmes" / "lsiac-v0-1" / "gen0002"
STATE = ROOT / "records" / "research_operations" / "lsiac" / "LSIAC_PROGRAMME_STATE_v0_9.json"
PROTOCOL = ROOT / "docs" / "programmes" / "lsiac-v0-1" / "adjudication" / "LSIAC_ACCESSION_ADJUDICATION_PROTOCOL_v0_1.json"
HISTORICAL_FRONTIER = ROOT / "docs" / "programmes" / "lsiac-v0-1" / "frontier-freeze" / "LSIAC_ACCESSION_FRONTIER_FREEZE_RECEIPT_v0_1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def test_gen0002_closeout_identities_reproduce_from_exact_accounting() -> None:
    observed = audit_frozen_passport_subject_identity(ROOT)
    audit = _load(GEN / "LSIAC_GEN0002_EXACT_SUBJECT_ACCOUNTING_AUDIT_v0_1.json")
    universe = _load(GEN / "LSIAC_GEN0002_SUCCESSOR_SOURCE_UNIVERSE_IDENTITY_v0_1.json")
    protocol = _load(GEN / "LSIAC_GEN0002_UNCHANGED_PROTOCOL_SEMANTICS_BINDING_RECEIPT_v0_1.json")
    frontier = _load(GEN / "LSIAC_GEN0002_SUCCESSOR_FRONTIER_FREEZE_RECEIPT_v0_1.json")

    assert audit["audit_receipt_id"] == _canonical_sha256(audit["identity_payload"])
    assert universe["source_universe_id"] == _canonical_sha256(universe["identity_payload"])
    assert protocol["protocol_binding_id"] == _canonical_sha256(protocol["identity_payload"])
    assert frontier["frontier_receipt_id"] == _canonical_sha256(frontier["identity_payload"])

    assert audit["observed"]["passport_count"] == observed["passport_count"] == 434
    assert audit["observed"]["subject_count"] == observed["subject_count"] == 431
    assert audit["observed"]["singleton_subject_count"] == observed["singleton_subject_count"] == 428
    assert audit["observed"]["multi_passport_subject_count"] == observed["multi_passport_subject_count"] == 3
    assert audit["observed"]["co_reference_groups"] == observed["co_reference_groups"]
    assert universe["identity_payload"]["co_reference_groups"] == observed["co_reference_groups"]
    assert universe["identity_payload"]["frozen_source_passport_set_sha256"] == observed["frozen_source_passport_set_sha256"]
    assert frontier["source_universe_id"] == universe["source_universe_id"]
    assert frontier["protocol_binding_id"] == protocol["protocol_binding_id"]


def test_gen0002_protocol_and_history_are_preserved_forward_only() -> None:
    protocol = _load(GEN / "LSIAC_GEN0002_UNCHANGED_PROTOCOL_SEMANTICS_BINDING_RECEIPT_v0_1.json")
    frontier = _load(GEN / "LSIAC_GEN0002_SUCCESSOR_FRONTIER_FREEZE_RECEIPT_v0_1.json")
    historical = _load(HISTORICAL_FRONTIER)

    assert _git_blob_sha(PROTOCOL) == "e0541a48ed2206224203485038a7ebcaba3607fc"
    assert protocol["protocol_git_blob_sha"] == "e0541a48ed2206224203485038a7ebcaba3607fc"
    assert protocol["semantics_changed"] is False
    assert protocol["bytes_changed"] is False
    assert historical["frontier_receipt_id"] == "54d20c358fe110198c0a33b20132a13244c63e8e89448e3a0fde1ef79fb18996"
    assert frontier["supersedes_frontier_receipt_id"] == historical["frontier_receipt_id"]
    assert frontier["supersession_semantics"] == "FORWARD_ONLY_PRESERVE_GEN0001_HISTORY"


def test_gen0002_gate_is_zero_delta_and_pass1_only_successor() -> None:
    qa = _load(GEN / "LSIAC_GEN0002_ACCOUNTING_REPAIR_QA_v0_1.json")
    gate = _load(GEN / "LSIAC_GEN0002_ACCOUNTING_REPAIR_GATE_PACKET_v0_1.json")
    decision = _load(GEN / "LSIAC_GEN0002_ACCOUNTING_REPAIR_DECISION_v0_1.json")
    state = _load(STATE)

    assert qa["verdict"] == "PASS"
    assert qa["recommendation"] == "PASS"
    assert qa["auto_ratifiable"] is True
    assert qa["blockers"] == []
    assert gate["gate_class"] == "AUTO_RATIFIABLE_NON_RESERVED"
    assert gate["recommended_decision"] == "PASS"
    assert decision["decision"] == "PASS"
    assert decision["decision_class"] == "DELEGATED_AUTO_RATIFICATION_NON_RESERVED"
    assert decision["authority_delta"] == "NONE_ACCOUNTING_REPAIR_ONLY"
    assert state["status"] == "APPROVED"
    assert state["blockers"] == []
    assert state["scientific_accession_decisions"] == 0
    assert state["pass2"] == "DENIED"
    assert state["next_packet"] == "LSIAC-GEN0002-PASS1-SOURCE-STANDING-EXPOSURE-DEPENDENCE"
    assert state["next_operator_gate"] == "LSIAC-SCIENCE-RESUME"
