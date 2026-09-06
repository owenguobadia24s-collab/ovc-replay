from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ovc.research_orchestration.serialization import logical_sha256

from .correspondence import CandidateEdge, merge_candidate_chunks


@dataclass(frozen=True)
class QualificationReceipt:
    status: str
    occurrence_count_left: int
    occurrence_count_right: int
    candidate_pair_count: int
    chunk_size: int
    canonical_hash: str | None
    complete: bool
    reason_codes: tuple[str, ...] = ()


def qualify_candidate_transport(chunks: Iterable[Iterable[CandidateEdge]], *, left_count: int, right_count: int, chunk_size: int, max_per_side: int = 20_000, max_total: int = 40_000, max_pairs: int = 2_000_000, max_chunk: int = 512) -> QualificationReceipt:
    values = merge_candidate_chunks(chunks)
    reasons = []
    if left_count > max_per_side or right_count > max_per_side: reasons.append("MCAC_MAX_PER_SIDE_EXCEEDED")
    if left_count + right_count > max_total: reasons.append("MCAC_MAX_TOTAL_EXCEEDED")
    if len(values) > max_pairs: reasons.append("MCAC_MAX_CANDIDATE_PAIRS_EXCEEDED")
    if chunk_size > max_chunk: reasons.append("MCAC_MAX_CHUNK_EXCEEDED")
    if reasons:
        return QualificationReceipt("CAPACITY_EXCEEDED", left_count, right_count, len(values), chunk_size, None, False, tuple(reasons))
    return QualificationReceipt("PASS", left_count, right_count, len(values), chunk_size, logical_sha256([item.semantic_dict() for item in values]), True)
