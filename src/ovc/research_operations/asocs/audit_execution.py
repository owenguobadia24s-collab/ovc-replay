"""ASOCS WP4 fail-closed audit adapter and execution harness.

This module deliberately does not construct active OPT-A/C1 SourceBar identities for the
unresolved Darwinex single stream.  It reuses the frozen C1 arithmetic implementation only
through the fields that implementation actually consumes.  All upper active-stack constructs
remain NOT_EVALUABLE until a lawful exact side/clock/release input exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Any

from ovc.opt_b.c1.formulas import calculate as calculate_c1

AUTHORITY_CLASS = "ASOCS_AUDIT_ONLY"
CLAIM_CLASS = "ASOCS_SINGLE_STREAM_MORPHOLOGY_COHERENCE"
SOURCE_SIDE_STATE = "UNRESOLVED_SINGLE_STREAM"
SOURCE_CLOCK_STATE = "SOURCE_TIMEZONE_UNRESOLVED"

UPPER_CONSTRUCTS = (
    "C2_OBSERVATION", "C2_HORIZON", "C2_LEVEL", "C2_CONTAINER",
    "C2_RELATION", "C2_FORMULA", "C2_TRANSITION", "C2_PARENT_CONTEXT",
    "C2_COMPUTABILITY", "C2E_EPISODE", "C2E_PHASE",
    "OCCURRENCE_CONTEXT_ATTACHMENT",
)

FORBIDDEN_SEMANTIC_INPUT_KEYS = {
    "release_id", "manifest_id", "research_role", "clock_id", "price_side",
    "side", "timezone", "selector_state", "authority_state",
    "validation_consumption_state", "candidate", "family", "outcome",
    "validation", "deferred_layer",
}


class ASOCSAuditRouteError(ValueError):
    pass


@dataclass(frozen=True)
class MorphologyBar:
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    price_increment: Decimal | None = None


def _decimal(value: object) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def morphology_bar(source: Mapping[str, object]) -> MorphologyBar:
    leaked = sorted(FORBIDDEN_SEMANTIC_INPUT_KEYS.intersection(source))
    if leaked:
        raise ASOCSAuditRouteError("FORBIDDEN_SEMANTIC_INPUT:" + ",".join(leaked))
    required = {"open", "high", "low", "close"}
    if not required.issubset(source):
        raise ASOCSAuditRouteError("MISSING_OHLC")
    o, h, l, c = (_decimal(source[k]) for k in ("open", "high", "low", "close"))
    if h < max(o, c) or l > min(o, c) or h < l:
        raise ASOCSAuditRouteError("OHLC_ENVELOPE_INVALID")
    return MorphologyBar(o, h, l, c, None)


def route_for_construct(construct: str) -> str:
    if construct == "C1_ARITHMETIC_PRIMITIVES":
        return "MORPHOLOGY_COMPATIBLE"
    if construct in UPPER_CONSTRUCTS:
        return "NOT_EVALUABLE"
    raise ASOCSAuditRouteError("UNKNOWN_CONSTRUCT:" + str(construct))


def evaluate_c1_morphology(
    current: Mapping[str, object],
    *,
    prior: Mapping[str, object] | None = None,
    prior_contiguous: bool = False,
) -> dict[str, Any]:
    current_bar = morphology_bar(current)
    prior_bar = morphology_bar(prior) if prior is not None and prior_contiguous else None
    prior_reason = None if prior_bar is not None else "SOURCE_CONTINUITY_UNRESOLVED_OR_GAP"
    measurements, categorical, null_reasons = calculate_c1(
        current_bar, prior_bar, prior_reason
    )
    return {
        "schema": "ovc-asocs-c1-morphology-audit/v0_1",
        "construct": "C1_ARITHMETIC_PRIMITIVES",
        "route": "MORPHOLOGY_COMPATIBLE",
        "claim_class": CLAIM_CLASS,
        "source_side_state": SOURCE_SIDE_STATE,
        "source_clock_state": SOURCE_CLOCK_STATE,
        "measurements": measurements,
        "categorical": categorical,
        "null_reasons": null_reasons,
        "implementation": "ovc.opt_b.c1.formulas.calculate",
        "exact_active_interface": "NOT_EVALUABLE_EXACT_ACTIVE_INTERFACE",
        "authority_class": AUTHORITY_CLASS,
        "active": False,
        "canonical": False,
        "publication": False,
    }


def not_evaluable_record(construct: str) -> dict[str, Any]:
    if route_for_construct(construct) != "NOT_EVALUABLE":
        raise ASOCSAuditRouteError("CONSTRUCT_HAS_MORPHOLOGY_ROUTE:" + construct)
    return {
        "schema": "ovc-asocs-not-evaluable-trace/v0_1",
        "construct": construct,
        "disposition": "NOT_EVALUABLE",
        "reason_codes": [
            "NO_LAWFUL_ACTIVE_INPUT_IDENTITY",
            "PRICE_SIDE_UNRESOLVED",
            "TIMESTAMP_TIMEZONE_UNRESOLVED",
            "NO_MEANING_BEARING_SHADOW_REIMPLEMENTATION",
        ],
        "authority_class": AUTHORITY_CLASS,
        "active": False,
        "canonical": False,
        "publication": False,
    }
