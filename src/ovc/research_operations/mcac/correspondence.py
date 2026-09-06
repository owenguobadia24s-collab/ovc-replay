from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ovc.research_orchestration.serialization import logical_sha256, stable_id

from .contracts import ComparabilityContext, MCACContractError


@dataclass(frozen=True)
class CandidateEdge:
    left_occurrence_id: str
    right_occurrence_id: str
    evidence_hash: str
    score_micros: int
    representation_id: str

    def __post_init__(self) -> None:
        if not self.left_occurrence_id or not self.right_occurrence_id or not self.evidence_hash or not self.representation_id:
            raise MCACContractError("MCAC_CORRESPONDENCE_EDGE_FIELD_REQUIRED", repr(self))
        if not 0 <= self.score_micros <= 1_000_000:
            raise MCACContractError("MCAC_CORRESPONDENCE_SCORE_INVALID", str(self.score_micros))

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "left_occurrence_id": self.left_occurrence_id, "right_occurrence_id": self.right_occurrence_id,
            "evidence_hash": self.evidence_hash, "score_micros": self.score_micros,
            "representation_id": self.representation_id,
        }


@dataclass(frozen=True)
class CorrespondenceRule:
    rule_id: str
    version: str
    left_representation_id: str
    right_representation_id: str
    threshold_micros: int
    assignment_mode: str = "COMPONENT_ALL"
    tie_rule: str = "AMBIGUOUS_NO_TIE_BREAK"
    rule_fvt: str = "1970-01-01T00:00:00Z"

    def __post_init__(self) -> None:
        if self.assignment_mode not in {"COMPONENT_ALL", "ONE_TO_ONE_BEST"}:
            raise MCACContractError("MCAC_ASSIGNMENT_MODE_INVALID", self.assignment_mode)
        if self.tie_rule != "AMBIGUOUS_NO_TIE_BREAK":
            raise MCACContractError("MCAC_TIE_RULE_FORBIDDEN", self.tie_rule)
        if not 0 <= self.threshold_micros <= 1_000_000:
            raise MCACContractError("MCAC_CORRESPONDENCE_THRESHOLD_INVALID", str(self.threshold_micros))

    def semantic_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @property
    def logical_hash(self) -> str:
        return logical_sha256(self.semantic_dict())


@dataclass(frozen=True)
class CorrespondenceGroup:
    cardinality: str
    left_occurrence_ids: tuple[str, ...]
    right_occurrence_ids: tuple[str, ...]
    evidence_hashes: tuple[str, ...]
    group_id: str

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "cardinality": self.cardinality, "left_occurrence_ids": list(self.left_occurrence_ids),
            "right_occurrence_ids": list(self.right_occurrence_ids), "evidence_hashes": list(self.evidence_hashes),
            "group_id": self.group_id,
        }


@dataclass(frozen=True)
class CorrespondenceResult:
    status: str
    context_id: str
    rule_hash: str
    doctrine_hash: str
    groups: tuple[CorrespondenceGroup, ...]
    unmatched_left_ids: tuple[str, ...]
    unmatched_right_ids: tuple[str, ...]
    reason_codes: tuple[str, ...] = ()
    identity_effect: str = "NONE"
    composition_effect: str = "NONE"
    complete: bool = True

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "status": self.status, "context_id": self.context_id, "rule_hash": self.rule_hash,
            "doctrine_hash": self.doctrine_hash,
            "groups": [group.semantic_dict() for group in self.groups],
            "unmatched_left_ids": list(self.unmatched_left_ids), "unmatched_right_ids": list(self.unmatched_right_ids),
            "reason_codes": list(self.reason_codes), "identity_effect": self.identity_effect,
            "composition_effect": self.composition_effect, "complete": self.complete,
        }

    @property
    def logical_hash(self) -> str:
        return logical_sha256(self.semantic_dict())


