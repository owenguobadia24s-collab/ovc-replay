from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .canonical import canonical_sha256

MEMBERSHIP_STATES = frozenset({
    "MATCH", "NON_MATCH", "AMBIGUOUS", "NOT_EVALUABLE", "NOT_COMPARABLE",
    "CENSORED", "QUARANTINED", "OUT_OF_SCOPE", "PROCESS_INVALID",
})
CHANGE_RESULTS = frozenset({"SEMANTIC_CHANGE", "EXECUTION_CORRECTION", "BLOCK_UNRESOLVED"})
INFLUENCE_KINDS = frozenset({"ORIGIN", "SEARCH", "DEFINITION", "EXAMPLE", "VOCABULARY", "PARAMETER"})


class CandidateInvariantError(ValueError):
    pass


@dataclass(frozen=True)
class ResearchCandidateSeries:
    series_id: str
    origin_mode: str
    title: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        if not self.series_id or not self.title:
            raise CandidateInvariantError("series_id and title required")
        if self.origin_mode not in {"PATH_1_EMPIRICAL", "PATH_2_THEORY_FORMALISATION"}:
            raise CandidateInvariantError("invalid origin mode")
        if self.authority_effect != "NONE":
            raise CandidateInvariantError("candidate series creation grants no authority")


@dataclass(frozen=True)
class ResearchCandidateGeneration:
    series_id: str
    generation: int
    definition: Mapping[str, Any]
    population_binding: Mapping[str, Any]
    dependency_manifest: Mapping[str, Any]
    first_valid_rule: Mapping[str, Any]
    frozen: bool = True
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        if not self.series_id or self.generation < 1:
            raise CandidateInvariantError("valid series_id/generation required")
        if self.authority_effect != "NONE":
            raise CandidateInvariantError("generation construction grants no authority")

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "series_id": self.series_id,
            "generation": self.generation,
            "definition": dict(self.definition),
            "population_binding": dict(self.population_binding),
            "dependency_manifest": dict(self.dependency_manifest),
            "first_valid_rule": dict(self.first_valid_rule),
        }

    @property
    def semantic_sha256(self) -> str:
        return canonical_sha256(self.semantic_dict())

    @property
    def candidate_generation_id(self) -> str:
        return f"rcg:{self.semantic_sha256}"


@dataclass(frozen=True)
class CandidateOccurrence:
    candidate_generation_id: str
    population_unit_id: str

    def __post_init__(self) -> None:
        if not self.candidate_generation_id or not self.population_unit_id:
            raise CandidateInvariantError("candidate_generation_id and population_unit_id required")

    @property
    def occurrence_id(self) -> str:
        return "rco:" + canonical_sha256({
            "candidate_generation_id": self.candidate_generation_id,
            "population_unit_id": self.population_unit_id,
        })


@dataclass(frozen=True)
class MembershipEntry:
    population_unit_id: str
    state: str
    first_valid_time: str | None = None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.state not in MEMBERSHIP_STATES:
            raise CandidateInvariantError(f"invalid membership state: {self.state}")


@dataclass
class MembershipLedger:
    candidate_generation_id: str
    entries: dict[str, MembershipEntry] = field(default_factory=dict)

    def add(self, entry: MembershipEntry) -> None:
        if entry.population_unit_id in self.entries:
            raise CandidateInvariantError("duplicate population unit")
        self.entries[entry.population_unit_id] = entry

    def assert_complete(self, expected_population_unit_ids: set[str]) -> None:
        actual = set(self.entries)
        if actual != expected_population_unit_ids:
            missing = sorted(expected_population_unit_ids - actual)
            extra = sorted(actual - expected_population_unit_ids)
            raise CandidateInvariantError(f"membership ledger incomplete missing={missing} extra={extra}")

    @property
    def semantic_sha256(self) -> str:
        return canonical_sha256({
            "candidate_generation_id": self.candidate_generation_id,
            "entries": [
                {"population_unit_id": item.population_unit_id, "state": item.state, "first_valid_time": item.first_valid_time, "reason_codes": list(item.reason_codes)}
                for item in sorted(self.entries.values(), key=lambda x: x.population_unit_id)
            ],
        })


@dataclass(frozen=True)
class CandidateChangeAssessment:
    changed_surfaces: tuple[str, ...]
    classification: str
    rationale: str
    successor_generation_required: bool
    authority_effect: str = "NONE"


SEMANTIC_SURFACES = frozenset({
    "definition", "membership", "first_valid_rule", "required_evidence", "dependency_manifest",
    "population_binding", "parameter_pack", "scope", "missingness_semantics",
})
EXECUTION_ONLY_SURFACES = frozenset({"worker_count", "cache_backend", "checkpoint_path", "log_format", "implementation_bugfix_no_semantic_change"})


def assess_candidate_change(changed_surfaces: set[str], *, unresolved: bool = False) -> CandidateChangeAssessment:
    changed = tuple(sorted(changed_surfaces))
    if unresolved:
        return CandidateChangeAssessment(changed, "BLOCK_UNRESOLVED", "Unresolved materiality fails toward a new generation.", True)
    if set(changed) & SEMANTIC_SURFACES:
        return CandidateChangeAssessment(changed, "SEMANTIC_CHANGE", "Change can alter membership, FVT or required evidence/dependencies.", True)
    if set(changed) <= EXECUTION_ONLY_SURFACES:
        return CandidateChangeAssessment(changed, "EXECUTION_CORRECTION", "No meaning-bearing scientific surface changed.", False)
    return CandidateChangeAssessment(changed, "BLOCK_UNRESOLVED", "Unknown change surface is conservatively generation-material.", True)


def merge_series(left: ResearchCandidateSeries, right: ResearchCandidateSeries) -> ResearchCandidateSeries:
    if left.origin_mode != right.origin_mode:
        raise CandidateInvariantError("Path-1 and Path-2 candidate series cannot merge automatically")
    if left.series_id != right.series_id:
        raise CandidateInvariantError("different candidate series cannot merge")
    return left


@dataclass(frozen=True)
class ResearchInfluenceEdge:
    source_mode: str
    target_mode: str
    influence_kind: str
    source_ref: str
    target_ref: str
    observed_at: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        if self.influence_kind not in INFLUENCE_KINDS:
            raise CandidateInvariantError("invalid influence kind")
        if self.authority_effect != "NONE":
            raise CandidateInvariantError("influence evidence cannot grant authority")


@dataclass
class CrossModeExposureLedger:
    edges: list[ResearchInfluenceEdge] = field(default_factory=list)

    def add(self, edge: ResearchInfluenceEdge) -> None:
        self.edges.append(edge)

    def independence_claim_allowed(self, source_ref: str, target_ref: str) -> bool:
        return not any(edge.source_ref == source_ref and edge.target_ref == target_ref for edge in self.edges)

    @property
    def semantic_sha256(self) -> str:
        return canonical_sha256([edge.__dict__ for edge in sorted(self.edges, key=lambda e: (e.source_ref, e.target_ref, e.influence_kind, e.observed_at))])
