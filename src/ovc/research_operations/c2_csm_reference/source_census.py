"""Deterministic source-sufficiency classification for P3-R5-T2-S2.

WP1 is deliberately incapable of reconstructing historical mechanics.  It only
classifies whether exact implementation-bearing source is present.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

LOAD_BEARING_SEMANTICS = (
    "P3_FORMATION_LIFECYCLE",
    "R5_BOUNDARY_ROLE_SUCCESSION",
    "T2_ATOMIC_COMPOUND_TRANSITIONS",
    "S2_SNAPSHOT_SUCCESSION_LEDGER",
)

_EXACT_BINDING = "EXACT_IMPLEMENTATION_BOUND"
_DERIVED = "SOURCE_DERIVED"


def _sources(manifest: Mapping[str, object]) -> Sequence[Mapping[str, object]]:
    value = manifest.get("sources")
    if not isinstance(value, list):
        raise ValueError("sources must be a list")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError("every source must be an object")
    return value  # type: ignore[return-value]


def validate_no_derived_semantic_promotion(manifest: Mapping[str, object]) -> None:
    """Reject any SOURCE_DERIVED source allowed to define implementation semantics."""

    for source in _sources(manifest):
        confidence = source.get("source_confidence")
        binding = source.get("implementation_binding")
        if confidence == _DERIVED and binding == _EXACT_BINDING:
            raise ValueError(
                f"SOURCE_DERIVED source {source.get('source_id')!r} cannot be implementation-bearing"
            )


def classify_source_completeness(manifest: Mapping[str, object]) -> tuple[str, tuple[str, ...]]:
    """Return the reference completeness state and missing load-bearing semantics.

    A semantic is covered only when at least one source explicitly supports it
    and is EXACT_IMPLEMENTATION_BOUND. Exact result/consumer artifacts remain
    evidence-only and do not satisfy the gate.
    """

    validate_no_derived_semantic_promotion(manifest)
    covered: set[str] = set()
    for source in _sources(manifest):
        if source.get("implementation_binding") != _EXACT_BINDING:
            continue
        supports = source.get("supports", [])
        if not isinstance(supports, list):
            raise ValueError("supports must be a list")
        covered.update(str(item) for item in supports if item in LOAD_BEARING_SEMANTICS)

    missing = tuple(item for item in LOAD_BEARING_SEMANTICS if item not in covered)
    status = "REFERENCE_COMPLETE" if not missing else "REFERENCE_PARTIAL_SOURCE_LIMITED"
    return status, missing
