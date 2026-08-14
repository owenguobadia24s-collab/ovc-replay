from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import subprocess

from ovc.development.identity import canonical_sha256

TREE_IDENTITY_PROFILE = "git-tree-v1"
PIP_SCHEMA_VERSION = "packet-integration-payload/v0.1"

REASON_CODES = frozenset({
    "CONTENT_CONFLICT", "INPUT_PRECONDITION_MISMATCH", "DEPENDENCY_INVALIDATED",
    "AUTHORITY_INVALIDATED", "GRT_CONFORMANCE_FAIL", "TEST_ASSURANCE_FAIL", "SECURITY_DENY",
    "PLACEMENT_RECOMPUTE_ONLY", "ASSURANCE_RENEWAL_REQUIRED", "PAYLOAD_REBUILD_REQUIRED",
    "AUTHORITY_REVIEW_REQUIRED", "SAFE_BYPASS", "RECOVERY_REORDER", "DEPENDENCY_CHANGE",
    "CONFLICT_RESOLUTION", "EXTERNAL_MAIN_REANCHOR", "FAIRNESS_REBALANCE", "LEASE_UNAVAILABLE",
    "PREDECESSOR_MOVED", "WRITE_REJECTED", "POST_WRITE_TREE_MISMATCH", "POST_WRITE_STATE_UNKNOWN",
    "CONTROLLER_FAILURE", "PHYSICAL_MAIN_DIVERGED", "INTEGRATION_EXCLUSIVITY_BREACH",
    "VIT_LEDGER_INTEGRITY_FAIL", "REPOSITORY_INTEGRITY_INCIDENT", "NO_REPOSITORY_DELTA",
    "WAITING_OPERATOR_AUTHORITY", "RECOVERY_BUDGET_EXHAUSTED", "AVOIDABLE_INTEGRATION_IDLE",
    "FALSE_PARALLEL_VALUE", "SUCCESSOR_UNRESOLVED",
})

PREDECESSOR_REQUIREMENTS = frozenset({
    "PHYSICAL_MATERIALISATION_REQUIRED", "QUALIFIED_VIT_GENERATION_REQUIRED",
    "PAYLOAD_OUTPUT_REQUIRED", "EXECUTION_COMPLETION_REQUIRED", "ORDER_ONLY", "NONE",
})

CONFLICT_CLASSES = frozenset({"COMMUTATIVE", "ORDER_SENSITIVE", "SERIAL_REQUIRED", "MUTUALLY_EXCLUSIVE", "UNKNOWN"})
INVALIDATION_SEVERITIES = frozenset({"PLACEMENT_RECOMPUTE_ONLY", "ASSURANCE_RENEWAL_REQUIRED", "PAYLOAD_REBUILD_REQUIRED", "AUTHORITY_REVIEW_REQUIRED"})

class VitContractError(ValueError):
    pass


