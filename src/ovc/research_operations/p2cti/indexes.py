from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from ovc.research_operations.canonical import canonical_sha256


class IndexValidationError(ValueError):
    pass


def _entry_key(entry: Mapping[str, Any]) -> str:
    value = entry.get("subject_id") or entry.get("entry_id")
    if type(value) is not str or not value:
        raise IndexValidationError("entry requires stable subject_id or entry_id")
    return value


def reference_search(entries: Sequence[Mapping[str, Any]], token: str) -> list[str]:
    needle = token.casefold()
    return sorted(_entry_key(entry) for entry in entries if needle in str(entry.get("search_text", entry)).casefold())


def build_search_index(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    postings: dict[str, set[str]] = defaultdict(set)
    identities: dict[str, str] = {}
    for entry in entries:
        key = _entry_key(entry)
        if key in identities:
            raise IndexValidationError("duplicate logical entry")
        identities[key] = canonical_sha256(entry)
        text = str(entry.get("search_text", "")).casefold()
        for token in sorted(set(text.split())):
            postings[token].add(key)
    body = {
        "schema": "ovc-p2ctii-search-index/v0.1",
        "entry_identities": dict(sorted(identities.items())),
        "postings": {token: sorted(values) for token, values in sorted(postings.items())},
        "canonical": False,
        "rebuildable": True,
        "authority_effect": "NONE",
    }
    return {**body, "index_sha256": canonical_sha256(body)}


def optimized_search(index: Mapping[str, Any], token: str) -> list[str]:
    body = {key: value for key, value in index.items() if key != "index_sha256"}
    if index.get("index_sha256") != canonical_sha256(body):
        raise IndexValidationError("index corruption detected")
    return list(index.get("postings", {}).get(token.casefold(), []))


def assert_reference_equivalence(entries: Sequence[Mapping[str, Any]], tokens: Sequence[str]) -> dict[str, Any]:
    index = build_search_index(entries)
    mismatches = []
    for token in tokens:
        if optimized_search(index, token) != reference_search(entries, token):
            mismatches.append(token)
    body = {"entry_count": len(entries), "tokens": sorted(tokens), "mismatches": sorted(mismatches), "equivalent": not mismatches, "index_sha256": index["index_sha256"], "authority_effect": "NONE"}
    return {**body, "evidence_sha256": canonical_sha256(body)}
