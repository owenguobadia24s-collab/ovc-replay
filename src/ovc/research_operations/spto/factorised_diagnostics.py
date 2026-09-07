"""Source-free WP9 diagnostics for the factorised C2S-SPTO substrate.

The module qualifies denominator, exposure, sensitivity, temporal and drift
mechanics on synthetic records.  It cannot load protected source or emit an
empirical grammar claim.  Counts always retain their declared universal
population and use explicit disposition rows for excluded or unevaluable
opportunities.
"""

from __future__ import annotations

import copy
import json
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .factorised_mechanics import (
    ANTECEDENT_HIERARCHIES,
    DECLARED_REPRESENTATIONS,
    MICRO_APPLICABILITY_STATES,
    PROTOCOL_ID,
    PROTOCOL_SHA256,
    SUPPORT_SENSITIVITIES,
    TARGET_HIERARCHIES,
    build_population_manifest,
    content_id,
)
from .factorised_nulls import NULL_SPECS


PACKET_ID = "C2S-SPTOI-WP9"
DIAGNOSTIC_MATURITY = "SYNTHETIC_QUALIFICATION_ONLY"
SPECIFICATIONS = (
    "FG-RECURRENCE-RAW",
    "FG-RECURRENCE-RUN-COLLAPSED",
    "FG-ROBUST-DECLARED-SET",
)
CLAIMS = (
    "RECURRENCE",
    "DECLARED_SET_ROBUSTNESS",
    "TEMPORAL_BREADTH",
    "SOURCE_STABILITY",
)


class DiagnosticError(ValueError):
    """A typed, fail-closed diagnostic qualification failure."""

    def __init__(self, reason_code: str, detail: str):
        super().__init__(f"{reason_code}: {detail}")
        self.reason_code = reason_code
        self.detail = detail


def _ratio(numerator: int, denominator: int) -> dict[str, int | str]:
    if denominator < 0 or numerator < 0 or numerator > denominator:
        raise DiagnosticError("INVALID_RATIO", f"{numerator}/{denominator}")
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rendering": f"{numerator}/{denominator}",
    }


def _freeze(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True))


def synthetic_diagnostic_population() -> dict[str, Any]:
    """Return a fixed population with explicit non-survivor dispositions."""
    rows = [
        ("OPP-01", "RUN-A", "SEG-A", "2022Q1", "SYNTH-GEN-A", "MICRO_BEARING", True, "TARGET-A"),
        ("OPP-02", "RUN-A", "SEG-A", "2022Q1", "SYNTH-GEN-A", "MICRO_BEARING", True, "TARGET-A"),
        ("OPP-03", "RUN-B", "SEG-A", "2022Q2", "SYNTH-GEN-A", "MICRO_BEARING", False, "TARGET-B"),
        ("OPP-04", "RUN-C", "SEG-B", "2022Q3", "SYNTH-GEN-A", "MICRO_BEARING", True, "TARGET-A"),
        ("OPP-05", "RUN-C", "SEG-B", "2022Q3", "SYNTH-GEN-B", "MICRO_BEARING", True, "TARGET-C"),
        ("OPP-06", "RUN-D", "SEG-C", "2022Q4", "SYNTH-GEN-B", "MICRO_BEARING", True, "TARGET-C"),
        ("OPP-07", "RUN-E", "SEG-C", "2022Q4", "SYNTH-GEN-B", "NO_MICRO", None, None),
        ("OPP-08", "RUN-F", "SEG-D", "2023Q1", "SYNTH-GEN-B", "CENSORED", None, None),
    ]
    opportunities = []
    for index, (opp, run, segment, period, generation, applicability, recurrent, target) in enumerate(rows):
        views = []
        for rep_index, representation_id in enumerate(DECLARED_REPRESENTATIONS):
            status = "COMPUTED" if applicability == "MICRO_BEARING" else "NOT_APPLICABLE"
            support = 2 + ((index + rep_index) % 4) if status == "COMPUTED" else 0
            if opp == "OPP-06" and representation_id == "NO_PATH":
                status = "NOT_EVALUABLE_SUPPORT"
                support = 1
            views.append(
                {
                    "representation_id": representation_id,
                    "status": status,
                    "antecedent_support": support,
                    "backoff_level": ANTECEDENT_HIERARCHIES[representation_id][
                        (index + rep_index) % len(ANTECEDENT_HIERARCHIES[representation_id])
                    ] if status == "COMPUTED" else None,
                    "target_resolution": tuple(TARGET_HIERARCHIES)[
                        (index + rep_index) % len(TARGET_HIERARCHIES)
                    ] if status == "COMPUTED" else None,
                    "supports_target": recurrent if status == "COMPUTED" else None,
                }
            )
        opportunities.append(
            {
                "opportunity_id": opp,
                "run_id": run,
                "segment_id": segment,
                "period_id": period,
                "source_generation_id": generation,
                "applicability": applicability,
                "recurrent": recurrent,
                "target_id": target,
                "representation_views": views,
            }
        )
    return {
        "population_id": "C2S-SPTOI-WP9-SYNTHETIC-POPULATION-v1",
        "opportunities": opportunities,
    }


