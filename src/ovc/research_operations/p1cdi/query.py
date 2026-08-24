from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

from .demand import assert_non_actuating
from .indexes import optimized_search, reference_search

QUERY_FAMILIES = (
    "SEARCH",
    "GET_DISTINCTION",
    "WHY_HERE",
    "HISTORY_AS_OF",
    "EVIDENCE",
    "CORRESPONDENCE",
    "DEMAND",
    "WHY_BLOCKED",
    "UNBLOCK_PATH",
    "CANDIDATE_PROGRESSION",
    "PORTFOLIO_STATE",
    "NEXT_DISCOVERY_WORK",
)


class P1CDIQueryError(ValueError):
    """A read-only P1CDI query cannot preserve the frozen query contract."""


def _exact_string(value: Any, name: str) -> str:
    if type(value) is not str or not value:
        raise P1CDIQueryError(f"{name} must be a non-empty string")
    return value


def _string_list(value: Sequence[str], name: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise P1CDIQueryError(f"{name} must be a sequence")
    rows = tuple(sorted(_exact_string(item, name) for item in value))
    if len(rows) != len(set(rows)):
        raise P1CDIQueryError(f"{name} must not contain duplicates")
    return rows


def _ordered_string_list(value: Sequence[str], name: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise P1CDIQueryError(f"{name} must be a sequence")
    rows = tuple(_exact_string(item, name) for item in value)
    if len(rows) != len(set(rows)):
        raise P1CDIQueryError(f"{name} must not contain duplicates")
    return rows


def _record_identifier(record: Mapping[str, Any]) -> str:
    for field in (
        "generation_id",
        "series_id",
        "record_id",
        "demand_id",
        "recommendation_id",
        "assessment_id",
        "referral_id",
        "binding_id",
        "event_id",
    ):
        value = record.get(field)
        if type(value) is str and value:
            return value
    return canonical_sha256(record)


def _parse_cutoff(value: str) -> datetime:
    text = _exact_string(value, "as_of")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise P1CDIQueryError("as_of must be an ISO date-time") from exc
    if parsed.tzinfo is None:
        raise P1CDIQueryError("as_of must include a timezone")
    return parsed


def _first_valid(record: Mapping[str, Any]) -> datetime | None:
    value = record.get("first_valid_time")
    if value is None:
        value = record.get("source_first_valid_time")
    if value is None:
        value = record.get("evidence_first_valid_time")
    if value is None:
        return None
    return _parse_cutoff(str(value))


class P1CDIReadOnlyQueryService:
    """Typed query facade over records that already passed WP7 visibility filtering.

    The service never reads protected raw records and owns no persistence, execution,
    authority-transition, candidate-write, or research-orchestration capability.
    """

    def __init__(
        self,
        *,
        visibility_safe_entries: Sequence[Mapping[str, Any]],
        source_frontier_id: str,
        assessment_profile_generation: str,
        currentness_state: str,
        visibility_state: str,
        completeness_state: str,
        warnings: Sequence[str] = (),
        optimized_index: Mapping[str, Any] | None = None,
    ) -> None:
        self._frontier = _exact_string(source_frontier_id, "source_frontier_id")
        self._profile = _exact_string(
            assessment_profile_generation, "assessment_profile_generation"
        )
        self._currentness = _exact_string(currentness_state, "currentness_state")
        self._visibility = _exact_string(visibility_state, "visibility_state")
        self._completeness = _exact_string(completeness_state, "completeness_state")
        self._warnings = _string_list(warnings, "warnings")
        self._entries: tuple[dict[str, Any], ...] = tuple(
            deepcopy(dict(entry)) for entry in visibility_safe_entries
        )
        self._optimized_index = deepcopy(dict(optimized_index)) if optimized_index is not None else None
        self._entry_by_id: dict[str, dict[str, Any]] = {}
        for entry in self._entries:
            if entry.get("record_type") != "P1CDIVisibilitySafeIndexEntry":
                raise P1CDIQueryError("queries accept only WP7 visibility-safe index entries")
            if entry.get("schema_version") != "0.1" or entry.get("authority_effect") != "NONE":
                raise P1CDIQueryError("visibility-safe entry schema or authority is invalid")
            if entry.get("classified_before_indexing") is not True:
                raise PermissionError("visibility classification must precede query indexing")
            entry_id = _exact_string(entry.get("entry_id"), "entry_id")
            if entry_id in self._entry_by_id:
                raise P1CDIQueryError("duplicate visibility-safe entry identity")
            record = entry.get("record")
            if not isinstance(record, Mapping):
                raise P1CDIQueryError("visibility-safe entry requires a projected record")
            if record.get("authority_effect") not in {None, "NONE"}:
                raise PermissionError("queryable record may not carry authority")
            self._entry_by_id[entry_id] = entry

    def _records(self) -> list[dict[str, Any]]:
        return [deepcopy(entry["record"]) for entry in self._entries]

    def _matching_records(self, target: str) -> list[dict[str, Any]]:
        wanted = _exact_string(target, "target")
        fields = (
            "generation_id",
            "series_id",
            "record_id",
            "demand_id",
            "recommendation_id",
            "assessment_id",
            "referral_id",
            "binding_id",
            "event_id",
            "logical_id",
            "left_generation_id",
            "right_generation_id",
            "distinction_generation_id",
            "proposal_id",
            "candidate_id",
        )
        result = []
        for record in self._records():
            if any(record.get(field) == wanted for field in fields):
                result.append(record)
                continue
            for field in ("generation_refs", "source_refs", "demand_refs"):
                refs = record.get(field)
                if isinstance(refs, Sequence) and not isinstance(refs, (str, bytes)) and wanted in refs:
                    result.append(record)
                    break
        return sorted(result, key=lambda record: (_record_identifier(record), canonical_sha256(record)))

    def _envelope(self, family: str, result: Any, *, reason_trace: Sequence[str] = ()) -> dict[str, Any]:
        query_family = _exact_string(family, "query_family")
        if query_family not in QUERY_FAMILIES:
            raise P1CDIQueryError("query_family is outside the frozen WP9 registry")
        reasons = _ordered_string_list(reason_trace, "reason_trace")
        body = {
            "schema": "ovc-p1cdii-query-result/v0.1",
            "query_family": query_family,
            "source_frontier_id": self._frontier,
            "assessment_profile_generation": self._profile,
            "currentness_state": self._currentness,
            "visibility_state": self._visibility,
            "completeness_state": self._completeness,
            "warnings": list(self._warnings),
            "reason_trace": list(reasons),
            "result": deepcopy(result),
            "read_only": True,
            "silent_truncation": "FORBIDDEN",
            "write_controls_present": False,
            "operational_reliance": False,
            "authority_effect": "NONE",
        }
        return {**body, "content_sha256": canonical_sha256(body)}

    def search(self, token: str) -> dict[str, Any]:
        needle = _exact_string(token, "token")
        reference_ids = reference_search(self._entries, needle)
        selected_ids = reference_ids
        if self._optimized_index is not None:
            optimized_ids = optimized_search(self._optimized_index, needle)
            if optimized_ids != reference_ids:
                raise P1CDIQueryError("REFERENCE_OPTIMIZED_DIVERGENCE")
            selected_ids = optimized_ids
        result = [deepcopy(self._entry_by_id[entry_id]["record"]) for entry_id in selected_ids]
        return self._envelope("SEARCH", result, reason_trace=("VISIBILITY_FILTERED_BEFORE_SEARCH",))

    def get_distinction(self, target: str) -> dict[str, Any]:
        records = self._matching_records(target)
        return self._envelope("GET_DISTINCTION", records, reason_trace=("EXACT_VISIBLE_IDENTITY_MATCH",))

    def why_here(self, target: str) -> dict[str, Any]:
        records = self._matching_records(target)
        allowed = (
            "record_type",
            "series_id",
            "generation_id",
            "source_ref",
            "source_refs",
            "profile_id",
            "projection_sha256",
            "owner_semantic_binding",
            "intake_resolution",
            "resolution_state",
            "first_valid_time",
            "source_first_valid_time",
        )
        result = [{key: deepcopy(record[key]) for key in allowed if key in record} for record in records]
        return self._envelope("WHY_HERE", result, reason_trace=("SOURCE_AND_PROFILE_REFERENCES_ONLY",))

    def history_as_of(self, target: str, as_of: str) -> dict[str, Any]:
        cutoff = _parse_cutoff(as_of)
        result = []
        for record in self._matching_records(target):
            first_valid = _first_valid(record)
            if first_valid is None or first_valid <= cutoff:
                result.append(record)
        return self._envelope("HISTORY_AS_OF", result, reason_trace=("FIRST_VALID_CUTOFF_ENFORCED",))

    def evidence(self, target: str) -> dict[str, Any]:
        types = {
            "P1DistinctionEvidenceStateVector",
            "P1DistinctionEvidenceAssessment",
            "P1ReplicationOutcomeRecord",
            "P1NullEvidenceBinding",
            "P1DistinctionContradictionRecord",
            "P1MethodChallengeResult",
        }
        result = [record for record in self._matching_records(target) if record.get("record_type") in types]
        return self._envelope("EVIDENCE", result, reason_trace=("FULL_VISIBLE_VECTOR_NO_SCALAR_SCORE",))

    def correspondence(self, target: str) -> dict[str, Any]:
        result = [
            record
            for record in self._matching_records(target)
            if record.get("record_type") == "P1DistinctionCorrespondenceRecord"
        ]
        return self._envelope("CORRESPONDENCE", result, reason_trace=("TYPED_CORRESPONDENCE_ONLY",))

    def demand(self, target: str) -> dict[str, Any]:
        allowed_types = {
            "P1DiscoveryDemand",
            "P1DemandEligibilityAssessment",
            "P1RCCRReferral",
            "P1StackSufficiencyBinding",
            "P1RCCRReturnProjection",
            "P1DiscoveryWorkRecommendation",
        }
        result = [record for record in self._matching_records(target) if record.get("record_type") in allowed_types]
        return self._envelope("DEMAND", result, reason_trace=("RCCR_REFERENCES_ONE_WAY",))

    def why_blocked(self, target: str) -> dict[str, Any]:
        result = []
        for record in self.demand(target)["result"]:
            projected = {"record_type": record.get("record_type")}
            for field in ("demand_id", "state", "blockers", "reason_codes", "required_information", "rccr_result_ref"):
                if field in record:
                    projected[field] = deepcopy(record[field])
            result.append(projected)
        return self._envelope("WHY_BLOCKED", result, reason_trace=("BLOCKERS_ARE_DESCRIPTIVE_ONLY",))

    def unblock_path(self, target: str) -> dict[str, Any]:
        result = []
        for record in self.demand(target)["result"]:
            projected = {"record_type": record.get("record_type")}
            for field in ("demand_id", "required_information", "rccr_result_ref", "current_stack_result", "reason_codes"):
                if field in record:
                    projected[field] = deepcopy(record[field])
            result.append(projected)
        return self._envelope("UNBLOCK_PATH", result, reason_trace=("NO_CAPABILITY_ACTIVATION",))

    def candidate_progression(self, target: str) -> dict[str, Any]:
        types = {
            "P1ProposalReadinessAssessment",
            "P1CandidateDerivationManifest",
            "P1CandidateProposalRevision",
            "P1DistinctionCandidateBinding",
            "CandidateDispositionBinding",
            "P1CandidateFreezeDispositionProjection",
        }
        result = [record for record in self._matching_records(target) if record.get("record_type") in types]
        return self._envelope("CANDIDATE_PROGRESSION", result, reason_trace=("CANDIDATE_STATES_REMAIN_SEPARATE",))

    def portfolio_state(self) -> dict[str, Any]:
        records = self._records()
        counts = dict(sorted(Counter(str(record.get("record_type", "UNKNOWN")) for record in records).items()))
        return self._envelope(
            "PORTFOLIO_STATE",
            {"visible_record_count": len(records), "record_type_counts": counts},
            reason_trace=("DESCRIPTIVE_VISIBLE_COUNTS_ONLY",),
        )

    def next_discovery_work(self) -> dict[str, Any]:
        recommendations = []
        for record in self._records():
            if record.get("record_type") != "P1DiscoveryWorkRecommendation":
                continue
            assert_non_actuating(record)
            recommendations.append(record)
        recommendations = sorted(
            recommendations,
            key=lambda record: (str(record.get("recommendation_id", "")), canonical_sha256(record)),
        )
        return self._envelope(
            "NEXT_DISCOVERY_WORK",
            recommendations,
            reason_trace=("ADVISORY_ONLY", "NO_ACTUATOR_REACHABILITY"),
        )

    def query(self, family: str, *, target: str | None = None, token: str | None = None, as_of: str | None = None) -> dict[str, Any]:
        query_family = _exact_string(family, "query_family")
        if query_family == "SEARCH":
            return self.search(_exact_string(token, "token"))
        if query_family == "PORTFOLIO_STATE":
            return self.portfolio_state()
        if query_family == "NEXT_DISCOVERY_WORK":
            return self.next_discovery_work()
        wanted = _exact_string(target, "target")
        dispatch = {
            "GET_DISTINCTION": self.get_distinction,
            "WHY_HERE": self.why_here,
            "EVIDENCE": self.evidence,
            "CORRESPONDENCE": self.correspondence,
            "DEMAND": self.demand,
            "WHY_BLOCKED": self.why_blocked,
            "UNBLOCK_PATH": self.unblock_path,
            "CANDIDATE_PROGRESSION": self.candidate_progression,
        }
        if query_family == "HISTORY_AS_OF":
            return self.history_as_of(wanted, _exact_string(as_of, "as_of"))
        handler = dispatch.get(query_family)
        if handler is None:
            raise P1CDIQueryError("query_family is outside the frozen WP9 registry")
        return handler(wanted)


def service_from_bundle(bundle: Mapping[str, Any]) -> P1CDIReadOnlyQueryService:
    if not isinstance(bundle, Mapping):
        raise P1CDIQueryError("query bundle must be an object")
    return P1CDIReadOnlyQueryService(
        visibility_safe_entries=bundle.get("visibility_safe_entries", ()),
        source_frontier_id=bundle.get("source_frontier_id"),
        assessment_profile_generation=bundle.get("assessment_profile_generation"),
        currentness_state=bundle.get("currentness_state"),
        visibility_state=bundle.get("visibility_state"),
        completeness_state=bundle.get("completeness_state"),
        warnings=bundle.get("warnings", ()),
        optimized_index=bundle.get("optimized_index"),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="p1cdi-query", description="Read-only P1CDI WP9 query CLI")
    parser.add_argument("--bundle", required=True, help="Path to a visibility-safe read-only query bundle JSON")
    parser.add_argument("--family", required=True, choices=QUERY_FAMILIES)
    parser.add_argument("--target")
    parser.add_argument("--token")
    parser.add_argument("--as-of")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
        result = service_from_bundle(bundle).query(
            args.family, target=args.target, token=args.token, as_of=args.as_of
        )
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except Exception as exc:
        error = {
            "status": "BLOCK",
            "error_type": type(exc).__name__,
            "message": str(exc),
            "read_only": True,
            "authority_effect": "NONE",
        }
        print(json.dumps(error, sort_keys=True, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
