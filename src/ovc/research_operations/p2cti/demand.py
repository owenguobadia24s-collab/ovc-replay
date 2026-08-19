from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

from .identity import control_record_id
from .currentness import evaluate_two_point_currentness
from .sources import resolve_owner_predicate


_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p2cti/P2CTI_OPERATIONAL_VOCABULARY_REGISTRY_v0_1.json"
)
_OWNER_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p2cti/P2CTI_OWNER_SOURCE_REGISTRY_v0_1.json"
)
_CURRENT_GENERATION_BUNDLE_PATH = (
    Path(__file__).resolve().parents[4]
    / "records/research_operations/p2cti/P2CTII_GENERATION_0_v0_1.json"
)
_CURRENT_REFERENCE_SEMANTIC_GENERATION = "v0.1"
_OWNER_REF_FIELDS = {
    "owner_programme", "object_type", "object_id", "semantic_generation", "source_path",
    "content_sha256", "authority_refs", "scientific_payload_copied",
}
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
_OWNER_REGISTRY = json.loads(_OWNER_REGISTRY_PATH.read_text(encoding="utf-8"))


def _canonical_current_context() -> tuple[str, frozenset[str]]:
    try:
        bundle = json.loads(_CURRENT_GENERATION_BUNDLE_PATH.read_text(encoding="utf-8"))
        if bundle.get("schema") != "ovc-p2ctii-generation-zero-bundle/v0.1":
            raise ValueError("current generation bundle schema mismatch")
        if bundle.get("content_sha256") != canonical_sha256(
            {key: value for key, value in bundle.items() if key != "content_sha256"}
        ):
            raise ValueError("current generation bundle content hash mismatch")
        generation = bundle["generation"]
        frontier = bundle["source_frontier"]
        series = bundle["series"]
        currentness = bundle["currentness_evaluation"]
        reproduced = evaluate_two_point_currentness(
            series_id=series["series_id"], generation_id=generation["generation_id"],
            prebuild_frontier=frontier, prepublish_frontier=frontier,
        )
        if reproduced != currentness:
            raise ValueError("current generation bundle does not reproduce two-point currentness")
        if (
            currentness.get("currentness_state") != "CURRENT"
            or currentness.get("completeness_state") != "COMPLETE"
            or generation.get("completeness_state") != "COMPLETE"
            or generation.get("source_frontier_id") != frontier.get("frontier_id")
        ):
            raise ValueError("current generation bundle is not complete and current")
        refs = frozenset(
            canonical_sha256(_exact_ref(entry["source_object_ref"], "current_source_ref"))
            for entry in bundle["entries"]
        )
        return str(frontier["frontier_id"]), refs
    except (KeyError, TypeError, ValueError) as exc:
        raise DemandValidationError(f"canonical current context is invalid: {exc}") from exc