def validate_complete_population(population: Mapping[str, Any]) -> None:
    rows = population.get("opportunities")
    if not isinstance(rows, list) or not rows:
        raise DiagnosticError("POPULATION_INCOMPLETE", "opportunities absent")
    ids = [row.get("opportunity_id") for row in rows]
    if any(not item for item in ids) or len(set(ids)) != len(ids):
        raise DiagnosticError("POPULATION_INCOMPLETE", "opportunity identities missing or duplicated")
    for row in rows:
        applicability = row.get("applicability")
        if applicability not in MICRO_APPLICABILITY_STATES:
            raise DiagnosticError("POPULATION_INCOMPLETE", f"bad applicability {applicability}")
        views = row.get("representation_views", [])
        view_ids = tuple(view.get("representation_id") for view in views)
        if view_ids != DECLARED_REPRESENTATIONS:
            raise DiagnosticError("DECLARED_REPRESENTATION_SET_INCOMPLETE", str(row.get("opportunity_id")))
        if applicability != "MICRO_BEARING" and row.get("recurrent") is not None:
            raise DiagnosticError("CONDITIONAL_SURVIVOR_PROMOTED", str(row.get("opportunity_id")))


def _population_manifest(population: Mapping[str, Any]) -> dict[str, Any]:
    rows = population["opportunities"]
    applicability = Counter(row["applicability"] for row in rows)
    complete_applicability = {state: applicability.get(state, 0) for state in MICRO_APPLICABILITY_STATES}
    evaluable = sum(row["applicability"] == "MICRO_BEARING" for row in rows)
    manifest = build_population_manifest(
        owner_transition_opportunities=len(rows),
        applicability=complete_applicability,
        micro_factor_occurrences=evaluable,
        micro_factorised_paths=evaluable,
        grammar_evaluation_opportunities=evaluable,
        dependence_clusters=len({row["run_id"] for row in rows if row["applicability"] == "MICRO_BEARING"}),
        evaluation_cohorts=Counter(row["period_id"] for row in rows if row["applicability"] == "MICRO_BEARING"),
    )
    return _freeze(manifest.__dict__)


