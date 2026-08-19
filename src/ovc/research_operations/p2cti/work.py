from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

from .identity import control_record_id

_ROOT = Path(__file__).resolve().parents[4]
_OPERATIONAL = json.loads((_ROOT / "registries/research_operations/p2cti/P2CTI_OPERATIONAL_VOCABULARY_REGISTRY_v0_1.json").read_text(encoding="utf-8"))
_REASON = json.loads((_ROOT / "registries/research_operations/p2cti/P2CTI_REASON_CODE_REGISTRY_v0_1.json").read_text(encoding="utf-8"))
_WORK_CLASSES = frozenset(_OPERATIONAL["work_classes"])
_WORK_STATES = frozenset(_OPERATIONAL["work_states"])
_REASON_CODES = frozenset(row["code"] for row in _REASON["reason_codes"])


class WorkValidationError(ValueError):
    pass


def _frontier(value: str) -> str:
    if type(value) is not str or not value.startswith("p2cti:frontier:"):
        raise WorkValidationError("source_frontier_id must be a P2CTI frontier")
    digest = value.rsplit(":", 1)[1]
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise WorkValidationError("source_frontier_id digest is invalid")
    return value


def _strings(values: Sequence[str], field: str, *, allow_empty: bool = False) -> list[str]:
    if type(values) not in (list, tuple) or any(type(v) is not str or not v for v in values):
        raise WorkValidationError(f"{field} must contain non-empty strings")
    result = sorted(set(values))
    if len(result) != len(values):
        raise WorkValidationError(f"{field} must be unique")
    if not result and not allow_empty:
        raise WorkValidationError(f"{field} must not be empty")
    return result


def _reasons(values: Sequence[str]) -> list[str]:
    result = _strings(values, "reason_codes", allow_empty=True)
    unknown = set(result) - _REASON_CODES
    if unknown:
        raise WorkValidationError(f"unknown reason codes: {sorted(unknown)}")
    return result


