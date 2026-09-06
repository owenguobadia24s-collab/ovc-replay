from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.cbs.enums import EstimateState
from ovc.research_operations.cbs.evaluation_universe import build_evaluation_universe, reconcile_opportunities
from ovc.research_operations.cbs.identity import CBSContractError, verify_object
from ovc.research_operations.cbs.projections import (
    B0_ACTIONS, build_b0_projection_manifest, build_input_projection_manifest, project_b0_events, project_record,
)
from ovc.research_operations.cbs.sources import (
    EXPECTED_C2E_PACK, EXPECTED_C2E_PACK_SHA256, build_source_population_manifest,
    resolve_current_authority, validate_owner_snapshot,
)
from ovc.research_operations.cbs.support import build_support_manifest, classify_support, support_analysis_populations

ROOT = Path(__file__).resolve().parents[3]


def test_current_owner_authority_and_pack_resolve_exactly() -> None:
    record = resolve_current_authority(ROOT)
    verify_object(record, id_field="authority_resolution_id")
    assert record["c2e_pack_id"] == EXPECTED_C2E_PACK
    assert record["c2e_pack_sha256"] == EXPECTED_C2E_PACK_SHA256
    assert record["market_envelope"]["validation"] == "LOCKED_UNCONSUMED"
    assert record["owner_state_effect"] == "READ_ONLY_NONE"


def test_source_population_builder_enforces_existing_envelope() -> None:
    population = build_source_population_manifest(authority_resolution_id="a"*64, source_release_id="SYNTHETIC.WP2",
        source_manifest_sha256="b"*64, source_object_ids=["s2", "s1"], instrument="GBPUSD", sides=["BID","ASK"],
        clocks=["15M","2H_A_L"], research_role="DISCOVERY", interval_start="2020-01-01T00:00:00Z", interval_end_exclusive="2020-01-02T00:00:00Z")
    verify_object(population, id_field="source_population_id")
    assert population["source_object_ids"] == ["s1", "s2"]
    with pytest.raises(CBSContractError, match="MARKET_ENVELOPE"):
        build_source_population_manifest(authority_resolution_id="a"*64, source_release_id="x", source_manifest_sha256="b"*64,
            source_object_ids=["x"], instrument="EURUSD", sides=["BID"], clocks=["15M"], research_role="DISCOVERY",
            interval_start="x", interval_end_exclusive="y")


def test_owner_snapshot_validation_preserves_chronology_and_read_only() -> None:
    snapshot={"owner_authority_id":"AUTH.OPT-B.C2.vNext.ACTIVE.RUNTIME.v0.1","owner_generation_id":"g",
              "effective_time":"t1","interval_end":"t1","authority":{"read_only":True,"validation":"LOCKED_UNCONSUMED"}}
    validate_owner_snapshot(snapshot, expected_generation_id="g")
    with pytest.raises(CBSContractError, match="SNAPSHOT_CHRONOLOGY"):
        validate_owner_snapshot({**snapshot,"effective_time":"t0"}, expected_generation_id="g")


def test_projection_is_exact_and_forbidden_fields_fail() -> None:
    manifest=build_input_projection_manifest(comparator_id="B1",profile_id="p",source_schema="s",fields=["snapshot_id","chronology.fvt"],
        transforms=[{"id":"identity"}],scaling="NONE",missingness="FAIL_CLOSED",representation="C2_RAW_TYPED",first_valid_time_field="chronology.fvt",exposure_classification="SYNTHETIC")
    projected=project_record({"snapshot_id":"s1","chronology":{"fvt":"t1"},"hidden":"never"},manifest)
    assert projected["values"] == {"snapshot_id":"s1","chronology.fvt":"t1"}
    with pytest.raises(CBSContractError, match="INPUT_FIREWALL"):
        build_input_projection_manifest(comparator_id="B1",profile_id="p",source_schema="s",fields=["validation.outcome"],transforms=[],scaling="NONE",missingness="x",representation="x",first_valid_time_field="x",exposure_classification="x")


