from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Iterable

_TYPED = {"PASS","FAIL","BLOCKED_UPSTREAM","NOT_APPLICABLE","STALE","SUPERSEDED","CAPACITY_FAILED"}


def canonical_id(value: object, role: str) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(role.encode("utf-8") + b"\0" + encoded).hexdigest()


@dataclass(frozen=True)
class ShadowPIPRecord:
    programme_id: str
    packet_id: str
    logical_changes: tuple
    authority_manifest_id: str
    dependency_frontier_id: str
    @property
    def pip_id(self) -> str:
        return canonical_id(asdict(self), "ShadowPIPRecord")


@dataclass(frozen=True)
class TypedAssuranceResult:
    assertion_id: str
    state: str
    dependency_frontier_id: str
    evidence_id: str
    required: bool = True
    def __post_init__(self) -> None:
        if self.state not in _TYPED:
            raise ValueError("ASSURANCE_STATE_INVALID")
        if self.required and self.state == "NOT_APPLICABLE":
            raise ValueError("REQUIRED_NOT_APPLICABLE")
    @property
    def result_id(self) -> str:
        return canonical_id(asdict(self), "TypedAssuranceResult")


@dataclass(frozen=True)
class ShadowVITPlacement:
    pip_id: str
    predecessor_tree: str
    result_tree: str
    authority_manifest_id: str
    dependency_frontier_id: str
    ordinal: int = 0
    @property
    def placement_id(self) -> str:
        return canonical_id(asdict(self), "ShadowVITPlacement")


@dataclass(frozen=True)
class ShadowGRTProofBinding:
    result_tree: str
    proof_id: str
    constitution_id: str
    state: str
    def __post_init__(self) -> None:
        if self.state not in {"PASS","FAIL","STALE","NOT_EVALUABLE"}:
            raise ValueError("GRT_STATE_INVALID")
    @property
    def binding_id(self) -> str:
        return canonical_id(asdict(self), "ShadowGRTProofBinding")


@dataclass(frozen=True)
class IntegrationAssuranceGeneration:
    pip_id: str
    placement_id: str
    predecessor_tree: str
    result_tree: str
    authority_manifest_id: str
    dependency_frontier_id: str
    policy_id: str
    evidence_ids: tuple
    statuses: tuple
    supersedes: str | None = None
    @property
    def generation_id(self) -> str:
        return canonical_id(asdict(self), "IntegrationAssuranceGeneration")


@dataclass(frozen=True)
class ShadowIntegrationAdmissionReceipt:
    assurance_generation_id: str
    pip_id: str
    placement_id: str
    result_tree: str
    grt_binding_id: str
    disposition: str
    @property
    def receipt_id(self) -> str:
        return canonical_id(asdict(self), "ShadowIntegrationAdmissionReceipt")


@dataclass(frozen=True)
class ReplayCaseRecord:
    pr_number: int
    source_head: str
    source_base: str
    observed_state: str
    shadow_disposition: str
    invalidation_class: str
    safety_equivalent: bool
    warnings: tuple = ()
    @property
    def record_id(self) -> str:
        return canonical_id(asdict(self), "ReplayCaseRecord")


def classify_main_movement(*, same_pip: bool, same_dependency: bool, same_authority: bool, intersecting_change: bool = False) -> str:
    if same_pip and same_dependency and same_authority and not intersecting_change:
        return "PLACEMENT_RECOMPUTE_ONLY"
    if same_pip and same_authority and not intersecting_change:
        return "ASSURANCE_RENEWAL_REQUIRED"
    if not same_authority:
        return "AUTHORITY_REVIEW_REQUIRED"
    return "PAYLOAD_OR_FRONTIER_REBUILD_REQUIRED"


def evaluate_admission(pip: ShadowPIPRecord, placement: ShadowVITPlacement, assurances: Iterable[TypedAssuranceResult], grt: ShadowGRTProofBinding) -> str:
    if placement.pip_id != pip.pip_id:
        return "BLOCK"
    if placement.authority_manifest_id != pip.authority_manifest_id or placement.dependency_frontier_id != pip.dependency_frontier_id:
        return "BLOCK"
    if grt.result_tree != placement.result_tree or grt.state != "PASS":
        return "BLOCK"
    if any(item.required and item.state != "PASS" for item in assurances):
        return "BLOCK"
    return "SHADOW_READY"


def semantic_dispatch_key(programme_id: str, packet_id: str, pip_id: str) -> str:
    return canonical_id({"programme_id": programme_id, "packet_id": packet_id, "pip_id": pip_id}, "PRVIT_DISPATCH")
