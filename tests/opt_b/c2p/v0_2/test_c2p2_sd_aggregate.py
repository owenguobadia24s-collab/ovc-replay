from __future__ import annotations

import copy
from pathlib import Path

import pytest

from ovc.opt_b.c2p_v0_2.sd_aggregate import (
    ScientificDiscriminationAggregateError,
    aggregate_reanalysis,
    load_json,
)

ROOT = Path(__file__).resolve().parents[4]
R5_RESULT = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_R5_RESULT_v0_1.json"


def test_r5_compact_reanalysis_preserves_no_selection_and_exact_contrast() -> None:
    result = aggregate_reanalysis(load_json(R5_RESULT))

    assert result["population_count_per_candidate"] == 1_489_144
    assert result["candidate_metrics"]["A"]["object_assertions"] == 163_327
    assert result["candidate_metrics"]["B"]["object_assertions"] == 60
    assert result["candidate_metrics"]["C"]["object_assertions"] == 24
    assert result["candidate_metrics"]["A"]["tracklets"] == 624_833
    assert result["candidate_metrics"]["B"]["tracklets"] == 60
    assert result["candidate_metrics"]["C"]["tracklets"] == 24
    assert result["pairwise"][0]["object_assertion_ratio"] == pytest.approx(2722.116666666667)
    assert result["pairwise"][1]["object_assertion_ratio"] == pytest.approx(6805.291666666667)
    assert result["pairwise"][2]["object_assertion_ratio"] == pytest.approx(2.5)
    assert result["selection"]["recommended_candidate"] is None
    assert result["authority_effect"] == "NONE_READ_ONLY_REANALYSIS"


def test_c_episode_enrichment_is_firewalled_as_untested() -> None:
    result = aggregate_reanalysis(load_json(R5_RESULT))
    firewall = result["c_episode_enrichment_firewall"]

    assert firewall == {
        "episode_relative_role_count": 0,
        "r5_observed_disposition": "NOT_APPLICABLE_C2_ONLY",
        "scientific_value_claim": "NOT_EVALUATED",
        "selection_justification": "FORBIDDEN",
    }


def test_reanalysis_fails_closed_on_selection_or_population_drift() -> None:
    source = load_json(R5_RESULT)

    selected = copy.deepcopy(source)
    selected["active_object_pack_id"] = "ILLEGAL"
    with pytest.raises(ScientificDiscriminationAggregateError, match="ACTIVE_PACK_FORBIDDEN"):
        aggregate_reanalysis(selected)

    drifted = copy.deepcopy(source)
    drifted["candidate_results"][0]["scientific_summary"]["counts"]["candidates"] -= 1
    with pytest.raises(ScientificDiscriminationAggregateError, match="POPULATION_COUNT_DRIFT"):
        aggregate_reanalysis(drifted)
