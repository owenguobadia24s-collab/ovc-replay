from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
from typing import Literal

from ovc.development.skills.vit_apply import apply_payload_reference
from ovc.development.skills.vit_core import (
    PacketIntegrationPayload,
    ProspectiveTreeState,
    VirtualIntegrationGeneration,
    VitContractError,
    git_tree_sha,
)
from ovc.development.skills.vit_materialisation import (
    PacketCompletionReceipt,
    PhysicalIntegrationLease,
    PhysicalMaterialisationTransaction,
    ReceiptStore,
    authorize_materialisation,
    materialisation_receipt,
    recover_unknown_write,
    validate_lease,
)

CrashPoint = Literal["NONE", "BEFORE_WRITE", "POST_WRITE_PRE_RECEIPT", "POST_RECEIPT_PRE_SUCCESSOR"]


@dataclass(frozen=True)
class IsolatedRehearsalResult:
    outcome: str
    predecessor_commit: str
    predecessor_tree: str
    predicted_result_tree: str | None
    observed_commit: str | None
    observed_tree: str | None
    materialisation_receipt_id: str | None
    completion_receipt_id: str | None
    recovery_disposition: str | None
    physical_main_touched: bool = False
    vit_generation_id: str | None = None
    gateway_disposition: str | None = None
    closeout_churn_detected: bool = False


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(os.environ, **(env or {})),
    )
    return proc.stdout.strip()


