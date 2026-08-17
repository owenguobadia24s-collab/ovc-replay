from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_materialisation import ReceiptStore

COMPLETION_STATE_SCHEMA = "ovc-vit-physical-completion-state/v1"
SUCCESSOR_RELEASE_SCHEMA = "ovc-vit-successor-release/v1"
PACKET_BINDING_SCHEMA = "ovc-vit-packet-completion-binding/v1"


def _write_immutable(path: Path, payload: Mapping[str, Any]) -> None:
    encoded = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != encoded:
            raise VitContractError("VIT_LEDGER_INTEGRITY_FAIL")
        return
    path.write_text(encoded, encoding="utf-8")


def _load_record(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VitContractError("VIT_COMPLETION_RECEIPT_UNREADABLE") from exc
    if not isinstance(value, Mapping):
        raise VitContractError("VIT_COMPLETION_RECEIPT_INVALID")
    return value


def persist_non_churning_completion_closeout(
    *,
    receipt_store: ReceiptStore,
    proof: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Materialise effective packet completion outside Git after exact physical proof.

    The four canonical completion receipts remain the normative evidence bundle. This
    function adds an external, append-only effective-state projection and at most one
    successor-release signal. It deliberately performs no repository write and creates
    no PR. Repeating the same completion is idempotent; a second physical transaction
    attempting to complete the same programme/packet fails closed.
    """
    if proof.get("exact_tree_equal") is not True:
        raise VitContractError("POST_WRITE_TREE_MISMATCH")
    if proof.get("four_content_addressed_receipts_present") is not True:
        raise VitContractError("VIT_COMPLETION_BUNDLE_INCOMPLETE")

    transaction_id = str(proof.get("transaction_id", "")).strip()
    receipt_ids = proof.get("receipt_ids")
    if not transaction_id or not isinstance(receipt_ids, Mapping):
        raise VitContractError("VIT_COMPLETION_PROOF_INVALID")
    completion_receipt_id = str(receipt_ids.get("completion_receipt_id", "")).strip()
    materialisation_receipt_id = str(receipt_ids.get("materialisation_receipt_id", "")).strip()
    if not completion_receipt_id or not materialisation_receipt_id:
        raise VitContractError("VIT_COMPLETION_PROOF_INVALID")

    completion_path = receipt_store.root / f"{completion_receipt_id}.json"
    completion = _load_record(completion_path)
    programme_id = str(completion.get("programme_id", "")).strip()
    packet_id = str(completion.get("packet_id", "")).strip()
    next_packet_raw = completion.get("next_packet")
    next_packet = str(next_packet_raw).strip() if next_packet_raw is not None else None
    if not programme_id or not packet_id:
        raise VitContractError("VIT_COMPLETION_RECEIPT_INVALID")
    if str(completion.get("materialisation_receipt_id", "")) != materialisation_receipt_id:
        raise VitContractError("VIT_COMPLETION_PROOF_RECEIPT_MISMATCH")

    state_logical = {
        "schema": COMPLETION_STATE_SCHEMA,
        "transaction_id": transaction_id,
        "programme_id": programme_id,
        "packet_id": packet_id,
        "completion_receipt_id": completion_receipt_id,
        "materialisation_receipt_id": materialisation_receipt_id,
        "status": "COMPLETED",
        "next_packet": next_packet,
        "physical_tree_verified": True,
        "canonical_git_state_mutated": False,
        "ordinary_closeout_pr_required": False,
        "authority_effect": "NONE",
    }
    completion_state_id = canonical_sha256(
        state_logical, role="DSAI3V_EFFECTIVE_PACKET_COMPLETION_STATE"
    )
    state_record = {**state_logical, "completion_state_id": completion_state_id}

    state_path = receipt_store.root / "completion-state" / f"{completion_state_id}.json"
    _write_immutable(state_path, state_record)

    packet_key = canonical_sha256(
        {"programme_id": programme_id, "packet_id": packet_id},
        role="DSAI3V_PACKET_COMPLETION_KEY",
    )
    packet_binding = {
        "schema": PACKET_BINDING_SCHEMA,
        "programme_id": programme_id,
        "packet_id": packet_id,
        "packet_key": packet_key,
        "transaction_id": transaction_id,
        "completion_state_id": completion_state_id,
        "completion_receipt_id": completion_receipt_id,
        "authority_effect": "NONE",
    }
    binding_path = receipt_store.root / "completion-state" / "by-packet" / f"{packet_key}.json"
    if binding_path.exists():
        existing = _load_record(binding_path)
        if dict(existing) != packet_binding:
            raise VitContractError("VIT_DUPLICATE_EFFECTIVE_PACKET_COMPLETION")
    else:
        _write_immutable(binding_path, packet_binding)

    successor_release_id: str | None = None
    successor_release_status = "PROGRAMME_TERMINAL"
    if next_packet:
        release_logical = {
            "schema": SUCCESSOR_RELEASE_SCHEMA,
            "programme_id": programme_id,
            "completed_packet_id": packet_id,
            "next_packet": next_packet,
            "completion_state_id": completion_state_id,
            "completion_receipt_id": completion_receipt_id,
            "status": "RELEASED_TO_AUTHORITY_RESOLVER",
            "execution_started": False,
            "authority_inferred": False,
            "ordinary_closeout_pr_required": False,
            "authority_effect": "NONE",
        }
        successor_release_id = canonical_sha256(
            release_logical, role="DSAI3V_SUCCESSOR_RELEASE"
        )
        release_record = {**release_logical, "successor_release_id": successor_release_id}
        release_path = receipt_store.root / "successor-releases" / f"{successor_release_id}.json"
        _write_immutable(release_path, release_record)
        successor_release_status = "RELEASED_TO_AUTHORITY_RESOLVER"

    return {
        "completion_state_id": completion_state_id,
        "status": "COMPLETED",
        "programme_id": programme_id,
        "packet_id": packet_id,
        "next_packet": next_packet,
        "successor_release_id": successor_release_id,
        "successor_release_status": successor_release_status,
        "ordinary_closeout_pr_required": False,
        "canonical_git_state_mutated": False,
        "authority_effect": "NONE",
    }
