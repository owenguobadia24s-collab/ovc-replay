import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ovc.opt_b.c2e_v2.replacement_run_preflight import assess_accepted_surface

ROOT = Path(__file__).resolve().parents[4]
SURVEY = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp0/C2E2_C2_SOURCE_SURFACE_SURVEY_v0_1.json"
OLD_MANIFEST = ROOT / "registries/implementation/c2e_v0_2/run_authority/C2E2_SOURCE_RUN_MANIFEST_JUNE_v0_1.json"


class C2E2G6ReplacementRunPreflightTests(unittest.TestCase):
    def test_frozen_handoff_requires_observation_profiles_and_parent_context(self):
        survey = json.loads(SURVEY.read_text())
        by_name = {row["normative_field"]: row for row in survey["fields"]}
        self.assertEqual(by_name["c2_record_id"]["source_record_identity"], "observation_id")
        for axis in ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION"):
            self.assertEqual(by_name[axis]["source_record_identity"], "profile_output_id")
        self.assertIn("context_bundle_id", by_name["parent_context_refs"]["source_record_identity"])

    def test_old_authorized_run_manifest_binds_discovery_population_not_observation_frames(self):
        old = json.loads(OLD_MANIFEST.read_text())
        source = old["source_population"]
        self.assertEqual(source["input_binding_id"], "C2VNEXT.JUNE.DISCOVERY.INPUT.v1")
        self.assertEqual(source["logical_population_sha256"], "3f1089e3a4eefe94147c8c2f912e77899e4ed21fe8b3b8b85993e47bf7151ee7")
        self.assertEqual(source["counts"]["requested"], 33320)
        self.assertNotIn("population_unit", source)
        self.assertNotIn("observation_population_sha256", source)

    def test_probe_blocks_sequence_window_artifacts_without_required_surface(self):
        with TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = root / "output-manifest.json"
            manifest.write_text(json.dumps({
                "schema":"ovc-c2-vnext-full-population-replay-manifest/v1",
                "binding_id":"BINDING",
                "logical_population_sha256":"abc",
                "scope":{"opportunity_types":["REGISTERED_SEQUENCE_WINDOW"],"object_families":["AXIS_BUNDLE"],"sequence_lengths":[2,3]},
                "counts":{"requested":2},
            }) + "\n")
            requests = root / "requests.jsonl"
            requests.write_text('{"source_unit_id":"SEQ.1"}\n{"source_unit_id":"SEQ.2"}\n')
            result = assess_accepted_surface(output_manifest=manifest, replay_artifacts={"requests":requests})
            self.assertEqual(result["disposition"], "BLOCK")
            self.assertTrue(result["sequence_window_population"])
            self.assertFalse(result["required_observation_profile_parent_surface_materialised"])
            self.assertEqual(result["marker_totals"]["observation_id"], 0)
            self.assertEqual(result["marker_totals"]["profile_output_id"], 0)
            self.assertEqual(result["marker_totals"]["context_bundle_id"], 0)

    def test_probe_pass_requires_materialised_observation_profile_parent_surface(self):
        with TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = root / "output-manifest.json"
            manifest.write_text(json.dumps({
                "schema":"candidate-observation-replay/v1","binding_id":"BINDING","logical_population_sha256":"abc",
                "scope":{"opportunity_types":[],"object_families":[],"sequence_lengths":[]},"counts":{"requested":1},
            }) + "\n")
            frames = root / "frames.jsonl"
            frames.write_text(json.dumps({
                "observation_id":"C2.OBSERVATION.1",
                "profile_output_id":"C2.FORMULA.OUTPUT.1",
                "context_bundle_id":"C2.PARENT.BUNDLE.1",
            }) + "\n")
            result = assess_accepted_surface(output_manifest=manifest, replay_artifacts={"frames":frames})
            self.assertEqual(result["disposition"], "PASS")
            self.assertFalse(result["sequence_window_population"])
            self.assertTrue(result["required_observation_profile_parent_surface_materialised"])


if __name__ == "__main__":
    unittest.main()
