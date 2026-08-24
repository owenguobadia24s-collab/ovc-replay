from __future__ import annotations

import copy
import json
import time

import pytest

from ovc.research_operations.p1cdi.indexes import (
    P1CDICapacityExceeded,
    P1CDIIndexError,
    assert_reference_equivalence,
    build_search_index,
    measure_review_queue,
    optimized_search,
    reference_search,
)
from ovc.research_operations.p1cdi.visibility import (
    build_visibility_decision,
    build_visibility_safe_index_entry,
)


def _population(size: int) -> list[dict]:
    decision = build_visibility_decision(
        source_ref="synthetic:wp8",
        classification="PATH1_SAFE",
        classification_complete=True,
    )
    rows = []
    for index in range(size):
        entry = build_visibility_safe_index_entry(
            decision=decision,
            record={
                "generation_id": f"p1:generation:synthetic:{index:05d}",
                "title": f"Synthetic structural distinction {index:05d}",
                "state": "CURRENT" if index % 2 == 0 else "HISTORICAL",
                "review": {
                    "review_required": index % 3 == 0,
                    "state": "UNRESOLVED" if index % 11 == 0 else "RESOLVED",
                    "reopened": index % 17 == 0,
                    "queue_age_units": index % 7,
                    "reviewer_effort_units": index % 5,
                },
            },
        )
        assert entry is not None
        rows.append(entry)
    return rows


@pytest.mark.parametrize("size", [0, 300, 3000])
def test_reference_optimized_equivalence_clean_rebuild_and_scale(size: int, capsys) -> None:
    entries = _population(size)
    started = time.perf_counter()
    evidence = assert_reference_equivalence(
        entries, ["synthetic", "structural distinction", "000", "current", "missing"]
    )
    first = build_search_index(entries)
    second = build_search_index(list(reversed(entries)))
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)

    assert evidence["equivalent"] is True
    assert evidence["mismatches"] == []
    assert first == second
    assert first["population_complete"] is True
    assert first["silent_truncation"] == "FORBIDDEN"
    assert first["sampling"] == "FORBIDDEN"
    assert first["canonical"] is False
    assert first["rebuildable"] is True
    assert first["authority_effect"] == "NONE"

    measurement = {
        "packet_id": "P1CDII-WP8",
        "tier_size": size,
        "elapsed_ms_informational": elapsed_ms,
        "index_sha256": first["index_sha256"],
        "equivalence_evidence_sha256": evidence["evidence_sha256"],
        "threshold_effect": "NONE",
    }
    print("P1CDII_WP8_MEASUREMENT " + json.dumps(measurement, sort_keys=True))
    captured = capsys.readouterr().out
    assert "P1CDII_WP8_MEASUREMENT" in captured


def test_search_semantics_match_reference_for_casefold_infix_short_and_missing() -> None:
    entries = _population(30)
    index = build_search_index(entries)
    for token in ("SYNTHETIC", "structural distinction 0001", "5", "missing"):
        assert optimized_search(index, token) == reference_search(entries, token)


def test_corrupt_index_fails_closed_and_cannot_change_answers() -> None:
    index = build_search_index(_population(30))
    corrupted = copy.deepcopy(index)
    posting_key = next(iter(corrupted["trigram_postings"]))
    corrupted["trigram_postings"][posting_key].clear()
    with pytest.raises(P1CDIIndexError, match="corruption"):
        optimized_search(corrupted, "synthetic")


def test_duplicate_logical_entry_is_rejected() -> None:
    entries = _population(2)
    with pytest.raises(P1CDIIndexError, match="duplicate"):
        build_search_index([entries[0], entries[0]])


def test_capacity_failure_preserves_complete_population_and_never_samples() -> None:
    entries = _population(30)
    with pytest.raises(P1CDICapacityExceeded, match="CAPACITY_EXCEEDED"):
        build_search_index(entries, capacity_limit=29)
    assert len(build_search_index(entries, capacity_limit=30)["entry_identities"]) == 30


def test_visibility_is_a_hard_precondition_for_indexing() -> None:
    unsafe = {
        "record_type": "P1CDIVisibilitySafeIndexEntry",
        "schema_version": "0.1",
        "entry_id": "unsafe",
        "visibility_decision_id": "missing",
        "record": {"title": "must not index"},
        "classified_before_indexing": False,
        "authority_effect": "NONE",
    }
    with pytest.raises(PermissionError, match="classified before indexing"):
        build_search_index([unsafe])


def test_review_load_is_measured_without_creating_a_threshold() -> None:
    measurement = measure_review_queue(_population(300))
    assert measurement["measured_records"] == 300
    assert measurement["review_required_count"] == 100
    assert measurement["unresolved_count"] > 0
    assert measurement["reopened_count"] > 0
    assert measurement["queue_age_units"] > 0
    assert measurement["reviewer_effort_units"] > 0
    assert measurement["threshold_effect"] == "NONE"
    assert measurement["authority_effect"] == "NONE"