def _recurrence(population: Mapping[str, Any]) -> dict[str, Any]:
    rows = population["opportunities"]
    eligible = [row for row in rows if row["applicability"] == "MICRO_BEARING"]
    raw_recurrent = sum(row["recurrent"] is True for row in eligible)
    run_groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in eligible:
        run_groups[row["run_id"]].append(row)
    recurrent_runs = sum(any(row["recurrent"] is True for row in group) for group in run_groups.values())
    return {
        "universal_population": {
            "unit": "OwnerTransitionOpportunity",
            "denominator": len(rows),
            "explicit_non_eligible": len(rows) - len(eligible),
        },
        "raw": {
            "unit": "GrammarEvaluationOpportunity",
            "eligible": _ratio(len(eligible), len(rows)),
            "recurrent_among_eligible": _ratio(raw_recurrent, len(eligible)),
            "scope": "CONDITIONAL_MICRO_BEARING_NOT_UNIVERSAL",
        },
        "run_collapsed": {
            "unit": "DependenceCluster",
            "eligible_run_denominator": len(run_groups),
            "recurrent_runs": _ratio(recurrent_runs, len(run_groups)),
            "collapse_rule": "ONE_RUN_ONE_UNIT_ANY_RECURRENT_MEMBER",
            "scope": "CONDITIONAL_MICRO_BEARING_RUNS_NOT_UNIVERSAL",
        },
    }


def _representation_completeness(population: Mapping[str, Any]) -> dict[str, Any]:
    rows = population["opportunities"]
    expected = len(rows) * len(DECLARED_REPRESENTATIONS)
    observed = sum(len(row["representation_views"]) for row in rows)
    computed = sum(
        view["status"] == "COMPUTED"
        for row in rows for view in row["representation_views"]
    )
    statuses = Counter(
        view["status"] for row in rows for view in row["representation_views"]
    )
    return {
        "declared_representation_set": list(DECLARED_REPRESENTATIONS),
        "universal_opportunity_denominator": len(rows),
        "expected_view_denominator": expected,
        "recorded_views": _ratio(observed, expected),
        "computed_views": _ratio(computed, expected),
        "status_counts": dict(sorted(statuses.items())),
        "missing_declared_view_rows": expected - observed,
        "universal_statement": "EVERY_DECLARED_VIEW_HAS_AN_EXPLICIT_ROW",
        "computed_statement_scope": "CONDITIONAL_NOT_UNIVERSAL",
    }


def _sensitivity(population: Mapping[str, Any]) -> dict[str, Any]:
    eligible_views = [
        view for row in population["opportunities"]
        if row["applicability"] == "MICRO_BEARING"
        for view in row["representation_views"]
    ]
    threshold_rows = []
    for threshold in (2, *SUPPORT_SENSITIVITIES):
        supported = sum(view["antecedent_support"] >= threshold for view in eligible_views)
        threshold_rows.append(
            {
                "support_min": threshold,
                "supported": _ratio(supported, len(eligible_views)),
                "dropped_rows": 0,
                "unsupported_disposition": "RETAIN_EXPLICIT_NOT_EVALUABLE",
            }
        )
    backoff = Counter(
        view["backoff_level"] for view in eligible_views if view["backoff_level"] is not None
    )
    targets = Counter(
        view["target_resolution"] for view in eligible_views if view["target_resolution"] is not None
    )
    return {
        "eligible_view_denominator": len(eligible_views),
        "support_thresholds": threshold_rows,
        "backoff_hierarchy": dict(sorted(backoff.items())),
        "target_resolution": dict(sorted(targets.items())),
        "antecedent_hierarchies_exercised": list(ANTECEDENT_HIERARCHIES),
        "target_hierarchies_exercised": list(TARGET_HIERARCHIES),
    }


def _temporal_and_context(population: Mapping[str, Any]) -> dict[str, Any]:
    rows = population["opportunities"]
    eligible = [row for row in rows if row["applicability"] == "MICRO_BEARING"]
    all_periods = sorted({row["period_id"] for row in rows})
    all_segments = sorted({row["segment_id"] for row in rows})
    represented_periods = sorted({row["period_id"] for row in eligible})
    represented_segments = sorted({row["segment_id"] for row in eligible})
    return {
        "temporal_stability_vector": [
            {
                "period_id": period,
                "universal_opportunities": sum(row["period_id"] == period for row in rows),
                "eligible_opportunities": sum(row["period_id"] == period for row in eligible),
                "recurrent_opportunities": sum(row["period_id"] == period and row["recurrent"] is True for row in eligible),
            }
            for period in all_periods
        ],
        "temporal_breadth": _ratio(len(represented_periods), len(all_periods)),
        "segment_breadth": _ratio(len(represented_segments), len(all_segments)),
        "context_denominator": len(rows),
        "scope": "SYNTHETIC_DIAGNOSTIC_NO_TEMPORAL_STABILITY_CLAIM",
    }


