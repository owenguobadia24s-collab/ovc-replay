from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/dsai3v-wp11"
STATE_ROOT = ROOT / "registries/implementation/dsai_vit_v0_3"
AUTHORITY = ROOT / "registries/authority/DSAI3V_VIT_GENERAL_AUTHORITY_v0_1.json"


class DsaiVitV03Wp11CloseoutTests(unittest.TestCase):
    def _load(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_two_independent_general_smoke_lanes_are_exact_and_serial(self) -> None:
        pack = self._load(RELEASE / "DSAI3V_WP11_GENERAL_SMOKE_RECEIPTS.json")
        self.assertEqual(len(pack["lanes"]), 2)
        self.assertTrue(pack["chain_complete"])
        self.assertTrue(pack["second_lane_predecessor_equals_first_lane_physical_commit"])
        self.assertTrue(pack["all_exact_tree_equal"])
        self.assertEqual(pack["parallel_merges"], 0)
        self.assertEqual(pack["tree_mismatches"], 0)
        self.assertEqual(pack["false_authority_allows"], 0)
        self.assertEqual(pack["duplicate_effective_writes"], 0)
        self.assertEqual(pack["lost_mandatory_receipts"], 0)
        self.assertEqual(pack["safety_class_incidents"], 0)
        first, second = pack["lanes"]
        self.assertEqual(first["physical_tree"], first["qualified_tree"])
        self.assertEqual(second["physical_tree"], second["qualified_tree"])
        self.assertEqual(second["baseline_main"], first["physical_commit"])

    def test_general_authority_and_bindings_remain_narrow(self) -> None:
        authority = self._load(AUTHORITY)
        self.assertEqual(authority["authority_status"], "ACTIVE")
        self.assertEqual(authority["required_authority_delta"], "NONE")
        self.assertEqual(authority["physical_gateway"], "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY")
        self.assertFalse(authority["serialization"]["parallel_physical_merge"])
        self.assertEqual(authority["grt_binding"]["grt_g3"], "NOT_AUTHORISED")
        self.assertEqual(authority["reserved_boundaries"], "PROGRAMME_OWNED_AND_UNCHANGED")

    def test_programme_frontier_is_wp11_closeout_or_completed(self) -> None:
        pointer = self._load(STATE_ROOT / "CURRENT_STATE_POINTER.json")
        self.assertIn(pointer["status"], {"QA_REVIEW", "COMPLETED"})
        self.assertEqual(pointer["current_packet"], "DSAI3V-WP11")
        self.assertEqual(pointer["current_gate"], "DSAI3V-G11")
        self.assertEqual(pointer["next_packet"], "DSAI3V-WP12")


if __name__ == "__main__":
    unittest.main()
