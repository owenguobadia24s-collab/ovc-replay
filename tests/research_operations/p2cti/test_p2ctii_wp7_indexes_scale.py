from __future__ import annotations

import copy

import pytest

from ovc.research_operations.p2cti.indexes import (
    IndexValidationError,
    assert_reference_equivalence,
    build_search_index,
    optimized_search,
)


def _population(size: int) -> list[dict]:
    return [
        {"subject_id": f"theory:{i:05d}", "search_text": f"theory family-{i % 17} method-{i % 11} seed-{i}"}
        for i in range(size)
    ]


@pytest.mark.parametrize("size", [30, 300, 3000])
def test_reference_optimized_equivalence_and_clean_rebuild(size: int) -> None:
    entries = _population(size)
    evidence = assert_reference_equivalence(entries, ["theory", "family-3", "method-7", "missing"])
    assert evidence["equivalent"] is True
    assert evidence["mismatches"] == []
    first = build_search_index(entries)
    second = build_search_index(list(reversed(entries)))
    assert first == second
    assert first["canonical"] is False
    assert first["rebuildable"] is True
    assert first["authority_effect"] == "NONE"


def test_corrupt_index_fails_closed_and_cannot_change_answers() -> None:
    index = build_search_index(_population(30))
    corrupted = copy.deepcopy(index)
    corrupted["postings"]["theory"].pop()
    with pytest.raises(IndexValidationError, match="corruption"):
        optimized_search(corrupted, "theory")


def test_duplicate_logical_entry_is_rejected() -> None:
    entries = _population(2)
    with pytest.raises(IndexValidationError, match="duplicate"):
        build_search_index([entries[0], entries[0]])
