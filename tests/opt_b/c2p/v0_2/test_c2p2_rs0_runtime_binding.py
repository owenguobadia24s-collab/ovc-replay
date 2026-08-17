from __future__ import annotations

import pytest

from ovc.opt_b.c2e_v2 import source_replay as base
from ovc.opt_b.c2e_v2 import source_replay_runtime as runtime
from ovc.opt_b.c2e_v2.handoff import C2EHandoffError, build_input_frame
from ovc.opt_b.c2p_v0_2 import rs0_source_materialisation_runtime as adapter


def test_rs0_runtime_adapter_binds_canonical_wp6_dependencies() -> None:
    assert base._dependencies is runtime._dependencies
    assert adapter.c2e_base._dependencies is runtime._dependencies
    bundle = {
        "observation_id": "OBS.1",
        "context_bundle_id": "CTX.1",
        "profile_output_ids": {
            "LOCATION": ["P.LOC"],
            "MOTION": ["P.M1", "P.M2", "P.M3"],
            "ORGANISATION": ["P.ORG"],
            "INTERACTION": ["P.INT"],
        },
    }
    profiles = {key: {"computability": "COMPUTABLE"} for key in ("P.LOC", "P.M1", "P.M2", "P.M3", "P.ORG", "P.INT")}
    context = {"fixed_parent_observation_link": {"computability": "NOT_COMPUTABLE", "parent_observation_id": None, "reason_codes": ["NO_PARENT"]}}
    rows = base._dependencies(bundle, profiles, context)
    assert {row["dependency_id"] for row in rows} == {
        "DEP.CONTINUITY", "DEP.PARENT_CONTEXT", "DEP.SOURCE_RELEASE", "DEP.STRUCTURAL"
    }
    assert not {"FDI_C2G", "OUTCOME", "VALIDATION", "C2_5", "C3"}.intersection(
        row["dependency_id"] for row in rows
    )


def test_firewall_remains_fail_closed_for_actual_forbidden_dependency_value() -> None:
    payload = {
        "source_binding": {"c2_release_id": "R", "c2_contract_id": "C", "source_build_commit": "0" * 40},
        "identity": {"instrument_id": "GBPUSD", "side": "BID", "scope_id": "LOCAL_15M", "scale_id": "15M", "clock_id": "UTC_15M", "lattice_id": "L", "observation_id": "OBS", "c2_record_id": "OBS", "parameter_pack_id": "P", "contract_id": "C2E.HANDOFF.SIGNATURE.v0_3", "schema_id": "c2e_input_frame/v0_3"},
        "chronology": {"source_time": "2021-01-01T00:00:00Z", "candidate_onset_time": "2021-01-01T00:00:00Z", "first_valid_time": "2021-01-01T00:15:00Z", "evaluation_cutoff": "2021-01-01T00:15:00Z", "continuity_segment_id": "SEG", "predecessor_observation_id": None},
        "structural": {"location_record_ids": [], "motion_record_ids": [], "organisation_record_ids": [], "interaction_record_ids": [], "level_record_ids": [], "container_record_ids": [], "relation_set_id": None, "transition_record_ids": [], "run_record_ids": []},
        "context": {"context_resolution_bundle_id": "CTX", "fixed_parent_links": [], "structural_object_links": [], "parent_axis_links": []},
        "evidence": {"dependency_results": [{"dependency_id": "FDI_C2G", "role": "PROHIBITED", "status": "UNAVAILABLE", "source_record_ids": [], "reason_codes": []}], "availability_status": "AVAILABLE", "technical_status": "COMPUTABLE", "assurance": [], "consumer_eligibility": "INELIGIBLE_INACTIVE_SHADOW", "authority_state": "UNAUTHORIZED_ACTIVE_C2E", "reason_codes": []},
        "lineage": {"parent_record_ids": [], "artifact_hashes": {}, "source_build_commit": "0" * 40},
    }
    with pytest.raises(C2EHandoffError, match="DEP_FORBIDDEN_VALUE_CONSUMED"):
        build_input_frame(payload)