def _support_uncertainty(population: Mapping[str, Any]) -> dict[str, Any]:
    rows = population["opportunities"]
    evaluable = [row for row in rows if row["applicability"] == "MICRO_BEARING"]
    ambiguous = 0
    complete_agreement = 0
    for row in evaluable:
        signals = {
            view["supports_target"] for view in row["representation_views"]
            if view["status"] == "COMPUTED"
        }
        if len(signals) > 1 or any(view["status"] != "COMPUTED" for view in row["representation_views"]):
            ambiguous += 1
        elif len(signals) == 1:
            complete_agreement += 1
    return {
        "universal_opportunity_denominator": len(rows),
        "conditional_evaluable_denominator": len(evaluable),
        "complete_view_agreement": _ratio(complete_agreement, len(evaluable)),
        "support_representation_uncertain": _ratio(ambiguous, len(evaluable)),
        "scope": "CONDITIONAL_DIAGNOSTIC_NOT_UNIVERSAL",
    }


def _source_drift(population: Mapping[str, Any]) -> dict[str, Any]:
    rows = population["opportunities"]
    generation_ids = sorted({row["source_generation_id"] for row in rows})
    summaries = []
    for generation in generation_ids:
        generation_rows = [row for row in rows if row["source_generation_id"] == generation]
        eligible = [row for row in generation_rows if row["applicability"] == "MICRO_BEARING"]
        summaries.append(
            {
                "source_generation_id": generation,
                "universal_opportunities": len(generation_rows),
                "eligible_opportunities": len(eligible),
                "recurrent_opportunities": sum(row["recurrent"] is True for row in eligible),
                "target_counts": dict(sorted(Counter(row["target_id"] for row in eligible).items())),
            }
        )
    return {
        "generation_denominator": len(generation_ids),
        "universal_opportunity_denominator": len(rows),
        "generation_summaries": summaries,
        "comparison": "DESCRIPTIVE_COUNT_VECTOR_ONLY",
        "disposition": "NO_EMPIRICAL_SOURCE_DRIFT_CLAIM",
    }


def _opportunity_ledger(population: Mapping[str, Any]) -> dict[str, Any]:
    rows = []
    opportunities = population["opportunities"]
    for specification_id in SPECIFICATIONS:
        for row in opportunities:
            if row["applicability"] != "MICRO_BEARING":
                disposition = "NOT_APPLICABLE"
            elif specification_id == "FG-ROBUST-DECLARED-SET" and any(
                view["status"] != "COMPUTED" for view in row["representation_views"]
            ):
                disposition = "NOT_EVALUABLE_DECLARED_VIEW"
            else:
                disposition = "ELIGIBLE"
            rows.append(
                {
                    "specification_id": specification_id,
                    "opportunity_id": row["opportunity_id"],
                    "disposition": disposition,
                }
            )
    expected = len(SPECIFICATIONS) * len(opportunities)
    return {
        "contract": "TVXGrammarSpecificationOpportunityLedger",
        "specification_denominator": len(SPECIFICATIONS),
        "universal_opportunity_denominator": len(opportunities),
        "row_denominator": expected,
        "rows": rows,
        "complete": len(rows) == expected,
    }


