"""Shadow materialisation, receipt reconstruction, and owner-local liveness plan."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256
from ovc.development.skills.dias import DiasContractError
from ovc.development.skills.dias_transaction import RouteFence


REQUIRED_LIVENESS_FUNCTIONS = frozenset(
    {
        "PROGRAMME_DISCOVERY_AND_ADMISSION",
        "PERSISTENT_SWEEP_HEARTBEAT_LEASE_RECLAIM",
        "PACKET_START_AND_SUCCESSOR_DISPATCH",
        "DETACHED_QUALIFICATION_LEDGER_ENVELOPE_WRITE",
        "EXACT_HEAD_POINTER_PUBLICATION",
        "CONTENT_ADDRESSED_IDEMPOTENT_REPLAY",
    }
)


@dataclass(frozen=True)
class RepositoryProtectionManifest:
    observed_main: str
    observed_tree: str
    ruleset_id: int
    ruleset_updated_at: str
    required_check: str
    merge_method: str
    bypass_actors: tuple[str, ...]
    controller: str
    gateway: str
    parallel_physical_merge: bool

    def __post_init__(self) -> None:
        if len(self.observed_main) != 40 or len(self.observed_tree) != 40:
            raise DiasContractError("repository protection lacks exact main/tree")
        if self.ruleset_id < 1 or not self.required_check or self.merge_method != "squash":
            raise DiasContractError("repository protection rules invalid")
        if self.bypass_actors or self.parallel_physical_merge:
            raise DiasContractError("repository protection permits bypass or parallel writer")

    @property
    def manifest_id(self) -> str:
        return canonical_sha256(asdict(self), role="repository-protection-manifest/v1")


@dataclass(frozen=True)
class MaterialisationAdmissionEnvelope:
    pip_id: str
    transaction_key: str
    protection_manifest_id: str
    expected_predecessor_commit: str
    expected_predecessor_tree: str
    expected_result_tree: str
    route_fence: RouteFence
    qualification_id: str
    shadow_only: bool = True
    live_authority: bool = False

    def __post_init__(self) -> None:
        for field in ("pip_id", "transaction_key", "protection_manifest_id", "qualification_id"):
            if len(getattr(self, field)) != 64:
                raise DiasContractError(f"{field} must be SHA-256")
        for field in ("expected_predecessor_commit", "expected_predecessor_tree", "expected_result_tree"):
            if len(getattr(self, field)) != 40:
                raise DiasContractError(f"{field} must be Git identity")
        if not self.shadow_only or self.live_authority:
            raise DiasContractError("WP4A envelope is shadow-only and cannot grant live authority")

    @property
    def envelope_id(self) -> str:
        return canonical_sha256(asdict(self), role="materialisation-admission-envelope/v1")


@dataclass(frozen=True)
class AdmissionAssessment:
    envelope_id: str
    accepted: bool
    reasons: tuple[str, ...]
    a3_exact: bool
    physical_write_authorised: bool = False


def validate_admission(
    envelope: MaterialisationAdmissionEnvelope,
    *,
    current: RepositoryProtectionManifest,
    expected_protection_id: str,
    writer_id: str,
    writer_generation: int,
    fence_token: str,
    prospective_tree: str,
) -> AdmissionAssessment:
    reasons = []
    if current.manifest_id != expected_protection_id or current.manifest_id != envelope.protection_manifest_id:
        reasons.append("REPOSITORY_PROTECTION_DRIFT")
    if current.observed_main != envelope.expected_predecessor_commit or current.observed_tree != envelope.expected_predecessor_tree:
        reasons.append("PHYSICAL_MAIN_MOVED")
    if not envelope.route_fence.accepts(writer_id=writer_id, generation=writer_generation, fence_token=fence_token):
        reasons.append("STALE_OR_UNKNOWN_WRITER")
    a3 = prospective_tree == envelope.expected_result_tree
    if not a3:
        reasons.append("A3_MISMATCH")
    return AdmissionAssessment(envelope.envelope_id, not reasons, tuple(reasons), a3, False)


@dataclass(frozen=True)
class PreMaterialisationAnchor:
    envelope_id: str
    transaction_key: str
    predecessor_commit: str
    predecessor_tree: str
    expected_result_tree: str
    writer_id: str
    writer_generation: int
    qualification_id: str

    @property
    def anchor_id(self) -> str:
        return canonical_sha256(asdict(self), role="pre-materialisation-anchor/v1")


@dataclass(frozen=True)
class PhysicalMaterialisationReceipt:
    anchor_id: str
    observed_commit: str
    observed_tree: str
    expected_result_tree: str
    a3_exact: bool
    mode: str
    physical_write_performed: bool

    @property
    def receipt_id(self) -> str:
        return canonical_sha256(asdict(self), role="physical-materialisation-receipt/v1")


@dataclass(frozen=True)
class PacketCompletionReceipt:
    transaction_key: str
    pip_id: str
    materialisation_receipt_id: str
    next_packet: str
    successor_release_key: str
    status: str = "COMPLETED"

    @property
    def receipt_id(self) -> str:
        return canonical_sha256(asdict(self), role="packet-completion-receipt/v1")


@dataclass(frozen=True)
class ReceiptReconstructionProof:
    anchor_id: str
    materialisation_receipt_id: str
    completion_receipt_id: str
    observed_main_intact: bool
    receipt_store_available: bool
    deterministic: bool

    @property
    def proof_id(self) -> str:
        return canonical_sha256(asdict(self), role="receipt-reconstruction-proof/v1")


def build_receipts(
    *,
    anchor: PreMaterialisationAnchor,
    pip_id: str,
    observed_commit: str,
    observed_tree: str,
    next_packet: str,
    mode: str = "SHADOW",
) -> tuple[PhysicalMaterialisationReceipt, PacketCompletionReceipt]:
    if mode != "SHADOW":
        raise DiasContractError("WP4A cannot perform live materialisation")
    materialisation = PhysicalMaterialisationReceipt(
        anchor_id=anchor.anchor_id,
        observed_commit=observed_commit,
        observed_tree=observed_tree,
        expected_result_tree=anchor.expected_result_tree,
        a3_exact=observed_tree == anchor.expected_result_tree,
        mode=mode,
        physical_write_performed=False,
    )
    if not materialisation.a3_exact:
        raise DiasContractError("A3 mismatch blocks completion receipt")
    release_key = canonical_sha256(
        {"transaction_key": anchor.transaction_key, "materialisation_receipt_id": materialisation.receipt_id, "next_packet": next_packet},
        role="successor-release-key/v1",
    )
    completion = PacketCompletionReceipt(anchor.transaction_key, pip_id, materialisation.receipt_id, next_packet, release_key)
    return materialisation, completion


def reconstruct_receipts(
    *,
    anchor: PreMaterialisationAnchor,
    pip_id: str,
    observed_commit: str,
    observed_tree: str,
    next_packet: str,
    receipt_store_available: bool,
) -> tuple[PhysicalMaterialisationReceipt, PacketCompletionReceipt, ReceiptReconstructionProof]:
    materialisation, completion = build_receipts(
        anchor=anchor,
        pip_id=pip_id,
        observed_commit=observed_commit,
        observed_tree=observed_tree,
        next_packet=next_packet,
    )
    proof = ReceiptReconstructionProof(anchor.anchor_id, materialisation.receipt_id, completion.receipt_id, True, receipt_store_available, True)
    return materialisation, completion, proof


@dataclass(frozen=True)
class QualificationLedgerAuthorityTransferCandidate:
    ledger_ref: str
    ledger_root: str
    incumbent: str
    target_owner: str
    exact_functions: tuple[str, ...]
    status: str = "SHADOW_CANDIDATE"
    live_transfer: bool = False

    def __post_init__(self) -> None:
        if self.status != "SHADOW_CANDIDATE" or self.live_transfer:
            raise DiasContractError("ledger authority transfer is not live-authorised")


@dataclass(frozen=True)
class LivenessFunctionBinding:
    function: str
    incumbent: str
    replacement_owner: str
    durable_trigger: str
    reconciliation_route: str
    active: bool = False


@dataclass(frozen=True)
class OwnerLocalLivenessReplacementManifest:
    bindings: tuple[LivenessFunctionBinding, ...]
    generic_supervisor: bool = False
    active: bool = False

    def __post_init__(self) -> None:
        functions = {binding.function for binding in self.bindings}
        if functions != REQUIRED_LIVENESS_FUNCTIONS:
            raise DiasContractError(f"liveness replacement coverage mismatch: {sorted(REQUIRED_LIVENESS_FUNCTIONS - functions)}")
        if self.generic_supervisor or self.active or any(binding.active for binding in self.bindings):
            raise DiasContractError("WP4A owner-local replacements must remain inactive and non-generic")
        if any(binding.replacement_owner not in {"DSAI_VIT_OWNER_LOCAL", "VIT_QUALIFICATION_OWNER_LOCAL"} for binding in self.bindings):
            raise DiasContractError("replacement must be absorbed by an existing owner")
        object.__setattr__(self, "bindings", tuple(sorted(self.bindings, key=lambda binding: binding.function)))

    @property
    def manifest_id(self) -> str:
        return canonical_sha256(asdict(self), role="owner-local-liveness-replacement-manifest/v1")
