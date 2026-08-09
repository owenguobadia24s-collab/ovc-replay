import copy
import json
from pathlib import Path
import unittest

from ovc.opt_b.c2e_v2.empirical_boundary_rules_v2 import evaluate_boundary_predicates_v2
from ovc.opt_b.c2e_v2.handoff import C2EHandoffError
from ovc.opt_b.c2e_v2.handoff_v0_3 import build_input_frame_v0_3
from ovc.opt_b.c2e_v2.stable_signatures import StableSignatureError, build_comparison_signatures

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/opt_b/c2e/v0_2/wp1/ordinary_frame.json"
SCHEMA = ROOT / "schemas/opt_b/c2e/v0_2/c2e_input_frame_v0_3.schema.json"
CONTRACT = ROOT / "contracts/opt_b/c2e/v0_2/C2_TO_C2E_STABLE_COMPARISON_SIGNATURE_CONTRACT_v0_3.md"


def comparison_source(location_value="ABOVE", parent_id="PARENT.OBS.STABLE", dep_status="AVAILABLE"):
    return {
        "structural": {
            "LOCATION": {"status":"COMPUTABLE","reason_codes":[],"source_object_ids":["LEVEL.STABLE"],"facts":{"topology":location_value,"signed_distance":"0.00100"}},
            "MOTION": {"status":"COMPUTABLE","reason_codes":[],"source_object_ids":[],"facts":{"price_delta":"0.00020"}},
            "ORGANISATION": {"status":"COMPUTABLE","reason_codes":[],"source_object_ids":["CONTAINER.STABLE"],"facts":{"container_relation":"INSIDE"}},
            "INTERACTION": {"status":"COMPUTABLE","reason_codes":[],"source_object_ids":["LEVEL.STABLE"],"facts":{"crossing_status":"NO_CROSSING"}},
        },
        "parent": {
            "selected_parent_observation_ids":[parent_id],
            "selected_parent_object_ids":["PARENT.OBJECT.STABLE"],
            "dependency_states":[{"dependency_id":"DEP.PARENT","role":"OPTIONAL","status":dep_status,"reason_codes":[]}],
        },
    }


def boundary_frame(*, structural_ids, context_ids, comparison):
    return {
        "identity":{"instrument_id":"GBPUSD","side":"BID","scope_id":"LOCAL_15M","scale_id":"15M","clock_id":"UTC_15M"},
        "chronology":{"continuity_segment_id":"SEG.STABLE","first_valid_time":"2026-06-01T00:30:00Z","evaluation_cutoff":"2026-06-01T00:30:00Z"},
        "structural":{
            "location_record_ids":[structural_ids[0]],"motion_record_ids":[structural_ids[1]],
            "organisation_record_ids":[structural_ids[2]],"interaction_record_ids":[structural_ids[3]],
            "level_record_ids":[],"container_record_ids":[],"relation_set_id":None,"transition_record_ids":[],"run_record_ids":[]
        },
        "context":{"context_resolution_bundle_id":context_ids[0],"fixed_parent_links":[context_ids[1]],"structural_object_links":[],"parent_axis_links":[]},
        "evidence":{"dependency_results":[],"availability_status":"AVAILABLE","technical_status":"COMPUTABLE","authority_state":"UNAUTHORIZED_ACTIVE_C2E","reason_codes":[]},
        "lineage":{"parent_record_ids":[],"artifact_hashes":{"probe":"stable"},"source_build_commit":"probe"},
        "comparison":comparison,
    }


