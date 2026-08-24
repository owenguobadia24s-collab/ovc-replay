from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from ovc.research_operations.canonical import canonical_json_bytes, canonical_sha256


class P1CDIIndexError(ValueError):
    """A rebuildable P1CDI index cannot preserve exact reference semantics."""


class P1CDICapacityExceeded(P1CDIIndexError):
    """The declared complete population cannot be indexed within the bound capacity."""


def _entry_id(entry: Mapping[str, Any]) -> str:
    if not isinstance(entry, Mapping):
        raise P1CDIIndexError("index entry must be an object")
    if entry.get("record_type") != "P1CDIVisibilitySafeIndexEntry":
        raise P1CDIIndexError("indexing requires a P1CDIVisibilitySafeIndexEntry")
    if entry.get("schema_version") != "0.1":
        raise P1CDIIndexError("visibility-safe index entry schema mismatch")
    if entry.get("classified_before_indexing") is not True:
        raise PermissionError("visibility must be classified before indexing")
    if entry.get("authority_effect") != "NONE":
        raise PermissionError("P1CDI indexes may not carry authority")
    value = entry.get("entry_id")
    if type(value) is not str or not value:
        raise P1CDIIndexError("index entry requires stable entry_id")
    record = entry.get("record")
    if not isinstance(record, Mapping):
        raise P1CDIIndexError("visibility-safe index entry requires a projected record")
    return value


def _search_text(entry: Mapping[str, Any]) -> str:
    _entry_id(entry)
    try:
        encoded = canonical_json_bytes(entry["record"], trailing_newline=False)
    except (TypeError, ValueError) as exc:
        raise P1CDIIndexError("visibility-safe record is not canonical JSON") from exc
    return encoded.decode("utf-8").casefold()


def _trigrams(text: str) -> set[str]:
    return {text[index : index + 3] for index in range(max(0, len(text) - 2))}


def reference_search(entries: Sequence[Mapping[str, Any]], token: str) -> list[str]:
    """Authoritative exhaustive substring search over already visibility-safe records."""

    if type(token) is not str or not token:
        raise P1CDIIndexError("search token must be non-empty")
    needle = token.casefold()
    results: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        key = _entry_id(entry)
        if key in seen:
            raise P1CDIIndexError("duplicate logical index entry")
        seen.add(key)
        if needle in _search_text(entry):
            results.append(key)
    return sorted(results)


def build_search_index(
    entries: Sequence[Mapping[str, Any]], *, capacity_limit: int | None = None
) -> dict[str, Any]:
    """Build a deterministic disposable index without sampling or semantic weakening."""

    if capacity_limit is not None:
        if type(capacity_limit) is not int or capacity_limit < 0:
            raise P1CDIIndexError("capacity_limit must be a non-negative integer")
        if len(entries) > capacity_limit:
            raise P1CDICapacityExceeded(
                f"CAPACITY_EXCEEDED: complete population {len(entries)} exceeds {capacity_limit}"
            )

    postings: dict[str, set[str]] = defaultdict(set)
    entry_identities: dict[str, str] = {}
    search_text: dict[str, str] = {}
    for entry in entries:
        key = _entry_id(entry)
        if key in entry_identities:
            raise P1CDIIndexError("duplicate logical index entry")
        entry_identities[key] = canonical_sha256(entry)
        text = _search_text(entry)
        search_text[key] = text
        for trigram in sorted(_trigrams(text)):
            postings[trigram].add(key)

    body = {
        "schema": "ovc-p1cdii-search-index/v0.1",
        "search_semantics": "WP8_VISIBILITY_SAFE_CANONICAL_RECORD_CASEFOLD_SUBSTRING",
        "entry_identities": dict(sorted(entry_identities.items())),
        "search_text": dict(sorted(search_text.items())),
        "trigram_postings": {
            token: sorted(values) for token, values in sorted(postings.items())
        },
        "population_complete": True,
        "silent_truncation": "FORBIDDEN",
        "sampling": "FORBIDDEN",
        "canonical": False,
        "rebuildable": True,
        "authority_effect": "NONE",
    }
    return {**body, "index_sha256": canonical_sha256(body)}


