from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ovc.development.dsai3v_completion_observability import build_canonical_completion_latency_receipt
from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_core import VitContractError, git_tree_sha
from ovc.development.skills.vit_materialisation import (
    PacketCompletionReceipt,
    PhysicalMaterialisationTransaction,
    ReceiptStore,
    materialisation_receipt,
)
from ovc.development.skills.vit_routing import VIT_MANDATORY, validate_vit_lineage_record
from ovc_evidence_store.external_root import resolve_external_root

LIVE_COMPLETION_STORE_RELATIVE = Path("receipts") / "development" / "dsai3v"
LIVE_CONTROLLER = "DSAI_VIT_PHYSICAL_CONTROLLER"
LIVE_GATEWAY = "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY"


def _required(value: object, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise VitContractError(f"{name} is required")
    return text


def _required_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VitContractError(f"{name} must be an object")
    return value


def _ticket_id(lineage: Mapping[str, Any]) -> str:
    """Return an exact persisted ticket identity; never synthesize historical tickets."""
    validated = validate_vit_lineage_record(lineage)
    ticket = lineage.get("integration_ticket")
    ticket_id = str(lineage.get("ticket_id") or "")
    if ticket is None or not ticket_id or validated.ticket_id is None:
        raise VitContractError("VIT_COMPLETION_TICKET_ID_MISSING")
    ticket_map = _required_mapping(ticket, "integration_ticket")
    if canonical_sha256(dict(ticket_map)) != ticket_id or validated.ticket_id != ticket_id:
        raise VitContractError("VIT_COMPLETION_TICKET_ID_INVALID")
    return ticket_id


def resolve_live_completion_receipt_store(
    repository_root: str | Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> ReceiptStore:
    """Resolve the already-governed operator-local receipts plane.

    This deliberately has no arbitrary path override and no network/R2 transport. The only
    production binding is OVC_EXTERNAL_ARTIFACT_ROOT/receipts/development/dsai3v.
    """
    repository = Path(repository_root).resolve()
    external_root = resolve_external_root(
        repository_root=repository,
        environ=environ,
        create=True,
    )
    return ReceiptStore(external_root / LIVE_COMPLETION_STORE_RELATIVE)


@dataclass(frozen=True)
class LiveCompletionResult:
    transaction_id: str
    materialisation_receipt_id: str
    completion_receipt_id: str
    development_latency_receipt_id: str
    completion_observability_attachment_id: str
    observed_commit: str
    observed_tree: str
    expected_result_tree: str
    exact_tree_equal: bool
    receipt_store_binding: str = "OVC_EXTERNAL_ARTIFACT_ROOT/receipts/development/dsai3v"
    controller: str = LIVE_CONTROLLER
    physical_gateway: str = LIVE_GATEWAY


def record_live_completion(
    repository_root: str | Path,
    *,
    lineage: Mapping[str, Any],
    predecessor_commit: str,
    observed_commit: str,
    implementation_ref: str,
    qa_ref: str,
    gate_decision_ref: str,
    assurance_frontier_id: str,
    attempt: int = 1,
    contextual_latency_receipt: Mapping[str, Any] | None = None,
    trace_summary: Mapping[str, Any] | None = None,
    orch_receipts: Sequence[Mapping[str, Any]] = (),
    vit_receipts: Sequence[Mapping[str, Any]] = (),
    siq_receipts: Sequence[Mapping[str, Any]] = (),
    async_assurance_metrics: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> LiveCompletionResult:
    """Persist one recoverable live VIT materialisation/completion/DEVOBS bundle.

    The caller supplies already-observed merge and assurance provenance. This function never
    performs a GitHub write, never merges, never publishes, and never infers missing telemetry.
    """
    repository = Path(repository_root).resolve()
    validated = validate_vit_lineage_record(lineage)
    if validated.route_class != VIT_MANDATORY:
        raise VitContractError("VIT_COMPLETION_ROUTE_NOT_MANDATORY")
    ticket_id = _ticket_id(lineage)

    routing = _required_mapping(lineage.get("routing"), "routing")
    if routing.get("controller") != LIVE_CONTROLLER or routing.get("physical_gateway") != LIVE_GATEWAY:
        raise VitContractError("VIT_COMPLETION_ROUTING_OWNER_INVALID")

    generation = _required_mapping(lineage.get("generation"), "generation")
    predecessor_tree_record = _required_mapping(generation.get("predecessor_tree"), "generation.predecessor_tree")
    result_tree_record = _required_mapping(generation.get("result_tree"), "generation.result_tree")
    expected_predecessor_tree = _required(predecessor_tree_record.get("tree_sha"), "expected_predecessor_tree")
    expected_result_tree = _required(result_tree_record.get("tree_sha"), "expected_result_tree")
    predecessor_commit = _required(predecessor_commit, "predecessor_commit")
    observed_commit = _required(observed_commit, "observed_commit")

    actual_predecessor_tree = git_tree_sha(repository, predecessor_commit)
    if actual_predecessor_tree != expected_predecessor_tree:
        raise VitContractError("VIT_COMPLETION_PREDECESSOR_TREE_MISMATCH")
    observed_tree = git_tree_sha(repository, observed_commit)

    tx = PhysicalMaterialisationTransaction(
        vit_generation_id=validated.generation_id,
        ticket_id=ticket_id,
        train_generation_id=_required(generation.get("train_generation_id"), "train_generation_id"),
        expected_predecessor_commit=predecessor_commit,
        expected_predecessor_tree=expected_predecessor_tree,
        expected_result_tree=expected_result_tree,
        authority_frontier_id=_required(generation.get("authority_manifest_id"), "authority_frontier_id"),
        assurance_frontier_id=_required(assurance_frontier_id, "assurance_frontier_id"),
        materialisation_profile="LIVE_PHYSICAL_MAIN",
        attempt=attempt,
    )
    materialised = materialisation_receipt(tx, observed_commit, observed_tree)
    if not materialised.equality:
        raise VitContractError("POST_WRITE_TREE_MISMATCH")

    pip = _required_mapping(lineage.get("pip"), "pip")
    transition = pip.get("completion_transition")
    transition_map = dict(transition) if isinstance(transition, Mapping) else {}
    next_packet_value = transition_map.get("next_packet")
    next_packet = str(next_packet_value) if next_packet_value else None
    completion = PacketCompletionReceipt(
        programme_id=validated.programme_id,
        packet_id=validated.packet_id,
        implementation_ref=_required(implementation_ref, "implementation_ref"),
        qa_ref=_required(qa_ref, "qa_ref"),
        gate_decision_ref=_required(gate_decision_ref, "gate_decision_ref"),
        payload_id=validated.pip_id,
        vit_generation_id=validated.generation_id,
        materialisation_receipt_id=materialised.receipt_id,
        next_packet=next_packet,
    )

    observed_vit_receipt = {
        "schema": "ovc-vital-materialisation-observation/v1",
        "receipt_id": materialised.receipt_id,
        "packet_id": validated.packet_id,
        "equality": materialised.equality,
        "outcome": materialised.outcome,
    }
    devobs = build_canonical_completion_latency_receipt(
        programme_id=completion.programme_id,
        packet_id=completion.packet_id,
        completion_receipt_id=completion.receipt_id,
        contextual_latency_receipt=contextual_latency_receipt,
        trace_summary=trace_summary,
        orch_receipts=tuple(dict(row) for row in orch_receipts),
        vit_receipts=tuple(dict(row) for row in vit_receipts) + (observed_vit_receipt,),
        siq_receipts=tuple(dict(row) for row in siq_receipts),
        async_assurance_metrics=async_assurance_metrics,
    )

    store = resolve_live_completion_receipt_store(repository, environ=environ)
    # This ordering is deliberately recoverable rather than pretending filesystem writes are
    # atomic. A retry is content-addressed/idempotent and repairs interruption at any boundary.
    store.put(materialised, materialised.receipt_id)
    attached = store.put_completion_with_devobs(completion, devobs)
    store.rebuild_index()

    return LiveCompletionResult(
        transaction_id=tx.transaction_id,
        materialisation_receipt_id=materialised.receipt_id,
        completion_receipt_id=attached["completion_receipt_id"],
        development_latency_receipt_id=attached["development_latency_receipt_id"],
        completion_observability_attachment_id=attached["attachment_id"],
        observed_commit=observed_commit,
        observed_tree=observed_tree,
        expected_result_tree=expected_result_tree,
        exact_tree_equal=True,
    )
