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


def persist_non_churning_completion_closeout(*, receipt_store: ReceiptStore, proof: Mapping[str, Any]) -> Mapping[str, Any]:
    """Persist effective completion externally; never create a Git closeout mutation."""
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
    completion = _load_record(receipt_store.root / f"{completion_receipt_id}.json")
    programme_id = str(completion.get("programme_id", "")).strip()
    packet_id = str(completion.get("packet_id", "")).strip()
    next_raw = completion.get("next_packet")
    next_packet = str(next_raw).strip() if next_raw is not None else None
    if not programme_id or not packet_id:
        raise VitContractError("VIT_COMPLETION_RECEIPT_INVALID")
    if str(completion.get("materialisation_receipt_id", "")) != materialisation_receipt_id:
        raise VitContractError("VIT_COMPLETION_PROOF_RECEIPT_MISMATCH")

    logical = {"schema": COMPLETION_STATE_SCHEMA, "transaction_id": transaction_id, "programme_id": programme_id, "packet_id": packet_id, "completion_receipt_id": completion_receipt_id, "materialisation_receipt_id": materialisation_receipt_id, "status": "COMPLETED", "next_packet": next_packet, "physical_tree_verified": True, "canonical_git_state_mutated": False, "ordinary_closeout_pr_required": False, "authority_effect": "NONE"}
    state_id = canonical_sha256(logical, role="DSAI3V_EFFECTIVE_PACKET_COMPLETION_STATE")
    _write_immutable(receipt_store.root / "completion-state" / f"{state_id}.json", {**logical, "completion_state_id": state_id})

    packet_key = canonical_sha256({"programme_id": programme_id, "packet_id": packet_id}, role="DSAI3V_PACKET_COMPLETION_KEY")
    binding = {"schema": PACKET_BINDING_SCHEMA, "programme_id": programme_id, "packet_id": packet_id, "packet_key": packet_key, "transaction_id": transaction_id, "completion_state_id": state_id, "completion_receipt_id": completion_receipt_id, "authority_effect": "NONE"}
    binding_path = receipt_store.root / "completion-state" / "by-packet" / f"{packet_key}.json"
    if binding_path.exists() and dict(_load_record(binding_path)) != binding:
        raise VitContractError("VIT_DUPLICATE_EFFECTIVE_PACKET_COMPLETION")
    _write_immutable(binding_path, binding)

    release_id = None
    release_status = "PROGRAMME_TERMINAL"
    if next_packet:
        release = {"schema": SUCCESSOR_RELEASE_SCHEMA, "programme_id": programme_id, "completed_packet_id": packet_id, "next_packet": next_packet, "completion_state_id": state_id, "completion_receipt_id": completion_receipt_id, "status": "RELEASED_TO_AUTHORITY_RESOLVER", "execution_started": False, "authority_inferred": False, "ordinary_closeout_pr_required": False, "authority_effect": "NONE"}
        release_id = canonical_sha256(release, role="DSAI3V_SUCCESSOR_RELEASE")
        _write_immutable(receipt_store.root / "successor-releases" / f"{release_id}.json", {**release, "successor_release_id": release_id})
        release_status = "RELEASED_TO_AUTHORITY_RESOLVER"
    return {"completion_state_id": state_id, "status": "COMPLETED", "programme_id": programme_id, "packet_id": packet_id, "next_packet": next_packet, "successor_release_id": release_id, "successor_release_status": release_status, "ordinary_closeout_pr_required": False, "canonical_git_state_mutated": False, "authority_effect": "NONE"}
