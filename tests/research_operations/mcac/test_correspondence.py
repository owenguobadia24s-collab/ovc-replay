from __future__ import annotations

from itertools import permutations

import pytest

from ovc.research_operations.mcac.correspondence import CandidateEdge, CorrespondenceRule, correspond, merge_candidate_chunks

from .conftest import context


def e(left, right, score=900000): return CandidateEdge(left, right, f"h-{left}-{right}", score, "GEOM")
def rule(mode="COMPONENT_ALL"): return CorrespondenceRule("RULE-1", "0.1", "GEOM", "GEOM", 500000, mode)


@pytest.mark.parametrize("edges,status", [([e("l1","r1")],"ONE_TO_ONE"),([e("l1","r1"),e("l1","r2")],"ONE_TO_MANY"),([e("l1","r1"),e("l2","r1")],"MANY_TO_ONE"),([e("l1","r1"),e("l2","r1"),e("l2","r2")],"MANY_TO_MANY")])
def test_cardinalities(edges, status):
    result = correspond(context(), rule(), edges)
    assert result.status == status and result.identity_effect == result.composition_effect == "NONE"


def test_no_match_and_missing_are_distinct():
    result = correspond(context(), rule(), [e("l","r",1)], all_left_ids=("l",), all_right_ids=("r",))
    assert result.status == "NO_MATCH" and result.unmatched_left_ids == ("l",)


def test_equal_optimum_is_ambiguous_not_arbitrarily_tied():
    result = correspond(context(), rule("ONE_TO_ONE_BEST"), [e("l1","r1"), e("l1","r2")])
    assert result.status == "AMBIGUOUS" and "MCAC_EQUAL_OPTIMUM_ASSIGNMENT" in result.reason_codes


def test_order_and_chunk_independence():
    edges = [e("l1","r1"), e("l2","r1"), e("l2","r2")]
    hashes = {correspond(context(), rule(), perm).logical_hash for perm in permutations(edges)}
    assert len(hashes) == 1
    assert merge_candidate_chunks((edges[:1], edges[1:])) == merge_candidate_chunks((edges[1:], edges[:1]))


def test_capacity_exceeded_is_incomplete_non_result():
    result = correspond(context(), rule(), [e("l1","r1"), e("l2","r2")], max_candidate_pairs=1)
    assert result.status == "CAPACITY_EXCEEDED" and not result.complete and not result.groups
