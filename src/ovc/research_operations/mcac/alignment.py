from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ovc.research_orchestration.serialization import logical_sha256

from .contracts import ClockIndexedOccurrenceRef, ComparabilityContext, MCACContractError


class Relation(str, Enum):
    EQUAL_POINT = "EQUAL_POINT"
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    POINT_AT_START = "POINT_AT_START"
    POINT_INSIDE = "POINT_INSIDE"
    POINT_AT_END = "POINT_AT_END"
    STARTED_BY_POINT = "STARTED_BY_POINT"
    CONTAINS_POINT = "CONTAINS_POINT"
    FINISHED_BY_POINT = "FINISHED_BY_POINT"
    EQUAL_INTERVAL = "EQUAL_INTERVAL"
    MEETS = "MEETS"
    MET_BY = "MET_BY"
    STARTS = "STARTS"
    STARTED_BY = "STARTED_BY"
    FINISHES = "FINISHES"
    FINISHED_BY = "FINISHED_BY"
    DURING = "DURING"
    CONTAINS = "CONTAINS"
    OVERLAPS = "OVERLAPS"
    OVERLAPPED_BY = "OVERLAPPED_BY"


INVERSE = {
    Relation.EQUAL_POINT: Relation.EQUAL_POINT, Relation.BEFORE: Relation.AFTER, Relation.AFTER: Relation.BEFORE,
    Relation.POINT_AT_START: Relation.STARTED_BY_POINT, Relation.POINT_INSIDE: Relation.CONTAINS_POINT,
    Relation.POINT_AT_END: Relation.FINISHED_BY_POINT, Relation.STARTED_BY_POINT: Relation.POINT_AT_START,
    Relation.CONTAINS_POINT: Relation.POINT_INSIDE, Relation.FINISHED_BY_POINT: Relation.POINT_AT_END,
    Relation.EQUAL_INTERVAL: Relation.EQUAL_INTERVAL, Relation.MEETS: Relation.MET_BY, Relation.MET_BY: Relation.MEETS,
    Relation.STARTS: Relation.STARTED_BY, Relation.STARTED_BY: Relation.STARTS,
    Relation.FINISHES: Relation.FINISHED_BY, Relation.FINISHED_BY: Relation.FINISHES,
    Relation.DURING: Relation.CONTAINS, Relation.CONTAINS: Relation.DURING,
    Relation.OVERLAPS: Relation.OVERLAPPED_BY, Relation.OVERLAPPED_BY: Relation.OVERLAPS,
}

CONTAINMENT_RELATIONS = frozenset({
    Relation.CONTAINS, Relation.STARTED_BY, Relation.FINISHED_BY, Relation.EQUAL_INTERVAL,
    Relation.STARTED_BY_POINT, Relation.CONTAINS_POINT, Relation.FINISHED_BY_POINT,
})


@dataclass(frozen=True)
class AlignmentResult:
    status: str
    context_id: str
    left_occurrence_id: str
    right_occurrence_id: str
    relation: Relation | None
    overlap_seconds: int
    boundary_touch: bool
    derived_fvt: str
    censoring_state: str
    reason_codes: tuple[str, ...] = ()

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "status": self.status, "context_id": self.context_id,
            "left_occurrence_id": self.left_occurrence_id, "right_occurrence_id": self.right_occurrence_id,
            "relation": self.relation.value if self.relation else None, "overlap_seconds": self.overlap_seconds,
            "boundary_touch": self.boundary_touch, "derived_fvt": self.derived_fvt,
            "censoring_state": self.censoring_state, "reason_codes": list(self.reason_codes),
        }

    @property
    def logical_hash(self) -> str:
        return logical_sha256(self.semantic_dict())


