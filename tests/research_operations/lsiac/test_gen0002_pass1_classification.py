from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ovc.research_operations.lsiac.pass1_gen0002 import (
    EXPECTED_PASSPORT_COUNT,
    EXPECTED_SUBJECT_COUNT,
    build_pass1_classification_view,
    build_shared_locator_dependence_graph,
    build_virtual_view_identity,
    load_source_passports,
)

ROOT = Path(__file__).resolve().parents[3]
SUMMARY = ROOT / "docs/programmes/lsiac-v0-1/source-census/LSIAC_LABORATORY_SOURCE_PASSPORTS_v0_1.json"
ALGORITHM = ROOT / "src/ovc/research_operations/lsiac/pass1_gen0002.py"
MANIFEST = ROOT / "docs/programmes/lsiac-v0-1/pass1-gen0002/LSIAC_GEN0002_PASS1_CLASSIFICATION_VIEW_MANIFEST_v0_1.json"


def _by_subject(view):
    return {row["subject_id"]: row for row in view["classifications"]}


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def test_gen0002_frozen_passports_reconstruct_completely() -> None:
    passports = load_source_passports(ROOT)
    assert len(passports) == EXPECTED_PASSPORT_COUNT == 434
    assert len({passport["subject_id"] for passport in passports}) == EXPECTED_SUBJECT_COUNT == 431


def test_gen0002_pass1_accounts_for_all_subjects_without_pass2_outputs() -> None:
    view = build_pass1_classification_view(ROOT)
    assert view["subject_count"] == 431
    assert view["passport_count"] == 434
    assert len(view["classifications"]) == 431
    assert view["generation_id"] == "OVC-LSIAC-ACCESSION-GEN-0002"
    assert view["source_universe_id"] == "d29e1c69399d6f312a7e0544c57e2e47c415f37347760f11ce983b926988114c"
    assert view["frontier_receipt_id"] == "022f6cf4149265cc545e6cffc2d0623a513ec2bf1ab38434c793bbf381a92bbe"
    assert view["protocol_binding_id"] == "15e449ffe15ded1d6419533257515ab9686122a1b5c73f7c82c49cea6e273d4f"
    assert view["pass1_only"] is True

    forbidden = {
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
        assert forbidden.isdisjoint(record)
        assert record["authority_effect"] == "NONE_PASS1_CLASSIFICATION_ONLY"
    for field_counts in view["counts"].values():
        assert sum(field_counts.values()) == 431


def test_gen0002_exact_post_v05_negatives_remain_scoped_and_exposed() -> None:
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


def test_gen0002_source_blocked_nominations_fail_closed() -> None:
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


def test_gen0002_observer_sufficiency_coreference_is_preserved_not_duplicated() -> None:
    records = _by_subject(build_pass1_classification_view(ROOT))
    record = records["OVC-OBSERVER-STATE-SUFFICIENCY-AND-GAMMA-ROBUSTNESS-FRONTIER"]
    assert record["passport_count"] == 2
    assert record["source_standing"] == "SOURCE_DERIVED"
    assert record["source_relation_state"] == "MULTIPLE_STANDING"
    assert record["scientific_disposition"] == "UNRESOLVED"
    assert record["exposure_state"] == "UNKNOWN"
    assert "EXACT_LOAD_BEARING_SOURCE_NOT_BOUND_FOR_STRONGER_CLAIM" in record["source_blockers"]


def test_gen0002_dependence_graph_never_infers_independence() -> None:
    graph = build_shared_locator_dependence_graph(load_source_passports(ROOT))
    assert graph["subject_count"] == 431
    assert all(edge["dependence_class"] == "SHARED_SOURCE_DEPENDENT" for edge in graph["edges"])
    assert not any(edge["dependence_class"] == "INDEPENDENT_BY_FROZEN_CRITERION" for edge in graph["edges"])


def test_gen0002_virtual_view_identity_is_bound_to_exact_algorithm_bytes() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    algorithm_blob = _git_blob_sha(ALGORITHM)
    assert algorithm_blob == manifest["algorithm_git_blob_sha"]
    assert build_virtual_view_identity(algorithm_git_blob_sha=algorithm_blob) == manifest["virtual_view_id"]
    assert manifest["subject_count"] == 431
    assert manifest["passport_count"] == 434


def test_gen0002_source_passport_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    target = tmp_path / SUMMARY.relative_to(ROOT)
    target.parent.mkdir(parents=True)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    summary["full_passport_set_canonical_sha256"] = "0" * 64
    target.write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match="SOURCE_PASSPORT_SET_IDENTITY_MISMATCH"):
        load_source_passports(tmp_path)
