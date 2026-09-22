from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA = "ovc-population-allocation-exposure-register/v0.1"
RESEARCH_ROLES = frozenset({"DISCOVERY", "DEVELOPMENT", "VALIDATION"})
EXPOSURE_KINDS = frozenset({"METADATA_ONLY", "PAYLOAD_READ", "DERIVED_ANALYSIS", "RESULT_REVEAL", "OUTCOME_JOIN"})


class PopulationRegisterError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def validate_register(register: Mapping[str, Any]) -> None:
    if register.get("schema") != SCHEMA:
        raise PopulationRegisterError("unsupported population register schema")
    populations = register.get("populations")
    events = register.get("exposure_events")
    if not isinstance(populations, list) or not isinstance(events, list):
        raise PopulationRegisterError("populations and exposure_events must be arrays")
    ids: set[str] = set()
    for pop in populations:
        pid = str(pop.get("population_id", "")).strip()
        gid = str(pop.get("evidence_group_id", "")).strip()
        if not pid or not gid:
            raise PopulationRegisterError("population_id and evidence_group_id required")
        if pid in ids:
            raise PopulationRegisterError(f"duplicate population_id: {pid}")
        ids.add(pid)
        views = pop.get("clock_views")
        if not isinstance(views, list) or not views:
            raise PopulationRegisterError(f"clock_views required: {pid}")
        clocks: set[str] = set()
        for view in views:
            clock = str(view.get("clock", "")).strip()
            if not clock or clock in clocks:
                raise PopulationRegisterError(f"invalid/duplicate clock view for {pid}")
            clocks.add(clock)
    if register.get("population_count") != len(populations):
        raise PopulationRegisterError("population_count mismatch")
    if register.get("clock_view_count") != sum(len(p["clock_views"]) for p in populations):
        raise PopulationRegisterError("clock_view_count mismatch")
    event_ids: set[str] = set()
    for event in events:
        eid = str(event.get("event_id", ""))
        if not eid or eid in event_ids:
            raise PopulationRegisterError("event_id must be unique and non-empty")
        event_ids.add(eid)
        if event.get("population_id") not in ids:
            raise PopulationRegisterError(f"event references unknown population: {event.get('population_id')}")
        if event.get("research_role") not in RESEARCH_ROLES:
            raise PopulationRegisterError("invalid research_role")
        if event.get("exposure_kind") not in EXPOSURE_KINDS:
            raise PopulationRegisterError("invalid exposure_kind")
        if event.get("authority_effect") != "NONE":
            raise PopulationRegisterError("exposure event cannot grant authority")


def make_exposure_event(*, population_id: str, programme_id: str, study_id: str, research_role: str,
                        exposure_kind: str, occurred_at: str, clock: str | None = None,
                        candidate_generation_id: str | None = None, protocol_id: str | None = None,
                        detail_refs: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    role = research_role.upper()
    kind = exposure_kind.upper()
    if role not in RESEARCH_ROLES:
        raise PopulationRegisterError("invalid research_role")
    if kind not in EXPOSURE_KINDS:
        raise PopulationRegisterError("invalid exposure_kind")
    material = {
        "population_id": population_id,
        "programme_id": programme_id,
        "study_id": study_id,
        "research_role": role,
        "exposure_kind": kind,
        "occurred_at": occurred_at,
        "clock": clock,
        "candidate_generation_id": candidate_generation_id,
        "protocol_id": protocol_id,
        "detail_refs": [dict(item) for item in detail_refs],
        "authority_effect": "NONE",
    }
    material["event_id"] = "OVC.POP.EXPOSURE." + canonical_sha256(material)
    return material


def append_exposure_event(register: Mapping[str, Any], event: Mapping[str, Any]) -> dict[str, Any]:
    out = deepcopy(dict(register))
    out["exposure_events"] = list(out.get("exposure_events", [])) + [deepcopy(dict(event))]
    validate_register(out)
    return out


def exposure_summary(register: Mapping[str, Any], population_id: str) -> dict[str, Any]:
    validate_register(register)
    populations = {p["population_id"]: p for p in register["populations"]}
    if population_id not in populations:
        raise PopulationRegisterError("unknown population_id")
    target = populations[population_id]
    group = target["evidence_group_id"]
    related = {p["population_id"] for p in register["populations"] if p["evidence_group_id"] == group}
    events = [e for e in register["exposure_events"] if e["population_id"] in related]
    substantive = [e for e in events if e["exposure_kind"] != "METADATA_ONLY"]
    result_reveals = [e for e in events if e["exposure_kind"] in {"RESULT_REVEAL", "OUTCOME_JOIN"}]
    return {
        "population_id": population_id,
        "evidence_group_id": group,
        "event_count": len(events),
        "substantive_exposure_count": len(substantive),
        "result_reveal_count": len(result_reveals),
        "has_substantive_exposure": bool(substantive),
        "has_result_reveal": bool(result_reveals),
    }


def eligibility(register: Mapping[str, Any], population_id: str, research_role: str) -> dict[str, str]:
    role = research_role.upper()
    if role not in RESEARCH_ROLES:
        raise PopulationRegisterError("invalid research_role")
    summary = exposure_summary(register, population_id)
    if role == "DISCOVERY":
        return {"status": "ELIGIBLE_WITH_DISCLOSURE", "authority_effect": "NONE"}
    if role == "DEVELOPMENT":
        status = (
            "EXPOSURE_RECONCILIATION_REQUIRED"
            if summary["has_substantive_exposure"]
            else "UNKNOWN_PENDING_OPERATOR_AND_OWNER_PREFLIGHT"
        )
        return {"status": status, "authority_effect": "NONE"}
    return {
        "status": "LOCKED_PENDING_EXPLICIT_VALIDATION_AUTHORITY_AND_EXPOSURE_RECONCILIATION",
        "authority_effect": "NONE",
    }
