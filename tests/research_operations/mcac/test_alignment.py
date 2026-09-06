from __future__ import annotations

import pytest

from ovc.research_operations.mcac.alignment import INVERSE, Relation, align, temporal_containment

from .conftest import context, occurrence


CASES = [
    ((0, 0), (0, 0), "POINT", "POINT", Relation.EQUAL_POINT), ((0, 0), (1, 1), "POINT", "POINT", Relation.BEFORE),
    ((0, 0), (0, 2), "POINT", "CLOSED_INTERVAL", Relation.POINT_AT_START), ((1, 1), (0, 2), "POINT", "CLOSED_INTERVAL", Relation.POINT_INSIDE),
    ((2, 2), (0, 2), "POINT", "CLOSED_INTERVAL", Relation.POINT_AT_END), ((0, 2), (0, 2), "CLOSED_INTERVAL", "CLOSED_INTERVAL", Relation.EQUAL_INTERVAL),
    ((0, 1), (1, 2), "CLOSED_INTERVAL", "CLOSED_INTERVAL", Relation.MEETS), ((0, 1), (2, 3), "CLOSED_INTERVAL", "CLOSED_INTERVAL", Relation.BEFORE),
    ((0, 1), (0, 2), "CLOSED_INTERVAL", "CLOSED_INTERVAL", Relation.STARTS), ((1, 2), (0, 2), "CLOSED_INTERVAL", "CLOSED_INTERVAL", Relation.FINISHES),
    ((1, 2), (0, 3), "CLOSED_INTERVAL", "CLOSED_INTERVAL", Relation.DURING), ((0, 3), (1, 2), "CLOSED_INTERVAL", "CLOSED_INTERVAL", Relation.CONTAINS),
    ((0, 2), (1, 3), "CLOSED_INTERVAL", "CLOSED_INTERVAL", Relation.OVERLAPS),
]


def t(hour): return f"2020-01-01T{hour:02d}:00:00Z"


@pytest.mark.parametrize("lb,rb,lk,rk,expected", CASES)
def test_primary_relations_and_inverse(lb, rb, lk, rk, expected):
    ctx = context(); l = occurrence(ctx.left_coordinate, ctx.left_registry, "l", t(lb[0]), t(lb[1]), kind=lk); r = occurrence(ctx.right_coordinate, ctx.right_registry, "r", t(rb[0]), t(rb[1]), kind=rk)
    actual = align(ctx, l, r)
    assert actual.relation == expected
    assert INVERSE[INVERSE[actual.relation]] == actual.relation
    reverse_ctx = context(ctx.right_coordinate, ctx.left_coordinate)
    assert align(reverse_ctx, r, l).relation == INVERSE[expected]


def test_containment_never_claims_composition():
    ctx = context(); l = occurrence(ctx.left_coordinate, ctx.left_registry, "l", t(0), t(3)); r = occurrence(ctx.right_coordinate, ctx.right_registry, "r", t(1), t(2))
    result = align(ctx, l, r)
    assert temporal_containment(result) is True
    assert "composition" not in result.semantic_dict()


@pytest.mark.parametrize("change,status,reason", [("gap","NOT_COMPARABLE","MCAC_SOURCE_GAP"),("missing","NOT_EVALUABLE","MCAC_REQUIRED_INPUT_MISSING"),("segment","NOT_EVALUABLE","MCAC_CONTINUITY_SEGMENT_MISSING"),("generation","NOT_COMPARABLE","MCAC_GENERATION_MISMATCH")])
def test_fail_closed_states(change, status, reason):
    ctx = context(); kwargs = {"gap": "PRESENT"} if change == "gap" else ({"missing": "ENDPOINT"} if change == "missing" else ({"segment": None} if change == "segment" else {"generation": "OTHER"}))
    left = occurrence(ctx.left_coordinate, ctx.left_registry, "l", t(0), t(1), **kwargs); right = occurrence(ctx.right_coordinate, ctx.right_registry, "r", t(0), t(2))
    result = align(ctx, left, right)
    assert result.status == status and reason in result.reason_codes and result.relation is None


def test_censoring_is_explicit_when_endpoints_remain():
    ctx = context(); left = occurrence(ctx.left_coordinate, ctx.left_registry, "l", t(0), t(1), censor="RIGHT_BOUNDED"); right = occurrence(ctx.right_coordinate, ctx.right_registry, "r", t(0), t(2))
    assert align(ctx, left, right).censoring_state == "PRESENT_BOUNDED"