def _validate_index(index: Mapping[str, Any]) -> None:
    body = {key: value for key, value in index.items() if key != "index_sha256"}
    if index.get("index_sha256") != canonical_sha256(body):
        raise P1CDIIndexError("index corruption detected")
    if index.get("schema") != "ovc-p1cdii-search-index/v0.1":
        raise P1CDIIndexError("index schema mismatch")
    if index.get("search_semantics") != "WP8_VISIBILITY_SAFE_CANONICAL_RECORD_CASEFOLD_SUBSTRING":
        raise P1CDIIndexError("index search semantics mismatch")
    if (
        index.get("population_complete") is not True
        or index.get("silent_truncation") != "FORBIDDEN"
        or index.get("sampling") != "FORBIDDEN"
    ):
        raise P1CDIIndexError("index completeness contract is invalid")
    if index.get("canonical") is not False or index.get("rebuildable") is not True:
        raise P1CDIIndexError("P1CDI index must remain disposable and rebuildable")
    if index.get("authority_effect") != "NONE":
        raise PermissionError("P1CDI index cannot grant authority")
    if not isinstance(index.get("search_text"), Mapping) or not isinstance(
        index.get("trigram_postings"), Mapping
    ):
        raise P1CDIIndexError("index structure is invalid")


def optimized_search(index: Mapping[str, Any], token: str) -> list[str]:
    """Optimized search whose result set must remain byte-for-byte reference-equivalent."""

    if type(token) is not str or not token:
        raise P1CDIIndexError("search token must be non-empty")
    _validate_index(index)
    search_text = index["search_text"]
    postings = index["trigram_postings"]
    needle = token.casefold()
    if len(needle) < 3:
        candidates = set(search_text)
    else:
        grams = sorted(_trigrams(needle))
        sets = [set(postings.get(gram, [])) for gram in grams]
        candidates = set.intersection(*sets) if sets else set(search_text)
    return sorted(key for key in candidates if needle in str(search_text[key]))


def assert_reference_equivalence(
    entries: Sequence[Mapping[str, Any]], tokens: Sequence[str]
) -> dict[str, Any]:
    index = build_search_index(entries)
    mismatches: list[str] = []
    for token in tokens:
        if optimized_search(index, token) != reference_search(entries, token):
            mismatches.append(token)
    body = {
        "record_type": "P1CDIReferenceOptimizedEquivalenceReceipt",
        "schema_version": "0.1",
        "entry_count": len(entries),
        "tokens": sorted(tokens),
        "mismatches": sorted(mismatches),
        "equivalent": not mismatches,
        "index_sha256": index["index_sha256"],
        "authority_effect": "NONE",
    }
    return {**body, "evidence_sha256": canonical_sha256(body)}


def measure_review_queue(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Measure review load without turning review pressure into a scientific threshold."""

    total = 0
    review_required = 0
    unresolved = 0
    reopened = 0
    queue_age_units = 0
    reviewer_effort_units = 0
    for entry in entries:
        _entry_id(entry)
        record = entry["record"]
        review = record.get("review")
        if review is None:
            continue
        if not isinstance(review, Mapping):
            raise P1CDIIndexError("review metadata must be an object")
        total += 1
        required = review.get("review_required")
        if type(required) is not bool:
            raise P1CDIIndexError("review_required must be boolean")
        review_required += int(required)
        unresolved += int(review.get("state") == "UNRESOLVED")
        reopened += int(review.get("reopened") is True)
        age = review.get("queue_age_units", 0)
        effort = review.get("reviewer_effort_units", 0)
        if type(age) is not int or age < 0 or type(effort) is not int or effort < 0:
            raise P1CDIIndexError("review load units must be non-negative integers")
        queue_age_units += age
        reviewer_effort_units += effort
    body = {
        "record_type": "P1CDIReviewLoadMeasurement",
        "schema_version": "0.1",
        "measured_records": total,
        "review_required_count": review_required,
        "unresolved_count": unresolved,
        "reopened_count": reopened,
        "queue_age_units": queue_age_units,
        "reviewer_effort_units": reviewer_effort_units,
        "threshold_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {**body, "measurement_sha256": canonical_sha256(body)}
