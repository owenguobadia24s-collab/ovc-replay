from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from ovc.research_operations.canonical import canonical_sha256
from ovc.research_operations.p1cdi.identity import build_semantic_projection
from ovc.research_operations.p1cdi.reference import (
    ReferenceEngineError,
    assign_series_generation,
    stage_correspondence,
)


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads(
    (ROOT / "fixtures/research_operations/p1cdi/P1CDII_WP4_REFERENCE_FIXTURES_v0_1.json").read_text()
)


def new_bundle(fields: dict | None = None, when: str | None = None) -> dict:
    return assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=fields or FIXTURE["identity_a"],
        source_first_valid_time=when or FIXTURE["first_valid_time"],
    )


def existing(result: dict) -> dict:
    return {key: copy.deepcopy(result[key]) for key in ("series", "generation", "projection")}


def stage_partial(
    bundle: dict,
    *,
    left_history: list[dict] | None = None,
    right_history: list[dict] | None = None,
) -> dict:
    return stage_correspondence(
        left_projection=bundle["projection"],
        right_projection=copy.deepcopy(bundle["projection"]),
        left_generation_record=bundle["generation"],
        right_generation_record=bundle["generation"],
        left_identity_history=[] if left_history is None else left_history,
        right_identity_history=[] if right_history is None else right_history,
        planes=FIXTURE["exact_planes"],
        admission_basis="EXACT_CANONICAL_BYTES",
    )


def forged_orphan_bundle() -> dict:
    projection_sha = new_bundle()["projection"]["projection_sha256"]
    series_id = "p1:series:orphan-remediation-4"
    source_time = FIXTURE["first_valid_time"]
    generation_id = "p1:generation:" + canonical_sha256(
        {
            "series_id": series_id,
            "projection_sha256": projection_sha,
            "source_first_valid_time": source_time,
        }
    )
    projection = build_semantic_projection(
        generation_id=generation_id,
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=FIXTURE["identity_a"],
    )
    generation = {
        "record_type": "P1EmpiricalDistinctionGeneration",
        "schema_version": "0.1",
        "authority_effect": "NONE",
        "generation_id": generation_id,
        "series_id": series_id,
        "profile_id": projection["profile_id"],
        "projection_sha256": projection["projection_sha256"],
        "source_first_valid_time": source_time,
        "immutable": True,
    }
    series = {
        "record_type": "P1EmpiricalDistinctionSeries",
        "schema_version": "0.1",
        "authority_effect": "NONE",
        "series_id": series_id,
        "first_generation_id": generation_id,
        "predecessor_series_refs": [],
    }
    return {"series": series, "generation": generation, "projection": projection}


def test_forged_orphan_series_id_is_rejected_before_any_correspondence_plane_result() -> None:
    forged = forged_orphan_bundle()
    with pytest.raises(ReferenceEngineError, match="series/root identity history"):
        stage_partial(forged)


def test_forged_orphan_series_record_does_not_self_authorise_root_identity() -> None:
    forged = forged_orphan_bundle()
    with pytest.raises(ReferenceEngineError, match="series"):
        stage_partial(
            forged,
            left_history=[existing(forged)],
            right_history=[existing(forged)],
        )


def test_direct_deterministic_first_generation_remains_valid_without_history_reconstruction() -> None:
    first = new_bundle()
    result = stage_partial(first)
    assert result["semantic_identity"] == "EXACT"
    assert result["record"] is None
    assert result["executability"] == "BLOCKED_UNRESOLVED_PLANES"


def test_lawful_successor_requires_and_accepts_canonical_root_history() -> None:
    first = new_bundle()
    successor = assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=FIXTURE["identity_b"],
        source_first_valid_time="2026-02-01T00:00:00Z",
        existing=[existing(first)],
        predecessor_generation_id=first["generation"]["generation_id"],
        source_explicit_successor_ref="fixture:source:remediation-4:successor",
    )
    with pytest.raises(ReferenceEngineError, match="series/root identity history"):
        stage_partial(successor)
    history = [existing(first), existing(successor)]
    result = stage_partial(successor, left_history=history, right_history=history)
    assert result["semantic_identity"] == "EXACT"
    assert result["record"] is None
    assert result["authority_effect"] == "NONE"


def test_successor_history_missing_first_generation_root_fails_closed() -> None:
    first = new_bundle()
    successor = assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=FIXTURE["identity_b"],
        source_first_valid_time="2026-02-01T00:00:00Z",
        existing=[existing(first)],
        predecessor_generation_id=first["generation"]["generation_id"],
        source_explicit_successor_ref="fixture:source:remediation-4:successor",
    )
    with pytest.raises(ReferenceEngineError, match="first-generation binding"):
        stage_partial(
            successor,
            left_history=[existing(successor)],
            right_history=[existing(successor)],
        )


def test_mismatched_first_generation_root_is_rejected() -> None:
    first = new_bundle()
    successor = assign_series_generation(
        owner_semantic_binding=FIXTURE["owner_semantic_binding"],
        identity_fields=FIXTURE["identity_b"],
        source_first_valid_time="2026-02-01T00:00:00Z",
        existing=[existing(first)],
        predecessor_generation_id=first["generation"]["generation_id"],
        source_explicit_successor_ref="fixture:source:remediation-4:successor",
    )
    bad_first = existing(first)
    bad_first["series"]["first_generation_id"] = "p1:generation:missing-root"
    with pytest.raises(ReferenceEngineError, match="first-generation binding"):
        stage_partial(
            successor,
            left_history=[bad_first, existing(successor)],
            right_history=[bad_first, existing(successor)],
        )