class C2E2G6StableSignatureRepairTests(unittest.TestCase):
    def test_contract_and_schema_are_additive_versioned_artifacts(self):
        self.assertTrue(CONTRACT.exists())
        schema = json.loads(SCHEMA.read_text())
        self.assertEqual(schema["properties"]["schema"]["const"], "c2e_input_frame/v0_3")
        self.assertEqual(schema["properties"]["comparison"]["properties"]["wrapper_identity_in_comparison"]["const"], False)

    def test_v03_handoff_retains_lineage_and_adds_verified_comparison(self):
        payload = json.loads(FIXTURE.read_text())
        payload["identity"]["contract_id"] = "C2E.HANDOFF.SIGNATURE.v0_3"
        payload["identity"]["schema_id"] = "c2e_input_frame/v0_3"
        payload["comparison_source"] = comparison_source()
        frame = build_input_frame_v0_3(payload)
        self.assertEqual(frame["schema"], "c2e_input_frame/v0_3")
        self.assertEqual(frame["comparison"]["signature_contract_id"], "C2E.STABLE.COMPARISON.SIGNATURES.v1")
        self.assertFalse(frame["comparison"]["wrapper_identity_in_comparison"])
        self.assertEqual(frame["lineage"]["parent_record_ids"], sorted(row["record_id"] for row in payload["parent_records"]))
        self.assertEqual(frame["authority"], "INACTIVE_NONCANONICAL_BUILD_TEST_ONLY")

    def test_wrapper_and_chronology_fields_are_rejected_from_comparison_basis(self):
        bad = comparison_source()
        bad["structural"]["LOCATION"]["facts"]["profile_output_id"] = "C2.FORMULA.OUTPUT.WRAPPER"
        with self.assertRaisesRegex(StableSignatureError, "WRAPPER_OR_PROHIBITED_COMPARISON_FIELD"):
            build_comparison_signatures(bad)
        payload = json.loads(FIXTURE.read_text())
        payload["identity"]["contract_id"] = "C2E.HANDOFF.SIGNATURE.v0_3"
        payload["identity"]["schema_id"] = "c2e_input_frame/v0_3"
        payload["comparison_source"] = bad
        with self.assertRaisesRegex(C2EHandoffError, "WRAPPER_OR_PROHIBITED_COMPARISON_FIELD"):
            build_input_frame_v0_3(payload)

    def test_wrapper_identity_churn_no_longer_triggers_phase_or_reparent(self):
        stable = build_comparison_signatures(comparison_source())
        previous = boundary_frame(
            structural_ids=("LOC.WRAP.1","MOT.WRAP.1","ORG.WRAP.1","INT.WRAP.1"),
            context_ids=("CTX.WRAP.1","LINK.WRAP.1"), comparison=stable,
        )
        current = boundary_frame(
            structural_ids=("LOC.WRAP.2","MOT.WRAP.2","ORG.WRAP.2","INT.WRAP.2"),
            context_ids=("CTX.WRAP.2","LINK.WRAP.2"), comparison=copy.deepcopy(stable),
        )
        result = evaluate_boundary_predicates_v2(current, previous)
        self.assertEqual(result["matched_rules"], ["C2E.RULE.JUNE.BASELINE.CONTINUATION.v1"])
        self.assertFalse(result["matched"]["C2E.RULE.JUNE.BASELINE.PHASE_MUTATION.v1"])
        self.assertFalse(result["matched"]["C2E.RULE.JUNE.BASELINE.RE_PARENT.v1"])

    def test_genuine_structural_content_change_still_triggers_phase_mutation(self):
        previous = boundary_frame(
            structural_ids=("L1","M1","O1","I1"), context_ids=("C1","P1"),
            comparison=build_comparison_signatures(comparison_source(location_value="ABOVE")),
        )
        current = boundary_frame(
            structural_ids=("L2","M2","O2","I2"), context_ids=("C2","P2"),
            comparison=build_comparison_signatures(comparison_source(location_value="BELOW")),
        )
        result = evaluate_boundary_predicates_v2(current, previous)
        self.assertTrue(result["matched"]["C2E.RULE.JUNE.BASELINE.PHASE_MUTATION.v1"])
        self.assertFalse(result["matched"]["C2E.RULE.JUNE.BASELINE.RE_PARENT.v1"])

    def test_genuine_parent_selection_or_dependency_change_triggers_reparent(self):
        previous = boundary_frame(
            structural_ids=("L1","M1","O1","I1"), context_ids=("C1","P1"),
            comparison=build_comparison_signatures(comparison_source(parent_id="PARENT.A", dep_status="AVAILABLE")),
        )
        selected_changed = boundary_frame(
            structural_ids=("L2","M2","O2","I2"), context_ids=("C2","P2"),
            comparison=build_comparison_signatures(comparison_source(parent_id="PARENT.B", dep_status="AVAILABLE")),
        )
        dependency_changed = boundary_frame(
            structural_ids=("L3","M3","O3","I3"), context_ids=("C3","P3"),
            comparison=build_comparison_signatures(comparison_source(parent_id="PARENT.A", dep_status="NOT_COMPUTABLE")),
        )
        self.assertTrue(evaluate_boundary_predicates_v2(selected_changed, previous)["matched"]["C2E.RULE.JUNE.BASELINE.RE_PARENT.v1"])
        self.assertTrue(evaluate_boundary_predicates_v2(dependency_changed, previous)["matched"]["C2E.RULE.JUNE.BASELINE.RE_PARENT.v1"])

    def test_no_threshold_selector_or_downstream_authority_added(self):
        result = evaluate_boundary_predicates_v2(
            boundary_frame(
                structural_ids=("L","M","O","I"), context_ids=("C","P"),
                comparison=build_comparison_signatures(comparison_source()),
            )
        )
        self.assertEqual(result["thresholds_used"], [])
        self.assertFalse(result["outcome_inputs_used"])
        self.assertFalse(result["family_inputs_used"])
        self.assertFalse(result["validation_inputs_used"])
        self.assertEqual(result["authority"], "CANDIDATE_INACTIVE_NONCANONICAL")

if __name__ == "__main__":
    unittest.main()
