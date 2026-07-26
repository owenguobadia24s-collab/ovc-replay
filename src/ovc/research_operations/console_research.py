from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from .canonical import canonical_sha256

RESEARCH_SCHEMA = "ovc-research-console-research-projection/v0.3"
CUTOFF_MODES = ("PROSPECTIVE", "REVIEW")
EVIDENCE_ROLES = (
    "SUPPORT",
    "CONTRADICTION",
    "BOUNDARY",
    "NULL",
    "ANOMALY",
    "CENSORED",
    "UNRESOLVED",
)


@dataclass(frozen=True)
class ResearchContext:
    instrument: str
    release_id: str
    clock: str
    price_side: str
    selected_time: str
    cutoff_mode: str = "PROSPECTIVE"

    def normalized(self) -> "ResearchContext":
        mode = str(self.cutoff_mode).upper().strip()
        if mode not in CUTOFF_MODES:
            raise ValueError(f"Unsupported cutoff mode: {self.cutoff_mode}")
        _parse_time(self.selected_time)
        return ResearchContext(
            instrument=str(self.instrument).upper().strip(),
            release_id=str(self.release_id).strip(),
            clock=str(self.clock).upper().strip(),
            price_side=str(self.price_side).upper().strip(),
            selected_time=_canonical_time(self.selected_time),
            cutoff_mode=mode,
        )

    def to_dict(self) -> dict[str, str]:
        return asdict(self.normalized())


@dataclass(frozen=True)
class ResearchWorkspaceProjection:
    schema: str
    source_commit: str
    context: ResearchContext
    summary_status: str
    brief: dict[str, Any]
    replay: tuple[dict[str, Any], ...]
    evidence: tuple[dict[str, Any], ...]
    queue: tuple[dict[str, Any], ...]
    sessions: tuple[dict[str, Any], ...]
    source_refs: tuple[str, ...]
    logical_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "source_commit": self.source_commit,
            "context": self.context.to_dict(),
            "summary_status": self.summary_status,
            "brief": dict(self.brief),
            "replay": [dict(item) for item in self.replay],
            "evidence": [dict(item) for item in self.evidence],
            "queue": [dict(item) for item in self.queue],
            "sessions": [dict(item) for item in self.sessions],
            "source_refs": list(self.source_refs),
            "logical_sha256": self.logical_sha256,
        }


def _parse_time(value: Any) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("Timestamp is required")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _canonical_time(value: Any) -> str:
    return _parse_time(value).isoformat().replace("+00:00", "Z")


def _first_valid_time(record: Mapping[str, Any]) -> datetime:
    return _parse_time(record.get("frozen_at") or record.get("created_at"))


def _record_id(record: Mapping[str, Any]) -> str:
    return str(record.get("record_id") or "UNRESOLVED")


def _record_type(record: Mapping[str, Any]) -> str:
    return str(record.get("record_type") or "UNKNOWN").upper()


def _payload(record: Mapping[str, Any]) -> dict[str, Any]:
    value = record.get("payload", {})
    return dict(value) if isinstance(value, Mapping) else {}


