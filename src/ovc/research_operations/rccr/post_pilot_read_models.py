from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from .core import canonical_json_bytes
from .read_models import RCCRReadModelError, _digest, _deny_scalar_scores


GAP_CLASSES = frozenset(
    {
        "METHOD_GAP",
        "INFORMATION_GAP",
        "DENOMINATOR_GAP",
        "DATA_GAP",
        "OWNER_SEMANTICS_GAP",
        "IMPLEMENTATION_GAP",
        "AUTHORITY_GAP",
        "CAPACITY_REVIEW_GAP",
        "UNRESOLVED",
        "NONE",
    }
)

NEXT_ROUTE_BY_GAP = {
    "METHOD_GAP": "METHOD_FIRST",
    "INFORMATION_GAP": "EXTERNAL_RESEARCH_DELTA",
    "DENOMINATOR_GAP": "DENOMINATOR_RECONCILIATION",
    "DATA_GAP": "SOURCE_DATA_RECONCILIATION",
    "OWNER_SEMANTICS_GAP": "OWNER_SEMANTICS_REVIEW",
    "IMPLEMENTATION_GAP": "OWNER_IMPLEMENTATION_REVIEW",
    "AUTHORITY_GAP": "OWNER_AUTHORITY_REVIEW",
    "CAPACITY_REVIEW_GAP": "CAPACITY_REVIEW",
    "UNRESOLVED": "HUMAN_REVIEW",
    "NONE": "NO_ROUTE_REQUIRED",
}