def test_b0_projection_requires_full_explicit_frozen_classification() -> None:
    classes={action:"NON_BOUNDARY_EVENT" for action in B0_ACTIONS}
    classes.update({"PHASE_MUTATION":"REFERENCE_BOUNDARY","CENSOR_GAP":"SOURCE_GAP","CENSOR_RELEASE_END":"CENSOR"})
    draft=build_b0_projection_manifest(pack_id=EXPECTED_C2E_PACK,pack_sha256=EXPECTED_C2E_PACK_SHA256,action_classes=classes,status="DRAFT")
    with pytest.raises(CBSContractError, match="INPUT_PROJECTION_UNFROZEN"):
        project_b0_events([],draft)
    frozen={**draft,"status":"FROZEN_SYNTHETIC"}
    from ovc.research_operations.cbs.identity import canonical_id
    frozen["b0_projection_id"]=canonical_id({k:v for k,v in frozen.items() if k!="b0_projection_id"})
    out=project_b0_events([{"event_id":"e1","action":"PHASE_MUTATION","effective_time":"t0","first_valid_time":"t1"}],frozen)
    assert out[0]["classification"] == "REFERENCE_BOUNDARY"


def test_support_preserves_all_states_and_both_analysis_populations() -> None:
    manifest=build_support_manifest(comparator_id="B2",projection_id="p",warmup=1,lookback=1,lookahead=1,edge_censor=1,gap_policy="BREAK",abstention_reasons=["MISSING"])
    assert classify_support(index=0,total=5,manifest=manifest) == EstimateState.CENSORED
    assert classify_support(index=2,total=5,manifest=manifest,evaluable=False) == EstimateState.NOT_EVALUABLE
    assert classify_support(index=2,total=5,manifest=manifest) == EstimateState.NO_ESTIMATE
    analysis=support_analysis_populations({"B1":["CENSORED","NO_ESTIMATE","ESTIMATED"],"B2":["NOT_EVALUABLE","NO_ESTIMATE","ESTIMATED"]})
    assert analysis["full_population_indices"] == [0,1,2]
    assert analysis["matched_support_indices"] == [1,2]
    assert analysis["support_differs"] is True


def test_evaluation_universe_is_formed_before_detections_and_conserves_count() -> None:
    universe=build_evaluation_universe(population_id="p",opportunity_keys=["t0","t1","t2","t3"],evaluation_cutoff="2020-01-01T01:00:00Z")
    assert universe["formed_before_detection"] is True
    reconciliation=reconcile_opportunities(universe,[{"opportunity_id":"t1","state":"ESTIMATED"},{"opportunity_id":"t2","state":"NOT_EVALUABLE"},{"opportunity_id":"t3","state":"CENSORED"}])
    assert reconciliation["state_counts"] == {"CENSORED":1,"ESTIMATED":1,"NOT_EVALUABLE":1,"NO_ESTIMATE":1}
    assert reconciliation["count_conserved"] is True
    with pytest.raises(CBSContractError, match="ASCERTAINMENT_FAIL"):
        reconcile_opportunities(universe,[{"opportunity_id":"not-in-universe","state":"ESTIMATED"}])


def test_wp2_manifests_preserve_pending_development_boundary() -> None:
    registry=json.loads((ROOT/"registries/research_operations/cbs/CBSI_WP2_INPUT_PROJECTION_MANIFESTS_v0_1.json").read_text())
    assert registry["development_status"] == "CANDIDATE_NOT_FROZEN_NOT_AUTHORIZED"
    assert registry["hidden_source_fields"] == "FORBIDDEN"
    b0=json.loads((ROOT/"registries/research_operations/cbs/CBSI_WP2_B0_REFERENCE_PROJECTION_CONTRACT_v0_1.json").read_text())
    assert b0["current_development_projection_status"] == "UNFROZEN_PENDING_ATOMIC_WP6_CANDIDATE"
    fixture=json.loads((ROOT/"fixtures/research_operations/cbs/wp2/synthetic_owner_opportunities_v0_1.json").read_text())
    assert len(fixture["opportunities"]) == 6
