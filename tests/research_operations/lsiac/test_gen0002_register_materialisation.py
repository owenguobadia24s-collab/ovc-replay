from __future__ import annotations

from pathlib import Path

from ovc.research_operations.lsiac.registers_gen0002 import (
    AUTHORITY_EFFECT,
    PASS2_MERGE_COMMIT,
    PASS2_VIRTUAL_VIEW_ID,
    REGISTER_KINDS,
    build_register_bundle,
    build_virtual_bundle_identity,
)
from ovc.research_operations.lsiac.pass2_gen0002 import build_pass2_adjudication_view

ROOT = Path(__file__).resolve().parents[3]
ALGORITHM_BLOB_SHA = "ed17ddd29c2361220fbfc214e16147e98a7c24fd"


def test_register_bundle_materialises_all_six_required_registers() -> None:
    bundle = build_register_bundle(str(ROOT))
    assert bundle["source_pass2_virtual_view_id"] == PASS2_VIRTUAL_VIEW_ID
    assert bundle["source_pass2_merge_commit"] == PASS2_MERGE_COMMIT
    assert bundle["register_kind_count"] == 6
    assert set(bundle["registers"]) == {
        "lsir",
        "negative_knowledge",
        "supersession",
        "destination_binding",
        "architecture_effect",
        "architecture_gap",
    }
    assert set(REGISTER_KINDS) == {
        "LSIR",
        "NEGATIVE_KNOWLEDGE",
        "SUPERSESSION",
        "DESTINATION_BINDING",
        "ARCHITECTURE_EFFECT",
        "ARCHITECTURE_GAP",
    }
    assert bundle["authority_effect"] == AUTHORITY_EFFECT


def test_registers_preserve_fail_closed_pass2_result_without_new_science() -> None:
    bundle = build_register_bundle(str(ROOT))
    registers = bundle["registers"]
    assert registers["lsir"]["entry_count"] == 0
    assert registers["lsir"]["decision_index_count"] == 431
    assert registers["negative_knowledge"]["entry_count"] == 0
    assert registers["negative_knowledge"]["deferred_negative_subject_count"] == 3
    assert registers["supersession"]["edge_count"] == 0
    assert registers["destination_binding"]["binding_count"] == 0
    assert registers["destination_binding"]["empty_binding_decision_count"] == 431
    assert registers["architecture_effect"]["record_count"] == 431
    assert registers["architecture_effect"]["primary_effect_counts"] == {"NO_FORWARD_IMPLEMENTATION": 431}
    assert registers["architecture_effect"]["actionable_effect_count"] == 0
    assert registers["architecture_effect"]["execution_count"] == 0


def test_architecture_gap_register_is_only_explicit_source_binding_debt() -> None:
    bundle = build_register_bundle(str(ROOT))
    pass2 = build_pass2_adjudication_view(str(ROOT))
    debt_by_subject = {}
    for manifest in pass2["counterevidence_manifests"]:
        candidate = manifest["inheritance_candidate_id"]
        debt_by_subject[candidate] = sorted(manifest["source_binding_debt"])

    gaps = bundle["registers"]["architecture_gap"]["gaps"]
    assert len(gaps) >= 2
    assert len(gaps) == bundle["registers"]["architecture_gap"]["gap_count"]
    for gap in gaps:
        assert gap["severity"] == "REPRODUCIBILITY_BLOCKER"
        assert gap["basis"]
        assert gap["downstream_effect"] == "NO_FORWARD_IMPLEMENTATION"
        decision = next(
            item for item in pass2["decisions"] if item["decision_id"] == gap["decision_id"]
        )
        assert gap["basis"] == debt_by_subject[decision["inheritance_id"]]


def test_register_ids_and_bundle_id_are_deterministic() -> None:
    first = build_register_bundle(str(ROOT))
    second = build_register_bundle(str(ROOT))
    assert first == second
    assert first["bundle_id"] == second["bundle_id"]
    assert first["register_identities"] == second["register_identities"]
    assert len(set(first["register_identities"].values())) == 6


def test_register_materialisation_does_not_create_downstream_authority() -> None:
    bundle = build_register_bundle(str(ROOT))
    for register in bundle["registers"].values():
        assert register["authority_effect"] == AUTHORITY_EFFECT
    for record in bundle["registers"]["architecture_effect"]["records"]:
        assert record["actionable_under_current_authority"] is False


def test_virtual_bundle_identity_is_bound_to_exact_algorithm_blob() -> None:
    identity = build_virtual_bundle_identity(algorithm_git_blob_sha=ALGORITHM_BLOB_SHA)
    assert len(identity) == 64
    assert identity == build_virtual_bundle_identity(algorithm_git_blob_sha=ALGORITHM_BLOB_SHA)
    assert identity != build_virtual_bundle_identity(algorithm_git_blob_sha="0" * 40)
