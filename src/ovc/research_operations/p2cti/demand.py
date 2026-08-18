from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

from .identity import control_record_id


_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p2cti/P2CTI_OPERATIONAL_VOCABULARY_REGISTRY_v0_1.json"
)
_SOURCE_REF_FIELDS = {"owner_programme", "object_type", "object_id", "semantic_generation", "content_sha256"}
_QUESTION_REF_FIELDS = {"owner_programme", "question_id", "semantic_generation", "content_sha256"}
_RCCR_OWNED = {"METHOD_GAP", "INFORMATION_GAP", "DATA_GAP", "ARCHITECTURE_NEED_HYPOTHESIS"}
_FORBIDDEN_SCORE_KEYS = {"truth_score", "value_score", "alpha_score", "probability", "risk", "exposure"}


class DemandValidationError(ValueError):
    """Research demand or advisory work selection violates the WP4 boundary."""


def _load_contract() -> tuple[frozenset[str], frozenset[str]]:
    registry = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    if registry.get("schema") != "ovc-p2cti-operational-vocabulary-registry/v0.1":
        raise RuntimeError("operational vocabulary schema mismatch")
    if registry.get("next_theory_work_authority") != "ADVISORY_ONLY":
        raise RuntimeError("NEXT_THEORY_WORK must remain advisory")
    if registry.get("architecture_need_owner") != "RCCR":
        raise RuntimeError("RCCR must own architecture-need classification")
    if registry.get("method_gap_precedes_architecture_pressure") is not True:
        raise RuntimeError("METHOD_GAP precedence contract missing")
    return frozenset(registry["demand_classes"]), frozenset(registry["work_classes"])


DEMAND_CLASSES, WORK_CLASSES = _load_contract()


def _exact_ref(raw: Mapping[str, Any], fields: set[str], name: str) -> dict[str, str]:
    if not isinstance(raw, Mapping) or set(raw) != fields:
        raise DemandValidationError(f"{name} must use the exact closed reference shape")
    if any(type(raw[field]) is not str or not raw[field] for field in fields):
        raise DemandValidationError(f"{name} values must be non-empty strings")
    digest = raw["content_sha256"]
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise DemandValidationError(f"{name} content_sha256 is invalid")
    return {field: raw[field] for field in sorted(fields)}


