import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BLOCKER = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-g6-replacement-run-prep/C2E2_G6_REPLACEMENT_RUN_PREP_PREFLIGHT_BLOCKER.json"
QA = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-g6-replacement-run-prep/C2E2_G6_REPLACEMENT_RUN_PREP_QA_PACKET.json"
SURVEY = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp0/C2E2_C2_SOURCE_SURFACE_SURVEY_v0_1.json"
OLD_MANIFEST = ROOT / "registries/implementation/c2e_v0_2/run_authority/C2E2_SOURCE_RUN_MANIFEST_JUNE_v0_1.json"


class C2E2G6ReplacementRunPrepBlockerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blocker = json.loads(BLOCKER.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.survey = json.loads(SURVEY.read_text())
        cls.old_manifest = json.loads(OLD_MANIFEST.read_text())

    def test_required_surface_is_exactly_the_frozen_handoff_surface(self):
        fields = {row["normative_field"]: row for row in self.survey["fields"]}
        self.assertEqual(fields["c2_record_id"]["source_record_identity"], "observation_id")
        for axis in ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION"):
            self.assertEqual(fields[axis]["source_record_identity"], "profile_output_id")
        self.assertIn("context_bundle_id", fields["parent_context_refs"]["source_record_identity"])

    def test_old_real_replay_is_still_discovery_sequence_window_population(self):
        source = self.old_manifest["source_population"]
        accepted = self.blocker["accepted_real_replay_surface"]["output_manifest"]
        self.assertEqual(source["input_binding_id"], "C2VNEXT.JUNE.DISCOVERY.INPUT.v1")
        self.assertEqual(source["logical_population_sha256"], accepted["logical_population_sha256"])
        self.assertEqual(accepted["opportunity_types"], ["REGISTERED_SEQUENCE_WINDOW"])
        self.assertEqual(accepted["object_families"], ["AXIS_BUNDLE"])
        self.assertEqual(accepted["requested"], 33320)

    def test_verified_surface_scan_finds_no_required_observation_profile_parent_ids(self):
        scan = self.blocker["accepted_real_replay_surface"]["marker_scan"]
        for marker in ("observation_id", "profile_output_id", "context_bundle_id", "C2.OBSERVATION", "C2.FORMULA.OUTPUT", "C2.PARENT.BUNDLE"):
            self.assertEqual(scan[marker], 0)

    def test_fail_closed_before_any_replacement_authority_object(self):
        status = self.blocker["run_status"]
        self.assertFalse(status["replacement_c2e_input_frame_population_frozen"])
        self.assertFalse(status["replacement_boundary_pack_created"])
        self.assertFalse(status["replacement_resource_envelope_created"])
        self.assertFalse(status["replacement_run_manifest_created"])
        self.assertFalse(status["replacement_run_token_created"])
        self.assertFalse(status["wp6_executed"])
        self.assertEqual(self.blocker["authority_effect"], "NONE")

    def test_qa_blocks_and_routes_to_separate_upstream_governance(self):
        self.assertEqual(self.qa["qa_disposition"], "BLOCK")
        self.assertIn("MANDATORY_C2_FOUR_AXIS_PROFILE_OUTPUT_SURFACE_NOT_MATERIALISED_IN_ACCEPTED_REAL_REPLAY", self.qa["blocking_warnings"])
        self.assertTrue(self.blocker["smallest_lawful_resolution"]["cannot_be_self_authorized_by_c2e"])
        self.assertEqual(self.blocker["next_action"], "STOP_BLOCKED_UPSTREAM_C2_OBSERVATION_LEVEL_REAL_MATERIALISATION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
