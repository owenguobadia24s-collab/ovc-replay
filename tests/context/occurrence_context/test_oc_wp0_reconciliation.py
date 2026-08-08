import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs/releases/occurrence-context-v0-1/oc-wp0"

class OCWP0ReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.census = json.loads((BASE / "OC_WP0_SOURCE_SURFACE_CENSUS.json").read_text())
        cls.auth = json.loads((BASE / "OC_WP0_AUTHORITY_FREEZE.json").read_text())
        cls.gaps = json.loads((BASE / "OC_WP0_REGISTRY_GAP_LEDGER.json").read_text())
        cls.collisions = json.loads((BASE / "OC_WP0_COLLISION_AND_DEPRECATION_LEDGER.json").read_text())
        cls.qa = json.loads((BASE / "OC_WP0_QA_PACKET.json").read_text())
        cls.decision = json.loads((BASE / "OC_G1_DELEGATED_DECISION.json").read_text())

    def test_baseline_and_no_runtime_collision(self):
        self.assertEqual(self.census["baseline_main"], "d85d98470ebfd4d2a7a911e5e22b7962e8a1ca6a")
        self.assertEqual(self.census["standalone_occurrence_context_runtime_on_baseline"], "ABSENT")
        self.assertFalse(self.census["validation_rows_read"])
        self.assertFalse(self.census["provider_fetch"])

    def test_authority_freeze_is_fail_closed(self):
        self.assertEqual(self.auth["authorized"]["instrument_ids"], ["GBPUSD"])
        self.assertEqual(self.auth["authorized"]["price_sides"], ["BID", "ASK"])
        for key, value in self.auth["denied"].items():
            self.assertTrue(value, key)
        self.assertEqual(self.auth["validation"], "LOCKED_UNCONSUMED")

    def test_registry_gaps_are_visible_and_noninvented(self):
        by_id = {x["gap_id"]: x for x in self.gaps["gaps"]}
        self.assertEqual(by_id["OC-GAP-CALENDAR-SESSION-REGISTRY"]["classification"], "OPTIONAL_DEFER")
        self.assertIn("NO_ACTIVE_SESSION_BOUNDARY_DEFINITION", by_id["OC-GAP-CALENDAR-SESSION-REGISTRY"]["lawful_resolution"])
        self.assertEqual(self.gaps["blocking_gaps"], [])

    def test_srfdo_occurrence_context_is_preserved_not_reused(self):
        entry = next(x for x in self.collisions["entries"] if x["subject"] == "SRFDOccurrenceContext")
        self.assertEqual(entry["disposition"], "PRESERVE_UNCHANGED")
        self.assertEqual(self.collisions["namespace_reserved_for_forward_service"], "ovc.context.occurrence_context")

    def test_qa_and_delegated_gate_are_nonreserved_pass(self):
        self.assertEqual(self.qa["recommendation"], "PASS")
        self.assertEqual(self.qa["blockers"], [])
        self.assertEqual(self.decision["gate_id"], "OC-G1")
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(self.decision["authority_delta"], "NONE")
        self.assertTrue(self.decision["reserved_boundaries_unchanged"])

if __name__ == "__main__":
    unittest.main()
