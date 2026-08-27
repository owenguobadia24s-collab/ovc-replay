from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from ovc.development.identity import canonical_sha256
from ovc.development.skills.dias import DiasContractError
from ovc.development.skills.dias_materialisation import (
    LivenessFunctionBinding,
    MaterialisationAdmissionEnvelope,
    OwnerLocalLivenessReplacementManifest,
    PreMaterialisationAnchor,
    QualificationLedgerAuthorityTransferCandidate,
    RepositoryProtectionManifest,
    build_receipts,
    reconstruct_receipts,
    validate_admission,
)
from ovc.development.skills.dias_transaction import RouteFence


SHA64_A = "a" * 64
SHA64_B = "b" * 64
SHA64_C = "c" * 64
COMMIT = "1" * 40
TREE = "2" * 40
RESULT = "3" * 40
TOKEN = "4" * 64


def protection(**changes: object) -> RepositoryProtectionManifest:
    value = RepositoryProtectionManifest(COMMIT, TREE, 20229411, "2026-08-24T12:46:03.557+01:00", "OVC merge readiness", "squash", (), "DSAI_VIT_PHYSICAL_CONTROLLER", "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY", False)
    return replace(value, **changes)


def envelope(p: RepositoryProtectionManifest) -> MaterialisationAdmissionEnvelope:
    return MaterialisationAdmissionEnvelope(SHA64_A, SHA64_B, p.manifest_id, COMMIT, TREE, RESULT, RouteFence("DSAI_VIT_PHYSICAL_CONTROLLER", 9, TOKEN), SHA64_C)


def anchor(env: MaterialisationAdmissionEnvelope) -> PreMaterialisationAnchor:
    return PreMaterialisationAnchor(env.envelope_id, env.transaction_key, COMMIT, TREE, RESULT, "DSAI_VIT_PHYSICAL_CONTROLLER", 9, SHA64_C)


def test_admission_revalidates_protection_fence_and_a3() -> None:
    current = protection()
    env = envelope(current)
    assessment = validate_admission(env, current=current, expected_protection_id=current.manifest_id, writer_id="DSAI_VIT_PHYSICAL_CONTROLLER", writer_generation=9, fence_token=TOKEN, prospective_tree=RESULT)
    assert assessment.accepted is True
    assert assessment.a3_exact is True
    assert assessment.physical_write_authorised is False


@pytest.mark.parametrize(
    "mutation,reason",
    [
        ({"ruleset_updated_at": "drift"}, "REPOSITORY_PROTECTION_DRIFT"),
        ({"observed_main": "5" * 40}, "PHYSICAL_MAIN_MOVED"),
    ],
)
def test_protection_or_main_drift_blocks(mutation: dict[str, object], reason: str) -> None:
    original = protection()
    current = protection(**mutation)
    observed = validate_admission(envelope(original), current=current, expected_protection_id=original.manifest_id, writer_id="DSAI_VIT_PHYSICAL_CONTROLLER", writer_generation=9, fence_token=TOKEN, prospective_tree=RESULT)
    assert observed.accepted is False
    assert reason in observed.reasons


def test_stale_writer_split_brain_and_a3_mismatch_block() -> None:
    p = protection()
    env = envelope(p)
    stale = validate_admission(env, current=p, expected_protection_id=p.manifest_id, writer_id="OLD_WRITER", writer_generation=8, fence_token=TOKEN, prospective_tree="6" * 40)
    assert stale.accepted is False
    assert set(stale.reasons) == {"STALE_OR_UNKNOWN_WRITER", "A3_MISMATCH"}


def test_shadow_cannot_be_promoted_to_live_by_constructor() -> None:
    p = protection()
    with pytest.raises(DiasContractError):
        replace(envelope(p), shadow_only=False, live_authority=True)


def test_crash_after_merge_and_lost_receipt_store_reconstruct_exact_receipts() -> None:
    env = envelope(protection())
    pre = anchor(env)
    first = build_receipts(anchor=pre, pip_id=SHA64_A, observed_commit="7" * 40, observed_tree=RESULT, next_packet="DIASI-WP5")
    rebuilt = reconstruct_receipts(anchor=pre, pip_id=SHA64_A, observed_commit="7" * 40, observed_tree=RESULT, next_packet="DIASI-WP5", receipt_store_available=False)
    assert first == rebuilt[:2]
    assert rebuilt[2].receipt_store_available is False
    assert rebuilt[2].deterministic is True


