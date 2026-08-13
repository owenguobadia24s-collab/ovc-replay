from __future__ import annotations

import copy
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from .canonical import sha256_canonical
from .soi_compat import TOPOLOGY_IDS


class OrganisationEvidenceError(ValueError):
    """Raised when organisation evidence would violate the ESL constitution."""


METRIC_STATUSES = frozenset({"EVALUATED", "NOT_EVALUABLE", "NOT_COMPARABLE", "QUARANTINED"})
CORRESPONDENCE_RELATIONS = frozenset(
    {
        "CORRESPONDS",
        "CONTAINS",
        "SPLITS_INTO",
        "REFINES",
        "OVERLAPS",
        "SHARES_CORE",
        "ADJACENT_TO",
        "CONTRADICTS",
        "INCOMPATIBLE",
        "NO_CORRESPONDENCE",
        "NOT_COMPARABLE",
        "NOT_EVALUABLE",
    }
)
DISAGREEMENT_AXES = frozenset(
    {
        "REPRESENTATION",
        "COMPARISON",
        "METHOD",
        "SENSITIVITY",
        "TOPOLOGY",
        "POPULATION",
        "CHRONOLOGY",
        "BOUNDARY",
    }
)
DISAGREEMENT_STATUSES = frozenset({"OBSERVED", "NOT_OBSERVED", "NOT_EVALUABLE", "QUARANTINED"})
INVARIANT_KINDS = frozenset(
    {
        "MEMBERSHIP",
        "RELATION",
        "COMPONENT",
        "NEIGHBOURHOOD",
        "ORDERING",
        "CORE",
        "OTHER_REGISTERED",
    }
)
SCIENTIFIC_DISPOSITIONS = frozenset(
    {
        "NOT_EVALUATED_RULE_PACK_REQUIRED",
        "SUPPORTED",
        "PARTIALLY_SUPPORTED",
        "MULTIPLE_PLAUSIBLE",
        "VIEW_DEPENDENT",
        "NO_STABLE_VIEW",
        "NO_STABLE_ORGANISATION",
        "NOT_EVALUABLE",
        "UNRESOLVED",
        "QUARANTINED",
    }
)
_PROHIBITED_KEYS = frozenset(
    {
        "future_return",
        "expected_return",
        "mfe",
        "mae",
        "outcome",
        "outcomes",
        "validation_label",
        "validation_result",
        "forecast",
        "probability",
        "confidence_probability",
        "risk",
        "exposure",
        "trade",
        "trading",
        "execution",
        "setup_eligibility",
        "semantic_term",
        "semantic_label",
        "mechanism",
        "cause",
        "causal_claim",
        "intent",
        "admitted_active",
        "canonical_family",
        "canonical_topology",
        "production_selector",
    }
)


def _copy_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _copy_json(child) for key, child in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_copy_json(child) for child in value]
    return copy.deepcopy(value)


