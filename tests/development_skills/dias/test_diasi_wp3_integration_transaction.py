from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import pytest

from ovc.development.skills.dias import DiasContractError
from ovc.development.identity import canonical_sha256
from ovc.development.skills.dias_transaction import (
    EventCursor,
    IntegrationTransaction,
    IntegrationTriggerCoverageManifest,
    OwnerFactReference,
    OwnerFactReferenceManifest,
    RouteFence,
    TransactionStateCoverage,
    reconstruct_transaction,
)


SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
TOKEN = "d" * 64


def coverage() -> IntegrationTriggerCoverageManifest:
    states = []
    for state in ("READY", "ADMITTED", "APPLYING", "WRITE_UNKNOWN", "MATERIALISED", "RECEIPTS_PENDING"):
        states.append(TransactionStateCoverage(state, False, (f"TRIGGER:{state}",), f"RECONCILE:{state}", 300, "DEAD_LETTER"))
    for state in ("COMPLETED", "DEAD_LETTER", "QUARANTINED"):
        states.append(TransactionStateCoverage(state, True, (), None, None, None))
    return IntegrationTriggerCoverageManifest(tuple(states))


def transaction(*, budget: int = 2) -> IntegrationTransaction:
    manifest = OwnerFactReferenceManifest(
        transaction_key=SHA_A,
        facts=(OwnerFactReference("DSAI_VIT", "current_state", SHA_B, "registries/state.json", "e" * 40),),
    )
    return IntegrationTransaction(
        programme_id="OVC-DIAS-CONFORMANCE-v0.1",
        packet_id="DIASI-WP3-SLICE",
        pip_id=SHA_A,
        owner_fact_manifest_id=manifest.manifest_id,
        trigger_coverage_manifest_id=coverage().manifest_id,
        route_fence=RouteFence("DSAI_VIT_PHYSICAL_CONTROLLER", 7, TOKEN),
        state="READY",
        event_cursor=EventCursor("stream"),
        idempotence_key=SHA_C,
        recovery_budget=budget,
    )


def apply(tx: IntegrationTransaction, event_id: str, event_type: str, *, generation: int = 7, writer: str = "DSAI_VIT_PHYSICAL_CONTROLLER") -> IntegrationTransaction:
    return tx.apply_event(event_id=event_id, event_type=event_type, writer_id=writer, generation=generation, fence_token=TOKEN)


def test_every_nonterminal_state_has_trigger_reconciliation_age_and_dead_letter() -> None:
    manifest = coverage()
    for item in manifest.states:
        if not item.terminal:
            assert item.durable_triggers
            assert item.reconciliation_route
            assert item.maximum_age_seconds and item.maximum_age_seconds > 0
            assert item.dead_letter_disposition == "DEAD_LETTER"
    assert len(manifest.manifest_id) == 64


def test_missing_nonterminal_coverage_is_rejected() -> None:
    with pytest.raises(DiasContractError):
        TransactionStateCoverage("READY", False, (), None, None, None)


def test_happy_path_is_deterministic_and_idempotent() -> None:
    tx = transaction()
    sequence = [
        ("1", "ADMIT", "ADMITTED"),
        ("2", "START_APPLY", "APPLYING"),
        ("3", "WRITE_CONFIRMED", "MATERIALISED"),
        ("4", "START_RECEIPTS", "RECEIPTS_PENDING"),
        ("5", "RECEIPTS_CONFIRMED", "COMPLETED"),
    ]
    for event_id, event_type, expected in sequence:
        tx = apply(tx, event_id, event_type)
        assert tx.state == expected
        assert apply(tx, event_id, event_type) is tx
    assert tx.event_cursor.sequence == 5


def test_write_unknown_reconstructs_without_runtime_memory() -> None:
    tx = apply(apply(transaction(), "1", "ADMIT"), "2", "START_APPLY")
    tx = apply(tx, "3", "WRITE_OUTCOME_UNKNOWN")
    assert tx.state == "WRITE_UNKNOWN"
    decoded = json.loads(json.dumps(asdict(tx), sort_keys=True))
    rebuilt = reconstruct_transaction(decoded)
    assert rebuilt == tx
    recovered = apply(rebuilt, "4", "RECONSTRUCT_WRITE")
    assert recovered.state == "MATERIALISED"


@pytest.mark.parametrize("writer,generation", [("STALE_WRITER", 7), ("DSAI_VIT_PHYSICAL_CONTROLLER", 6), ("DSAI_VIT_PHYSICAL_CONTROLLER", 8)])
def test_stale_or_unknown_writer_is_quarantined(writer: str, generation: int) -> None:
    tx = apply(transaction(), "attack", "ADMIT", writer=writer, generation=generation)
    assert tx.state == "QUARANTINED"


def test_invalid_transitions_use_bounded_recovery_then_dead_letter() -> None:
    tx = transaction(budget=1)
    tx = apply(tx, "x1", "WRITE_CONFIRMED")
    assert tx.state == "READY"
    assert len(tx.recovery_history) == 1
    tx = apply(tx, "x2", "WRITE_CONFIRMED")
    assert tx.state == "DEAD_LETTER"
    assert len(tx.recovery_history) == 1


def test_owner_fact_reference_manifest_is_exact_and_conflict_free() -> None:
    fact = OwnerFactReference("DSAI_VIT", "current_state", SHA_B, "registries/state.json", "e" * 40)
    manifest = OwnerFactReferenceManifest(SHA_A, (fact,))
    assert len(manifest.manifest_id) == 64
    with pytest.raises(DiasContractError):
        OwnerFactReferenceManifest(SHA_A, (fact, fact))


def test_transaction_identity_excludes_transient_state_but_state_identity_does_not() -> None:
    initial = transaction()
    admitted = apply(initial, "1", "ADMIT")
    assert initial.transaction_key == admitted.transaction_key
    assert initial.state_id != admitted.state_id


def test_reconstruction_fails_closed_on_missing_durable_field() -> None:
    payload = asdict(transaction())
    del payload["route_fence"]
    with pytest.raises(DiasContractError):
        reconstruct_transaction(payload)


def test_wp3_court_record_binds_vit_and_zero_runtime_dependencies() -> None:
    root = Path(__file__).resolve().parents[3]
    wp3 = root / "docs/programmes/dias-v0-1/wp3"
    authority = json.loads((wp3 / "DIASI_WP3_VIT_AUTHORITY_MANIFEST.json").read_text(encoding="utf-8"))
    frontier = json.loads((wp3 / "DIASI_WP3_VIT_DEPENDENCY_FRONTIER.json").read_text(encoding="utf-8"))
    packet = json.loads((wp3 / "DIASI_WP3_IMPLEMENTATION_PACKET.json").read_text(encoding="utf-8"))
    assert canonical_sha256(authority["payload"]) == authority["logical_id"]
    assert canonical_sha256(frontier["payload"]) == frontier["logical_id"]
    assert packet["runtime_state_dependencies"] == []
    pointer = json.loads((root / "registries/implementation/dias_v0_1/CURRENT_STATE_POINTER.json").read_text(encoding="utf-8"))
    state = json.loads((root / pointer["current_state"]).read_text(encoding="utf-8"))
    assert state["next_packet"] == "DIASI-WP4A"
    assert state["live_cutover"] is False
