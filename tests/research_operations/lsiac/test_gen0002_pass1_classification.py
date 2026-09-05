from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ovc.research_operations.lsiac.gen0002 import audit_frozen_passport_subject_identity
from ovc.research_operations.lsiac.pass1 import (
    EXPECTED_PASSPORT_COUNT,
    EXPECTED_SUBJECT_COUNT,
    FRONTIER_RECEIPT_ID,
    GENERATION_ID,
    PROTOCOL_BINDING_ID,
    SOURCE_UNIVERSE_ID,
    build_pass1_classification_view,
    build_shared_locator_dependence_graph,
    build_virtual_view_identity,
    load_source_passports,
)


ROOT = Path(__file__).resolve().parents[3]
SUMMARY = ROOT / "docs/programmes/lsiac-v0-1/source-census/LSIAC_LABORATORY_SOURCE_PASSPORTS_v0_1.json"
ALGORITHM = ROOT / "src/ovc/research_operations/lsiac/pass1.py"
MANIFEST = ROOT / "docs/programmes/lsiac-v0-1/gen0002/pass1/LSIAC_GEN0002_PASS1_CLASSIFICATION_VIEW_MANIFEST_v0_1.json"
ALGORITHM_BLOB_SHA = "e8d062cb4dd9b3be4749e257343cd17cb77b85ca"
EXPECTED_VIRTUAL_VIEW_ID = "a3e954b7db9d9c63d14d5b03baa94eb3c791dc4c0bdfc39ab19f29c9f2ecc3b5"


def _by_subject(view):
    return {row["subject_id"]: row for row in view["classifications"]}


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def test_gen0002_exact_accounting_and_passport_identity_are_preserved() -> None:
    audit = audit_frozen_passport_subject_identity(ROOT)
    passports = load_source_passports(ROOT)
    assert audit["subject_count"] == EXPECTED_SUBJECT_COUNT == 431
    assert audit["passport_count"] == EXPECTED_PASSPORT_COUNT == 434
    assert len(passports) == 434
    assert len({passport["subject_id"] for passport in passports}) == 431
    assert audit["multi_passport_subject_count"] == 3
    assert audit["scientific_accession_decisions"] == 0


def test_gen0002_pass1_accounts_for_all_subjects_without_survival_outputs() -> None:
    view = build_pass1_classification_view(ROOT)
    assert view["generation_id"] == GENERATION_ID == "OVC-LSIAC-ACCESSION-GEN-0002"
    assert view["subject_count"] == 431
    assert view["passport_count"] == 434
    assert len(view["classifications"]) == 431
    assert len({row["subject_id"] for row in view["classifications"]}) == 431
    assert view["source_universe_id"] == SOURCE_UNIVERSE_ID
    assert view["frontier_receipt_id"] == FRONTIER_RECEIPT_ID
    assert view["protocol_binding_id"] == PROTOCOL_BINDING_ID
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
        assert sum(field_counts.values()) == 431


def test_exact_post_v05_negative_subjects_preserve_source_supported_status_only() -> None:
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
        assert "inheritance_role" not in record
        assert "retain_forward" not in record


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


def test_observer_state_sufficiency_coreference_is_one_subject_not_evidence_duplication() -> None:
    passports = load_source_passports(ROOT)
    relevant = [
        passport for passport in passports
        if passport["subject_id"] == "OVC-OBSERVER-STATE-SUFFICIENCY-AND-GAMMA-ROBUSTNESS-FRONTIER"
    ]
    assert sorted(passport["passport_id"] for passport in relevant) == ["B0415", "D011-00"]
    records = _by_subject(build_pass1_classification_view(ROOT))
    record = records["OVC-OBSERVER-STATE-SUFFICIENCY-AND-GAMMA-ROBUSTNESS-FRONTIER"]
    assert record["source_standing"] == "SOURCE_DERIVED"
    assert record["scientific_disposition"] == "UNRESOLVED"
    assert record["exposure_state"] == "UNKNOWN"
    assert "EXACT_LOAD_BEARING_SOURCE_NOT_BOUND_FOR_STRONGER_CLAIM" in record["source_blockers"]


def test_dependence_graph_never_infers_independence_from_missing_edge() -> None:
    graph = build_shared_locator_dependence_graph(load_source_passports(ROOT))
    assert graph["subject_count"] == 431
    assert all(edge["dependence_class"] == "SHARED_SOURCE_DEPENDENT" for edge in graph["edges"])
    assert not any(edge["dependence_class"] == "INDEPENDENT_BY_FROZEN_CRITERION" for edge in graph["edges"])


def test_gen0002_virtual_view_identity_is_exact_and_manifest_bound() -> None:
    assert _git_blob_sha(ALGORITHM) == ALGORITHM_BLOB_SHA
    assert build_virtual_view_identity(algorithm_git_blob_sha=ALGORITHM_BLOB_SHA) == EXPECTED_VIRTUAL_VIEW_ID
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["algorithm_git_blob_sha"] == ALGORITHM_BLOB_SHA
    assert manifest["virtual_view_id"] == EXPECTED_VIRTUAL_VIEW_ID
    assert manifest["subject_count"] == 431
    assert manifest["passport_count"] == 434
    assert manifest["source_universe_id"] == SOURCE_UNIVERSE_ID
    assert manifest["frontier_receipt_id"] == FRONTIER_RECEIPT_ID
    assert manifest["protocol_binding_id"] == PROTOCOL_BINDING_ID


def test_source_passport_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    target = tmp_path / SUMMARY.relative_to(ROOT)
    target.parent.mkdir(parents=True)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    summary["full_passport_set_canonical_sha256"] = "0" * 64
    target.write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match="SOURCE_PASSPORT_SET_IDENTITY_MISMATCH"):
        load_source_passports(tmp_path)