def _design_exposure(population: Mapping[str, Any]) -> dict[str, Any]:
    dimensions = {
        "representation": list(DECLARED_REPRESENTATIONS),
        "antecedent_hierarchy": list(ANTECEDENT_HIERARCHIES),
        "target_hierarchy": list(TARGET_HIERARCHIES),
        "support_threshold": [2, *SUPPORT_SENSITIVITIES],
        "null_family": sorted(NULL_SPECS),
        "source_generation": sorted({row["source_generation_id"] for row in population["opportunities"]}),
        "temporal_period": sorted({row["period_id"] for row in population["opportunities"]}),
        "segment": sorted({row["segment_id"] for row in population["opportunities"]}),
    }
    rows = [
        {"dimension": dimension, "level": str(level), "exposure_status": "PREDECLARED_SYNTHETICALLY_EXERCISED"}
        for dimension, levels in dimensions.items() for level in levels
    ]
    return {
        "contract": "TVXDesignExposureManifest",
        "dimensions": dimensions,
        "rows": rows,
        "row_denominator": sum(len(levels) for levels in dimensions.values()),
        "post_outcome_design_selection": "FORBIDDEN",
        "complete": len(rows) == sum(len(levels) for levels in dimensions.values()),
    }


def _claim_controls(population: Mapping[str, Any]) -> dict[str, Any]:
    periods = sorted({row["period_id"] for row in population["opportunities"]})
    exposure = []
    for claim in CLAIMS:
        exposure.append(
            {
                "claim_id": claim,
                "source_basis": "SYNTHETIC_QUALIFICATION_ONLY",
                "universal_population_denominator": len(population["opportunities"]),
                "status": "NOT_AN_EMPIRICAL_CLAIM",
            }
        )
    return {
        "claim_exposure_matrix": exposure,
        "claim_freshness_cap": {
            "maximum_period_id": periods[-1],
            "cap_basis": "SYNTHETIC_FIXTURE_LAST_PERIOD_ONLY",
            "empirical_freshness": "UNASSESSED_PROTECTED_SOURCE_DENIED",
            "claim_status": "NOT_AN_EMPIRICAL_CLAIM",
        },
    }


def build_diagnostic_pack(population: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = copy.deepcopy(population if population is not None else synthetic_diagnostic_population())
    validate_complete_population(source)
    population_manifest = _population_manifest(source)
    opportunity_ledger = _opportunity_ledger(source)
    design_exposure = _design_exposure(source)
    claim_controls = _claim_controls(source)
    body = {
        "schema": "ovc-c2s-sptoi-factorised-diagnostic-qualification-pack/v0.1",
        "programme_id": "OVC-EML-C2S-SPTO-CONFORMANCE-PREREG-v0.1",
        "packet_id": PACKET_ID,
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": PROTOCOL_SHA256,
        "maturity": DIAGNOSTIC_MATURITY,
        "population_id": source["population_id"],
        "population_manifest": population_manifest,
        "recurrence": _recurrence(source),
        "representation_set_completeness": _representation_completeness(source),
        "backoff_hierarchy_target_sensitivity": _sensitivity(source),
        "temporal_segment_context": _temporal_and_context(source),
        "support_representation_uncertainty": _support_uncertainty(source),
        "source_generation_drift": _source_drift(source),
        "specification_opportunity_ledger": opportunity_ledger,
        "design_exposure_manifest": design_exposure,
        **claim_controls,
        "universal_population_rule": "NO_CONDITIONAL_SURVIVOR_SUBSET_MAY_BE_REPORTED_AS_UNIVERSAL",
        "protected_source_access": "NONE",
        "factorised_evidence_execution": "DENIED",
        "validation": "LOCKED_UNCONSUMED",
        "scientific_claims": "NONE",
        "authority_effect": "NONE_SOURCE_FREE_DIAGNOSTIC_QUALIFICATION_ONLY",
    }
    body = _freeze(body)
    body["pack_id"] = content_id("FactorisedDiagnosticQualificationPack/v1", body)
    return body