def _exact_ref(raw: Mapping[str, Any], name: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != _OWNER_REF_FIELDS:
        raise DemandValidationError(f"{name} must use the exact closed reference shape")
    if any(
        type(raw[field]) is not str or not raw[field]
        for field in _OWNER_REF_FIELDS - {"authority_refs", "scientific_payload_copied"}
    ):
        raise DemandValidationError(f"{name} values must be non-empty strings")
    digest = raw["content_sha256"]
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise DemandValidationError(f"{name} content_sha256 is invalid")
    refs = raw["authority_refs"]
    if type(refs) is not list or any(type(ref) is not str or not ref for ref in refs):
        raise DemandValidationError(f"{name} authority_refs are invalid")
    if len(refs) != len(set(refs)):
        raise DemandValidationError(f"{name} authority_refs must be unique")
    if raw["scientific_payload_copied"] is not False:
        raise DemandValidationError(f"{name} must remain reference-only")
    normalized = {field: raw[field] for field in sorted(_OWNER_REF_FIELDS)}
    normalized["authority_refs"] = sorted(refs)
    return normalized


def _resolved_owner_ref(
    *, reference: Mapping[str, Any], predicate: str,
    evidence: Sequence[Mapping[str, Any]], name: str, owner_object_type: str | None = None,
) -> dict[str, Any]:
    selected = [
        row for row in evidence
        if isinstance(row, Mapping)
        and row.get("object_type") == (owner_object_type or reference["object_type"])
        and row.get("predicate") == predicate
    ]
    if len(selected) != 1:
        raise DemandValidationError(f"{name} requires exactly one current owner evidence record")
    try:
        resolution = resolve_owner_predicate(
            object_type=owner_object_type or str(reference["object_type"]), predicate=predicate,
            evidence=evidence, owner_registry=_OWNER_REGISTRY,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DemandValidationError(f"{name} owner evidence is invalid: {exc}") from exc
    if resolution["resolution_state"] != "RESOLVED":
        raise DemandValidationError(
            f"{name} owner evidence did not resolve CURRENT: {resolution['resolution_state']}"
        )
    source = resolution["resolved_source"]
    expected = {
        "owner_programme": reference["owner_programme"],
        "source_ref": reference["source_path"],
        "semantic_generation": reference["semantic_generation"],
        "source_sha256": reference["content_sha256"],
        "authority_refs": reference["authority_refs"],
    }
    observed = {field: source[field] for field in expected}
    if observed != expected:
        raise DemandValidationError(f"{name} does not match resolved current owner evidence")
    return resolution


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
    source_owner_evidence: Sequence[Mapping[str, Any]] = (),
    question_owner_evidence: Sequence[Mapping[str, Any]] = (),
    rccr_owner_evidence: Sequence[Mapping[str, Any]] = (),
    research_question_status: str = "UNRESOLVED",
) -> dict[str, Any]:
    if demand_class not in DEMAND_CLASSES:
        raise DemandValidationError(f"unknown demand_class: {demand_class}")
    if status not in {"OPEN", "BLOCKED", "DEFERRED", "RESOLVED", "QUARANTINED", "SUPERSEDED"}:
        raise DemandValidationError(f"unknown demand status: {status}")
    if type(source_frontier_id) is not str or not source_frontier_id.startswith("p2cti:frontier:"):
        raise DemandValidationError("exact source_frontier_id is required")
    source = _exact_ref(source_ref, "source_ref")
    question = _exact_ref(research_question_ref, "research_question_ref")
    current_frontier_id, current_source_refs = _canonical_current_context()
    if source_frontier_id != current_frontier_id:
        raise DemandValidationError("research demand source frontier is not the exact current frontier")
    if canonical_sha256(source) not in current_source_refs:
        raise DemandValidationError("research demand source is not in the exact current generation")
    if source["object_type"] not in {"THEORY_RECORD", "EXTERNAL_THEORY_RECORD", "IN_HOUSE_THEORY_RECORD", "ARCHITECTURE_NEED_SEED"}:
        raise DemandValidationError("research demand source is not a declared theory-record reference class")
    if question["object_type"] not in {"RESEARCH_PROTOCOL", "EC1_OBJECT"}:
        raise DemandValidationError("research question must be an exact Path2 or EC1 owner reference")
    if research_question_status != "CURRENT":
        raise DemandValidationError("research question must carry exact CURRENT owner status")
    if question["semantic_generation"] != _CURRENT_REFERENCE_SEMANTIC_GENERATION:
        raise DemandValidationError("research question generation is not the current v0.1 owner generation")
    _resolved_owner_ref(
        reference=source, predicate="THEORY_IDENTITY", evidence=source_owner_evidence,
        name="source_ref", owner_object_type="THEORY_RECORD",
    )
    question_predicate = (
        "THEORY_BINDING" if question["object_type"] == "RESEARCH_PROTOCOL" else "PATH1_QUESTION"
    )
    _resolved_owner_ref(
        reference=question, predicate=question_predicate, evidence=question_owner_evidence,
        name="research_question_ref",
    )
    if demand_class in _RCCR_OWNED:
        if classification_owner != "RCCR" or rccr_assessment_ref is None:
            raise DemandValidationError(f"{demand_class} classification requires exact RCCR owner evidence")
        assessment = _exact_ref(rccr_assessment_ref, "rccr_assessment_ref")
        if assessment["owner_programme"] != "RCCR" or assessment["object_type"] != "RCCR_ASSESSMENT":
            raise DemandValidationError("gap/capability classification must remain RCCR-owned")
        _resolved_owner_ref(
            reference=assessment, predicate="GAP_CLASS", evidence=rccr_owner_evidence,
            name="rccr_assessment_ref",
        )
    else:
        assessment = None
        if classification_owner not in {None, source["owner_programme"]}:
            raise DemandValidationError("non-RCCR demand classification owner conflicts with source owner")
    identity = {
        "source_ref": source,
        "research_question_ref": question,
        "research_question_status": research_question_status,
        "demand_class": demand_class,
        "rccr_assessment_ref": assessment,
    }
    demand_id = f"p2cti:demand:{canonical_sha256(identity)}"
    payload = {
        "demand_id": demand_id,
        "source_ref": source,
        "research_question_ref": question,
        "research_question_status": research_question_status,
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
