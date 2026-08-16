from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from ovc.development.dsai3v_completion_observability import build_canonical_completion_latency_receipt
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_materialisation import (
    PacketCompletionReceipt,
    PhysicalMaterialisationTransaction,
    ReceiptStore,
    materialisation_receipt,
    recover_unknown_write,
)

VIT_PHYSICAL_CONTROLLER = "DSAI_VIT_PHYSICAL_CONTROLLER"
SIQ_PHYSICAL_GATEWAY = "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY"
RECEIPT_STORE_ROOT_ENV = "OVC_DSAI3V_RECEIPT_STORE_ROOT"


def resolve_receipt_store(
    root: str | Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> ReceiptStore:
    """Resolve the already-authorised durable ReceiptStore without inventing a sink.

    Production callers must supply an explicit root or bind the existing runtime mount
    through OVC_DSAI3V_RECEIPT_STORE_ROOT. Absence fails closed instead of silently
    falling back to a repository path or ephemeral working directory.
    """
    if root is None:
        source = os.environ if env is None else env
        configured = str(source.get(RECEIPT_STORE_ROOT_ENV, "")).strip()
        if not configured:
            raise VitContractError("DSAI3V_RECEIPT_STORE_ROOT_UNBOUND")
        root = configured
    path = Path(root).expanduser()
    if not str(path).strip():
        raise VitContractError("DSAI3V_RECEIPT_STORE_ROOT_UNBOUND")
    return ReceiptStore(path)


def persist_physical_completion(
    *,
    transaction: PhysicalMaterialisationTransaction,
    observed_commit: str,
    observed_tree: str,
    programme_id: str,
    packet_id: str,
    implementation_ref: str,
    qa_ref: str,
    gate_decision_ref: str,
    payload_id: str,
    next_packet: str | None,
    receipt_store: ReceiptStore,
    controller: str = VIT_PHYSICAL_CONTROLLER,
    physical_gateway: str = SIQ_PHYSICAL_GATEWAY,
    contextual_latency_receipt: Mapping[str, Any] | None = None,
    trace_summary: Mapping[str, Any] | None = None,
    orch_receipts: Sequence[Mapping[str, Any]] = (),
    vit_receipts: Sequence[Mapping[str, Any]] = (),
    siq_receipts: Sequence[Mapping[str, Any]] = (),
    async_assurance_metrics: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Persist one live VIT/SIQ materialisation and mandatory completion bundle.

    This is the runtime binding for the existing physical controller. It creates no
    merge authority and performs no Git write. The caller supplies the already-observed
    post-write commit/tree. Exact tree mismatch is persisted as evidence and fails
    closed before PacketCompletionReceipt creation. Bundle writes are content-addressed
    and idempotent, so retry after an interrupted receipt write is recovery, not a new
    completion.
    """
    if controller != VIT_PHYSICAL_CONTROLLER:
        raise VitContractError("PHYSICAL_MAIN_WRITER_IDENTITY_INVALID")
    if physical_gateway != SIQ_PHYSICAL_GATEWAY:
        raise VitContractError("PHYSICAL_GATEWAY_INVALID")
    if transaction.materialisation_profile != "LIVE_PHYSICAL_MAIN":
        raise VitContractError("LIVE_COMPLETION_REQUIRES_LIVE_PHYSICAL_MAIN_TRANSACTION")

    materialisation = materialisation_receipt(transaction, observed_commit, observed_tree)
    receipt_store.put(materialisation, materialisation.receipt_id)
    if not materialisation.equality:
        raise VitContractError("POST_WRITE_TREE_MISMATCH")

    completion = PacketCompletionReceipt(
        programme_id=programme_id,
        packet_id=packet_id,
        implementation_ref=implementation_ref,
        qa_ref=qa_ref,
        gate_decision_ref=gate_decision_ref,
        payload_id=payload_id,
        vit_generation_id=transaction.vit_generation_id,
        materialisation_receipt_id=materialisation.receipt_id,
        next_packet=next_packet,
    )
    observed_vit = tuple(dict(row) for row in vit_receipts) + (asdict(materialisation),)
    development_latency_receipt = build_canonical_completion_latency_receipt(
        programme_id=programme_id,
        packet_id=packet_id,
        completion_receipt_id=completion.receipt_id,
        contextual_latency_receipt=contextual_latency_receipt,
        trace_summary=trace_summary,
        orch_receipts=orch_receipts,
        vit_receipts=observed_vit,
        siq_receipts=siq_receipts,
        async_assurance_metrics=async_assurance_metrics,
    )
    bundle_ids = receipt_store.put_completion_with_devobs(completion, development_latency_receipt)
    return {
        "transaction_id": transaction.transaction_id,
        "materialisation_receipt_id": materialisation.receipt_id,
        **bundle_ids,
        "observed_commit": observed_commit,
        "observed_tree": observed_tree,
        "exact_tree_equal": True,
        "controller": controller,
        "physical_gateway": physical_gateway,
        "authority_effect": "NONE",
    }


def recover_effective_write_completion(
    *,
    transaction: PhysicalMaterialisationTransaction,
    observed_commit: str,
    observed_tree: str,
    **completion_kwargs: Any,
) -> Mapping[str, Any]:
    """Recover receipt persistence after main advanced but bundle persistence did not.

    The physical write is never repeated here. If the exact expected result tree is
    already physical, the same deterministic completion bundle is persisted idempotently.
    Any other post-write state fails closed.
    """
    disposition = recover_unknown_write(transaction, observed_commit, observed_tree)
    if disposition == "WRITE_NOT_EFFECTIVE_RETRYABLE":
        return {
            "status": disposition,
            "transaction_id": transaction.transaction_id,
            "authority_effect": "NONE",
        }
    if disposition != "WRITE_EFFECTIVE_RECEIPT_RECOVERY_REQUIRED":
        raise VitContractError(disposition)
    result = persist_physical_completion(
        transaction=transaction,
        observed_commit=observed_commit,
        observed_tree=observed_tree,
        **completion_kwargs,
    )
    return {"status": "WRITE_EFFECTIVE_RECEIPT_RECOVERED", **result}
