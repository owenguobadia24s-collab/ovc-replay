from __future__ import annotations

from dataclasses import asdict
import base64
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_completion_runtime import recover_effective_write_completion
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_materialisation import (
    PhysicalMaterialisationTransaction,
    ReceiptStore,
)
from ovc.development.skills.vit_routing import (
    SIQ_GATEWAY,
    VIT_CONTROLLER,
    VIT_MANDATORY,
    validate_vit_lineage_record,
)

FREEZE_SCHEMA = "ovc-vit-live-physical-transaction-freeze/v1"
PROOF_SCHEMA = "ovc-vit-local-post-merge-completion-proof/v1"
FREEZE_MARKER_PREFIX = "OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64="
_FREEZE_MARKER = re.compile(
    rf"(?m)^{re.escape(FREEZE_MARKER_PREFIX)}([A-Za-z0-9_\-=]+)\s*$"
)


def _sha(value: str, length: int) -> str:
    value = str(value).strip()
    if len(value) != length:
        raise VitContractError("VIT_LIVE_COMPLETION_SHA_INVALID")
    try:
        int(value, 16)
    except ValueError as exc:
        raise VitContractError("VIT_LIVE_COMPLETION_SHA_INVALID") from exc
    if value.lower() != value:
        raise VitContractError("VIT_LIVE_COMPLETION_SHA_INVALID")
    return value