def _scan_prohibited(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if key_text.lower() in _PROHIBITED_KEYS:
                raise OrganisationEvidenceError(f"ORG_EVIDENCE_FORBIDDEN_FIELD:{path}.{key_text}")
            _scan_prohibited(child, f"{path}.{key_text}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _scan_prohibited(child, f"{path}[{index}]")


def _require_nonempty(value: Any, code: str) -> str:
    text = str(value or "")
    if not text:
        raise OrganisationEvidenceError(code)
    return text


def _normalise_strings(values: Sequence[Any], code: str) -> list[str]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise OrganisationEvidenceError(code)
    result = sorted({str(value) for value in values})
    if any(not value for value in result):
        raise OrganisationEvidenceError(code)
    return result


def _decimal_ratio(numerator: int, denominator: int) -> str:
    try:
        return format((Decimal(numerator) / Decimal(denominator)).normalize(), "f")
    except (InvalidOperation, ZeroDivisionError) as exc:
        raise OrganisationEvidenceError("ORG_METRIC_DECIMAL_RATIO_INVALID") from exc


def _authority_envelope() -> dict[str, str]:
    return {
        "authority_state": "INACTIVE_CONFORMANCE_ONLY",
        "authority_effect": "NONE",
        "topology_activation": "NONE",
        "method_selection": "NONE",
        "scientific_support_disposition": "NONE",
        "family_promotion": "NONE",
        "semantic_promotion": "NONE",
        "validation_consumption": "LOCKED_UNCONSUMED",
        "publication": "NONE",
        "probability_risk_exposure_execution": "NONE",
    }


def validate_soi_view_result(view: Mapping[str, Any]) -> dict[str, Any]:
    raw = _copy_json(view)
    if not isinstance(raw, Mapping):
        raise OrganisationEvidenceError("ORG_VIEW_OBJECT_REQUIRED")
    _scan_prohibited(raw)
    if raw.get("schema") != "ovc-esl-soi-view-result/v1":
        raise OrganisationEvidenceError("ORG_VIEW_SCHEMA_INVALID")
    view_id = _require_nonempty(raw.get("soi_view_result_id"), "ORG_VIEW_ID_REQUIRED")
    logical_hash = _require_nonempty(raw.get("logical_hash"), "ORG_VIEW_LOGICAL_HASH_REQUIRED")
    payload = dict(raw)
    payload.pop("soi_view_result_id", None)
    payload.pop("logical_hash", None)
    if sha256_canonical(payload) != logical_hash or view_id != "soi1:" + logical_hash:
        raise OrganisationEvidenceError("ORG_VIEW_LOGICAL_HASH_MISMATCH")
    topology = raw.get("topology")
    method = raw.get("method")
    chronology = raw.get("chronology")
    authority = raw.get("authority")
    topology_result = raw.get("topology_result")
    if not all(isinstance(item, Mapping) for item in (topology, method, chronology, authority, topology_result)):
        raise OrganisationEvidenceError("ORG_VIEW_REQUIRED_SURFACE_MISSING")
    topology_id = str(topology.get("topology_id") or "")
    if topology_id not in TOPOLOGY_IDS:
        raise OrganisationEvidenceError("ORG_VIEW_TOPOLOGY_UNKNOWN:" + topology_id)
    if method.get("topology_id") != topology_id:
        raise OrganisationEvidenceError("ORG_VIEW_METHOD_TOPOLOGY_MISMATCH")
    if method.get("method_topology_separation") != "EXPLICIT":
        raise OrganisationEvidenceError("ORG_VIEW_METHOD_TOPOLOGY_SEPARATION_REQUIRED")
    if authority != _authority_envelope():
        raise OrganisationEvidenceError("ORG_VIEW_AUTHORITY_ENVELOPE_INVALID")
    _require_nonempty(chronology.get("first_valid_time"), "ORG_VIEW_FVT_REQUIRED")
    _require_nonempty(chronology.get("evaluation_cutoff"), "ORG_VIEW_CUTOFF_REQUIRED")
    denominators = topology_result.get("denominators")
    if not isinstance(denominators, Mapping):
        raise OrganisationEvidenceError("ORG_VIEW_DENOMINATORS_REQUIRED")
    for name, value in denominators.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise OrganisationEvidenceError("ORG_VIEW_DENOMINATOR_INVALID:" + str(name))
    return dict(raw)


def build_metric_record(
    *,
    view_result: Mapping[str, Any],
    metric_id: str,
    eligible_universe_id: str,
    numerator: int,
    denominator: int,
    exclusions: Sequence[Any] = (),
    missingness: Sequence[Any] = (),
    status: str | None = None,
) -> dict[str, Any]:
    view = validate_soi_view_result(view_result)
    metric = _require_nonempty(metric_id, "ORG_METRIC_ID_REQUIRED")
    universe = _require_nonempty(eligible_universe_id, "ORG_METRIC_UNIVERSE_REQUIRED")
    if not isinstance(numerator, int) or isinstance(numerator, bool) or numerator < 0:
        raise OrganisationEvidenceError("ORG_METRIC_NUMERATOR_INVALID")
    if not isinstance(denominator, int) or isinstance(denominator, bool) or denominator < 0:
        raise OrganisationEvidenceError("ORG_METRIC_DENOMINATOR_INVALID")
    if numerator > denominator:
        raise OrganisationEvidenceError("ORG_METRIC_NUMERATOR_EXCEEDS_DENOMINATOR")
    metric_status = status or ("NOT_EVALUABLE" if denominator == 0 else "EVALUATED")
    if metric_status not in METRIC_STATUSES:
        raise OrganisationEvidenceError("ORG_METRIC_STATUS_INVALID:" + metric_status)
    if denominator == 0 and metric_status != "NOT_EVALUABLE":
        raise OrganisationEvidenceError("ORG_METRIC_UNDEFINED_DENOMINATOR_MUST_ABSTAIN")
    if denominator > 0 and metric_status == "EVALUATED":
        value_decimal: str | None = _decimal_ratio(numerator, denominator)
    else:
        value_decimal = None
    chronology = view["chronology"]
    payload = {
        "schema": "ovc-esl-organisation-metric-record/v1",
        "metric_id": metric,
        "view_result_id": view["soi_view_result_id"],
        "topology_id": view["topology"]["topology_id"],
        "eligible_universe_id": universe,
        "numerator": numerator,
        "denominator": denominator,
        "value_decimal": value_decimal,
        "status": metric_status,
        "exclusions": _normalise_strings(exclusions, "ORG_METRIC_EXCLUSIONS_INVALID"),
        "missingness": _normalise_strings(missingness, "ORG_METRIC_MISSINGNESS_INVALID"),
        "first_valid_time": chronology["first_valid_time"],
        "evaluation_cutoff": chronology["evaluation_cutoff"],
        "authority": _authority_envelope(),
    }
    logical_hash = sha256_canonical(payload)
    return {**payload, "metric_record_id": "orgm1:" + logical_hash, "logical_hash": logical_hash}


def build_correspondence_edge(
    *,
    subject_view_result: Mapping[str, Any],
    object_view_result: Mapping[str, Any],
    relation: str,
    evidence_refs: Sequence[Any],
    directionality: str = "DIRECTIONAL",
) -> dict[str, Any]:
    subject = validate_soi_view_result(subject_view_result)
    obj = validate_soi_view_result(object_view_result)
    relation_id = str(relation)
    if relation_id not in CORRESPONDENCE_RELATIONS:
        raise OrganisationEvidenceError("ORG_CORRESPONDENCE_RELATION_INVALID:" + relation_id)
    if subject["soi_view_result_id"] == obj["soi_view_result_id"]:
        raise OrganisationEvidenceError("ORG_CORRESPONDENCE_SELF_EDGE_FORBIDDEN")
    if directionality not in {"DIRECTIONAL", "SYMMETRIC"}:
        raise OrganisationEvidenceError("ORG_CORRESPONDENCE_DIRECTIONALITY_INVALID")
    first_valid_time = max(
        str(subject["chronology"]["first_valid_time"]),
        str(obj["chronology"]["first_valid_time"]),
    )
    evaluation_cutoff = min(
        str(subject["chronology"]["evaluation_cutoff"]),
        str(obj["chronology"]["evaluation_cutoff"]),
    )
    payload = {
        "schema": "ovc-esl-organisation-correspondence-edge/v1",
        "subject_view_result_id": subject["soi_view_result_id"],
        "object_view_result_id": obj["soi_view_result_id"],
        "relation": relation_id,
        "directionality": directionality,
        "evidence_refs": _normalise_strings(evidence_refs, "ORG_CORRESPONDENCE_EVIDENCE_REQUIRED"),
        "identity_merge": "FORBIDDEN",
        "first_valid_time": first_valid_time,
        "evaluation_cutoff": evaluation_cutoff,
        "authority": _authority_envelope(),
    }
    if not payload["evidence_refs"]:
        raise OrganisationEvidenceError("ORG_CORRESPONDENCE_EVIDENCE_REQUIRED")
    logical_hash = sha256_canonical(payload)
    return {**payload, "correspondence_edge_id": "orgc1:" + logical_hash, "logical_hash": logical_hash}


def build_disagreement_record(
    *,
    view_result_ids: Sequence[Any],
    axis: str,
    status: str,
    evidence_refs: Sequence[Any],
    first_valid_time: str,
    evaluation_cutoff: str,
) -> dict[str, Any]:
    views = _normalise_strings(view_result_ids, "ORG_DISAGREEMENT_VIEW_IDS_INVALID")
    if len(views) < 2:
        raise OrganisationEvidenceError("ORG_DISAGREEMENT_REQUIRES_MULTIPLE_VIEWS")
    axis_id = str(axis)
    if axis_id not in DISAGREEMENT_AXES:
        raise OrganisationEvidenceError("ORG_DISAGREEMENT_AXIS_INVALID:" + axis_id)
    status_id = str(status)
    if status_id not in DISAGREEMENT_STATUSES:
        raise OrganisationEvidenceError("ORG_DISAGREEMENT_STATUS_INVALID:" + status_id)
    refs = _normalise_strings(evidence_refs, "ORG_DISAGREEMENT_EVIDENCE_INVALID")
    if status_id == "OBSERVED" and not refs:
        raise OrganisationEvidenceError("ORG_DISAGREEMENT_OBSERVED_REQUIRES_EVIDENCE")
    payload = {
        "schema": "ovc-esl-organisation-disagreement-record/v1",
        "view_result_ids": views,
        "axis": axis_id,
        "status": status_id,
        "evidence_refs": refs,
        "scalar_collapse": "FORBIDDEN",
        "first_valid_time": _require_nonempty(first_valid_time, "ORG_DISAGREEMENT_FVT_REQUIRED"),
        "evaluation_cutoff": _require_nonempty(evaluation_cutoff, "ORG_DISAGREEMENT_CUTOFF_REQUIRED"),
        "authority": _authority_envelope(),
    }
    logical_hash = sha256_canonical(payload)
    return {**payload, "disagreement_record_id": "orgd1:" + logical_hash, "logical_hash": logical_hash}


def build_invariant_evidence_record(
    *,
    view_result_ids: Sequence[Any],
    invariant_kind: str,
    content_refs: Sequence[Any],
    evidence_refs: Sequence[Any],
    first_valid_time: str,
    evaluation_cutoff: str,
) -> dict[str, Any]:
    views = _normalise_strings(view_result_ids, "ORG_INVARIANT_VIEW_IDS_INVALID")
    if len(views) < 2:
        raise OrganisationEvidenceError("ORG_INVARIANT_REQUIRES_MULTIPLE_VIEWS")
    kind = str(invariant_kind)
    if kind not in INVARIANT_KINDS:
        raise OrganisationEvidenceError("ORG_INVARIANT_KIND_INVALID:" + kind)
    content = _normalise_strings(content_refs, "ORG_INVARIANT_CONTENT_INVALID")
    evidence = _normalise_strings(evidence_refs, "ORG_INVARIANT_EVIDENCE_INVALID")
    if not content or not evidence:
        raise OrganisationEvidenceError("ORG_INVARIANT_CONTENT_AND_EVIDENCE_REQUIRED")
    payload = {
        "schema": "ovc-esl-invariant-evidence-record/v1",
        "view_result_ids": views,
        "invariant_kind": kind,
        "content_refs": content,
        "evidence_refs": evidence,
        "identity_merge": "FORBIDDEN",
        "first_valid_time": _require_nonempty(first_valid_time, "ORG_INVARIANT_FVT_REQUIRED"),
        "evaluation_cutoff": _require_nonempty(evaluation_cutoff, "ORG_INVARIANT_CUTOFF_REQUIRED"),
        "authority": _authority_envelope(),
    }
    logical_hash = sha256_canonical(payload)
    return {**payload, "invariant_evidence_id": "orgi1:" + logical_hash, "logical_hash": logical_hash}


def validate_decision_rule_pack_interface(rule_pack: Mapping[str, Any]) -> dict[str, Any]:
    raw = _copy_json(rule_pack)
    if not isinstance(raw, Mapping):
        raise OrganisationEvidenceError("ORG_RULE_PACK_OBJECT_REQUIRED")
    if raw.get("schema") != "ovc-esl-organisation-decision-rule-pack-interface/v1":
        raise OrganisationEvidenceError("ORG_RULE_PACK_SCHEMA_INVALID")
    if raw.get("maturity") != "INTERFACE_ONLY" or raw.get("executable") is not False:
        raise OrganisationEvidenceError("ORG_RULE_PACK_EXECUTION_NOT_AUTHORISED")
    if raw.get("thresholds") != [] or raw.get("decision_rules") != []:
        raise OrganisationEvidenceError("ORG_RULE_PACK_THRESHOLDS_OR_RULES_FORBIDDEN")
    if raw.get("authority_effect") != "NONE":
        raise OrganisationEvidenceError("ORG_RULE_PACK_AUTHORITY_EFFECT_FORBIDDEN")
    return dict(raw)


def assemble_organisation_evidence_set(
    *,
    view_results: Sequence[Mapping[str, Any]],
    metric_records: Sequence[Mapping[str, Any]] = (),
    correspondence_edges: Sequence[Mapping[str, Any]] = (),
    disagreement_records: Sequence[Mapping[str, Any]] = (),
    invariant_records: Sequence[Mapping[str, Any]] = (),
    declared_topology_ids: Sequence[Any] = (),
    tested_envelope_complete: bool = False,
    decision_rule_pack_interface: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(tested_envelope_complete, bool):
        raise OrganisationEvidenceError("ORG_TESTED_ENVELOPE_COMPLETENESS_BOOL_REQUIRED")
    views = sorted((validate_soi_view_result(view) for view in view_results), key=lambda row: row["soi_view_result_id"])
    if not views:
        raise OrganisationEvidenceError("ORG_EVIDENCE_SET_VIEW_REQUIRED")
    view_ids = {row["soi_view_result_id"] for row in views}
    topology_ids = _normalise_strings(declared_topology_ids, "ORG_TESTED_TOPOLOGIES_INVALID")
    if not topology_ids:
        topology_ids = sorted({str(row["topology"]["topology_id"]) for row in views})
    if any(topology_id not in TOPOLOGY_IDS for topology_id in topology_ids):
        raise OrganisationEvidenceError("ORG_TESTED_TOPOLOGY_UNKNOWN")
    if decision_rule_pack_interface is not None:
        rule_pack = validate_decision_rule_pack_interface(decision_rule_pack_interface)
        rule_pack_id = _require_nonempty(rule_pack.get("rule_pack_id"), "ORG_RULE_PACK_ID_REQUIRED")
    else:
        rule_pack_id = "NONE"
    metrics = sorted((_copy_json(row) for row in metric_records), key=lambda row: str(row.get("metric_record_id", "")))
    correspondences = sorted(
        (_copy_json(row) for row in correspondence_edges),
        key=lambda row: str(row.get("correspondence_edge_id", "")),
    )
    disagreements = sorted(
        (_copy_json(row) for row in disagreement_records),
        key=lambda row: str(row.get("disagreement_record_id", "")),
    )
    invariants = sorted(
        (_copy_json(row) for row in invariant_records),
        key=lambda row: str(row.get("invariant_evidence_id", "")),
    )
    for row in metrics:
        if row.get("view_result_id") not in view_ids:
            raise OrganisationEvidenceError("ORG_METRIC_VIEW_OUTSIDE_SET")
    for row in correspondences:
        if row.get("subject_view_result_id") not in view_ids or row.get("object_view_result_id") not in view_ids:
            raise OrganisationEvidenceError("ORG_CORRESPONDENCE_VIEW_OUTSIDE_SET")
    for collection, field in ((disagreements, "view_result_ids"), (invariants, "view_result_ids")):
        for row in collection:
            if not set(row.get(field, ())).issubset(view_ids):
                raise OrganisationEvidenceError("ORG_CROSS_VIEW_RECORD_OUTSIDE_SET")
    chronology_fvts = [str(row["chronology"]["first_valid_time"]) for row in views]
    chronology_cutoffs = [str(row["chronology"]["evaluation_cutoff"]) for row in views]
    payload = {
        "schema": "ovc-esl-organisation-evidence-set/v1",
        "view_results": views,
        "metric_records": metrics,
        "correspondence_edges": correspondences,
        "disagreement_records": disagreements,
        "invariant_records": invariants,
        "tested_envelope": {
            "declared_topology_ids": topology_ids,
            "complete": tested_envelope_complete,
        },
        "decision_rule_pack_id": rule_pack_id,
        "scientific_disposition": "NOT_EVALUATED_RULE_PACK_REQUIRED",
        "view_scoped_nulls": sorted(
            {
                str(row["topology_result"]["evidence_status"])
                for row in views
                if str(row["topology_result"]["evidence_status"]).startswith("NO_STABLE_")
            }
        ),
        "organisation_absence_claim": "NOT_MADE",
        "first_valid_time": max(chronology_fvts),
        "evaluation_cutoff": min(chronology_cutoffs),
        "authority": _authority_envelope(),
    }
    logical_hash = sha256_canonical(payload)
    return {
        **payload,
        "organisation_evidence_set_id": "orges1:" + logical_hash,
        "logical_hash": logical_hash,
    }


def apply_organisation_decision_rule_pack(
    evidence_set: Mapping[str, Any],
    *,
    decision_rule_pack: Mapping[str, Any],
) -> dict[str, Any]:
    """Fail closed until a separately governed executable rule pack exists."""
    validate_decision_rule_pack_interface(decision_rule_pack)
    raise OrganisationEvidenceError("ORGANISATION_DECISION_RULE_PACK_NOT_EXECUTABLE")


def assert_no_stable_organisation_claim_lawful(
    *,
    evidence_set: Mapping[str, Any],
    proposed_disposition: str,
) -> None:
    disposition = str(proposed_disposition)
    if disposition not in SCIENTIFIC_DISPOSITIONS:
        raise OrganisationEvidenceError("ORG_SCIENTIFIC_DISPOSITION_INVALID:" + disposition)
    if disposition != "NO_STABLE_ORGANISATION":
        return
    tested_envelope = evidence_set.get("tested_envelope")
    if not isinstance(tested_envelope, Mapping) or tested_envelope.get("complete") is not True:
        raise OrganisationEvidenceError("ORG_NO_STABLE_ORGANISATION_REQUIRES_COMPLETE_ENVELOPE")
    declared = set(tested_envelope.get("declared_topology_ids", ()))
    if declared != set(TOPOLOGY_IDS):
        raise OrganisationEvidenceError("ORG_NO_STABLE_ORGANISATION_REQUIRES_ALL_TOPOLOGIES")
    raise OrganisationEvidenceError("ORG_NO_STABLE_ORGANISATION_REQUIRES_EXECUTABLE_RULE_PACK")
