from __future__ import annotations

from typing import Any, Mapping

from .candidate import CandidateExtractionResult, extract_candidate


FORBIDDEN_SOURCE_KEYS = {
    "raw_price",
    "legacy_quality",
    "family_label",
    "downstream_semantics",
    "forecast",
    "probability",
    "trade_signal",
}


def read_synthetic_source(source: Mapping[str, Any], object_pack: Mapping[str, Any]) -> CandidateExtractionResult:
    forbidden = sorted(FORBIDDEN_SOURCE_KEYS.intersection(source))
    if forbidden:
        return CandidateExtractionResult(
            candidate=None,
            computability="NOT_EVALUABLE",
            evidence_status="NOT_EVALUABLE",
            reason_codes=tuple(f"C2P_FORBIDDEN_SOURCE_FIELD:{name}" for name in forbidden),
        )
    return extract_candidate(source, object_pack)
