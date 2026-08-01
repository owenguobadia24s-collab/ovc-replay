from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from apps.research_console.ro4_projection_source import load_disabled_projection, route_registration
from ovc.research_operations.v0_4.console_projection import (
    REQUIRED_BANNERS,
    ROUTE_STATE,
    RO4ProjectionDenied,
    RO4ProjectionError,
    build_console_projection,
    count_cell,
    validate_console_projection,
    verify_projection_schema_binding,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/research_operations/v0_4/RO4_WP5_CONSOLE_PROJECTION_FIXTURE_v0_1.json"


class RO4G5ConsoleProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def build(self, **overrides):
        values = {
            "source_commit": self.fixture["source_commit"],
            "source_release_refs": deepcopy(self.fixture["source_release_refs"]),
            "panels": deepcopy(self.fixture["panels"]),
            "schema_root": ROOT,
        }
        values.update(overrides)
        return build_console_projection(**values)

    def test_schema_binding_is_exact(self):
        binding = verify_projection_schema_binding(ROOT)
        self.assertEqual("83bcf57c0374411dfdf02a61483b529b46f333c7", binding["git_blob_sha"])

    def test_projection_is_deterministic_disabled_and_read_only(self):
        first = self.build()
        second = self.build()
        self.assertEqual(first, second)
        self.assertEqual(ROUTE_STATE, first["route_state"])
        self.assertEqual("NONE", first["writes"])
        self.assertEqual("DENIED", first["remote_deployment"])
        self.assertEqual(REQUIRED_BANNERS, tuple(first["authority_banners"]))

    def test_count_cell_requires_visible_denominator(self):
        cell = count_cell(count=3, eligible_denominator=5, excluded_count=1, missing_count=1, slice_identity="slice-1")
        self.assertEqual("3 of 5 eligible records", cell["display_text"])
        with self.assertRaises(RO4ProjectionError):
            count_cell(count=6, eligible_denominator=5, slice_identity="slice-1")

    def test_percentage_ratio_heatmap_and_actions_are_denied(self):
        for key in ("percentage", "ratio", "heatmap", "actions"):
            panels = deepcopy(self.fixture["panels"])
            panels[0]["payload"][key] = 1
            with self.subTest(key=key), self.assertRaises(RO4ProjectionDenied):
                self.build(panels=panels)

    def test_validation_is_denied_before_panel_resolution(self):
        refs = deepcopy(self.fixture["source_release_refs"])
        refs[0]["role"] = "VALIDATION"
        refs[0]["release_id"] = "OPT-B.C2.GBPUSD.VALIDATION.2025.v2"
        with self.assertRaisesRegex(RO4ProjectionDenied, "VALIDATION_DENIED"):
            self.build(source_release_refs=refs, panels=[{"invalid": True}])

    def test_pattern_discovery_panel_is_trace_only(self):
        panels = deepcopy(self.fixture["panels"])
        pd_panel = next(panel for panel in panels if panel["panel_class"] == "PD_TRIGGER_TRACE_ONLY")
        pd_panel["payload"]["candidate_ids"] = ["PD.CANDIDATE.1"]
        with self.assertRaisesRegex(RO4ProjectionDenied, "PD_TRACE_EXCEEDS"):
            self.build(panels=panels)

    def test_silent_sampling_is_denied(self):
        panels = deepcopy(self.fixture["panels"])
        panels[0]["payload"]["sampled"] = True
        with self.assertRaisesRegex(RO4ProjectionDenied, "SILENT_SAMPLING"):
            self.build(panels=panels)

    def test_deterministic_sample_disclosure_is_accepted(self):
        panels = deepcopy(self.fixture["panels"])
        panels[0]["payload"]["sampled"] = True
        panels.append({
            "panel_id": "RO4-SAMPLE-DISCLOSURE",
            "panel_class": "SAMPLE_DISCLOSURE",
            "payload": {
                "sample_manifest_sha256": "c" * 64,
                "sample_count": 2,
                "population_count": 4,
                "method": "IDENTITY_ORDERED_FIRST_N",
                "deterministic": True,
                "banner": "SAMPLED ONLY — 2 of 4 eligible records",
            },
        })
        projection = self.build(panels=panels)
        self.assertTrue(any(panel["panel_class"] == "SAMPLE_DISCLOSURE" for panel in projection["panels"]))

    def test_tampered_route_or_logical_hash_is_denied(self):
        projection = self.build()
        route_tamper = deepcopy(projection)
        route_tamper["route_state"] = "ENABLED_LOCAL_READ_ONLY"
        with self.assertRaises(RO4ProjectionDenied):
            validate_console_projection(route_tamper, schema_root=ROOT)
        hash_tamper = deepcopy(projection)
        hash_tamper["logical_hash"] = "0" * 64
        with self.assertRaisesRegex(RO4ProjectionError, "LOGICAL_HASH_MISMATCH"):
            validate_console_projection(hash_tamper, schema_root=ROOT)

    def test_local_source_loads_without_route_registration(self):
        projection = self.build()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "projection.json"
            path.write_text(json.dumps(projection), encoding="utf-8")
            loaded = load_disabled_projection(path, schema_root=ROOT)
        self.assertEqual(projection, loaded)
        self.assertIsNone(route_registration())

    def test_fixture_is_non_authoritative(self):
        self.assertEqual("SYNTHETIC_NON_AUTHORITATIVE", self.fixture["status"])
        self.assertFalse(self.fixture["operator_evidence"])
        self.assertEqual("NONE", self.fixture["market_authority"])


if __name__ == "__main__":
    unittest.main()
