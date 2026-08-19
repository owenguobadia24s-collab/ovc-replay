from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_core import TREE_IDENTITY_PROFILE, VitContractError

QUALIFIED_STATES = frozenset({"QUALIFIED", "READY"})
BLOCKING_STATES = frozenset({"FAILED", "BLOCKED", "QUARANTINED", "WAITING_OPERATOR"})


@dataclass(frozen=True)
class QualifiedPayloadCandidate:
    candidate_id: str
    pr_number: int
    pip_id: str
    head_sha: str
    qualification_state: str
    authority_class: str
    authority_delta: str
    required_dependencies: tuple[str, ...] = ()
    satisfied_dependencies: tuple[str, ...] = ()
    conflict_blockers: tuple[str, ...] = ()
    fairness_rank: int = 0

    def __post_init__(self) -> None:
        if self.pr_number < 1:
            raise VitContractError("VIT_CANDIDATE_PR_INVALID")
        if len(self.pip_id) != 64 or len(self.head_sha) != 40:
            raise VitContractError("VIT_CANDIDATE_IDENTITY_INVALID")
        if self.fairness_rank < 0:
            raise VitContractError("VIT_CANDIDATE_FAIRNESS_INVALID")

    @property
    def missing_dependencies(self) -> tuple[str, ...]:
        satisfied = set(self.satisfied_dependencies)
        return tuple(dep for dep in self.required_dependencies if dep not in satisfied)

    @property
    def runnable(self) -> bool:
        return (
            self.qualification_state in QUALIFIED_STATES
            and self.authority_class == "AUTO_EXECUTABLE"
            and self.authority_delta == "NONE"
            and not self.missing_dependencies
            and not self.conflict_blockers
        )


@dataclass(frozen=True)
class RunnableFrontierDecision:
    selected_candidate_id: str | None
    runnable_candidate_ids: tuple[str, ...]
    blocked: Mapping[str, tuple[str, ...]]


def evaluate_runnable_frontier(candidates: Iterable[QualifiedPayloadCandidate]) -> RunnableFrontierDecision:
    rows = tuple(candidates)
    runnable: list[QualifiedPayloadCandidate] = []
    blocked: dict[str, tuple[str, ...]] = {}
    for row in rows:
        reasons: list[str] = []
        if row.qualification_state not in QUALIFIED_STATES:
            reasons.append(f"STATE:{row.qualification_state}")
        if row.authority_class != "AUTO_EXECUTABLE" or row.authority_delta != "NONE":
            reasons.append("AUTHORITY")
        if row.missing_dependencies:
            reasons.extend(f"DEPENDENCY:{dep}" for dep in row.missing_dependencies)
        if row.conflict_blockers:
            reasons.extend(f"CONFLICT:{item}" for item in row.conflict_blockers)
        if reasons:
            blocked[row.candidate_id] = tuple(reasons)
        else:
            runnable.append(row)

    # Arrival/PR order is a tie-breaker only among runnable candidates. It is
    # never a blocking relationship and never creates a predecessor edge.
    runnable.sort(key=lambda row: (row.fairness_rank, row.pr_number, row.candidate_id))
    return RunnableFrontierDecision(
        selected_candidate_id=runnable[0].candidate_id if runnable else None,
        runnable_candidate_ids=tuple(row.candidate_id for row in runnable),
        blocked=blocked,
    )


@dataclass(frozen=True)
class LateBindingPlacement:
    pip_id: str
    candidate_head_sha: str
    physical_base_sha: str
    physical_base_tree: str
    prospective_tree_sha: str
    authority_manifest_id: str
    dependency_frontier_id: str
    apply_profile: str = "LATE_BINDING_MERGE_TREE_v1"
    tree_profile: str = TREE_IDENTITY_PROFILE

    def __post_init__(self) -> None:
        for value, length, label in (
            (self.pip_id, 64, "PIP"),
            (self.candidate_head_sha, 40, "HEAD"),
            (self.physical_base_sha, 40, "BASE"),
            (self.physical_base_tree, 40, "BASE_TREE"),
            (self.prospective_tree_sha, 40, "RESULT_TREE"),
            (self.authority_manifest_id, 64, "AUTHORITY"),
            (self.dependency_frontier_id, 64, "DEPENDENCY"),
        ):
            if len(value) != length:
                raise VitContractError(f"VIT_LATE_BINDING_{label}_INVALID")
        if self.tree_profile != TREE_IDENTITY_PROFILE:
            raise VitContractError("VIT_LATE_BINDING_TREE_PROFILE_INVALID")

    @property
    def placement_id(self) -> str:
        return canonical_sha256(asdict(self))


@dataclass(frozen=True)
class BaseIndependentAssuranceGeneration:
    pip_id: str
    candidate_head_sha: str
    candidate_head_tree: str
    authority_manifest_id: str
    dependency_frontier_id: str
    policy_id: str
    source_run_ids: tuple[str, ...]

    @property
    def generation_id(self) -> str:
        return canonical_sha256(asdict(self))


def classify_main_movement_impact(
    *,
    payload_changed: bool,
    dependency_frontier_changed: bool,
    authority_changed: bool,
    assurance_dependency_intersection: bool,
) -> str:
    if payload_changed or dependency_frontier_changed:
        return "PAYLOAD_INVALIDATED"
    if authority_changed:
        return "AUTHORITY_REVIEW_REQUIRED"
    if assurance_dependency_intersection:
        return "ASSURANCE_RENEWAL_REQUIRED"
    return "PLACEMENT_ONLY"