def test_successor_release_is_deterministic_and_duplicate_safe() -> None:
    pre = anchor(envelope(protection()))
    first = build_receipts(anchor=pre, pip_id=SHA64_A, observed_commit="7" * 40, observed_tree=RESULT, next_packet="DIASI-WP5")[1]
    second = build_receipts(anchor=pre, pip_id=SHA64_A, observed_commit="7" * 40, observed_tree=RESULT, next_packet="DIASI-WP5")[1]
    assert first.receipt_id == second.receipt_id
    assert first.successor_release_key == second.successor_release_key


def liveness() -> OwnerLocalLivenessReplacementManifest:
    rows = [
        ("PROGRAMME_DISCOVERY_AND_ADMISSION", "CERS", "DSAI_VIT_OWNER_LOCAL"),
        ("PERSISTENT_SWEEP_HEARTBEAT_LEASE_RECLAIM", "CERS", "DSAI_VIT_OWNER_LOCAL"),
        ("PACKET_START_AND_SUCCESSOR_DISPATCH", "CERS", "DSAI_VIT_OWNER_LOCAL"),
        ("DETACHED_QUALIFICATION_LEDGER_ENVELOPE_WRITE", "PES", "VIT_QUALIFICATION_OWNER_LOCAL"),
        ("EXACT_HEAD_POINTER_PUBLICATION", "PES", "VIT_QUALIFICATION_OWNER_LOCAL"),
        ("CONTENT_ADDRESSED_IDEMPOTENT_REPLAY", "PES", "VIT_QUALIFICATION_OWNER_LOCAL"),
    ]
    return OwnerLocalLivenessReplacementManifest(tuple(LivenessFunctionBinding(function, incumbent, owner, f"TRIGGER:{function}", f"RECONCILE:{function}") for function, incumbent, owner in rows))


def test_all_cers_pes_liveness_functions_have_inactive_owner_local_replacements() -> None:
    manifest = liveness()
    assert len(manifest.bindings) == 6
    assert manifest.generic_supervisor is False
    assert manifest.active is False
    assert len(manifest.manifest_id) == 64


def test_partial_liveness_coverage_and_generic_supervisor_are_rejected() -> None:
    full = liveness()
    with pytest.raises(DiasContractError):
        OwnerLocalLivenessReplacementManifest(full.bindings[:-1])
    with pytest.raises(DiasContractError):
        replace(full, generic_supervisor=True)


def test_qualification_ledger_transfer_remains_shadow_candidate() -> None:
    candidate = QualificationLedgerAuthorityTransferCandidate("ovc/vit-qualification-ledger-v1", ".ovc/vit-qualifications", "PES", "VIT_QUALIFICATION_OWNER_LOCAL", ("ENVELOPE_WRITE", "EXACT_HEAD_POINTER", "IDEMPOTENT_REPLAY"))
    assert candidate.live_transfer is False
    with pytest.raises(DiasContractError):
        replace(candidate, live_transfer=True)


def test_wp4a_court_record_binds_vit_and_advances_only_to_wp4b() -> None:
    root = Path(__file__).resolve().parents[3]
    wp4a = root / "docs/programmes/dias-v0-1/wp4a"
    authority = json.loads((wp4a / "DIASI_WP4A_VIT_AUTHORITY_MANIFEST.json").read_text(encoding="utf-8"))
    frontier = json.loads((wp4a / "DIASI_WP4A_VIT_DEPENDENCY_FRONTIER.json").read_text(encoding="utf-8"))
    replacements = json.loads((wp4a / "DIASI_WP4A_OWNER_LOCAL_LIVENESS_REPLACEMENT_MANIFEST.json").read_text(encoding="utf-8"))
    assert canonical_sha256(authority["payload"]) == authority["logical_id"]
    assert canonical_sha256(frontier["payload"]) == frontier["logical_id"]
    assert len(replacements["bindings"]) == 6
    assert replacements["generic_supervisor"] is False
    assert all(binding["active"] is False for binding in replacements["bindings"])
    pointer = json.loads((root / "registries/implementation/dias_v0_1/CURRENT_STATE_POINTER.json").read_text(encoding="utf-8"))
    state = json.loads((root / pointer["current_state"]).read_text(encoding="utf-8"))
    assert state["next_packet"] == "DIASI-WP4B"
    assert state["live_cutover"] is False