def _require(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VitContractError(f"{field_name} is required")
    return value


def _sorted_unique(values: Iterable[str]) -> tuple[str, ...]:
    out = tuple(sorted(set(values)))
    if any(not isinstance(v, str) or not v for v in out):
        raise VitContractError("identity-bearing collections require non-empty strings")
    return out

@dataclass(frozen=True)
class IntegrationAuthorityManifest:
    plan_id: str
    packet_id: str
    gate_id: str
    authority_class: str
    authority_delta: str
    authority_sources: tuple[str, ...]
    reserved_boundaries: tuple[str, ...] = ()
    security_envelope_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("plan_id", "packet_id", "gate_id", "authority_class", "authority_delta"):
            _require(getattr(self, name), name)
        if self.authority_class not in {"AUTO_EXECUTABLE", "OPERATOR_REQUIRED", "HARD_DENY"}:
            raise VitContractError("unknown authority_class")
        if not self.authority_sources:
            raise VitContractError("authority_sources must be source-bound")

    @property
    def logical_id(self) -> str:
        return canonical_sha256(asdict(self))

@dataclass(frozen=True)
class DependencyFrontier:
    dependencies: tuple[str, ...]
    predecessor_requirement: str
    owner_bindings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.predecessor_requirement not in PREDECESSOR_REQUIREMENTS:
            raise VitContractError("unknown predecessor requirement")
        object.__setattr__(self, "dependencies", _sorted_unique(self.dependencies))
        object.__setattr__(self, "owner_bindings", _sorted_unique(self.owner_bindings))

    @property
    def logical_id(self) -> str:
        return canonical_sha256(asdict(self))

@dataclass(frozen=True)
class PacketIntegrationPayload:
    programme_id: str
    packet_id: str
    logical_changes: tuple[Mapping[str, Any], ...]
    authority_manifest: IntegrationAuthorityManifest
    dependency_frontier: DependencyFrontier
    completion_transition: Mapping[str, Any]
    schema_version: str = PIP_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require(self.programme_id, "programme_id")
        _require(self.packet_id, "packet_id")
        if not self.logical_changes:
            raise VitContractError("logical_changes must not be empty")
        if self.packet_id != self.authority_manifest.packet_id:
            raise VitContractError("packet authority mismatch")

    def identity_payload(self) -> Mapping[str, Any]:
        return {
            "schema_version": self.schema_version,
            "programme_id": self.programme_id,
            "packet_id": self.packet_id,
            "logical_changes": list(self.logical_changes),
            "authority_manifest_id": self.authority_manifest.logical_id,
            "dependency_frontier_id": self.dependency_frontier.logical_id,
            "completion_transition": dict(self.completion_transition),
        }

    @property
    def payload_id(self) -> str:
        return canonical_sha256(self.identity_payload())

@dataclass(frozen=True)
class ProspectiveTreeState:
    tree_sha: str
    profile: str = TREE_IDENTITY_PROFILE

    def __post_init__(self) -> None:
        _require(self.tree_sha, "tree_sha")
        if self.profile != TREE_IDENTITY_PROFILE:
            raise VitContractError("unknown tree identity profile")

    @property
    def state_id(self) -> str:
        return canonical_sha256({"profile": self.profile, "tree_sha": self.tree_sha})

@dataclass(frozen=True)
class VirtualIntegrationGeneration:
    train_generation_id: str
    ordinal: int
    predecessor_tree: ProspectiveTreeState
    payload_id: str
    result_tree: ProspectiveTreeState
    authority_manifest_id: str
    dependency_frontier_id: str

    def __post_init__(self) -> None:
        _require(self.train_generation_id, "train_generation_id")
        _require(self.payload_id, "payload_id")
        if self.ordinal < 0:
            raise VitContractError("ordinal must be non-negative")

    @property
    def generation_id(self) -> str:
        return canonical_sha256(asdict(self))

@dataclass(frozen=True)
class ContinuousExecutionMandate:
    programme_id: str
    entry_packet: str
    command: str
    continuation_policy: str
    authority_source: str
    stop_boundary: str | None = None

    def __post_init__(self) -> None:
        if self.command not in {"RUN", "CONTINUE", "RUN_ONLY", "CONTINUE_ONLY", "HOLD"}:
            raise VitContractError("unknown command")
        for name in ("programme_id", "entry_packet", "continuation_policy", "authority_source"):
            _require(getattr(self, name), name)

    @property
    def mandate_id(self) -> str:
        return canonical_sha256(asdict(self))

@dataclass(frozen=True)
class DevelopmentLane:
    lane_id: str
    programme_id: str
    current_packet: str
    build_frontier: str
    payload_frontier: str | None = None
    vit_frontier: str | None = None
    materialisation_frontier: str | None = None

@dataclass(frozen=True)
class AuthorizedMainWriter:
    writer_identity: str
    operation_classes: tuple[str, ...]
    authority_sources: tuple[str, ...]
    active: bool

@dataclass(frozen=True)
class PhysicalMainAnchor:
    commit_sha: str
    tree_sha: str
    authority_frontier: tuple[str, ...] = ()
    policy_frontier: tuple[str, ...] = ()

    @property
    def tree_state(self) -> ProspectiveTreeState:
        return ProspectiveTreeState(self.tree_sha)


def git_tree_sha(repo: str | Path, commitish: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", f"{commitish}^{{tree}}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.stdout.strip()


def assert_tree_equivalent(expected_tree_sha: str, actual_tree_sha: str) -> None:
    _require(expected_tree_sha, "expected_tree_sha")
    _require(actual_tree_sha, "actual_tree_sha")
    if expected_tree_sha != actual_tree_sha:
        raise VitContractError("POST_WRITE_TREE_MISMATCH")


def validate_reason_code(reason_code: str) -> str:
    if reason_code not in REASON_CODES:
        raise VitContractError(f"unknown reason code: {reason_code}")
    return reason_code


def classify_authority(manifest: IntegrationAuthorityManifest) -> str:
    if manifest.authority_class == "HARD_DENY":
        return "DENY"
    if manifest.authority_class == "OPERATOR_REQUIRED":
        return "WAITING_OPERATOR_AUTHORITY"
    if manifest.authority_class == "AUTO_EXECUTABLE" and manifest.authority_delta == "NONE":
        return "ALLOW_PROSPECTIVE_ONLY"
    return "AUTHORITY_REVIEW_REQUIRED"
