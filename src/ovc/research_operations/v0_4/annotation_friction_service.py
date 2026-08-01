from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ovc.research_operations.canonical import canonical_json_bytes
from ovc.research_operations.lifecycle import freeze_record
from ovc.research_operations.storage import ResearchWriteService

BOUNDARY_RECORD = "RO4_SEQUENCE_BOUNDARY_ANNOTATION.v0.1"
FRICTION_RECORD = "RO4_C2E_FRICTION_RECORD.v0.1"
REVIEW_RECORD = "RO4_PROSPECTIVE_SEQUENCE_REVIEW.v0.1"
ACK_RECORD = "RO4_SIGNATURE_CONCENTRATION_ACKNOWLEDGEMENT.v0.1"

ALLOWED_RECORD_TYPES = frozenset({BOUNDARY_RECORD, FRICTION_RECORD, REVIEW_RECORD, ACK_RECORD})
ALLOWED_ANNOTATIONS = frozenset({
    "PROPOSED_START", "PROPOSED_END", "CONTINUATION", "SPLIT", "MERGE", "UNCERTAIN", "NOT_A_SEQUENCE",
})
ALLOWED_FRICTION_REASONS = frozenset({
    "BOUNDARY_AMBIGUITY", "SPLIT_MERGE_FRICTION", "CROSS_SCALE_CONTEXT_FRICTION",
    "LONG_PERSISTENCE_FRICTION", "RAPID_ALTERNATION_FRICTION", "TRANSITION_CHAIN_FRICTION",
    "MISSINGNESS_FRICTION", "PRESENTATION_ONLY_FRICTION",
})
ALLOWED_MODES = frozenset({"LIVE_PROSPECTIVE", "TIME_GATED_REPLAY", "NON_EVIDENTIARY_REPLAY"})
ALLOWED_CLOCKS = frozenset({"15M", "2H_A_L"})
ALLOWED_SIDES = frozenset({"BID", "ASK"})
FORBIDDEN_KEYS = frozenset({
    "semantic_label", "episode_id", "episode_authority", "prediction", "probability", "pd_candidate_id",
    "family_id", "promotion", "c2_change", "open_c2e_automatically", "future_payload", "post_cutoff_ids",
    "relabelled_live",
})


class RO4RecordError(ValueError):
    pass


class RO4AuthorityDisabled(RO4RecordError):
    pass


@dataclass(frozen=True)
class RO4AppendAuthority:
    enabled: bool
    status: str
    service_version: str
    accepted_record_types: frozenset[str]
    gate_decision_id: str | None
    concentration_status: str
    acknowledgement_record_id: str | None
    console_write_state: str

    @classmethod
    def from_registry(cls, path: str | Path) -> "RO4AppendAuthority":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        authority = cls(
            enabled=bool(payload.get("enabled")),
            status=str(payload.get("status")),
            service_version=str(payload.get("service_version")),
            accepted_record_types=frozenset(payload.get("accepted_record_types", [])),
            gate_decision_id=payload.get("gate_decision_id"),
            concentration_status=str(payload.get("signature_diversity_status")),
            acknowledgement_record_id=payload.get("acknowledgement_record_id"),
            console_write_state=str(payload.get("console_write_state")),
        )
        authority.validate_registry()
        return authority

    @classmethod
    def synthetic_enabled(cls) -> "RO4AppendAuthority":
        """Fixture-only authority. Production CLI never uses this constructor."""
        return cls(
            enabled=True,
            status="SYNTHETIC_TEST_ONLY",
            service_version="v0.1",
            accepted_record_types=ALLOWED_RECORD_TYPES,
            gate_decision_id="SYNTHETIC.RO4-G4.TEST",
            concentration_status="PASS",
            acknowledgement_record_id=None,
            console_write_state="PROHIBITED",
        )

    def validate_registry(self) -> None:
        if self.service_version != "v0.1":
            raise RO4RecordError("RO4_SERVICE_VERSION_MISMATCH")
        if not self.accepted_record_types or not self.accepted_record_types <= ALLOWED_RECORD_TYPES:
            raise RO4RecordError("RO4_RECORD_ALLOWLIST_INVALID")
        if self.console_write_state != "PROHIBITED":
            raise RO4RecordError("RO4_CONSOLE_WRITE_MUST_REMAIN_PROHIBITED")
        if self.enabled:
            if self.status not in {"APPROVED_RO4_G4", "SYNTHETIC_TEST_ONLY"}:
                raise RO4RecordError("RO4_APPEND_ENABLED_WITHOUT_APPROVED_STATUS")
            if not self.gate_decision_id:
                raise RO4RecordError("RO4_APPEND_ENABLED_WITHOUT_GATE_DECISION")
        if self.concentration_status == "SIGNATURE_CONCENTRATION_WARNING" and not self.acknowledgement_record_id:
            raise RO4RecordError("RO4_CONCENTRATION_ACKNOWLEDGEMENT_REQUIRED")

    def require(self, record_type: str) -> None:
        if not self.enabled:
            raise RO4AuthorityDisabled("RO4_G4_APPEND_AUTHORITY_DISABLED")
        if record_type not in self.accepted_record_types:
            raise RO4RecordError(f"RO4_RECORD_TYPE_NOT_ALLOWED:{record_type}")


