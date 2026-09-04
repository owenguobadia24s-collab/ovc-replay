from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.lsiac.pass1 import (
    EXPECTED_PASSPORT_COUNT,
    EXPECTED_SUBJECT_COUNT,
    build_pass1_classification_view,
    build_shared_locator_dependence_graph,
    build_virtual_view_identity,
    load_source_passports,
)


ROOT = Path(__file__).resolve().parents[3]
SUMMARY = ROOT / "docs/programmes/lsiac-v0-1/source-census/LSIAC_LABORATORY_SOURCE_PASSPORTS_v0_1.json"
ALGORITHM_BLOB_SHA = "c3e840fcb55b6c7eeaac4fdec07e6e069592dabc"
EXPECTED_VIRTUAL_VIEW_ID = "22b9ffabbc18eb856fa0ffbc8938aa8a73d5e1e412e7401240b0c3ebb95e4816"


def _by_subject(view):
    return {row["subject_id"]: row for row in view["classifications"]}


def test_frozen_passports_reconstruct_completely() -> None:
    passports = load_source_passports(ROOT)
    assert len(passports) == EXPECTED_PASSPORT_COUNT == 434
    assert len({passport["subject_id"] for passport in passports}) == EXPECTED_SUBJECT_COUNT == 432


def test_pass1_accounts_for_all_432_subjects_without_survival_outputs() -> None:
    view = build_pass1_classification_view(ROOT)
    assert view["subject_count"] == EXPECTED_SUBJECT_COUNT
    assert view["passport_count"] == EXPECTED_PASSPORT_COUNT
    assert len(view["classifications"]) == EXPECTED_SUBJECT_COUNT
    assert len({row["subject_id"] for row in view["classifications"]}) == EXPECTED_SUBJECT_COUNT
    assert view["pass1_only"] is True
    assert view["dependence_absence_rule"] == "NO_EDGE_DOES_NOT_ESTABLISH_INDEPENDENCE"

    forbidden_fields = {
        "inheritance_roles",
        "inheritance_role",
        "lifecycle_state",
        "destination_binding_set",
        "architecture_effect_set",
        "retain_forward",
        "scientific_promotion",
        "surviving_statement",
    }
    for record in view["classifications"]:
        assert forbidden_fields.isdisjoint(record)
        assert record["authority_effect"] == "NONE_PASS1_CLASSIFICATION_ONLY"

    for field_counts in view["counts"].values():
        assert sum(field_counts.values()) == EXPECTED_SUBJECT_COUNT


def test_exact_post_v05_negative_subjects_keep_source_supported_disposition_and_exposure() -> None:
    records = _by_subject(build_pass1_classification_view(ROOT))
    for subject_id in (
        "OVC-MULTICLOCK-NONLINEAR-DYNAMICS-0005",
        "OVC-MULTICLOCK-PERSISTENCE-DWELL-0006",
        "OVC-MULTICLOCK-SUCCESSOR-SEQUENCE-0005-0006-FINAL-SYNTHESIS",
    ):
        record = records[subject_id]
        assert record["source_standing"] == "SOURCE_EXACT"
        assert record["scientific_disposition"] == "NEGATIVE_SUPPORTED"
        assert record["exposure_state"] == "DEVELOPMENT_EXPOSED"


def test_source_blocked_nominated_subjects_fail_closed() -> None:
    records = _by_subject(build_pass1_classification_view(ROOT))
    for subject_id in (
        "OVC-REPRESENTATION-ROBUSTNESS-0001-SOURCE-BINDING",
        "OVC-RRSCG-OBSERVER-STATE-GEOMETRY-0001-SOURCE-BINDING",
    ):
        record = records[subject_id]
        assert record["source_standing"] == "PENDING_SOURCE_BINDING"
        assert record["scientific_disposition"] == "NOT_EVALUABLE"
        assert record["exposure_state"] == "UNKNOWN"
        assert record["triage_class"] == "SOURCE_BLOCKED"
        assert "PENDING_SOURCE_BINDING" in record["source_blockers"]
        assert "ARTIFACT_MISSING" in record["source_blockers"]


def test_observer_state_sufficiency_frontier_remains_unresolved_derived_context() -> None:
    records = _by_subject(build_pass1_classification_view(ROOT))
    record = records["OVC-OBSERVER-STATE-SUFFICIENCY-AND-GAMMA-ROBUSTNESS-FRONTIER"]
    assert record["source_standing"] == "SOURCE_DERIVED"
    assert record["scientific_disposition"] == "UNRESOLVED"
    assert record["exposure_state"] == "UNKNOWN"
    assert "EXACT_LOAD_BEARING_SOURCE_NOT_BOUND_FOR_STRONGER_CLAIM" in record["source_blockers"]


def test_dependence_graph_never_infers_independence_from_missing_edge() -> None:
    passports = load_source_passports(ROOT)
    graph = build_shared_locator_dependence_graph(passports)
    assert set(graph) == {
        "schema",
        "generation_id",
        "subject_count",
        "edges",
        "authority_effect",
        "canonical_sha256",
    }
    assert graph["subject_count"] == EXPECTED_SUBJECT_COUNT
    assert all(edge["dependence_class"] == "SHARED_SOURCE_DEPENDENT" for edge in graph["edges"])
    assert not any(edge["dependence_class"] == "INDEPENDENT_BY_FROZEN_CRITERION" for edge in graph["edges"])


def test_virtual_pass1_view_identity_is_stable() -> None:
    assert build_virtual_view_identity(algorithm_git_blob_sha=ALGORITHM_BLOB_SHA) == EXPECTED_VIRTUAL_VIEW_ID


def test_source_passport_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    # Copy only enough of the frozen census for the loader to reach the summary identity check.
    target = tmp_path / SUMMARY.relative_to(ROOT)
    target.parent.mkdir(parents=True)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    summary["full_passport_set_canonical_sha256"] = "0" * 64
    target.write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match="SOURCE_PASSPORT_SET_IDENTITY_MISMATCH"):
        load_source_passports(tmp_path)
