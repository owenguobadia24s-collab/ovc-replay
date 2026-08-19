from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from ovc.research_operations.canonical import canonical_sha256


class IndexValidationError(ValueError):
    pass


def _entry_key(entry: Mapping[str, Any]) -> str:
    value = entry.get("subject_id")
    if type(value) is not str or not value:
        raise IndexValidationError("entry requires stable subject_id")
    return value


def reference_search(entries: Sequence[Mapping[str, Any]], token: str) -> list[str]:
    if type(token) is not str or not token:
        raise IndexValidationError("search token must be non-empty")
    needle = token.casefold()
    return sorted(_entry_key(entry) for entry in entries if needle in _entry_key(entry).casefold())


def _trigrams(text: str) -> set[str]:
    return {text[index : index + 3] for index in range(max(0, len(text) - 2))}


def build_search_index(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    postings: dict[str, set[str]] = defaultdict(set)
    identities: dict[str, str] = {}
    subjects: dict[str, str] = {}
    for entry in entries:
        key = _entry_key(entry)
        if key in identities:
            raise IndexValidationError("duplicate logical entry")
        identities[key] = canonical_sha256(entry)
        subjects[key] = key.casefold()
        for trigram in sorted(_trigrams(subjects[key])):
            postings[trigram].add(key)
    body = {
        "schema": "ovc-p2ctii-search-index/v0.1",
        "search_semantics": "WP4_SUBJECT_ID_CASEFOLD_SUBSTRING",
        "entry_identities": dict(sorted(identities.items())),
        "subjects": dict(sorted(subjects.items())),
        "trigram_postings": {token: sorted(values) for token, values in sorted(postings.items())},
        "canonical": False,
        "rebuildable": True,
        "authority_effect": "NONE",
    }
    return {**body, "index_sha256": canonical_sha256(body)}


def optimized_search(index: Mapping[str, Any], token: str) -> list[str]:
    if type(token) is not str or not token:
        raise IndexValidationError("search token must be non-empty")
    body = {key: value for key, value in index.items() if key != "index_sha256"}
    if index.get("index_sha256") != canonical_sha256(body):
        raise IndexValidationError("index corruption detected")
    if index.get("search_semantics") != "WP4_SUBJECT_ID_CASEFOLD_SUBSTRING":
        raise IndexValidationError("index search semantics mismatch")
    subjects = index.get("subjects")
    postings = index.get("trigram_postings")
    if not isinstance(subjects, Mapping) or not isinstance(postings, Mapping):
        raise IndexValidationError("index structure is invalid")
    needle = token.casefold()
    if len(needle) < 3:
        candidates = set(subjects)
    else:
        grams = sorted(_trigrams(needle))
        posting_sets = [set(postings.get(gram, [])) for gram in grams]
        candidates = set.intersection(*posting_sets) if posting_sets else set(subjects)
    return sorted(key for key in candidates if needle in str(subjects[key]))


def assert_reference_equivalence(entries: Sequence[Mapping[str, Any]], tokens: Sequence[str]) -> dict[str, Any]:
    index = build_search_index(entries)
    mismatches = []
    for token in tokens:
        if optimized_search(index, token) != reference_search(entries, token):
            mismatches.append(token)
    body = {
        "entry_count": len(entries),
        "tokens": sorted(tokens),
        "mismatches": sorted(mismatches),
        "equivalent": not mismatches,
        "index_sha256": index["index_sha256"],
        "authority_effect": "NONE",
    }
    return {**body, "evidence_sha256": canonical_sha256(body)}
