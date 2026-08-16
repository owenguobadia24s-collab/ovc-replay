from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any, Iterable, Mapping

from .core import canonical_json_bytes
from .need_review import NEED_STATUSES


class RCCRReadModelError(ValueError):
    pass


FORBIDDEN_SCALAR_KEYS = {
    "score",
    "coverage_score",
    "completeness_score",
    "coverage_percentage",
    "completeness_percentage",
}
RATE_COMPARISON_PURPOSES = {
    "TARGET",
    "RANKING",
    "PERFORMANCE_METRIC",
    "IMPROVEMENT_CLAIM",
    "DECLINE_CLAIM",
}


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _stable_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out = [deepcopy(dict(row)) for row in rows]
    out.sort(key=canonical_json_bytes)
    return out


def _deny_scalar_scores(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            if key_text in FORBIDDEN_SCALAR_KEYS or key_text.endswith("_score"):
                raise RCCRReadModelError(f"synthetic scalar score forbidden at {path}.{key}")
            _deny_scalar_scores(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _deny_scalar_scores(child, f"{path}[{index}]")


def build_capability_without_demand(
    *,
    capability_frontier: Mapping[str, Any],
    need_assessments: Iterable[Mapping[str, Any]],
    evaluation_cutoff: str | None = None,
    source_refs: Iterable[str] = (),
) -> dict[str, Any]:
    """Build the first RCCR operator read model without creating retirement or priority authority."""

    frontier = deepcopy(dict(capability_frontier))
    if frontier.get("authority_effect") not in (None, "NONE"):
        raise RCCRReadModelError("capability frontier authority_effect must be NONE")
    capabilities = [deepcopy(dict(row)) for row in frontier.get("capability_bindings", [])]
    by_id: dict[str, dict[str, Any]] = {}
    for row in capabilities:
        capability_id = str(row.get("capability_id", ""))
        if not capability_id:
            raise RCCRReadModelError("capability_id required")
        if capability_id in by_id:
            raise RCCRReadModelError(f"duplicate capability_id: {capability_id}")
        for plane in ("design", "implementation", "availability", "qualification", "authority", "activation"):
            if plane not in row:
                raise RCCRReadModelError(f"missing maturity plane {plane}: {capability_id}")
        by_id[capability_id] = row

    counts: dict[str, dict[str, int]] = {
        capability_id: {status: 0 for status in sorted(NEED_STATUSES)}
        for capability_id in by_id
    }
    assessment_refs: dict[str, list[str]] = {capability_id: [] for capability_id in by_id}
    for raw in need_assessments:
        assessment = deepcopy(dict(raw))
        _deny_scalar_scores(assessment)
        if assessment.get("authority_effect") not in (None, "NONE"):
            raise RCCRReadModelError("capability need assessment authority_effect must be NONE")
        candidate = assessment.get("candidate_capability") or {}
        capability_id = str(candidate.get("capability_id", ""))
        status = str(assessment.get("need_status", ""))
        if capability_id not in by_id:
            raise RCCRReadModelError(f"need assessment references unregistered capability: {capability_id}")
        if status not in NEED_STATUSES:
            raise RCCRReadModelError(f"unknown need status: {status}")
        counts[capability_id][status] += 1
        ref = str(assessment.get("capability_need_assessment_id", ""))
        if ref:
            assessment_refs[capability_id].append(ref)

    rows: list[dict[str, Any]] = []
    for capability_id in sorted(by_id):
        row = by_id[capability_id]
        status_counts = counts[capability_id]
        if status_counts["NEED_SUPPORTED"] != 0:
            continue
        rows.append(
            {
                "capability_id": capability_id,
                "owner_programme": row.get("owner_programme"),
                "responsibility": row.get("responsibility"),
                "maturity": {
                    "design": row["design"],
                    "implementation": row["implementation"],
                    "availability": row["availability"],
                    "qualification": row["qualification"],
                    "authority": row["authority"],
                    "activation": row["activation"],
                },
                "active_stack_classification": row.get("active_stack_classification"),
                "need_counts": status_counts,
                "need_assessment_refs": sorted(assessment_refs[capability_id]),
                "zero_supported_demand": True,
                "interpretation": "DESCRIPTIVE_OPPORTUNITY_COST_SIGNAL_ONLY",
                "retirement_authority": "NONE",
                "activation_authority": "NONE",
                "authority_effect": "NONE",
            }
        )

    cutoff = evaluation_cutoff or str(frontier.get("evaluation_cutoff", ""))
    if not cutoff:
        raise RCCRReadModelError("evaluation_cutoff required")
    model: dict[str, Any] = {
        "schema": "ovc-rccr-read-model/v1",
        "model_type": "CAPABILITY_WITHOUT_DEMAND",
        "read_model_id": "PENDING",
        "evaluation_cutoff": cutoff,
        "source_frontier_id": frontier.get("capability_frontier_id"),
        "eligible_capability_denominator": len(by_id),
        "zero_supported_demand_count": len(rows),
        "rows": rows,
        "source_refs": sorted(set(str(ref) for ref in source_refs if str(ref))),
        "zero_demand_is_retirement_authority": False,
        "zero_demand_is_priority_score": False,
        "authority_effect": "NONE",
    }
    _deny_scalar_scores(model)
    model["read_model_id"] = f"rccr-read-model:{_digest({k: v for k, v in model.items() if k != 'read_model_id'})}"
    return model


def build_portfolio_posture(
    *,
    admitted_items: Iterable[Mapping[str, Any]],
    evaluation_cutoff: str,
    source_universe_id: str,
    source_refs: Iterable[str] = (),
) -> dict[str, Any]:
    """Build denominator-explicit within-snapshot posture without a synthetic completeness score."""

    if not evaluation_cutoff or not source_universe_id:
        raise RCCRReadModelError("evaluation_cutoff and source_universe_id are required")
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in admitted_items:
        item = deepcopy(dict(raw))
        _deny_scalar_scores(item)
        item_id = str(item.get("item_id", ""))
        if not item_id or item_id in seen:
            raise RCCRReadModelError("item_id must be non-empty and unique")
        seen.add(item_id)
        if item.get("included", True) is False:
            reason = str(item.get("exclusion_reason", ""))
            if not reason:
                raise RCCRReadModelError(f"exclusion reason required: {item_id}")
            excluded.append({"item_id": item_id, "exclusion_reason": reason})
            continue
        answerability = str(item.get("answerability", ""))
        primary_gap = str(item.get("primary_gap", ""))
        need_status = str(item.get("need_status", "UNRESOLVED"))
        if not answerability or not primary_gap:
            raise RCCRReadModelError(f"answerability and primary_gap required: {item_id}")
        if need_status not in NEED_STATUSES:
            raise RCCRReadModelError(f"unknown need status: {need_status}")
        included.append(
            {
                "item_id": item_id,
                "answerability": answerability,
                "primary_gap": primary_gap,
                "need_status": need_status,
                "source_ref": item.get("source_ref"),
            }
        )

    included.sort(key=lambda row: row["item_id"])
    excluded.sort(key=lambda row: row["item_id"])
    denominator = len(included)

    def dimension(name: str) -> list[dict[str, Any]]:
        values: dict[str, int] = {}
        for row in included:
            key = str(row[name])
            values[key] = values.get(key, 0) + 1
        return [
            {
                "class": key,
                "count": count,
                "denominator": denominator,
                "rate": (count / denominator) if denominator else None,
                "rate_scope": "WITHIN_SNAPSHOT_ONLY",
            }
            for key, count in sorted(values.items())
        ]

    model: dict[str, Any] = {
        "schema": "ovc-rccr-read-model/v1",
        "model_type": "PORTFOLIO_POSTURE",
        "read_model_id": "PENDING",
        "evaluation_cutoff": evaluation_cutoff,
        "source_universe_id": source_universe_id,
        "eligible_item_denominator": denominator,
        "included_item_ids": [row["item_id"] for row in included],
        "excluded_items": excluded,
        "answerability": dimension("answerability"),
        "primary_gap": dimension("primary_gap"),
        "need_status": dimension("need_status"),
        "source_refs": sorted(set(str(ref) for ref in source_refs if str(ref))),
        "rate_comparison_policy": "NO_CROSS_PERIOD_PROGRAMME_POPULATION_OR_FRONTIER_RANKING_WITHOUT_PROTOCOL",
        "synthetic_completeness_score": "FORBIDDEN",
        "authority_effect": "NONE",
    }
    material = deepcopy(model)
    material.pop("synthetic_completeness_score", None)
    _deny_scalar_scores(material)
    model["read_model_id"] = f"rccr-read-model:{_digest({k: v for k, v in material.items() if k != 'read_model_id'})}"
    return model


def assess_rate_comparison(
    *,
    left_context: Mapping[str, Any],
    right_context: Mapping[str, Any],
    purpose: str,
    comparability_protocol_id: str | None = None,
) -> dict[str, Any]:
    """Fail closed on cross-context target/ranking claims without a governed comparability protocol."""

    purpose = str(purpose).upper()
    dimensions = ("period", "programme_id", "population_id", "frontier_id")
    changed = [
        dimension
        for dimension in dimensions
        if left_context.get(dimension) != right_context.get(dimension)
    ]
    if changed and purpose in RATE_COMPARISON_PURPOSES and not comparability_protocol_id:
        raise RCCRReadModelError(
            "cross-context rate target/ranking comparison denied without comparability protocol: "
            + ",".join(changed)
        )
    return {
        "disposition": "ALLOW_DESCRIPTIVE" if changed else "SAME_CONTEXT",
        "changed_dimensions": changed,
        "purpose": purpose,
        "comparability_protocol_id": comparability_protocol_id,
        "authority_effect": "NONE",
    }


def query_read_model(
    read_model: Mapping[str, Any],
    *,
    capability_id: str | None = None,
    item_id: str | None = None,
) -> dict[str, Any]:
    """Deterministic source-native query surface used by CLI/service adapters."""

    model = deepcopy(dict(read_model))
    _deny_scalar_scores({k: v for k, v in model.items() if k != "synthetic_completeness_score"})
    rows = model.get("rows")
    if capability_id is not None:
        if not isinstance(rows, list):
            raise RCCRReadModelError("capability query requires rows")
        selected = [row for row in rows if row.get("capability_id") == capability_id]
        return {
            "model_type": model.get("model_type"),
            "read_model_id": model.get("read_model_id"),
            "query": {"capability_id": capability_id},
            "rows": _stable_rows(selected),
            "authority_effect": "NONE",
        }
    if item_id is not None:
        selected = [row for row in model.get("items", []) if row.get("item_id") == item_id]
        return {
            "model_type": model.get("model_type"),
            "read_model_id": model.get("read_model_id"),
            "query": {"item_id": item_id},
            "rows": _stable_rows(selected),
            "authority_effect": "NONE",
        }
    return model


def build_pilot_exit_evidence_packet(
    *,
    baseline_commit: str,
    wp7a_candidate_commit: str,
    source_frontier_id: str,
    q01_q10_ref: str,
    assurance_ref: str,
    historical_validation_ref: str,
    review_load_ref: str,
    workaround_ref: str,
    capability_without_demand_ref: str,
    portfolio_posture_ref: str,
    g4_algorithmic_review_ref: str,
    adversarial_review_ref: str,
    fixture_currentness_ref: str,
    fixture_resource_actuals_ref: str,
    rollback: str,
    warnings: Iterable[str] = (),
    blockers: Iterable[str] = (),
) -> dict[str, Any]:
    refs = {
        "q01_q10": q01_q10_ref,
        "assurance": assurance_ref,
        "historical_validation": historical_validation_ref,
        "review_load": review_load_ref,
        "workaround": workaround_ref,
        "capability_without_demand": capability_without_demand_ref,
        "portfolio_posture": portfolio_posture_ref,
        "g4_algorithmic_review": g4_algorithmic_review_ref,
        "adversarial_review": adversarial_review_ref,
        "fixture_currentness": fixture_currentness_ref,
        "fixture_resource_actuals": fixture_resource_actuals_ref,
    }
    if not baseline_commit or not wp7a_candidate_commit or not source_frontier_id or not rollback:
        raise RCCRReadModelError("pilot-exit evidence identity fields are required")
    if any(not value for value in refs.values()):
        raise RCCRReadModelError("all pilot-exit evidence references are required")
    packet: dict[str, Any] = {
        "schema": "ovc-rccri-pilot-exit-evidence/v1",
        "packet_id": "RCCRI-G-PILOT-EXIT-EVIDENCE",
        "baseline_commit": baseline_commit,
        "candidate_commit": wp7a_candidate_commit,
        "source_frontier_id": source_frontier_id,
        "evidence_refs": refs,
        "warnings": sorted(set(str(item) for item in warnings)),
        "blockers": sorted(set(str(item) for item in blockers)),
        "real_source_ec1_claims": "NONE",
        "scaleout_authority": "DENIED_UNTIL_CLASSIFIED_AND_LAWFULLY_DECIDED",
        "rollback": rollback,
        "authority_effect": "NONE",
    }
    packet["evidence_packet_hash"] = _digest(packet)
    return packet