def _release_ids(record: Mapping[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    for ref in record.get("source_release_refs", []) or []:
        if isinstance(ref, Mapping):
            candidate = ref.get("release_id")
        else:
            candidate = ref
        if candidate:
            values.append(str(candidate))
    payload_release = _payload(record).get("release_id")
    if payload_release:
        values.append(str(payload_release))
    return tuple(sorted(set(values)))


def _source_refs(record: Mapping[str, Any]) -> tuple[str, ...]:
    refs = {_record_id(record)}
    refs.update(_release_ids(record))
    for ref in record.get("artifact_refs", []) or []:
        if isinstance(ref, Mapping):
            value = ref.get("artifact_id") or ref.get("path") or ref.get("sha256")
        else:
            value = ref
        if value:
            refs.add(str(value))
    return tuple(sorted(refs))


def _matches_context(record: Mapping[str, Any], context: ResearchContext) -> bool:
    payload = _payload(record)
    fields = {
        "instrument": context.instrument,
        "clock": context.clock,
        "price_side": context.price_side,
    }
    for key, expected in fields.items():
        represented = payload.get(key)
        if represented is not None and str(represented).upper().strip() != expected:
            return False
    releases = _release_ids(record)
    if releases and context.release_id not in releases:
        return False
    return True


def _visibility_phase(record: Mapping[str, Any], cutoff: datetime) -> str:
    return "PRE_CUTOFF" if _first_valid_time(record) <= cutoff else "POST_CUTOFF_REVIEW"


def _visible_record(record: Mapping[str, Any], context: ResearchContext, cutoff: datetime) -> bool:
    if not _matches_context(record, context):
        return False
    if context.cutoff_mode == "PROSPECTIVE" and _first_valid_time(record) > cutoff:
        return False
    return True


def _normalize_evidence_role(value: Any) -> tuple[str, str]:
    candidate = str(value or "UNRESOLVED").upper().strip()
    if candidate in EVIDENCE_ROLES:
        return candidate, "PASS" if candidate not in {"CENSORED", "UNRESOLVED"} else ("CENSORED" if candidate == "CENSORED" else "BLOCK")
    return "UNRESOLVED", "BLOCK"


def _queue_priority(status: str) -> int:
    return {
        "BLOCK": 90,
        "MISSING": 85,
        "CENSORED": 70,
        "WARN": 60,
        "NOT_EVALUATED": 50,
        "PASS": 0,
    }.get(str(status).upper(), 90)


class ResearchWorkspaceProjectionBuilder:
    """Build deterministic Research workspace candidate state.

    RC-WP3-v0.3 implements candidate-only read projections. The console may not
    consume this projection until RC-G3 accepts the contract and a fail-closed
    adapter validates schema, source commit, context and source references.
    """

    def build(
        self,
        *,
        source_commit: str,
        records: Iterable[Mapping[str, Any]],
        context: ResearchContext,
    ) -> ResearchWorkspaceProjection:
        normalized_context = context.normalized()
        if not str(source_commit).strip():
            raise ValueError("source_commit is required")
        cutoff = _parse_time(normalized_context.selected_time)
        ordered = tuple(sorted((dict(item) for item in records), key=lambda item: (_record_type(item), _record_id(item))))
        visible = tuple(item for item in ordered if _visible_record(item, normalized_context, cutoff))

        observations = tuple(item for item in visible if _record_type(item) == "OBSERVATION_SNAPSHOT" and _first_valid_time(item) <= cutoff)
        observation = max(observations, key=lambda item: (_first_valid_time(item), _record_id(item)), default=None)
        observation_id = _record_id(observation) if observation else None

        claims = tuple(
            item
            for item in visible
            if _record_type(item) == "CLAIM_RECORD"
            and (observation_id is None or str(_payload(item).get("observation_id")) == observation_id)
        )
        claim_ids = {_record_id(item) for item in claims}
        realizations = tuple(
            item
            for item in visible
            if _record_type(item) == "REALIZATION_SNAPSHOT"
            and (observation_id is None or str(_payload(item).get("observation_id")) == observation_id)
        )
        evidence_records = tuple(
            item
            for item in visible
            if _record_type(item) == "EVIDENCE_ITEM"
            and (
                observation_id is None
                or str(_payload(item).get("observation_id")) == observation_id
                or str(_payload(item).get("claim_id")) in claim_ids
            )
        )
        sessions = tuple(item for item in visible if _record_type(item) == "RESEARCH_SESSION")
        incidents = tuple(item for item in visible if _record_type(item) == "INCIDENT_RECORD")

        brief = self._brief(observation, claims, normalized_context)
        replay = self._replay(realizations, normalized_context, cutoff)
        evidence = self._evidence(evidence_records, cutoff)
        queue = self._queue(claims, realizations, incidents, ordered, normalized_context, cutoff)
        session_rows = self._sessions(sessions, cutoff)
        summary_status = self._summary_status(observation, queue, evidence)

        source_refs = tuple(sorted({ref for item in visible for ref in _source_refs(item)} | {f"source-commit:{source_commit}"}))
        logical = {
            "schema": RESEARCH_SCHEMA,
            "source_commit": source_commit,
            "context": normalized_context.to_dict(),
            "summary_status": summary_status,
            "brief": brief,
            "replay": list(replay),
            "evidence": list(evidence),
            "queue": list(queue),
            "sessions": list(session_rows),
            "source_refs": list(source_refs),
        }
        return ResearchWorkspaceProjection(
            schema=RESEARCH_SCHEMA,
            source_commit=str(source_commit),
            context=normalized_context,
            summary_status=summary_status,
            brief=brief,
            replay=replay,
            evidence=evidence,
            queue=queue,
            sessions=session_rows,
            source_refs=source_refs,
            logical_sha256=canonical_sha256(logical),
        )

    def _brief(
        self,
        observation: Mapping[str, Any] | None,
        claims: tuple[Mapping[str, Any], ...],
        context: ResearchContext,
    ) -> dict[str, Any]:
        if observation is None:
            return {
                "status": "NOT_MATERIALIZED",
                "observation_id": None,
                "visible_facts": [],
                "unknowns": ["No frozen observation is available at the selected cutoff."],
                "claims": [],
                "source_refs": [],
                "consequence": "No structural or market interpretation is produced.",
            }
        payload = _payload(observation)
        claim_rows = []
        for claim in claims:
            item = _payload(claim)
            claim_rows.append(
                {
                    "claim_id": _record_id(claim),
                    "eligibility": item.get("eligibility"),
                    "discriminator": item.get("discriminator"),
                    "falsifier": item.get("falsifier"),
                    "horizons": item.get("horizons", []),
                    "first_valid_at": _canonical_time(_first_valid_time(claim)),
                    "source_refs": list(_source_refs(claim)),
                }
            )
        return {
            "status": "MATERIALIZED_READ_ONLY",
            "observation_id": _record_id(observation),
            "visible_facts": list(payload.get("visible_facts", [])),
            "unknowns": list(payload.get("unknowns", [])),
            "claims": sorted(claim_rows, key=lambda item: item["claim_id"]),
            "selected_cutoff": context.selected_time,
            "source_refs": list(_source_refs(observation)),
            "consequence": "Research context is descriptive only; no probability, exposure or execution claim is created.",
        }

    def _replay(
        self,
        realizations: tuple[Mapping[str, Any], ...],
        context: ResearchContext,
        cutoff: datetime,
    ) -> tuple[dict[str, Any], ...]:
        rows: list[dict[str, Any]] = []
        for realization in realizations:
            payload = _payload(realization)
            for index, point in enumerate(payload.get("path", []) or []):
                if not isinstance(point, Mapping) or not point.get("time"):
                    continue
                point_time = _parse_time(point["time"])
                if context.cutoff_mode == "PROSPECTIVE" and point_time > cutoff:
                    continue
                rows.append(
                    {
                        "realization_id": _record_id(realization),
                        "observation_id": payload.get("observation_id"),
                        "claim_id": payload.get("claim_id"),
                        "horizon": payload.get("horizon"),
                        "time": _canonical_time(point_time),
                        "value": point.get("value"),
                        "event": point.get("event"),
                        "visibility_phase": "PRE_CUTOFF" if point_time <= cutoff else "POST_CUTOFF_REVIEW",
                        "cutoff_locked": context.cutoff_mode == "PROSPECTIVE",
                        "source_refs": list(_source_refs(realization)),
                        "sequence": index,
                    }
                )
        return tuple(sorted(rows, key=lambda item: (item["time"], item["realization_id"], item["sequence"])))

    def _evidence(
        self,
        records: tuple[Mapping[str, Any], ...],
        cutoff: datetime,
    ) -> tuple[dict[str, Any], ...]:
        rows: list[dict[str, Any]] = []
        for record in records:
            payload = _payload(record)
            role, presentation_status = _normalize_evidence_role(payload.get("evidence_role"))
            rows.append(
                {
                    "evidence_id": _record_id(record),
                    "observation_id": payload.get("observation_id"),
                    "claim_id": payload.get("claim_id"),
                    "realization_id": payload.get("realization_id"),
                    "evidence_role": role,
                    "presentation_status": presentation_status,
                    "admissibility": payload.get("admissibility"),
                    "summary": payload.get("summary"),
                    "visibility_phase": _visibility_phase(record, cutoff),
                    "first_valid_at": _canonical_time(_first_valid_time(record)),
                    "source_refs": list(_source_refs(record)),
                }
            )
        return tuple(sorted(rows, key=lambda item: (item["visibility_phase"], item["evidence_role"], item["evidence_id"])))

    def _queue(
        self,
        claims: tuple[Mapping[str, Any], ...],
        realizations: tuple[Mapping[str, Any], ...],
        incidents: tuple[Mapping[str, Any], ...],
        all_records: tuple[Mapping[str, Any], ...],
        context: ResearchContext,
        cutoff: datetime,
    ) -> tuple[dict[str, Any], ...]:
        rows: list[dict[str, Any]] = []
        realized = {
            (str(_payload(item).get("claim_id")), str(_payload(item).get("horizon")))
            for item in realizations
        }
        for claim in claims:
            payload = _payload(claim)
            for horizon in payload.get("horizons", []) or []:
                if not isinstance(horizon, Mapping) or not horizon.get("due_at"):
                    continue
                due_at = _parse_time(horizon["due_at"])
                key = (_record_id(claim), str(horizon.get("horizon")))
                if due_at <= cutoff and key not in realized:
                    rows.append(
                        {
                            "queue_id": f"DUE::{_record_id(claim)}::{horizon.get('horizon')}",
                            "queue_type": "DUE_REALIZATION",
                            "status": "WARN",
                            "label": f"Realization due for {horizon.get('horizon')}",
                            "due_at": _canonical_time(due_at),
                            "object_id": _record_id(claim),
                            "consequence": "The frozen claim remains incomplete at the selected horizon.",
                            "source_refs": list(_source_refs(claim)),
                        }
                    )
        for realization in realizations:
            payload = _payload(realization)
            censoring = str(payload.get("censoring_state") or "NOT_EVALUATED").upper()
            if censoring not in {"COMPLETE", "AVAILABLE", "NONE"}:
                rows.append(
                    {
                        "queue_id": f"CENSORED::{_record_id(realization)}",
                        "queue_type": "CENSORED_REALIZATION",
                        "status": "CENSORED",
                        "label": "Realization path censored",
                        "due_at": None,
                        "object_id": _record_id(realization),
                        "consequence": "No silent exclusion or completed-path claim is permitted.",
                        "source_refs": list(_source_refs(realization)),
                    }
                )
        for incident in incidents:
            payload = _payload(incident)
            effect = str(payload.get("blocking_effect") or "NONE").upper()
            if effect != "NONE":
                status = "BLOCK" if str(payload.get("severity") or "").upper() in {"BLOCK", "CRITICAL", "ERROR"} else "WARN"
                rows.append(
                    {
                        "queue_id": f"INCIDENT::{_record_id(incident)}",
                        "queue_type": "INCIDENT",
                        "status": status,
                        "label": str(payload.get("incident_code") or "Research incident"),
                        "due_at": None,
                        "object_id": str(payload.get("target_id") or _record_id(incident)),
                        "consequence": str(payload.get("description") or effect),
                        "source_refs": list(_source_refs(incident)),
                    }
                )
        for record in all_records:
            if not _matches_context(record, context):
                continue
            if not _source_refs(record) or _record_id(record) == "UNRESOLVED":
                rows.append(
                    {
                        "queue_id": f"MISSING_SOURCE::{_record_id(record)}",
                        "queue_type": "MISSING_SOURCE",
                        "status": "BLOCK",
                        "label": "Source identity unresolved",
                        "due_at": None,
                        "object_id": _record_id(record),
                        "consequence": "The affected research object cannot be represented as reproducible.",
                        "source_refs": list(_source_refs(record)),
                    }
                )
        return tuple(
            sorted(
                rows,
                key=lambda item: (-_queue_priority(item["status"]), str(item.get("due_at") or ""), item["queue_id"]),
            )
        )

    def _sessions(
        self,
        records: tuple[Mapping[str, Any], ...],
        cutoff: datetime,
    ) -> tuple[dict[str, Any], ...]:
        rows = []
        for record in records:
            payload = _payload(record)
            rows.append(
                {
                    "session_id": _record_id(record),
                    "objective": payload.get("objective"),
                    "research_role": payload.get("research_role"),
                    "session_state": payload.get("session_state"),
                    "objects_reviewed": list(payload.get("objects_reviewed", [])),
                    "visibility_phase": _visibility_phase(record, cutoff),
                    "source_refs": list(_source_refs(record)),
                }
            )
        return tuple(sorted(rows, key=lambda item: item["session_id"]))

    def _summary_status(
        self,
        observation: Mapping[str, Any] | None,
        queue: tuple[dict[str, Any], ...],
        evidence: tuple[dict[str, Any], ...],
    ) -> str:
        if observation is None:
            return "NOT_EVALUATED"
        statuses = [str(item["status"]).upper() for item in queue]
        statuses.extend(str(item["presentation_status"]).upper() for item in evidence)
        if "BLOCK" in statuses or "MISSING" in statuses:
            return "BLOCK"
        if any(value in {"WARN", "CENSORED"} for value in statuses):
            return "WARN"
        return "PASS"