def _stable(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    values = [deepcopy(dict(row)) for row in rows]
    values.sort(key=canonical_json_bytes)
    return values


def _base_model(model_type: str, *, evaluation_cutoff: str, source_universe_id: str) -> dict[str, Any]:
    if not evaluation_cutoff or not source_universe_id:
        raise RCCRReadModelError("evaluation_cutoff and source_universe_id are required")
    return {
        "schema": "ovc-rccr-read-model/v1",
        "model_type": model_type,
        "read_model_id": "PENDING",
        "evaluation_cutoff": evaluation_cutoff,
        "source_universe_id": source_universe_id,
        "authority_effect": "NONE",
    }


def _finish(model: dict[str, Any]) -> dict[str, Any]:
    _deny_scalar_scores(model)
    material = {key: value for key, value in model.items() if key != "read_model_id"}
    model["read_model_id"] = f"rccr-read-model:{_digest(material)}"
    return model


def _assessment_row(raw: Mapping[str, Any]) -> dict[str, Any]:
    row = deepcopy(dict(raw))
    _deny_scalar_scores(row)
    if row.get("authority_effect") not in (None, "NONE"):
        raise RCCRReadModelError("assessment authority_effect must be NONE")
    item_id = str(row.get("item_id", "")).strip()
    if not item_id:
        raise RCCRReadModelError("item_id required")
    primary_gap = str(row.get("primary_gap", "UNRESOLVED")).strip()
    if primary_gap not in GAP_CLASSES:
        raise RCCRReadModelError(f"unknown primary gap: {primary_gap}")
    source_ref = str(row.get("source_ref", "")).strip()
    if not source_ref:
        raise RCCRReadModelError(f"source_ref required: {item_id}")
    return {
        "item_id": item_id,
        "requirement_id": row.get("requirement_id"),
        "path": row.get("path"),
        "answerability": row.get("answerability"),
        "primary_gap": primary_gap,
        "secondary_gaps": sorted(set(str(value) for value in row.get("secondary_gaps", []) if str(value))),
        "need_status": row.get("need_status"),
        "capability_id": row.get("capability_id"),
        "source_ref": source_ref,
        "independence_state": row.get("independence_state"),
        "exposure_state": row.get("exposure_state"),
        "authority_effect": "NONE",
    }


def build_research_coverage_matrix(
    *,
    assessments: Iterable[Mapping[str, Any]],
    evaluation_cutoff: str,
    source_universe_id: str,
) -> dict[str, Any]:
    rows = [_assessment_row(row) for row in assessments]
    ids = [row["item_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise RCCRReadModelError("coverage matrix item_id values must be unique")
    model = _base_model("RESEARCH_COVERAGE_MATRIX", evaluation_cutoff=evaluation_cutoff, source_universe_id=source_universe_id)
    model.update(
        {
            "eligible_item_denominator": len(rows),
            "rows": _stable(rows),
            "source_native": True,
            "synthetic_completeness_score_forbidden": True,
        }
    )
    return _finish(model)


def build_gap_queues(
    *,
    assessments: Iterable[Mapping[str, Any]],
    evaluation_cutoff: str,
    source_universe_id: str,
) -> dict[str, Any]:
    rows = [_assessment_row(row) for row in assessments]
    queues = {gap: [] for gap in sorted(GAP_CLASSES - {"NONE"})}
    method_first: list[dict[str, Any]] = []
    architecture_pressure: list[dict[str, Any]] = []
    for row in rows:
        gap = row["primary_gap"]
        if gap != "NONE":
            queues[gap].append(row)
        if gap == "METHOD_GAP":
            method_first.append(row)
        if gap in {"IMPLEMENTATION_GAP", "AUTHORITY_GAP", "CAPACITY_REVIEW_GAP"} and row.get("capability_id"):
            architecture_pressure.append(row)
    model = _base_model("GAP_QUEUES", evaluation_cutoff=evaluation_cutoff, source_universe_id=source_universe_id)
    model.update(
        {
            "queues": {key: _stable(value) for key, value in queues.items()},
            "method_first": _stable(method_first),
            "architecture_pressure": _stable(architecture_pressure),
            "architecture_pressure_entry_rule": "PRIMARY_GAP_IN_IMPLEMENTATION_AUTHORITY_CAPACITY_AND_NAMED_CAPABILITY",
            "source_native": True,
        }
    )
    return _finish(model)


def build_path_correspondence(
    *,
    assessments: Iterable[Mapping[str, Any]],
    evaluation_cutoff: str,
    source_universe_id: str,
) -> dict[str, Any]:
    rows = [_assessment_row(row) for row in assessments]
    correspondence: list[dict[str, Any]] = []
    for row in rows:
        path = str(row.get("path") or "").upper()
        if path not in {"PATH_1", "PATH_2"}:
            continue
        independence = str(row.get("independence_state") or "UNSPECIFIED")
        exposure = str(row.get("exposure_state") or "UNSPECIFIED")
        correspondence.append(
            {
                "item_id": row["item_id"],
                "path": path,
                "requirement_id": row.get("requirement_id"),
                "primary_gap": row["primary_gap"],
                "independence_state": independence,
                "exposure_state": exposure,
                "source_ref": row["source_ref"],
                "ranking_authority": "NONE",
                "authority_effect": "NONE",
            }
        )
    model = _base_model("PATH_CORRESPONDENCE", evaluation_cutoff=evaluation_cutoff, source_universe_id=source_universe_id)
    model.update(
        {
            "rows": _stable(correspondence),
            "cross_path_ranking": "FORBIDDEN_WITHOUT_SEPARATE_PROTOCOL",
            "source_native": True,
        }
    )
    return _finish(model)


def build_next_research_routes(
    *,
    assessments: Iterable[Mapping[str, Any]],
    evaluation_cutoff: str,
    source_universe_id: str,
) -> dict[str, Any]:
    rows = [_assessment_row(row) for row in assessments]
    routes = [
        {
            "item_id": row["item_id"],
            "primary_gap": row["primary_gap"],
            "next_route": NEXT_ROUTE_BY_GAP[row["primary_gap"]],
            "source_ref": row["source_ref"],
            "priority_score": None,
            "effectuation_authority": "NONE",
            "authority_effect": "NONE",
        }
        for row in rows
    ]
    # priority_score is a literal denial marker, not a score. Remove it before scalar-score validation.
    model = _base_model("NEXT_RESEARCH_ROUTE", evaluation_cutoff=evaluation_cutoff, source_universe_id=source_universe_id)
    model.update(
        {
            "rows": _stable(routes),
            "route_semantics": "DESCRIPTIVE_NON_EFFECTUATING",
            "autonomous_research_priority_scoring": "FORBIDDEN",
            "source_native": True,
        }
    )
    material = deepcopy(model)
    for row in material["rows"]:
        row.pop("priority_score", None)
    _deny_scalar_scores(material)
    digest_material = {key: value for key, value in model.items() if key != "read_model_id"}
    model["read_model_id"] = f"rccr-read-model:{_digest(digest_material)}"
    return model


def build_ec1_rv_review_projection(
    *,
    evidence_records: Iterable[Mapping[str, Any]],
    e1_r1_assured: bool,
    evaluation_cutoff: str,
    source_universe_id: str,
) -> dict[str, Any]:
    model = _base_model("EC1_RV_REVIEW_PROJECTION", evaluation_cutoff=evaluation_cutoff, source_universe_id=source_universe_id)
    if not e1_r1_assured:
        if list(evidence_records):
            raise RCCRReadModelError("EC1-RV evidence consumption denied until E1/R1 is lawfully assured")
        model.update(
            {
                "availability": "DEFERRED_PENDING_LAWFULLY_ASSURED_E1_R1",
                "rows": [],
                "scientific_claims": "NONE",
                "source_native": True,
            }
        )
        return _finish(model)

    rows: list[dict[str, Any]] = []
    for raw in evidence_records:
        row = deepcopy(dict(raw))
        _deny_scalar_scores(row)
        if row.get("authority_effect") not in (None, "NONE"):
            raise RCCRReadModelError("EC1-RV projection input authority_effect must be NONE")
        source_ref = str(row.get("source_ref", "")).strip()
        review_id = str(row.get("review_id", "")).strip()
        if not source_ref or not review_id:
            raise RCCRReadModelError("EC1-RV review_id and source_ref required")
        rows.append(
            {
                "review_id": review_id,
                "question_id": row.get("question_id"),
                "review_state": row.get("review_state"),
                "source_ref": source_ref,
                "authority_effect": "NONE",
            }
        )
    model.update(
        {
            "availability": "SOURCE_BOUND_E1_R1_ASSURED",
            "rows": _stable(rows),
            "scientific_claims": "NONE_RCCR_ONLY_PROJECTS_OWNER_EVIDENCE",
            "source_native": True,
        }
    )
    return _finish(model)


def build_post_pilot_read_models(
    *,
    assessments: Iterable[Mapping[str, Any]],
    ec1_rv_records: Iterable[Mapping[str, Any]],
    e1_r1_assured: bool,
    evaluation_cutoff: str,
    source_universe_id: str,
) -> dict[str, Any]:
    stable_assessments = _stable(assessments)
    stable_rv = _stable(ec1_rv_records)
    models = {
        "coverage_matrix": build_research_coverage_matrix(
            assessments=stable_assessments,
            evaluation_cutoff=evaluation_cutoff,
            source_universe_id=source_universe_id,
        ),
        "gap_queues": build_gap_queues(
            assessments=stable_assessments,
            evaluation_cutoff=evaluation_cutoff,
            source_universe_id=source_universe_id,
        ),
        "correspondence": build_path_correspondence(
            assessments=stable_assessments,
            evaluation_cutoff=evaluation_cutoff,
            source_universe_id=source_universe_id,
        ),
        "next_routes": build_next_research_routes(
            assessments=stable_assessments,
            evaluation_cutoff=evaluation_cutoff,
            source_universe_id=source_universe_id,
        ),
        "ec1_rv": build_ec1_rv_review_projection(
            evidence_records=stable_rv,
            e1_r1_assured=e1_r1_assured,
            evaluation_cutoff=evaluation_cutoff,
            source_universe_id=source_universe_id,
        ),
    }
    return {
        "schema": "ovc-rccr-post-pilot-read-model-bundle/v1",
        "models": models,
        "console_get_adapter": "DEFERRED_OPTIONAL_NOT_CORRECTNESS_PREREQUISITE",
        "write_routes": "DENIED",
        "authority_effect": "NONE",
        "bundle_hash": _digest(models),
    }