def _relation(left: ClockIndexedOccurrenceRef, right: ClockIndexedOccurrenceRef) -> Relation:
    a, b, c, d = left.start, left.end, right.start, right.end
    lp, rp = left.interval_kind == "POINT", right.interval_kind == "POINT"
    if lp and rp:
        return Relation.EQUAL_POINT if a == c else (Relation.BEFORE if a < c else Relation.AFTER)
    if lp:
        if a < c: return Relation.BEFORE
        if a > d: return Relation.AFTER
        if a == c: return Relation.POINT_AT_START
        if a == d: return Relation.POINT_AT_END
        return Relation.POINT_INSIDE
    if rp:
        return INVERSE[_relation(right, left)]
    if a == c and b == d: return Relation.EQUAL_INTERVAL
    if b < c: return Relation.BEFORE
    if a > d: return Relation.AFTER
    if b == c: return Relation.MEETS
    if a == d: return Relation.MET_BY
    if a == c: return Relation.STARTS if b < d else Relation.STARTED_BY
    if b == d: return Relation.FINISHES if a > c else Relation.FINISHED_BY
    if c < a and b < d: return Relation.DURING
    if a < c and d < b: return Relation.CONTAINS
    return Relation.OVERLAPS if a < c else Relation.OVERLAPPED_BY


def align(context: ComparabilityContext, left: ClockIndexedOccurrenceRef, right: ClockIndexedOccurrenceRef) -> AlignmentResult:
    if context.evaluation_state != "EVALUABLE":
        return AlignmentResult("NOT_EVALUABLE", context.context_id, left.occurrence_ref_id, right.occurrence_ref_id, None, 0, False, context.derived_fvt, "NONE", ("MCAC_FUTURE_DEPENDENCY",))
    if left.clock_coordinate_id != context.left_coordinate.coordinate_id or right.clock_coordinate_id != context.right_coordinate.coordinate_id:
        raise MCACContractError("MCAC_OCCURRENCE_COORDINATE_MISMATCH", context.context_id)
    if left.owner_generation_id != context.left_generation_id or right.owner_generation_id != context.right_generation_id:
        return AlignmentResult("NOT_COMPARABLE", context.context_id, left.occurrence_ref_id, right.occurrence_ref_id, None, 0, False, context.derived_fvt, "NONE", ("MCAC_GENERATION_MISMATCH",))
    if not left.continuity_segment_id or not right.continuity_segment_id:
        return AlignmentResult("NOT_EVALUABLE", context.context_id, left.occurrence_ref_id, right.occurrence_ref_id, None, 0, False, context.derived_fvt, "NONE", ("MCAC_CONTINUITY_SEGMENT_MISSING",))
    if left.source_gap_state != "NONE" or right.source_gap_state != "NONE":
        return AlignmentResult("NOT_COMPARABLE", context.context_id, left.occurrence_ref_id, right.occurrence_ref_id, None, 0, False, context.derived_fvt, "NONE", ("MCAC_SOURCE_GAP",))
    if left.missingness_state != "NONE" or right.missingness_state != "NONE":
        return AlignmentResult("NOT_EVALUABLE", context.context_id, left.occurrence_ref_id, right.occurrence_ref_id, None, 0, False, context.derived_fvt, "NONE", ("MCAC_REQUIRED_INPUT_MISSING",))
    if left.representation_generation_id != context.left_generation_id or right.representation_generation_id != context.right_generation_id:
        return AlignmentResult("NOT_COMPARABLE", context.context_id, left.occurrence_ref_id, right.occurrence_ref_id, None, 0, False, context.derived_fvt, "NONE", ("MCAC_REPRESENTATION_GENERATION_MISMATCH",))
    relation = _relation(left, right)
    overlap = max(0, int((min(left.end, right.end) - max(left.start, right.start)).total_seconds()))
    censored = "PRESENT_BOUNDED" if left.censoring_state != "NONE" or right.censoring_state != "NONE" else "NONE"
    return AlignmentResult("EVALUABLE", context.context_id, left.occurrence_ref_id, right.occurrence_ref_id, relation, overlap, relation in {Relation.MEETS, Relation.MET_BY}, context.derived_fvt, censored)


def temporal_containment(result: AlignmentResult) -> bool:
    return result.status == "EVALUABLE" and result.relation in CONTAINMENT_RELATIONS