def _components(edges: tuple[CandidateEdge, ...]) -> tuple[tuple[CandidateEdge, ...], ...]:
    by_left: dict[str, list[CandidateEdge]] = {}
    by_right: dict[str, list[CandidateEdge]] = {}
    for edge in edges:
        by_left.setdefault(edge.left_occurrence_id, []).append(edge)
        by_right.setdefault(edge.right_occurrence_id, []).append(edge)
    unseen = set(edges)
    groups: list[tuple[CandidateEdge, ...]] = []
    while unseen:
        todo = [min(unseen, key=lambda e: (e.left_occurrence_id, e.right_occurrence_id, e.evidence_hash))]
        found: set[CandidateEdge] = set()
        while todo:
            edge = todo.pop()
            if edge in found: continue
            found.add(edge); unseen.discard(edge)
            todo.extend(item for item in by_left[edge.left_occurrence_id] + by_right[edge.right_occurrence_id] if item not in found)
        groups.append(tuple(sorted(found, key=lambda e: (e.left_occurrence_id, e.right_occurrence_id, e.evidence_hash))))
    return tuple(sorted(groups, key=lambda g: (g[0].left_occurrence_id, g[0].right_occurrence_id)))


def _cardinality(left_count: int, right_count: int) -> str:
    if left_count == right_count == 1: return "ONE_TO_ONE"
    if left_count == 1: return "ONE_TO_MANY"
    if right_count == 1: return "MANY_TO_ONE"
    return "MANY_TO_MANY"


def correspond(
    context: ComparabilityContext,
    rule: CorrespondenceRule,
    edges: Iterable[CandidateEdge],
    *,
    all_left_ids: Iterable[str] = (),
    all_right_ids: Iterable[str] = (),
    max_candidate_pairs: int = 2_000_000,
) -> CorrespondenceResult:
    if context.correspondence_rule_id != rule.rule_id:
        raise MCACContractError("MCAC_RULE_CONTEXT_MISMATCH", rule.rule_id)
    values = tuple(sorted(edges, key=lambda e: (e.left_occurrence_id, e.right_occurrence_id, e.evidence_hash)))
    if len(values) > max_candidate_pairs:
        return CorrespondenceResult("CAPACITY_EXCEEDED", context.context_id, rule.logical_hash, context.doctrine_hash, (), (), (), ("MCAC_MAX_CANDIDATE_PAIRS_EXCEEDED",), complete=False)
    seen_pairs: set[tuple[str, str]] = set()
    for edge in values:
        pair = (edge.left_occurrence_id, edge.right_occurrence_id)
        if pair in seen_pairs:
            raise MCACContractError("MCAC_DUPLICATE_CANDIDATE_PAIR", repr(pair))
        seen_pairs.add(pair)
    accepted = tuple(edge for edge in values if edge.score_micros >= rule.threshold_micros)
    left_all, right_all = set(all_left_ids), set(all_right_ids)
    if not accepted:
        return CorrespondenceResult("NO_MATCH", context.context_id, rule.logical_hash, context.doctrine_hash, (), tuple(sorted(left_all)), tuple(sorted(right_all)))
    groups: list[CorrespondenceGroup] = []
    ambiguous = False
    used_left: set[str] = set(); used_right: set[str] = set()
    for component in _components(accepted):
        left = tuple(sorted({edge.left_occurrence_id for edge in component}))
        right = tuple(sorted({edge.right_occurrence_id for edge in component}))
        if rule.assignment_mode == "ONE_TO_ONE_BEST" and (len(left) > 1 or len(right) > 1):
            best = max(edge.score_micros for edge in component)
            winners = tuple(edge for edge in component if edge.score_micros == best)
            if len(winners) != 1:
                ambiguous = True
                continue
            component = winners; left = (winners[0].left_occurrence_id,); right = (winners[0].right_occurrence_id,)
        payload = {"left": list(left), "right": list(right), "evidence": sorted(edge.evidence_hash for edge in component)}
        groups.append(CorrespondenceGroup(_cardinality(len(left), len(right)), left, right, tuple(payload["evidence"]), stable_id("MCAC.GROUP.", payload)))
        used_left.update(left); used_right.update(right)
    status = "AMBIGUOUS" if ambiguous else (groups[0].cardinality if len(groups) == 1 else "MATCHED_GROUPS")
    return CorrespondenceResult(status, context.context_id, rule.logical_hash, context.doctrine_hash, tuple(sorted(groups, key=lambda g: g.group_id)), tuple(sorted(left_all - used_left)), tuple(sorted(right_all - used_right)), ("MCAC_EQUAL_OPTIMUM_ASSIGNMENT",) if ambiguous else ())


def merge_candidate_chunks(chunks: Iterable[Iterable[CandidateEdge]]) -> tuple[CandidateEdge, ...]:
    return tuple(sorted((edge for chunk in chunks for edge in chunk), key=lambda e: (e.left_occurrence_id, e.right_occurrence_id, e.evidence_hash)))
