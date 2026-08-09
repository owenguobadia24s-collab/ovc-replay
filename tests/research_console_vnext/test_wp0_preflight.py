from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts" / "research_console_vnext"
STATE = ROOT / "registries" / "implementation" / "research_console_vnext" / "OVC_RCN_STATE_v0_1.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class RCNWP0PreflightTests(unittest.TestCase):
    def test_wp0_preflight_is_authority_neutral_and_stops_before_real_sources(self):
        value = _load(ART / "RCN_WP0_PREFLIGHT.json")
        self.assertEqual(value["status"], "PASS")
        self.assertEqual(value["authority"]["authority_effect"], "NONE")
        self.assertEqual(value["authority"]["real_source_route_exposure"], "DENIED_UNTIL_RCN_G4")
        self.assertEqual(value["stop_boundary"], "RCN-G3V")

    def test_reuse_census_is_complete_for_frozen_console_tree(self):
        value = _load(ART / "RCN_REUSE_CENSUS_v0_1.json")
        paths = {row["path"] for row in value["entries"]}
        self.assertEqual(len(paths), 24)
        self.assertTrue({"Home.py", "shell.py", "repository_topology_surface.py"}.issubset(paths))
        self.assertTrue(
            all(
                row["disposition"]
                in {
                    "REUSE_AS_DOMAIN_OR_APPLICATION_LOGIC",
                    "EXTRACT_AND_REFACTOR",
                    "SUPERSEDE",
                    "HISTORICAL_ONLY",
                }
                for row in value["entries"]
            )
        )

    def test_visual_target_hash_and_primary_canvas_contract(self):
        value = _load(ART / "RCN_VISUAL_TARGET_MANIFEST_v0_1.json")
        self.assertEqual(
            value["sha256"],
            "6f2bbfcdbed1ebf6090b78f25e2f3d14bf7da334719864eb4f1f8a0be47e3257",
        )
        self.assertEqual(
            [v["min_primary_canvas_height"] for v in value["supported_viewports"]],
            [420, 300, 260],
        )

    def test_toolchain_lock_is_exact_and_self_identifying(self):
        value = _load(ART / "RCN_TOOLCHAIN_LOCK_v0_1.json")
        canonical = json.dumps(value["tools"], sort_keys=True, separators=(",", ":"))
        self.assertEqual(
            value["canonical_selection_sha256"],
            hashlib.sha256(canonical.encode()).hexdigest(),
        )

    def test_programme_state_preserves_g0_boundaries_as_execution_progresses(self):
        value = _load(STATE)
        self.assertEqual(value["programme_id"], "OVC-RC-VNEXT-GREENFIELD-v0.1")
        self.assertEqual(value["plan_id"], "OVC-RC-VNEXT-GREENFIELD-IMPLEMENTATION-PLAN-0.1-FINAL-REVISED-1")
        self.assertIn(value["status"], {"APPROVED", "RUNNING", "IMPLEMENTED", "QA_REVIEW", "GATE_READY", "COMPLETED"})
        self.assertEqual(value["stop_boundary"], "RCN-G3V")
        self.assertNotIn("EXPOSURE", value["authority_delta"])
        self.assertNotIn("VALIDATION", value["authority_delta"])


if __name__ == "__main__":
    unittest.main()