def _timestamp(value: str) -> str:
    if type(value) is not str or not value:
        raise WorkValidationError("timestamp is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WorkValidationError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise WorkValidationError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _record(*, object_type: str, source_frontier_id: str, identity: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    frontier = _frontier(source_frontier_id)
    record_id = control_record_id(object_type=object_type, source_frontier=frontier, identity_payload=identity)
    body = {
        "schema_family": "P2CTI_CONTROL",
        "schema_version": "0.1",
        "object_type": object_type,
        "record_id": record_id,
        "source_frontier_id": frontier,
        "payload": dict(payload),
        "authority_effect": "NONE",
    }
    return {**body, "content_sha256": canonical_sha256(body)}


def build_work_ticket(
    *,
    source_frontier_id: str,
    ticket_key: str,
    subject_ref: str,
    work_class: str,
    work_state: str,
    authority_refs: Sequence[str],
    created_at: str,
    reason_codes: Sequence[str] = (),
    operator_touch_count: int = 0,
    effort_units: int = 0,
) -> dict[str, Any]:
    if type(ticket_key) is not str or not ticket_key or type(subject_ref) is not str or not subject_ref:
        raise WorkValidationError("ticket_key and subject_ref are required")
    if work_class not in _WORK_CLASSES or work_state not in _WORK_STATES:
        raise WorkValidationError("work_class/work_state is outside the closed registry")
    if type(operator_touch_count) is not int or operator_touch_count < 0 or type(effort_units) is not int or effort_units < 0:
        raise WorkValidationError("telemetry counters must be non-negative integers")
    refs = _strings(authority_refs, "authority_refs")
    reasons = _reasons(reason_codes)
    created = _timestamp(created_at)
    ticket_id = f"p2cti:ticket:{canonical_sha256({'ticket_key': ticket_key, 'subject_ref': subject_ref, 'work_class': work_class})}"
    payload = {
        "ticket_id": ticket_id,
        "subject_ref": subject_ref,
        "work_class": work_class,
        "work_state": work_state,
        "authority_refs": refs,
        "created_at": created,
        "reason_codes": reasons,
        "operator_touch_count": operator_touch_count,
        "effort_units": effort_units,
        "priority_score": None,
        "quota_effect": "NONE",
        "scientific_effect": "NONE",
        "write_activation": False,
        "execution_authority": "NONE",
    }
    return _record(object_type="WORK_TICKET", source_frontier_id=source_frontier_id, identity={"ticket_id": ticket_id}, payload=payload)


def build_deferral(*, source_frontier_id: str, subject_ref: str, reason_codes: Sequence[str], wake_triggers: Sequence[str]) -> dict[str, Any]:
    reasons = _reasons(reason_codes)
    triggers = _strings(wake_triggers, "wake_triggers")
    if type(subject_ref) is not str or not subject_ref:
        raise WorkValidationError("subject_ref is required")
    deferral_id = f"p2cti:deferral:{canonical_sha256({'subject_ref': subject_ref, 'reason_codes': reasons, 'wake_triggers': triggers})}"
    payload = {"deferral_id": deferral_id, "subject_ref": subject_ref, "reason_codes": reasons, "wake_triggers": triggers, "scientific_effect": "NONE", "write_activation": False}
    return _record(object_type="DEFERRAL", source_frontier_id=source_frontier_id, identity={"deferral_id": deferral_id}, payload=payload)


def build_abandonment(*, source_frontier_id: str, subject_ref: str, reason_codes: Sequence[str]) -> dict[str, Any]:
    reasons = _reasons(reason_codes)
    if type(subject_ref) is not str or not subject_ref:
        raise WorkValidationError("subject_ref is required")
    abandonment_id = f"p2cti:abandonment:{canonical_sha256({'subject_ref': subject_ref, 'reason_codes': reasons})}"
    payload = {"abandonment_id": abandonment_id, "subject_ref": subject_ref, "reason_codes": reasons, "preserve_evidence": True, "scientific_deletion": False, "scientific_effect": "NONE", "write_activation": False}
    return _record(object_type="ABANDONMENT", source_frontier_id=source_frontier_id, identity={"abandonment_id": abandonment_id}, payload=payload)


def build_reentry(*, source_frontier_id: str, subject_ref: str, prior_disposition_ref: str, trigger_refs: Sequence[str]) -> dict[str, Any]:
    if any(type(v) is not str or not v for v in (subject_ref, prior_disposition_ref)):
        raise WorkValidationError("subject_ref and prior_disposition_ref are required")
    triggers = _strings(trigger_refs, "trigger_refs")
    reentry_id = f"p2cti:reentry:{canonical_sha256({'subject_ref': subject_ref, 'prior_disposition_ref': prior_disposition_ref, 'trigger_refs': triggers})}"
    payload = {"reentry_id": reentry_id, "subject_ref": subject_ref, "prior_disposition_ref": prior_disposition_ref, "trigger_refs": triggers, "scientific_effect": "NONE", "write_activation": False}
    return _record(object_type="REENTRY", source_frontier_id=source_frontier_id, identity={"reentry_id": reentry_id}, payload=payload)


def project_work_queue(tickets: Sequence[Mapping[str, Any]], *, as_of: str) -> dict[str, Any]:
    cutoff = datetime.fromisoformat(_timestamp(as_of).replace("Z", "+00:00"))
    rows: list[dict[str, Any]] = []
    for ticket in tickets:
        if not isinstance(ticket, Mapping) or ticket.get("object_type") != "WORK_TICKET":
            raise WorkValidationError("queue accepts WORK_TICKET records only")
        expected = canonical_sha256({key: value for key, value in ticket.items() if key != "content_sha256"})
        if ticket.get("content_sha256") != expected:
            raise WorkValidationError("ticket content hash mismatch")
        payload = ticket.get("payload")
        if not isinstance(payload, Mapping):
            raise WorkValidationError("ticket payload is invalid")
        created = datetime.fromisoformat(_timestamp(str(payload.get("created_at", ""))).replace("Z", "+00:00"))
        age = int((cutoff - created).total_seconds())
        if age < 0:
            raise WorkValidationError("queue cutoff precedes ticket creation")
        rows.append({"ticket_id": payload["ticket_id"], "subject_ref": payload["subject_ref"], "work_class": payload["work_class"], "work_state": payload["work_state"], "queue_age_seconds": age, "operator_touch_count": payload.get("operator_touch_count", 0), "effort_units": payload.get("effort_units", 0)})
    rows.sort(key=lambda row: (row["work_state"], row["work_class"], row["ticket_id"]))
    body = {"schema": "ovc-p2ctii-work-queue-projection/v0.1", "as_of": _timestamp(as_of), "rows": rows, "decision_bearing": False, "priority_score": None, "quota_effect": "NONE", "scientific_effect": "NONE", "write_activation": False, "execution_authority": "NONE"}
    return {**body, "content_sha256": canonical_sha256(body)}