def run_isolated_rehearsal(
    repo: str | Path,
    predecessor_commit: str,
    payload: PacketIntegrationPayload,
    receipt_store: ReceiptStore,
    *,
    grt_pass: bool = True,
    siq_ready: bool = True,
    receipt_store_available: bool = True,
    crash_point: CrashPoint = "NONE",
) -> IsolatedRehearsalResult:
    """Exercise the Q5 physical-materialisation transaction on an isolated Git ref.

    This deliberately uses an isolated, non-authoritative repository/ref.  It composes
    the PIP into an exact prospective Git tree, materialises a VIT generation, applies
    GRT and serialized-gateway readiness, creates a PMT/lease, writes one deterministic
    commit-tree to ``refs/heads/vit-q5-isolated``, verifies exact tree equality and
    writes content-addressed materialisation/completion receipts.  It never advances
    the checked-out branch or physical OVC main.
    """
    repo = Path(repo)
    predecessor_tree = git_tree_sha(repo, predecessor_commit)
    composition = apply_payload_reference(repo, predecessor_tree, payload)
    if composition.failures or composition.result_tree is None:
        raise VitContractError("COMPOSITION_FAILED")
    if not grt_pass:
        raise VitContractError("GRT_CONFORMANCE_FAIL")

    vit_generation = VirtualIntegrationGeneration(
        train_generation_id="isolated-train:q5",
        ordinal=0,
        predecessor_tree=ProspectiveTreeState(predecessor_tree),
        payload_id=payload.payload_id,
        result_tree=ProspectiveTreeState(composition.result_tree),
        authority_manifest_id=payload.authority_manifest.logical_id,
        dependency_frontier_id=payload.dependency_frontier.logical_id,
    )

    if not siq_ready:
        raise VitContractError("LEASE_UNAVAILABLE")

    tx = PhysicalMaterialisationTransaction(
        vit_generation_id=vit_generation.generation_id,
        ticket_id=f"ticket:{payload.payload_id}",
        train_generation_id=vit_generation.train_generation_id,
        expected_predecessor_commit=predecessor_commit,
        expected_predecessor_tree=predecessor_tree,
        expected_result_tree=composition.result_tree,
        authority_frontier_id=payload.authority_manifest.logical_id,
        assurance_frontier_id="q5-isolated-assurance",
        materialisation_profile="ISOLATED_REHEARSAL",
    )
    if authorize_materialisation(tx, pilot_authority_active=False) != "ALLOW_ISOLATED_REHEARSAL":
        raise VitContractError("WAITING_OPERATOR_AUTHORITY")

    lease = PhysicalIntegrationLease(
        "q5-isolated-lease",
        predecessor_commit,
        predecessor_tree,
        "DSAI_VIT_Q5_ISOLATED",
    )
    if validate_lease(lease, predecessor_commit, predecessor_tree) != "LEASE_VALID":
        raise VitContractError("PREDECESSOR_MOVED")
    gateway_disposition = "SIQ_GATEWAY_ISOLATED_LEASE_VALID"

    if crash_point == "BEFORE_WRITE":
        recovery = recover_unknown_write(tx, predecessor_commit, predecessor_tree)
        return IsolatedRehearsalResult(
            "CRASH_BEFORE_WRITE",
            predecessor_commit,
            predecessor_tree,
            composition.result_tree,
            None,
            None,
            None,
            None,
            recovery,
            vit_generation_id=vit_generation.generation_id,
            gateway_disposition=gateway_disposition,
        )

    commit_env = {
        "GIT_AUTHOR_NAME": "OVC VIT Isolated Rehearsal",
        "GIT_AUTHOR_EMAIL": "vit-isolated@example.invalid",
        "GIT_COMMITTER_NAME": "OVC VIT Isolated Rehearsal",
        "GIT_COMMITTER_EMAIL": "vit-isolated@example.invalid",
        "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
        "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
    }
    observed_commit = _git(
        repo,
        "commit-tree",
        composition.result_tree,
        "-p",
        predecessor_commit,
        "-m",
        "Q5 isolated VIT materialisation",
        env=commit_env,
    )
    _git(repo, "update-ref", "refs/heads/vit-q5-isolated", observed_commit)
    observed_tree = git_tree_sha(repo, observed_commit)

    if crash_point == "POST_WRITE_PRE_RECEIPT":
        recovery = recover_unknown_write(tx, observed_commit, observed_tree)
        return IsolatedRehearsalResult(
            "CRASH_POST_WRITE_PRE_RECEIPT",
            predecessor_commit,
            predecessor_tree,
            composition.result_tree,
            observed_commit,
            observed_tree,
            None,
            None,
            recovery,
            vit_generation_id=vit_generation.generation_id,
            gateway_disposition=gateway_disposition,
        )

    receipt = materialisation_receipt(tx, observed_commit, observed_tree)
    if not receipt.equality:
        raise VitContractError("POST_WRITE_TREE_MISMATCH")
    if not receipt_store_available:
        return IsolatedRehearsalResult(
            "RECEIPT_STORE_UNAVAILABLE_STOP",
            predecessor_commit,
            predecessor_tree,
            composition.result_tree,
            observed_commit,
            observed_tree,
            None,
            None,
            "STOP_BEFORE_NEXT_TRANSACTION",
            vit_generation_id=vit_generation.generation_id,
            gateway_disposition=gateway_disposition,
        )
    receipt_store.put(receipt, receipt.receipt_id)

    if crash_point == "POST_RECEIPT_PRE_SUCCESSOR":
        return IsolatedRehearsalResult(
            "CRASH_POST_RECEIPT_PRE_SUCCESSOR",
            predecessor_commit,
            predecessor_tree,
            composition.result_tree,
            observed_commit,
            observed_tree,
            receipt.receipt_id,
            None,
            "RECEIPT_RECOVERABLE",
            vit_generation_id=vit_generation.generation_id,
            gateway_disposition=gateway_disposition,
        )

    completion = PacketCompletionReceipt(
        payload.programme_id,
        payload.packet_id,
        "q5-isolated-implementation",
        "q5-isolated-qa",
        "DSAI3V-G9:auto-pass-eligible",
        payload.payload_id,
        tx.vit_generation_id,
        receipt.receipt_id,
        str(payload.completion_transition.get("next_packet")) if payload.completion_transition.get("next_packet") else None,
    )
    receipt_store.put(completion, completion.receipt_id)
    return IsolatedRehearsalResult(
        "MATERIALISED_EQUIVALENT",
        predecessor_commit,
        predecessor_tree,
        composition.result_tree,
        observed_commit,
        observed_tree,
        receipt.receipt_id,
        completion.receipt_id,
        None,
        vit_generation_id=vit_generation.generation_id,
        gateway_disposition=gateway_disposition,
        closeout_churn_detected=False,
    )
