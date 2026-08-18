from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.opt_b.c2p_v0_2.sd_discrimination import (
    CANDIDATE_IDS,
    ScientificDiscriminationError,
    analyze_edge,
    build_blind_review_card,
    make_edge,
    run_streaming_discrimination,
)


def _dispositions(a: str, b: str, c: str) -> dict[str, str]:
    return {CANDIDATE_IDS[0]: a, CANDIDATE_IDS[1]: b, CANDIDATE_IDS[2]: c}


def _edge(
    ordinal: int,
    *,
    dispositions: dict[str, str] | None = None,
    breaks: list[str] | None = None,
    year: int = 2021,
    side: str = "BID",
    clock: str = "15M",
    successor_future: bool = False,
) -> dict:
    fvt = f"{year}-01-01T00:{ordinal % 60:02d}:00Z"
    cutoff = f"{year}-01-01T01:00:00Z"
    successor_time = f"{year}-01-01T02:00:00Z" if successor_future else f"{year}-01-01T00:59:00Z"
    return make_edge(
        prior_source_record_id=f"P-{year}-{side}-{clock}-{ordinal}",
        current_source_record_id=f"C-{year}-{side}-{clock}-{ordinal}",
        first_valid_time=fvt,
        evaluation_cutoff=cutoff,
        instrument="GBPUSD",
        side=side,
        clock=clock,
        structural_role_id="ROLE_LEVEL",
        geometry_kind_id="LEVEL",
        candidate_dispositions=dispositions or _dispositions("SAME", "SAME", "SAME"),
        confirmed_hard_breaks=breaks or [],
        owner_constitution_evidence={"hard_scope_constant": True, "continued_observation_permitted": True},
        review_context={
            "prior": {"source_record_id": f"P-{ordinal}", "first_valid_time": fvt},
            "current": {"source_record_id": f"C-{ordinal}", "first_valid_time": fvt},
            "successor": {"source_record_id": f"S-{ordinal}", "first_valid_time": successor_time},
        },
    )


def test_hard_break_same_is_candidate_level_hard_falsification() -> None:
    record = analyze_edge(
        _edge(
            1,
            dispositions=_dispositions("SAME", "DIFFERENT", "SAME"),
            breaks=["REQUIRED_SOURCE_DISCONTINUITY"],
        )
    )
    assert record["automatic_scientific_label"] == "DIFFERENT"
    assert record["hard_falsification_candidate_ids"] == [CANDIDATE_IDS[0], CANDIDATE_IDS[2]]
    assert record["include_in_disagreement_ledger"] is True


def test_absence_of_break_never_creates_automatic_same_label() -> None:
    record = analyze_edge(_edge(2, dispositions=_dispositions("DIFFERENT", "SAME", "SAME")))
    assert record["confirmed_hard_breaks"] == []
    assert record["automatic_scientific_label"] is None
    assert record["candidate_disagreement"] is True


def test_all_equal_without_break_is_not_a_disagreement_row() -> None:
    record = analyze_edge(_edge(3))
    assert record["candidate_disagreement"] is False
    assert record["include_in_disagreement_ledger"] is False


def test_blind_card_contains_no_candidate_identity_and_censors_future_successor() -> None:
    record = analyze_edge(
        _edge(4, dispositions=_dispositions("AMBIGUOUS", "SAME", "DIFFERENT"), successor_future=True)
    )
    card = build_blind_review_card(record, "C2P2-SD-BLIND-v0.1")
    encoded = json.dumps(card, sort_keys=True)
    for candidate_id in CANDIDATE_IDS:
        assert candidate_id not in encoded
    assert set(card["candidate_disposition_slots"]) == {"X", "Y", "Z"}
    assert "successor" not in card["context"]
    assert card["adjudication_label"] is None


def test_streaming_ledger_keeps_all_hard_cases_and_one_hash_min_representative_per_signature_stratum(tmp_path: Path) -> None:
    edges = [
        _edge(10, dispositions=_dispositions("DIFFERENT", "SAME", "SAME")),
        _edge(11, dispositions=_dispositions("DIFFERENT", "SAME", "SAME")),
        _edge(12, dispositions=_dispositions("SAME", "DIFFERENT", "SAME"), breaks=["DECLARED_GEOMETRY_KIND_CHANGE"]),
        _edge(13, dispositions=_dispositions("SAME", "DIFFERENT", "SAME"), breaks=["DECLARED_GEOMETRY_KIND_CHANGE"]),
        _edge(14, dispositions=_dispositions("AMBIGUOUS", "SAME", "DIFFERENT"), year=2022, side="ASK", clock="2H_A_L"),
    ]
    summary = run_streaming_discrimination(edges, output_dir=tmp_path, blinding_key="C2P2-SD-BLIND-v0.1")

    assert summary["total_edges"] == 5
    assert summary["disagreement_ledger_rows"] == 5
    assert summary["confirmed_hard_break_rows"] == 2
    assert summary["representative_selector_rows"] == 3
    assert summary["blind_review_rows"] == 4
    assert summary["unblinding_map_emitted"] is False
    assert summary["candidate_names_in_review_manifest"] is False
    review_text = (tmp_path / "blind-review-manifest.jsonl").read_text()
    assert all(candidate_id not in review_text for candidate_id in CANDIDATE_IDS)


def test_duplicate_edge_id_fails_closed(tmp_path: Path) -> None:
    edge = _edge(20, dispositions=_dispositions("DIFFERENT", "SAME", "SAME"))
    with pytest.raises(ScientificDiscriminationError, match="DUPLICATE_EDGE_ID"):
        run_streaming_discrimination([edge, dict(edge)], output_dir=tmp_path, blinding_key="blind")


def test_unknown_hard_break_and_future_edge_fail_closed() -> None:
    bad_break = _edge(30, dispositions=_dispositions("SAME", "SAME", "DIFFERENT"))
    bad_break["independent_anchor_evidence"]["confirmed_hard_breaks"] = ["TIME_GAP_HEURISTIC"]
    with pytest.raises(ScientificDiscriminationError, match="HARD_BREAK_INVALID"):
        analyze_edge(bad_break)

    future = make_edge(
        prior_source_record_id="P-FUTURE",
        current_source_record_id="C-FUTURE",
        first_valid_time="2021-01-01T00:31:00Z",
        evaluation_cutoff="2020-12-31T23:59:59Z",
        instrument="GBPUSD",
        side="BID",
        clock="15M",
        structural_role_id="ROLE_LEVEL",
        geometry_kind_id="LEVEL",
        candidate_dispositions=_dispositions("SAME", "SAME", "DIFFERENT"),
    )
    with pytest.raises(ScientificDiscriminationError, match="FUTURE_INFORMATION"):
        analyze_edge(future)
