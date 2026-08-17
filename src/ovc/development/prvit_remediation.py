"""Shadow-first PR/VIT remediation primitives.

The existing live admission path remains authoritative until PRVITR-G-LIVE-SWITCH.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import subprocess
from typing import Iterable, Mapping

from ovc.development.identity import canonical_sha256

TYPED_ASSURANCE_STATES = frozenset({"PASS", "FAIL", "BLOCKED_UPSTREAM", "NOT_APPLICABLE", "STALE", "SUPERSEDED", "CAPACITY_FAILED"})
GRT_STATES = frozenset({"PASS", "FAIL", "STALE", "NOT_EVALUABLE"})
_HEX = frozenset("0123456789abcdef")

class PRVITRemediationError(ValueError):
    pass

def _is_hex(value: str, length: int) -> bool:
    return isinstance(value, str) and len(value) == length and value == value.lower() and all(ch in _HEX for ch in value)

@dataclass(frozen=True)
class TypedAssuranceResult:
    assertion_id: str
    state: str
    dependency_frontier_id: str
    evidence_id: str
    required: bool = True
    source_run_id: str | None = None
    def __post_init__(self) -> None:
        if not self.assertion_id.strip(): raise PRVITRemediationError("ASSURANCE_ASSERTION_ID_MISSING")
        if self.state not in TYPED_ASSURANCE_STATES: raise PRVITRemediationError("ASSURANCE_STATE_INVALID")
        if self.required and self.state == "NOT_APPLICABLE": raise PRVITRemediationError("REQUIRED_ASSURANCE_NOT_APPLICABLE")
        if not _is_hex(self.dependency_frontier_id, 64): raise PRVITRemediationError("ASSURANCE_FRONTIER_INVALID")
        if not self.evidence_id.strip(): raise PRVITRemediationError("ASSURANCE_EVIDENCE_ID_MISSING")
    @property
    def result_id(self) -> str:
        return canonical_sha256(asdict(self), role="PRVITR.TypedAssuranceResult")

@dataclass(frozen=True)
class ImmutableVITLineagePointer:
    lineage_record_id: str
    repository_path: str
    lineage_sha256: str
    schema_version: str = "ovc-vit-routing-lineage/v1"
    def __post_init__(self) -> None:
        if not _is_hex(self.lineage_record_id, 64) or not _is_hex(self.lineage_sha256, 64): raise PRVITRemediationError("LINEAGE_POINTER_HASH_INVALID")
        if not self.repository_path or self.repository_path.startswith("/"): raise PRVITRemediationError("LINEAGE_POINTER_PATH_INVALID")
    @property
    def pointer_id(self) -> str:
        return canonical_sha256(asdict(self), role="PRVITR.ImmutableVITLineagePointer")

@dataclass(frozen=True)
class ShadowPlacement:
    pip_id: str
    predecessor_tree: str
    result_tree: str
    authority_manifest_id: str
    dependency_frontier_id: str
    ordinal: int = 0
    def __post_init__(self) -> None:
        for name, value, length in (("pip", self.pip_id, 64), ("predecessor", self.predecessor_tree, 40), ("result", self.result_tree, 40), ("authority", self.authority_manifest_id, 64), ("frontier", self.dependency_frontier_id, 64)):
            if not _is_hex(value, length): raise PRVITRemediationError(f"PLACEMENT_{name.upper()}_INVALID")
        if self.ordinal < 0: raise PRVITRemediationError("PLACEMENT_ORDINAL_INVALID")
    @property
    def placement_id(self) -> str:
        return canonical_sha256(asdict(self), role="PRVITR.ShadowPlacement")

@dataclass(frozen=True)
class ShadowGRTProof:
    result_tree: str
    proof_id: str
    constitution_id: str
    state: str
    def __post_init__(self) -> None:
        if not _is_hex(self.result_tree, 40): raise PRVITRemediationError("GRT_TREE_INVALID")
        if not self.proof_id.strip() or not self.constitution_id.strip(): raise PRVITRemediationError("GRT_ID_MISSING")
        if self.state not in GRT_STATES: raise PRVITRemediationError("GRT_STATE_INVALID")
    @property
    def proof_binding_id(self) -> str:
        return canonical_sha256(asdict(self), role="PRVITR.ShadowGRTProof")

@dataclass(frozen=True)
class IntegrationAssuranceGeneration:
    pip_id: str
    head_tree: str
    placement_id: str
    predecessor_tree: str
    authority_manifest_id: str
    dependency_frontier_id: str
    policy_id: str
    assurance_result_ids: tuple[str, ...]
    source_run_ids: tuple[str, ...] = ()
    supersedes_generation_id: str | None = None
    def __post_init__(self) -> None:
        for name, value, length in (("pip", self.pip_id, 64), ("head_tree", self.head_tree, 40), ("placement", self.placement_id, 64), ("predecessor", self.predecessor_tree, 40), ("authority", self.authority_manifest_id, 64), ("frontier", self.dependency_frontier_id, 64)):
            if not _is_hex(value, length): raise PRVITRemediationError(f"ASSURANCE_GENERATION_{name.upper()}_INVALID")
        if not self.policy_id.strip() or not self.assurance_result_ids: raise PRVITRemediationError("ASSURANCE_GENERATION_INCOMPLETE")
        if self.supersedes_generation_id is not None and not _is_hex(self.supersedes_generation_id, 64): raise PRVITRemediationError("ASSURANCE_SUPERSEDES_INVALID")
    @property
    def generation_id(self) -> str:
        return canonical_sha256(asdict(self), role="PRVITR.IntegrationAssuranceGeneration")

@dataclass(frozen=True)
class IntegrationAdmissionReceipt:
    assurance_generation_id: str
    pip_id: str
    placement_id: str
    result_tree: str
    grt_proof_binding_id: str
    disposition: str
    reason_codes: tuple[str, ...] = ()
    def __post_init__(self) -> None:
        for name, value, length in (("generation", self.assurance_generation_id, 64), ("pip", self.pip_id, 64), ("placement", self.placement_id, 64), ("tree", self.result_tree, 40), ("grt", self.grt_proof_binding_id, 64)):
            if not _is_hex(value, length): raise PRVITRemediationError(f"ADMISSION_{name.upper()}_INVALID")
        if self.disposition not in {"SHADOW_READY", "BLOCK", "RENEW_PLACEMENT", "AUTHORITY_REVIEW"}: raise PRVITRemediationError("ADMISSION_DISPOSITION_INVALID")
    @property
    def receipt_id(self) -> str:
        return canonical_sha256(asdict(self), role="PRVITR.IntegrationAdmissionReceipt")

@dataclass(frozen=True)
class PlacementRecoveryDecision:
    disposition: str
    payload_rebuild_required: bool
    a0_reuse_allowed: bool
    placement_sensitive_renewal_required: bool
    authority_review_required: bool = False

def classify_main_movement(*, same_pip: bool, dependency_frontier_changed: bool, authority_changed: bool, packet_local_payload_changed: bool = False, intersecting_change: bool = False) -> PlacementRecoveryDecision:
    if authority_changed: return PlacementRecoveryDecision("AUTHORITY_REVIEW_REQUIRED", False, False, True, True)
    if packet_local_payload_changed or not same_pip: return PlacementRecoveryDecision("PAYLOAD_REBUILD_REQUIRED", True, False, True)
    if dependency_frontier_changed or intersecting_change: return PlacementRecoveryDecision("ASSURANCE_RENEWAL_REQUIRED", False, True, True)
    return PlacementRecoveryDecision("PLACEMENT_RECOMPUTE_ONLY", False, True, True)

def evaluate_shadow_admission(*, pip_id: str, placement: ShadowPlacement, assurances: Iterable[TypedAssuranceResult], grt: ShadowGRTProof, authority_manifest_id: str | None = None, dependency_frontier_id: str | None = None) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    if placement.pip_id != pip_id: reasons.append("PIP_PLACEMENT_MISMATCH")
    if authority_manifest_id is not None and placement.authority_manifest_id != authority_manifest_id: reasons.append("PLACEMENT_AUTHORITY_MISMATCH")
    if dependency_frontier_id is not None and placement.dependency_frontier_id != dependency_frontier_id: reasons.append("PLACEMENT_FRONTIER_MISMATCH")
    if grt.result_tree != placement.result_tree: reasons.append("PROSPECTIVE_GRT_TREE_MISMATCH")
    if grt.state != "PASS": reasons.append(f"GRT_{grt.state}")
    for item in assurances:
        if item.required and item.state != "PASS": reasons.append(f"ASSURANCE_{item.assertion_id}_{item.state}")
    return ("SHADOW_READY", ()) if not reasons else ("BLOCK", tuple(reasons))

def semantic_dispatch_key(programme_id: str, packet_id: str, pip_id: str) -> str:
    if not programme_id.strip() or not packet_id.strip() or not _is_hex(pip_id, 64): raise PRVITRemediationError("DISPATCH_IDENTITY_INVALID")
    return canonical_sha256({"programme_id": programme_id, "packet_id": packet_id, "pip_id": pip_id}, role="PRVITR.SemanticDispatchKey")

def ancestry_disposition(*, compare_api_status: int | None, local_git_ancestor: bool | None) -> str:
    if local_git_ancestor is True: return "PASS_GIT_NATIVE"
    if local_git_ancestor is False: return "FAIL_NOT_ANCESTOR"
    return "NOT_EVALUABLE_GIT_PROOF_REQUIRED"

def git_is_ancestor(repo: str | Path, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, descendant], cwd=Path(repo), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if proc.returncode == 0: return True
    if proc.returncode == 1: return False
    raise PRVITRemediationError("GIT_ANCESTRY_PROOF_FAILED")

@dataclass(frozen=True)
class PhysicalMaterialisationReceipt:
    transaction_id: str
    pip_id: str
    qualified_tree: str
    physical_commit: str
    physical_tree: str
    completed_packet: str
    def __post_init__(self) -> None:
        if not self.transaction_id.strip() or not self.completed_packet.strip(): raise PRVITRemediationError("MATERIALISATION_IDENTITY_MISSING")
        if not _is_hex(self.pip_id, 64): raise PRVITRemediationError("MATERIALISATION_PIP_INVALID")
        if not _is_hex(self.qualified_tree, 40) or not _is_hex(self.physical_commit, 40) or not _is_hex(self.physical_tree, 40): raise PRVITRemediationError("MATERIALISATION_GIT_ID_INVALID")
        if self.qualified_tree != self.physical_tree: raise PRVITRemediationError("POST_WRITE_TREE_MISMATCH")
    @property
    def receipt_id(self) -> str:
        return canonical_sha256(asdict(self), role="PRVITR.PhysicalMaterialisationReceipt")

def build_post_materialisation_receipt(**kwargs: str) -> PhysicalMaterialisationReceipt:
    return PhysicalMaterialisationReceipt(**kwargs)

def compare_legacy_and_shadow(*, legacy_allowed: bool, shadow_disposition: str) -> Mapping[str, object]:
    shadow_allowed = shadow_disposition == "SHADOW_READY"
    if legacy_allowed == shadow_allowed: return {"equivalent": True, "classification": "AGREE_ALLOW" if legacy_allowed else "AGREE_BLOCK"}
    if legacy_allowed and not shadow_allowed: return {"equivalent": False, "classification": "SHADOW_SAFER_BLOCK"}
    return {"equivalent": False, "classification": "SHADOW_ONLY_ALLOW_REQUIRES_INVESTIGATION"}
