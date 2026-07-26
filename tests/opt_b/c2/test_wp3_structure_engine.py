from __future__ import annotations

import copy
import unittest

from ovc.opt_b.c2.adapter import HandoffError, accept_c1_record
from ovc.opt_b.c2.containers import build_containers
from ovc.opt_b.c2.levels import build_levels
from ovc.opt_b.c2.relations import build_relation_set


def parent() -> dict:
    measurements = {f"m{i}": str(i) for i in range(12)}
    measurements.update({"range_low":"1.1000","range_high":"1.1100","swing_low":"1.0950","swing_high":"1.1150","close":"1.1075","atr":"0.0025"})
    return {
        "c1_record_id":"c1:test:1","c1_release_id":"OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1",
        "c1_manifest_id":"MANIFEST.C1.TEST","opt_a_release_id":"OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
        "opt_a_manifest_id":"MANIFEST.OPT-A.TEST","role":"DISCOVERY","authority_state":"ACTIVE_DISCOVERY",
        "instrument":"GBPUSD","clock":"15M","side":"BID","close_time":"2023-01-01T00:15:00Z",
        "first_valid_time":"2023-01-01T00:15:00Z","measurements":measurements,"quality_state":"PASS",
    }


class WP3StructureTrustTests(unittest.TestCase):
    def test_adapter_rejects_validation(self):
        value=parent(); value["role"]="VALIDATION"; value["authority_state"]="ACTIVE_VALIDATION"
        with self.assertRaises(HandoffError): accept_c1_record(value)

    def test_adapter_rejects_future_leakage(self):
        value=parent(); value["future_outcome"]="UP"
        with self.assertRaises(HandoffError): accept_c1_record(value)

    def test_levels_are_deterministic_and_first_valid(self):
        one=build_levels(parent()); two=build_levels(copy.deepcopy(parent()))
        self.assertEqual(one,two)
        self.assertEqual(len(one),4)
        self.assertTrue(all(item["c2_level_id"].startswith("c2-level:") for item in one))

    def test_containers_preserve_all_eligible_boundaries(self):
        built=build_containers(parent())
        self.assertEqual({x["container_type"] for x in built},{"LOCAL_RANGE","SWING_ENVELOPE"})
        self.assertTrue(all(x["status"]=="ACTIVE" for x in built))

    def test_relation_set_is_complete_without_hidden_selection(self):
        value=parent(); levels=build_levels(value); containers=build_containers(value)
        result=build_relation_set(value,levels,containers)
        self.assertTrue(result["complete_inventory"])
        self.assertEqual(len(result["relations"]),len(levels)+len(containers))
        self.assertNotIn("winning_level",result)

    def test_inverted_container_is_visible_conflict(self):
        value=parent(); value["measurements"]["range_low"]="1.1200"
        built=build_containers(value)
        local=next(x for x in built if x["container_type"]=="LOCAL_RANGE")
        self.assertEqual(local["status"],"CONFLICT")


if __name__ == "__main__":
    unittest.main()