def _parse_time(value: str) -> datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise RO4RecordError("RO4_TIME_MUST_BE_TIMEZONE_AWARE")
    return parsed.astimezone(timezone.utc)


def _assert_hash(value: str, name: str) -> None:
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise RO4RecordError(f"RO4_INVALID_SHA256:{name}")


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _assert_no_forbidden_keys(payload: dict[str, Any]) -> None:
    forbidden = FORBIDDEN_KEYS.intersection(_walk_keys(payload))
    if forbidden:
        raise RO4RecordError("RO4_FORBIDDEN_AUTHORITY_FIELD:" + ",".join(sorted(forbidden)))


def _assert_cutoff(cutoff: str, first_valid_times: Iterable[str]) -> None:
    cutoff_dt = _parse_time(cutoff)
    for value in first_valid_times:
        if _parse_time(value) > cutoff_dt:
            raise RO4RecordError(f"RO4_POST_CUTOFF_SOURCE:{value}")


def _assert_sequence(sequence_id: str) -> None:
    if not sequence_id.startswith("RO4.SEQUENCE."):
        raise RO4RecordError("RO4_INVALID_SEQUENCE_ID")


class RO4AnnotationFrictionService:
    """Gate-disabled adapter over the accepted Research Operations v0.1 write/audit service."""

    def __init__(self, *, writes: ResearchWriteService, authority: RO4AppendAuthority):
        self.writes = writes
        self.authority = authority

    def _commit(self, draft: dict[str, Any], *, frozen_at: str, action: str) -> dict[str, Any]:
        """Return the same frozen record for an exact idempotent replay; never create a duplicate."""
        frozen = freeze_record(draft, frozen_at=frozen_at)
        try:
            existing = self.writes.records.read(frozen["record_id"])
        except FileNotFoundError:
            return self.writes.freeze_new(draft, frozen_at=frozen_at, action=action)
        if canonical_json_bytes(existing) != canonical_json_bytes(frozen):
            raise RO4RecordError("RO4_IDEMPOTENCY_COLLISION")
        return existing

    def append_boundary_annotation(
        self,
        *,
        source_sequence_id: str,
        source_release_id: str,
        manifest_sha256: str,
        clock: str,
        side: str,
        member_ids: list[str],
        member_first_valid_times: list[str],
        operation_mode: str,
        admissible_cutoff: str,
        annotation: str,
        rationale: str,
        frozen_at: str,
    ) -> dict[str, Any]:
        self.authority.require(BOUNDARY_RECORD)
        _assert_sequence(source_sequence_id)
        _assert_hash(manifest_sha256, "manifest_sha256")
        if clock not in ALLOWED_CLOCKS or side not in ALLOWED_SIDES:
            raise RO4RecordError("RO4_CLOCK_OR_SIDE_NOT_ALLOWED")
        if operation_mode not in ALLOWED_MODES or annotation not in ALLOWED_ANNOTATIONS:
            raise RO4RecordError("RO4_MODE_OR_ANNOTATION_NOT_ALLOWED")
        if len(member_ids) < 2 or len(member_ids) != len(member_first_valid_times):
            raise RO4RecordError("RO4_MEMBER_ID_TIME_CARDINALITY_MISMATCH")
        if len(rationale) > 2000:
            raise RO4RecordError("RO4_RATIONALE_TOO_LONG")
        _assert_cutoff(admissible_cutoff, member_first_valid_times)
        payload = {
            "source_sequence_id": source_sequence_id,
            "source_release_id": source_release_id,
            "manifest_sha256": manifest_sha256,
            "clock": clock,
            "side": side,
            "member_ids": list(member_ids),
            "member_first_valid_times": list(member_first_valid_times),
            "operation_mode": operation_mode,
            "annotation": annotation,
            "rationale": rationale,
            "record_authority": "APPEND_ONLY_RESEARCH_RECORD_AFTER_RO4_G4",
            "c2_mutation": "DENIED",
            "pd_population_write": "DENIED",
            "semantic_authority": "NONE",
        }
        _assert_no_forbidden_keys(payload)
        source_first_valid = max(member_first_valid_times, key=_parse_time)
        draft = self.writes.base_record(
            record_type=BOUNDARY_RECORD,
            created_at=frozen_at,
            cutoff=admissible_cutoff,
            operator_id=self.writes.operator_id,
            source_release_refs=[{
                "release_id": source_release_id,
                "manifest_sha256": manifest_sha256,
                "first_valid_time": source_first_valid,
            }],
            model_refs=[{
                "object_id": source_sequence_id,
                "object_type": "RO4_SEQUENCE_WINDOW",
                "first_valid_time": source_first_valid,
            }],
            payload=payload,
            lineage={"parent": [source_sequence_id], "derived_from": list(member_ids), "supersedes": None, "adjudicates": []},
        )
        return self._commit(draft, frozen_at=frozen_at, action="ro4.annotate-boundary")

    def append_friction_record(
        self,
        *,
        source_sequence_id: str,
        source_release_id: str,
        source_first_valid_times: list[str],
        operation_mode: str,
        admissible_cutoff: str,
        reason_code: str,
        evidence_refs: list[str],
        counterexample_refs: list[str] | None,
        remediation_ref: str | None,
        rationale: str,
        frozen_at: str,
    ) -> dict[str, Any]:
        self.authority.require(FRICTION_RECORD)
        _assert_sequence(source_sequence_id)
        if operation_mode not in ALLOWED_MODES or reason_code not in ALLOWED_FRICTION_REASONS:
            raise RO4RecordError("RO4_MODE_OR_FRICTION_REASON_NOT_ALLOWED")
        if not evidence_refs or not source_first_valid_times:
            raise RO4RecordError("RO4_FRICTION_REQUIRES_SOURCE_AND_EVIDENCE")
        if len(rationale) > 2000:
            raise RO4RecordError("RO4_RATIONALE_TOO_LONG")
        _assert_cutoff(admissible_cutoff, source_first_valid_times)
        source_first_valid = max(source_first_valid_times, key=_parse_time)
        payload = {
            "source_sequence_id": source_sequence_id,
            "source_release_id": source_release_id,
            "source_first_valid_times": list(source_first_valid_times),
            "operation_mode": operation_mode,
            "reason_code": reason_code,
            "evidence_refs": list(evidence_refs),
            "counterexample_refs": list(counterexample_refs or []),
            "remediation_ref": remediation_ref,
            "rationale": rationale,
            "record_authority": "APPEND_ONLY_RESEARCH_RECORD_AFTER_RO4_G4",
            "c2_mutation": "DENIED",
            "c2e_opening": "DENIED_PENDING_RO4_G6_AND_SEPARATE_PLAN",
            "pd_population_write": "DENIED",
            "semantic_authority": "NONE",
        }
        _assert_no_forbidden_keys(payload)
        draft = self.writes.base_record(
            record_type=FRICTION_RECORD,
            created_at=frozen_at,
            cutoff=admissible_cutoff,
            operator_id=self.writes.operator_id,
            source_release_refs=[{"release_id": source_release_id, "first_valid_time": source_first_valid}],
            model_refs=[{"object_id": source_sequence_id, "object_type": "RO4_SEQUENCE_WINDOW", "first_valid_time": source_first_valid}],
            payload=payload,
            lineage={"parent": [source_sequence_id], "derived_from": list(evidence_refs), "supersedes": None, "adjudicates": []},
        )
        return self._commit(draft, frozen_at=frozen_at, action="ro4.record-friction")

    def append_prospective_review(
        self,
        *,
        source_sequence_id: str,
        source_release_and_manifest: dict[str, Any],
        operation_mode: str,
        admissible_cutoff: str,
        admissible: dict[str, list[str]],
        post_cutoff_hidden_count: int,
        logical_hash: str,
        source_first_valid_times: list[str],
        frozen_at: str,
    ) -> dict[str, Any]:
        self.authority.require(REVIEW_RECORD)
        _assert_sequence(source_sequence_id)
        _assert_hash(logical_hash, "logical_hash")
        if operation_mode not in ALLOWED_MODES or post_cutoff_hidden_count < 0:
            raise RO4RecordError("RO4_INVALID_REVIEW_MODE_OR_COUNT")
        required = {"state_ids", "transition_ids", "sequence_ids"}
        if not required <= set(admissible):
            raise RO4RecordError("RO4_REVIEW_ADMISSIBLE_SET_INCOMPLETE")
        _assert_cutoff(admissible_cutoff, source_first_valid_times)
        source_first_valid = max(source_first_valid_times, key=_parse_time)
        payload = {
            "source_sequence_id": source_sequence_id,
            "source_release_and_manifest": dict(source_release_and_manifest),
            "operation_mode": operation_mode,
            "admissible": {key: list(value) for key, value in admissible.items()},
            "post_cutoff_review": {"hidden_count_only_in_prospective_mode": post_cutoff_hidden_count},
            "logical_hash": logical_hash,
            "source_first_valid_times": list(source_first_valid_times),
            "record_authority": "APPEND_ONLY_RESEARCH_RECORD_AFTER_RO4_G4",
            "replay_to_prospective_translation": "DENIED",
            "validation_consumption": "LOCKED_UNCONSUMED",
        }
        _assert_no_forbidden_keys(payload)
        release_id = str(source_release_and_manifest.get("release_id", ""))
        if not release_id:
            raise RO4RecordError("RO4_REVIEW_RELEASE_ID_REQUIRED")
        draft = self.writes.base_record(
            record_type=REVIEW_RECORD,
            created_at=frozen_at,
            cutoff=admissible_cutoff,
            operator_id=self.writes.operator_id,
            source_release_refs=[{
                "release_id": release_id,
                "manifest_sha256": source_release_and_manifest.get("manifest_sha256"),
                "first_valid_time": source_first_valid,
            }],
            model_refs=[{"object_id": source_sequence_id, "object_type": "RO4_SEQUENCE_WINDOW", "first_valid_time": source_first_valid}],
            payload=payload,
            lineage={"parent": [source_sequence_id], "derived_from": sorted(set(sum((list(v) for v in admissible.values()), []))), "supersedes": None, "adjudicates": []},
        )
        return self._commit(draft, frozen_at=frozen_at, action="ro4.review-sequence")

    def supersede(self, original_id: str, replacement_draft: dict[str, Any], *, frozen_at: str) -> dict[str, Any]:
        original = self.writes.records.read(original_id)
        record_type = str(original["record_type"])
        self.authority.require(record_type)
        if replacement_draft.get("record_type") != record_type:
            raise RO4RecordError("RO4_SUPERSESSION_TYPE_MISMATCH")
        _assert_no_forbidden_keys(replacement_draft.get("payload", {}))
        return self.writes.supersede(original_id, replacement_draft, frozen_at=frozen_at)
