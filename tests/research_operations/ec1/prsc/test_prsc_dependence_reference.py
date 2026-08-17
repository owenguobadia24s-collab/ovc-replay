from __future__ import annotations

import pytest

from ovc.research_operations.ec1_path1 import DependenceEdge, EvidenceDependenceGraph
from ovc.research_operations.prsc.contracts import PRSCContractError
from ovc.research_operations.prsc.dependence import (
    adapt_evidence_dependence_graph,
    build_candidate_dependence_profile,
    build_inference_block_manifest,
    leave_one_component_out,
)
from ovc.research_operations.prsc.reference import (
    build_negative_space_controls,
    build_reference_method_pack,
    dependency_preserving_block_resample,
    hac_ordered_secondary,
    validate_reference_preservation,
)


def _graph() -> EvidenceDependenceGraph:
    return EvidenceDependenceGraph((
        DependenceEdge("a", "b", "SAME_SOURCE_ANCHOR"),
        DependenceEdge("b", "c", "TRANSITION_SEQUENCE_OVERLAP"),
    ))


def _manifest() -> dict:
    return build_inference_block_manifest(
        graph=_graph(),
        candidate_unit_ids=["a", "b", "c", "d"],
        blocks={"ancestry-1": ["a", "b", "c"], "unresolved-declared-1": ["d"]},
        block_source="DECLARED_PREREGISTERED_BLOCKS",
    )


def test_read_only_owner_graph_adapter_never_invents_convenience_edges() -> None:
    view = adapt_evidence_dependence_graph(_graph(), ["a", "b", "c", "d"])
    assert [(e.left, e.right, e.edge_type) for e in view.owner_edges] == [
        ("a", "b", "SAME_SOURCE_ANCHOR"),
        ("b", "c", "TRANSITION_SEQUENCE_OVERLAP"),
    ]
    assert view.unresolved_unit_ids == ("d",)


def test_graph_absence_is_independence_unknown() -> None:
    profile = build_candidate_dependence_profile(_graph(), ["a", "b", "c", "d"])
    assert profile["unresolved_unit_ids"] == ["d"]
    assert profile["no_edge_semantics"] == "INDEPENDENCE_UNKNOWN"
    assert profile["independence_claim"] == "NOT_ESTABLISHED"


def test_inference_blocks_are_complete_and_do_not_split_owner_edges() -> None:
    manifest = _manifest()
    assert len(leave_one_component_out(manifest)) == 2
    with pytest.raises(PRSCContractError, match="PRSC_DEPENDENCE_COMPONENT_SPLIT"):
        build_inference_block_manifest(
            graph=_graph(),
            candidate_unit_ids=["a", "b", "c"],
            blocks={"split": ["a"], "other": ["b", "c"]},
            block_source="DECLARED_PREREGISTERED_BLOCKS",
        )


def test_reference_first_resampling_preserves_whole_blocks_and_complete_accounting() -> None:
    manifest = _manifest()
    ensemble = dependency_preserving_block_resample(manifest, draws=16, seed=20260817)
    assert ensemble["requested_draws"] == ensemble["generated_draws"] == 16
    assert ensemble["rejected_draws"] == 0
    assert ensemble["silent_surrogate_drop"] is False
    assert validate_reference_preservation(manifest, ensemble)["status"] == "PASS"

    tampered = dict(ensemble)
    tampered["draws"] = [{
        "draw_index": 0,
        "sampled_blocks": [{"source_block_id": "ancestry-1", "unit_ids": ["a"]}],
    }]
    assert validate_reference_preservation(manifest, tampered)["status"] == "BLOCK"


def test_negative_space_controls_cannot_split_a_positive_dependence_block() -> None:
    controls = build_negative_space_controls(_manifest(), positive_unit_ids=["a"])
    assert controls["eligible_negative_control_block_ids"] == ["unresolved-declared-1"]
    assert controls["ineligible_blocks"] == [{
        "block_id": "ancestry-1",
        "reason": "SHARES_DEPENDENCE_BLOCK_WITH_POSITIVE",
    }]
    assert controls["silent_drop"] is False


def test_hac_is_secondary_explicit_and_has_no_universal_neff_or_alpha() -> None:
    pack = build_reference_method_pack(
        method_pack_id="PRSC.REF.WP2.v0.1",
        secondary_methods=["HAC_EXPLICIT_ORDERED_SECONDARY"],
    )
    assert pack["reference_first"] is True
    assert pack["universal_n_eff"] is None
    assert pack["universal_alpha"] is None
    summary = hac_ordered_secondary([1.0, 2.0, 4.0, 8.0], max_lag=1, ordered=True)
    assert summary["n_eff"] is None and summary["alpha"] is None
    with pytest.raises(PRSCContractError, match="PRSC_HAC_REQUIRES_LAWFUL_ORDERING"):
        hac_ordered_secondary([1.0, 2.0, 3.0], max_lag=1, ordered=False)
