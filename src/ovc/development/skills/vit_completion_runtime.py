from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import os
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from ovc.development.dsai3v_completion_observability import build_canonical_completion_latency_receipt
from ovc.development.dsai3v_completion_observability_v2 import (
    build_canonical_completion_latency_receipt_v2,
    build_completion_attachment_v2,
    validate_canonical_completion_latency_receipt_v2,
)
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
EXTERNAL_ARTIFACT_ROOT_ENV = "OVC_EXTERNAL_ARTIFACT_ROOT"
EXTERNAL_RECEIPTS_RELATIVE_ROOT = "receipts"
_IMPLEMENTATION_HEAD = re.compile(r"^github:pr:\d+:head:([0-9a-f]{40})$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def resolve_receipt_store(
    root: str | Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> ReceiptStore:
    """Resolve the already-authorised durable ReceiptStore without inventing a sink.

    Resolution order is deliberately narrow:
    1. an explicitly injected ReceiptStore root (test/runtime dependency injection);
    2. the existing DSAI3V-specific runtime binding, if already configured;
    3. the already-governed OVC external-artifact root's canonical ``receipts/``
       directory.

    The third route reuses the existing development external-artifact binding and the
    root contract's declared receipts namespace. It does not select a new repository,
    cloud service, or publication destination. If neither existing runtime binding is
    present, resolution fails closed instead of falling back to the Git worktree or an
    ephemeral directory.
    """
    if root is None:
        source = os.environ if env is None else env
        dedicated = str(source.get(RECEIPT_STORE_ROOT_ENV, "")).strip()
        if dedicated:
            root = dedicated
        else:
            external_root = str(source.get(EXTERNAL_ARTIFACT_ROOT_ENV, "")).strip()
            if not external_root:
                raise VitContractError("DSAI3V_RECEIPT_STORE_ROOT_UNBOUND")
            root = Path(external_root).expanduser() / EXTERNAL_RECEIPTS_RELATIVE_ROOT
    path = Path(root).expanduser()
    if not str(path).strip():
        raise VitContractError("DSAI3V_RECEIPT_STORE_ROOT_UNBOUND")
    return ReceiptStore(path)


def _bind_exact_observation(
    target: dict[str, Any],
    key: str,
    exact_value: Any,
) -> None:
    if exact_value is None:
        return
    supplied = target.get(key)
    if supplied is not None and supplied != exact_value:
        raise VitContractError(f"V2_OBSERVABILITY_{key.upper()}_MISMATCH")
    target[key] = exact_value


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
    completion_timing_sources: Sequence[Mapping[str, Any]] = (),
    completion_aa0_observability: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Persist one live VIT/SIQ materialisation and mandatory completion bundle.

    The historical v1 bundle is emitted exactly as before. A prospective v2 receipt
    and v2 attachment are then added to the same bound ReceiptStore. V2 is
    observability-only; it does not become a prerequisite for the historical bundle,
    change merge authority, or create a new storage/write path.

    V2 timing accepts only explicit source rows supplied by their current owner. This
    runtime adds exactly one local timing observation after the historical completion
    bundle is successfully persisted. It deliberately does not reinterpret a generic
    DEVOBS trace-completion time as physical materialisation, SIQ readiness, PR open,
    or any other canonical event.
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
    completion_observed_at = _utc_now()

    timing_sources: list[Mapping[str, Any]] = [dict(row) for row in completion_timing_sources]
    timing_sources.append(
        {
            "field": "packet_completion_receipt_persisted_at_utc",
            "source_type": "OWNER_LOCAL_RECEIPT",
            "source_id": completion.receipt_id,
            "observed_at_utc": completion_observed_at,
            "authority": "OBSERVATIONAL_ONLY",
        }
    )

    aa0_observability: dict[str, Any] = dict(completion_aa0_observability or {})
    exact_pip_id = payload_id if re.fullmatch(r"[0-9a-f]{64}", str(payload_id)) else None
    _bind_exact_observation(aa0_observability, "pip_id", exact_pip_id)
    _bind_exact_observation(aa0_observability, "prospective_tree_sha", transaction.expected_result_tree)
    _bind_exact_observation(aa0_observability, "physical_tree_sha", observed_tree)
    head_match = _IMPLEMENTATION_HEAD.fullmatch(str(implementation_ref))
    if head_match:
        _bind_exact_observation(aa0_observability, "candidate_head_sha", head_match.group(1))
        _bind_exact_observation(aa0_observability, "pr_head_sha", head_match.group(1))

    v2_receipt = build_canonical_completion_latency_receipt_v2(
        v1_receipt=development_latency_receipt,
        timing_sources=timing_sources,
        aa0_observability=aa0_observability,
    )
    expected: dict[str, Any] = {
        "programme_id": programme_id,
        "packet_id": packet_id,
        "completion_receipt_id": completion.receipt_id,
        "prospective_tree_sha": transaction.expected_result_tree,
        "physical_tree_sha": observed_tree,
    }
    if head_match:
        expected["candidate_head_sha"] = head_match.group(1)
        expected["pr_head_sha"] = head_match.group(1)
    if exact_pip_id:
        expected["pip_id"] = exact_pip_id
    validate_canonical_completion_latency_receipt_v2(v2_receipt, expected=expected)
    v2_receipt_id = str(v2_receipt["record_id"])
    receipt_store.put_record(v2_receipt, v2_receipt_id)
    v2_attachment = build_completion_attachment_v2(
        programme_id=programme_id,
        packet_id=packet_id,
        completion_receipt_id=completion.receipt_id,
        development_latency_receipt=v2_receipt,
    )
    receipt_store.put_record(v2_attachment.to_record(), v2_attachment.attachment_id)

    return {
        "transaction_id": transaction.transaction_id,
        "materialisation_receipt_id": materialisation.receipt_id,
        **bundle_ids,
        "v2_development_latency_receipt_id": v2_receipt_id,
        "v2_attachment_id": v2_attachment.attachment_id,
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
    already physical, the same deterministic historical completion bundle is persisted
    idempotently. Prospective v2 is append-only and reuses the same bound store.
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
