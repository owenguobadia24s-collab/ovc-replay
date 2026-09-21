from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

REQUIRED_KEYS = ("depth", "anchor", "current_zone", "polarity")
REQUIRED_PROJECTIONS = ("P0", "P1", "P2", "P3")
NON_EVALUABLE = frozenset({"NOT_EVALUABLE", "CENSORED", "QUARANTINED", "SOURCE_BREAK"})


class PmmDfaR1TInvariantError(ValueError):
    pass


@dataclass(frozen=True)
class CandidateMatch:
    candidate_id: str
    state: str
    projection: str
    reason_codes: tuple[str, ...] = ()


def _coordinate(value: Mapping[str, Any]) -> dict[str, Any] | None:
    if any(key not in value or value[key] is None for key in REQUIRED_KEYS):
        return None
    return {key: value[key] for key in REQUIRED_KEYS}


def project_coordinate(value: Mapping[str, Any], projection: str) -> dict[str, Any] | None:
    if projection not in REQUIRED_PROJECTIONS:
        raise PmmDfaR1TInvariantError("only frozen required projections P0-P3 are compiler-admitted")
    coord = _coordinate(value)
    if coord is None:
        return None
    if projection in {"P1", "P3"}:
        coord.pop("polarity")
    if projection in {"P2", "P3"}:
        for key in ("anchor", "current_zone"):
            if coord.get(key) == "INTER_CORE":
                coord[key] = "CORE"
    return coord


def _match_identity(observed: Mapping[str, Any], expected: Mapping[str, Any], projection: str) -> bool | None:
    left = project_coordinate(observed, projection)
    right = project_coordinate(expected, projection)
    if left is None or right is None:
        return None
    return left == right


def classify_node(observed: Mapping[str, Any], candidate: Mapping[str, Any], projection: str = "P0") -> CandidateMatch:
    candidate_id = str(candidate.get("candidate_id", ""))
    if candidate.get("type") != "NODE" or not candidate_id:
        raise PmmDfaR1TInvariantError("NODE candidate required")
    status = str(observed.get("eligibility_state", ""))
    if status in NON_EVALUABLE:
        mapped = "CENSORED" if status == "SOURCE_BREAK" else status
        return CandidateMatch(candidate_id, mapped, projection, (status,))
    verdict = _match_identity(observed, candidate["exact_identity"], projection)
    if verdict is None:
        return CandidateMatch(candidate_id, "NOT_EVALUABLE", projection, ("MISSING_PRIMARY_COORDINATE",))
    return CandidateMatch(candidate_id, "MATCH" if verdict else "NON_MATCH", projection)


def classify_corridor(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    same_live_hypothesis: bool,
    projection: str = "P0",
) -> CandidateMatch:
    candidate_id = str(candidate.get("candidate_id", ""))
    if candidate.get("type") != "CORRIDOR" or not candidate_id:
        raise PmmDfaR1TInvariantError("CORRIDOR candidate required")
    if not same_live_hypothesis:
        return CandidateMatch(candidate_id, "NOT_COMPARABLE", projection, ("DIFFERENT_LIVE_HYPOTHESIS",))
    for observed in (previous, current):
        status = str(observed.get("eligibility_state", ""))
        if status in NON_EVALUABLE:
            mapped = "CENSORED" if status == "SOURCE_BREAK" else status
            return CandidateMatch(candidate_id, mapped, projection, (status,))
    left = _match_identity(previous, candidate["from"], projection)
    right = _match_identity(current, candidate["to"], projection)
    if left is None or right is None:
        return CandidateMatch(candidate_id, "NOT_EVALUABLE", projection, ("MISSING_PRIMARY_COORDINATE",))
    return CandidateMatch(candidate_id, "MATCH" if left and right else "NON_MATCH", projection)