def _reject_scores(value: Any) -> None:
    if isinstance(value, Mapping):
        forbidden = set(value).intersection(_FORBIDDEN_SCORE_KEYS)
        if forbidden:
            raise DemandValidationError(f"scalar scientific/market scores are forbidden: {sorted(forbidden)}")
        for item in value.values():
            _reject_scores(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _reject_scores(item)


def build_research_demand(
    *, source_ref: Mapping[str, Any], research_question_ref: Mapping[str, Any],
    demand_class: str, source_frontier_id: str, status: str = "OPEN",
    classification_owner: str | None = None, rccr_assessment_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if demand_class not in DEMAND_CLASSES:
        raise DemandValidationError(f"unknown demand_class: {demand_class}")
    if status not in {"OPEN", "BLOCKED", "DEFERRED", "RESOLVED", "QUARANTINED", "SUPERSEDED"}:
        raise DemandValidationError(f"unknown demand status: {status}")
    source = _exact_ref(source_ref, _SOURCE_REF_FIELDS, "source_ref")
    question = _exact_ref(research_question_ref, _QUESTION_REF_FIELDS, "research_question_ref")
    if demand_class in _RCCR_OWNED:
        if classification_owner != "RCCR" or rccr_assessment_ref is None:
            raise DemandValidationError(f"{demand_class} classification requires exact RCCR owner evidence")
        assessment = _exact_ref(rccr_assessment_ref, _SOURCE_REF_FIELDS, "rccr_assessment_ref")
        if assessment["owner_programme"] != "RCCR" or assessment["object_type"] != "RCCR_ASSESSMENT":
            raise DemandValidationError("gap/capability classification must remain RCCR-owned")
    else:
        assessment = None
        if classification_owner not in {None, source["owner_programme"]}:
            raise DemandValidationError("non-RCCR demand classification owner conflicts with source owner")
    identity = {
        "source_ref": source,
        "research_question_ref": question,
        "demand_class": demand_class,
        "rccr_assessment_ref": assessment,
    }
    demand_id = f"p2cti:demand:{canonical_sha256(identity)}"
    payload = {
        "demand_id": demand_id,
        "source_ref": source,
        "research_question_ref": question,
        "demand_class": demand_class,
        "status": status,
        "classification_owner": "RCCR" if demand_class in _RCCR_OWNED else source["owner_programme"],
        "rccr_assessment_ref": assessment,
        "authority_effect": "NONE",
    }
    _reject_scores(payload)
    body = {
        "schema_family": "P2CTI_CONTROL",
        "schema_version": "0.1",
        "object_type": "RESEARCH_DEMAND",
        "record_id": control_record_id(
            object_type="RESEARCH_DEMAND", source_frontier=source_frontier_id,
            identity_payload={"demand": identity},
        ),
        "source_frontier_id": source_frontier_id,
        "payload": payload,
        "authority_effect": "NONE",
    }
    return {**body, "content_sha256": canonical_sha256(body)}


def next_theory_work(
    *, demand_records: Sequence[Mapping[str, Any]], eligibility: Mapping[str, Mapping[str, Any]],
    authority_refs: Sequence[str], preference_classes: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not authority_refs or any(type(ref) is not str or not ref for ref in authority_refs):
        raise DemandValidationError("authority-aware selection requires explicit authority_refs")
    if not isinstance(demand_records, Sequence) or isinstance(demand_records, (str, bytes)):
        raise DemandValidationError("demand_records must be a sequence")
    preference_classes = dict(preference_classes or {})
    if any(value not in {"PREFERRED", "NORMAL", "DEFERRED_PREFERENCE"} for value in preference_classes.values()):
        raise DemandValidationError("preference classes must use the closed non-scalar vocabulary")
    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    for record in demand_records:
        if record.get("object_type") != "RESEARCH_DEMAND" or not isinstance(record.get("payload"), Mapping):
            raise DemandValidationError("NEXT_THEORY_WORK accepts canonical ResearchDemand records only")
        payload = record["payload"]
        demand_id = payload.get("demand_id")
        state = eligibility.get(demand_id)
        if not isinstance(state, Mapping) or type(state.get("eligible")) is not bool:
            raise DemandValidationError(f"explicit eligibility evidence missing: {demand_id}")
        reason_codes = state.get("reason_codes")
        if type(reason_codes) is not list or any(type(code) is not str or not code for code in reason_codes):
            raise DemandValidationError(f"eligibility reason trace missing: {demand_id}")
        if payload.get("status") != "OPEN" or state["eligible"] is not True:
            excluded.append({"demand_id": demand_id, "reason": "NOT_ELIGIBLE_OR_NOT_OPEN"})
            continue
        rows.append({
            "demand_id": demand_id,
            "demand_class": payload["demand_class"],
            "preference_class": preference_classes.get(demand_id, "NORMAL"),
            "reason_codes": sorted(set(reason_codes)),
            "classification_owner": payload["classification_owner"],
        })
    class_order = {name: 1 for name in DEMAND_CLASSES}
    class_order["METHOD_GAP"] = 0
    class_order["ARCHITECTURE_NEED_HYPOTHESIS"] = 2
    preference_order = {"PREFERRED": 0, "NORMAL": 1, "DEFERRED_PREFERENCE": 2}
    rows.sort(key=lambda row: (
        class_order[row["demand_class"]], preference_order[row["preference_class"]], row["demand_id"]
    ))
    return {
        "schema": "ovc-p2cti-next-theory-work/v0.1",
        "recommendations": rows,
        "excluded": sorted(excluded, key=lambda row: row["demand_id"]),
        "selection_order": "ELIGIBILITY_THEN_METHOD_GAP_ROUTE_THEN_NON_SCALAR_PREFERENCE_THEN_ID",
        "authority_refs": sorted(set(authority_refs)),
        "decision_bearing": False,
        "advisory_only": True,
        "theory_semantic_promotion": False,
        "execution_authority": False,
        "authority_effect": "NONE",
    }
