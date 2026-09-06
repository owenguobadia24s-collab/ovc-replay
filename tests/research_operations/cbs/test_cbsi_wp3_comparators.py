from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.cbs.comparators.b0_reference import run_b0_reference
from ovc.research_operations.cbs.comparators.b1_run_change import run_b1_run_change
from ovc.research_operations.cbs.comparators.b2_directional_change import run_b2_directional_change
from ovc.research_operations.cbs.comparators.b3_pelt import run_b3_penalised_segmentation
from ovc.research_operations.cbs.comparators.b8_annotation import adapt_annotations
from ovc.research_operations.cbs.comparators.b9_control import run_b9_control
from ovc.research_operations.cbs.comparators.common import build_estimate
from ovc.research_operations.cbs.comparators.interface import build_method_pack, build_run_manifest
from ovc.research_operations.cbs.identity import CBSContractError, canonical_id, verify_object
from ovc.research_operations.cbs.projections import B0_ACTIONS, build_b0_projection_manifest

ROOT=Path(__file__).resolve().parents[3]
FIXTURE=json.loads((ROOT/"fixtures/research_operations/cbs/wp3/core_comparator_golden_v0_1.json").read_text())
CUTOFF="2020-01-01T02:00:00Z"


def points(key: str) -> list[dict]:
    return [{"observation_id":f"o{i}","effective_time":time,"first_valid_time":time,key:FIXTURE[f"{key}s"][i]}
            for i,time in enumerate(FIXTURE["times"])]


def test_b0_preserves_typed_events_and_owner_identity() -> None:
    classes={action:"NON_BOUNDARY_EVENT" for action in B0_ACTIONS}
    classes.update({"PHASE_MUTATION":"REFERENCE_BOUNDARY","CENSOR_GAP":"SOURCE_GAP","CENSOR_RELEASE_END":"CENSOR"})
    manifest=build_b0_projection_manifest(pack_id="C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8",
        pack_sha256="043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313",action_classes=classes,status="FROZEN_SYNTHETIC")
    events=[{"event_id":"e1","action":"PHASE_MUTATION","effective_time":FIXTURE["times"][2],"first_valid_time":FIXTURE["times"][2]},
            {"event_id":"e2","action":"CENSOR_RELEASE_END","effective_time":FIXTURE["times"][5],"first_valid_time":FIXTURE["times"][5]}]
    output=run_b0_reference(projected_events=events,b0_projection=manifest,config_id="b0-synth",evaluation_cutoff=CUTOFF)
    assert len(output["estimates"]) == 1
    assert output["typed_non_estimates"] == [{"event_id":"e2","action":"CENSOR_RELEASE_END","classification":"CENSOR"}]
    assert output["owner_identity_mutation"] == "NONE"


def test_b1_run_change_golden_and_order_determinism() -> None:
    output=run_b1_run_change(points=points("signature"),config_id="b1-synth",min_run_length=2,evaluation_cutoff=CUTOFF)
    reversed_output=run_b1_run_change(points=list(reversed(points("signature"))),config_id="b1-synth",min_run_length=2,evaluation_cutoff=CUTOFF)
    assert output == reversed_output
    assert [FIXTURE["times"].index(item["effective_time"]) for item in output["estimates"]] == FIXTURE["expected"]["B1_break_indices"]


def test_b2_directional_change_separates_onset_confirmation_and_fvt() -> None:
    output=run_b2_directional_change(points=points("value"),config_id="b2-synth",threshold=5.0,evaluation_cutoff=CUTOFF)
    estimate=output["estimates"][0]
    assert estimate["direction"] == FIXTURE["expected"]["B2_first_direction"]
    assert estimate["candidate_onset_time"] < estimate["confirmation_time"]
    assert estimate["first_valid_time"] == estimate["confirmation_time"]


def test_b3_exact_penalised_segmentation_is_retrospective_only() -> None:
    output=run_b3_penalised_segmentation(points=points("value"),config_id="b3-synth",penalty=1.0,min_segment_length=2,evaluation_cutoff=CUTOFF)
    assert output["break_indices"] == FIXTURE["expected"]["B3_break_indices"]
    assert output["comparison_only"] is True and output["causal_join"] == "FORBIDDEN"
    assert all(item["causal_admissibility"] is False and item["first_valid_time"] == FIXTURE["times"][-1] for item in output["estimates"])
    with pytest.raises(CBSContractError,match="RETROSPECTIVE_CAUSAL_JOIN"):
        build_estimate(method_id="B3",family_id="f",config_id="c",temporal_class="RETROSPECTIVE",state="ESTIMATED",
            candidate_onset_time=FIXTURE["times"][1],effective_time=FIXTURE["times"][1],confirmation_time=FIXTURE["times"][2],
            first_valid_time=FIXTURE["times"][2],evaluation_cutoff=CUTOFF,causal_admissibility=True)


def test_b9_has_zero_boundaries_but_preserves_source_events() -> None:
    source_events=[{"event_id":"gap","classification":"SOURCE_GAP"}]
    output=run_b9_control(opportunity_count=6,source_events=source_events,config_id="b9-synth")
    assert output["estimates"] == [] and output["no_estimate_count"] == 6
    assert output["typed_source_events"] == source_events


def test_annotation_is_reference_only_never_ground_truth() -> None:
    result=adapt_annotations([{"annotation_id":"a1","role":"REFERENCE_ONLY","ground_truth":False}])
    assert result["fitted_target"] is False
    with pytest.raises(CBSContractError,match="GROUND_TRUTH_FORBIDDEN"):
        adapt_annotations([{"annotation_id":"a1","role":"REFERENCE_ONLY","ground_truth":True}])


def test_method_pack_and_run_manifest_bind_all_decision_inputs() -> None:
    pack=build_method_pack(comparator_id="B1",projection_id="p",support_manifest_id="s",parameters={"min_run_length":2},
        temporal_class="ONLINE_CAUSAL",dependence_cluster="CBS_B1_FAMILY",exposure_classification="SYNTHETIC")
    output=run_b1_run_change(points=points("signature"),config_id=pack["method_pack_id"],min_run_length=2,evaluation_cutoff=CUTOFF)
    run=build_run_manifest(method_pack=pack,source_population_id="synthetic",code_blobs={"b1_run_change.py":"a"*40},
        capacity_receipt_id="capacity",outputs=[output],qa_state="PASS")
    verify_object(pack,id_field="method_pack_id"); verify_object(run,id_field="run_manifest_id")
    assert run["output_ids"] == [output["output_id"]]


def test_consumed_lab_parity_is_not_reexecuted_or_promoted() -> None:
    receipt=json.loads((ROOT/"records/research_operations/cbs/CBSI_WP3_CONSUMED_LAB_PARITY_RECEIPT_v0_1.json").read_text())
    assert receipt["status"] == "RECEIPT_CONCORDANT_NOT_REEXECUTED"
    assert receipt["fresh_replication"] is False and receipt["parameter_promotion"] == "NONE"
    assert {item["comparator_id"] for item in receipt["bound_sources"]} == {"B0","B1","B2","B3"}