def _write_content_addressed(path: Path, payload: Mapping[str, Any]) -> None:
    encoded = json.dumps(
        dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != encoded:
            raise VitContractError("VIT_LEDGER_INTEGRITY_FAIL")
        return
    path.write_text(encoded, encoding="utf-8")


def build_live_transaction_freeze(
    *,
    lineage_record: Mapping[str, Any],
    pr_number: int,
    base_sha: str,
    head_sha: str,
    base_tree: str,
    head_tree: str,
    workflow_run_id: str,
    run_attempt: str,
) -> dict[str, Any]:
    """Freeze the exact live PhysicalMaterialisationTransaction before Git write.

    The freeze is authority-inert. Ticket and assurance-frontier identities are
    prospectively and deterministically created from already-observed PR/VIT/CI
    identities; no timing, retry, latency, or execution telemetry is inferred.
    """
    lineage = validate_vit_lineage_record(lineage_record)
    if lineage.route_class != VIT_MANDATORY:
        raise VitContractError("LIVE_COMPLETION_REQUIRES_VIT_MANDATORY_LINEAGE")

    base_sha = _sha(base_sha, 40)
    head_sha = _sha(head_sha, 40)
    base_tree = _sha(base_tree, 40)
    head_tree = _sha(head_tree, 40)

    generation = dict(lineage_record["generation"])
    placement = dict(lineage_record["placement"])
    pip = dict(lineage_record["pip"])
    if str(placement["predecessor_tree"]) != base_tree:
        raise VitContractError("LIVE_COMPLETION_PREDECESSOR_TREE_MISMATCH")
    if str(placement["result_tree"]) != head_tree:
        raise VitContractError("LIVE_COMPLETION_RESULT_TREE_MISMATCH")

    ticket_logical = {
        "programme_id": lineage.programme_id,
        "packet_id": lineage.packet_id,
        "payload_id": lineage.pip_id,
        "generation_id": lineage.generation_id,
        "placement_id": lineage.placement_id,
        "base_sha": base_sha,
        "head_sha": head_sha,
    }
    ticket_id = "VIT-LIVE-" + canonical_sha256(
        ticket_logical, role="DSAI3V_PHYSICAL_MATERIALISATION_TICKET"
    )
    assurance_logical = {
        "workflow_run_id": str(workflow_run_id),
        "run_attempt": str(run_attempt),
        "base_sha": base_sha,
        "head_sha": head_sha,
        "generation_id": lineage.generation_id,
        "placement_id": lineage.placement_id,
        "assurance_profile": "OVC_REQUIRED_ASSURANCE_PROFILE_v0_1",
    }
    assurance_frontier_id = canonical_sha256(
        assurance_logical, role="DSAI3V_PREWRITE_ASSURANCE_FRONTIER"
    )

    transaction = PhysicalMaterialisationTransaction(
        vit_generation_id=lineage.generation_id,
        ticket_id=ticket_id,
        train_generation_id=str(generation["train_generation_id"]),
        expected_predecessor_commit=base_sha,
        expected_predecessor_tree=base_tree,
        expected_result_tree=head_tree,
        authority_frontier_id=str(generation["authority_manifest_id"]),
        assurance_frontier_id=assurance_frontier_id,
        materialisation_profile="LIVE_PHYSICAL_MAIN",
        attempt=1,
    )
    completion_transition = dict(pip.get("completion_transition") or {})
    completion_context = {
        "programme_id": lineage.programme_id,
        "packet_id": lineage.packet_id,
        "implementation_ref": f"github:pr:{int(pr_number)}:head:{head_sha}",
        "qa_ref": (
            f"github:pr:{int(pr_number)}:head:{head_sha}:required-assurance"
        ),
        "gate_decision_ref": (
            f"vit-lineage:{lineage.generation_id}:completion_transition"
        ),
        "payload_id": lineage.pip_id,
        "next_packet": completion_transition.get("next_packet"),
    }
    logical = {
        "schema": FREEZE_SCHEMA,
        "controller": VIT_CONTROLLER,
        "physical_gateway": SIQ_GATEWAY,
        "pr_number": int(pr_number),
        "head_sha": head_sha,
        "pip_id": lineage.pip_id,
        "generation_id": lineage.generation_id,
        "placement_id": lineage.placement_id,
        "transaction": asdict(transaction),
        "transaction_id": transaction.transaction_id,
        "completion_context": completion_context,
        "freeze_provenance": {
            "workflow_run_id": str(workflow_run_id),
            "run_attempt": str(run_attempt),
            "source": "VIT_ROUTING_PREFLIGHT_BEFORE_PHYSICAL_WRITE",
            "evidence_rule": "OBSERVED_IDENTITIES_ONLY_NO_UNOBSERVED_TELEMETRY",
        },
        "authority_effect": "NONE",
    }
    return logical


def encode_freeze_marker(freeze: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(freeze), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    token = base64.urlsafe_b64encode(encoded).decode("ascii").rstrip("=")
    return FREEZE_MARKER_PREFIX + token


def decode_freeze_marker(value: str) -> Mapping[str, Any]:
    matches = _FREEZE_MARKER.findall(str(value))
    if len(matches) != 1:
        raise VitContractError("VIT_LIVE_TRANSACTION_FREEZE_NOT_UNIQUE")
    token = matches[0]
    token += "=" * ((4 - len(token) % 4) % 4)
    try:
        payload = json.loads(
            base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        )
    except Exception as exc:
        raise VitContractError("VIT_LIVE_TRANSACTION_FREEZE_INVALID") from exc
    if not isinstance(payload, Mapping):
        raise VitContractError("VIT_LIVE_TRANSACTION_FREEZE_INVALID")
    validate_live_transaction_freeze(payload)
    return payload


def validate_live_transaction_freeze(
    freeze: Mapping[str, Any],
) -> PhysicalMaterialisationTransaction:
    if freeze.get("schema") != FREEZE_SCHEMA:
        raise VitContractError("VIT_LIVE_TRANSACTION_FREEZE_SCHEMA_INVALID")
    if freeze.get("controller") != VIT_CONTROLLER:
        raise VitContractError("PHYSICAL_MAIN_WRITER_IDENTITY_INVALID")
    if freeze.get("physical_gateway") != SIQ_GATEWAY:
        raise VitContractError("PHYSICAL_GATEWAY_INVALID")
    raw = freeze.get("transaction")
    if not isinstance(raw, Mapping):
        raise VitContractError("VIT_LIVE_TRANSACTION_FREEZE_INVALID")
    transaction = PhysicalMaterialisationTransaction(**dict(raw))
    if transaction.materialisation_profile != "LIVE_PHYSICAL_MAIN":
        raise VitContractError("LIVE_COMPLETION_REQUIRES_LIVE_PHYSICAL_MAIN_TRANSACTION")
    if freeze.get("transaction_id") != transaction.transaction_id:
        raise VitContractError("VIT_LIVE_TRANSACTION_ID_MISMATCH")
    if str(freeze.get("generation_id")) != transaction.vit_generation_id:
        raise VitContractError("VIT_LIVE_TRANSACTION_GENERATION_MISMATCH")
    _sha(transaction.expected_predecessor_commit, 40)
    _sha(transaction.expected_predecessor_tree, 40)
    _sha(transaction.expected_result_tree, 40)
    return transaction


def complete_frozen_transaction(
    *,
    freeze: Mapping[str, Any],
    observed_commit: str,
    observed_tree: str,
    receipt_store: ReceiptStore,
    siq_receipts: Sequence[Mapping[str, Any]] = (),
    trace_summary: Mapping[str, Any] | None = None,
    async_assurance_metrics: Mapping[str, Any] | None = None,
    completion_timing_sources: Sequence[Mapping[str, Any]] = (),
    completion_aa0_observability: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Recover/persist the already-effective physical write and prove its bundle."""
    transaction = validate_live_transaction_freeze(freeze)
    observed_commit = _sha(observed_commit, 40)
    observed_tree = _sha(observed_tree, 40)
    if observed_tree != transaction.expected_result_tree:
        raise VitContractError("POST_WRITE_TREE_MISMATCH")

    context = freeze.get("completion_context")
    if not isinstance(context, Mapping):
        raise VitContractError("VIT_LIVE_COMPLETION_CONTEXT_INVALID")

    transaction_copy = (
        receipt_store.root / "transactions" / f"{transaction.transaction_id}.json"
    )
    _write_content_addressed(transaction_copy, freeze)

    trace_summary_id: str | None = None
    if trace_summary is not None:
        if trace_summary.get("schema") != "ovc-development-observability-trace-summary/v1":
            raise VitContractError("DEVOBS_TRACE_SUMMARY_SCHEMA_INVALID")
        raw_trace_id = trace_summary.get("record_id")
        if not isinstance(raw_trace_id, str) or not raw_trace_id:
            raise VitContractError("DEVOBS_TRACE_SUMMARY_ID_MISSING")
        trace_summary_id = raw_trace_id
        receipt_store.put(dict(trace_summary), trace_summary_id)

    result = recover_effective_write_completion(
        transaction=transaction,
        observed_commit=observed_commit,
        observed_tree=observed_tree,
        programme_id=str(context["programme_id"]),
        packet_id=str(context["packet_id"]),
        implementation_ref=str(context["implementation_ref"]),
        qa_ref=str(context["qa_ref"]),
        gate_decision_ref=str(context["gate_decision_ref"]),
        payload_id=str(context["payload_id"]),
        next_packet=(
            str(context["next_packet"])
            if context.get("next_packet") is not None
            else None
        ),
        receipt_store=receipt_store,
        siq_receipts=siq_receipts,
        trace_summary=trace_summary,
        async_assurance_metrics=async_assurance_metrics,
        completion_timing_sources=completion_timing_sources,
        completion_aa0_observability=completion_aa0_observability,
    )
    ids = {
        "materialisation_receipt_id": str(result["materialisation_receipt_id"]),
        "completion_receipt_id": str(result["completion_receipt_id"]),
        "development_latency_receipt_id": str(
            result["development_latency_receipt_id"]
        ),
        "attachment_id": str(result["attachment_id"]),
    }
    if len(set(ids.values())) != 4:
        raise VitContractError("VIT_COMPLETION_BUNDLE_ID_COLLISION")
    missing = [
        receipt_id
        for receipt_id in ids.values()
        if not (receipt_store.root / f"{receipt_id}.json").is_file()
    ]
    if missing:
        raise VitContractError(
            "VIT_COMPLETION_BUNDLE_INCOMPLETE:" + ",".join(sorted(missing))
        )
    for receipt_id in ids.values():
        payload = json.loads(
            (receipt_store.root / f"{receipt_id}.json").read_text(encoding="utf-8")
        )
        if not isinstance(payload, Mapping):
            raise VitContractError("VIT_COMPLETION_BUNDLE_RECORD_INVALID")

    v2_ids = {
        "v2_development_latency_receipt_id": str(
            result["v2_development_latency_receipt_id"]
        ),
        "v2_attachment_id": str(result["v2_attachment_id"]),
    }
    missing_v2 = [
        receipt_id
        for receipt_id in v2_ids.values()
        if not (receipt_store.root / f"{receipt_id}.json").is_file()
    ]
    if missing_v2:
        raise VitContractError(
            "VIT_COMPLETION_V2_BUNDLE_INCOMPLETE:" + ",".join(sorted(missing_v2))
        )

    index = receipt_store.rebuild_index()
    if index.get(f"transaction_id:{transaction.transaction_id}") != (
        f"{ids['materialisation_receipt_id']}.json"
    ):
        raise VitContractError("VIT_COMPLETION_TRANSACTION_INDEX_MISSING")
    proof_logical = {
        "schema": PROOF_SCHEMA,
        "transaction_id": transaction.transaction_id,
        "observed_commit": observed_commit,
        "observed_tree": observed_tree,
        "expected_result_tree": transaction.expected_result_tree,
        "exact_tree_equal": True,
        "four_content_addressed_receipts_present": True,
        "receipt_ids": ids,
        "controller": VIT_CONTROLLER,
        "physical_gateway": SIQ_GATEWAY,
        "telemetry_rule": "OBSERVED_ONLY_UNAVAILABLE_WHERE_ABSENT",
        "authority_effect": "NONE",
    }
    if trace_summary_id is not None:
        proof_logical["trace_summary_id"] = trace_summary_id
    proof_id = canonical_sha256(
        proof_logical, role="DSAI3V_LOCAL_POST_MERGE_COMPLETION_PROOF"
    )
    proof = {**proof_logical, "proof_id": proof_id}
    _write_content_addressed(
        receipt_store.root / "proofs" / f"{proof_id}.json",
        proof,
    )
    return {**proof, "v2_receipt_ids": v2_ids}
