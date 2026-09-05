from __future__ import annotations

from pathlib import Path

from ovc.research_operations.lsiac.registers_gen0002 import (
    AUTHORITY_EFFECT,
    EXPECTED_PASS2_VIRTUAL_VIEW_ID,
    GAP_CLASS,
    build_gen0002_register_bundle,
)

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_GAP_SUBJECTS = {
    "OVC-REPRESENTATION-ROBUSTNESS-0001-SOURCE-BINDING",
    "OVC-RRSCG-OBSERVER-STATE-GEOMETRY-0001-SOURCE-BINDING",
}


def test_register_bundle_binds_exact_frozen_pass2_view():
    bundle = build_gen0002_register_bundle(ROOT)
    assert bundle["source_binding"]["pass2_virtual_view_id"] == EXPECTED_PASS2_VIRTUAL_VIEW_ID
    assert bundle["authority_effect"] == AUTHORITY_EFFECT
    assert bundle["generation_id"] == "OVC-LSIAC-ACCESSION-GEN-0002"
    assert len(bundle["bundle_id"]) == 64


def test_lsir_is_complete_zero_copy_projection_of_all_431_decisions():
    bundle = build_gen0002_register_bundle(ROOT)
    register = bundle["registers"]["laboratory_scientific_inheritance_register"]
    assert register["member_count"] == 431
    assert len(register["members"]) == 431
    assert len({item["source_subject_id"] for item in register["members"]}) == 431
    assert len({item["decision_id"] for item in register["members"]}) == 431
    assert all(item["inheritance_roles"] == ["NONE"] for item in register["members"])
    assert all(item["authority_state"] == "NONE" for item in register["members"])


def test_negative_knowledge_register_is_exact_negative_supported_filter():
    bundle = build_gen0002_register_bundle(ROOT)
    register = bundle["registers"]["negative_knowledge_register"]
    assert register["member_count"] > 0
    assert all(item["scientific_disposition"] == "NEGATIVE_SUPPORTED" for item in register["members"])
    assert all(item["inheritance_roles"] == ["NONE"] for item in register["members"])
    subjects = {item["source_subject_id"] for item in register["members"]}
    for expected in (
        "OVC-MULTICLOCK-NONLINEAR-DYNAMICS-0005",
        "OVC-MULTICLOCK-PERSISTENCE-DWELL-0006",
        "OVC-MULTICLOCK-SUCCESSOR-SEQUENCE-0005-0006-FINAL-SYNTHESIS",
    ):
        assert expected in subjects


def test_no_supersession_or_destination_is_invented():
    bundle = build_gen0002_register_bundle(ROOT)
    assert bundle["registers"]["supersession_register"]["member_count"] == 0
    assert bundle["registers"]["destination_binding_sets"]["member_count"] == 0


def test_architecture_effect_register_is_complete_but_non_executing():
    bundle = build_gen0002_register_bundle(ROOT)
    register = bundle["registers"]["architecture_effect_sets"]
    assert register["member_count"] == 431
    assert all(item["execution_authority"] == "NONE" for item in register["members"])
    assert all(
        item["architecture_effect_set"]["primary_effect"] == "NO_FORWARD_IMPLEMENTATION"
        for item in register["members"]
    )


def test_architecture_gap_register_contains_only_exact_source_binding_debt():
    bundle = build_gen0002_register_bundle(ROOT)
    register = bundle["registers"]["architecture_gap_register"]
    assert register["member_count"] == 2
    assert {item["source_subject_id"] for item in register["members"]} == EXPECTED_GAP_SUBJECTS
    assert all(item["gap_class"] == GAP_CLASS for item in register["members"])
    assert all(item["authority_effect"] == "NONE" for item in register["members"])


def test_register_bundle_is_deterministic():
    first = build_gen0002_register_bundle(ROOT)
    second = build_gen0002_register_bundle(ROOT)
    assert first == second
    assert first["bundle_id"] == second["bundle_id"]
    for key in first["registers"]:
        assert (
            first["registers"][key]["members_canonical_sha256"]
            == second["registers"][key]["members_canonical_sha256"]
        )
