from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.console_vnext.application.research_native import (
    DegradedState, ValidationResolutionDenied, degraded, deny_validation_before_resolution,
)

ROOT = Path(__file__).resolve().parents[2]
CENSUS = ROOT / "registries/research_console_vnext/research_native/source_adapter_inventory_v2.json"


class ResearchNativeWP1Tests(unittest.TestCase):
    def test_census_covers_all_required_source_families(self):
        value = json.loads(CENSUS.read_text(encoding="utf-8"))
        sources = {x["capability_id"]: x for x in value["sources"]}
        self.assertEqual(set(sources), {"opt_a","c1","c2","c2e","c2p","c2_5","c3","sri_fdi","srfd","mcarb","dmrp_research_operations","evidence","programme_governance","irof"})
        authorised_pending_binding = {"opt_a", "c1", "c2", "c2e"}
        self.assertEqual(
            {capability_id for capability_id, source in sources.items() if source["real_route"] == "AUTHORIZED_PENDING_BINDING"},
            authorised_pending_binding,
        )
        for capability_id, source in sources.items():
            if capability_id in authorised_pending_binding:
                self.assertEqual("AUTHORIZED_PENDING_BINDING", source["real_route"])
            else:
                self.assertTrue(source["real_route"].startswith("DENIED"), capability_id)
        self.assertEqual("DENIED", sources["c2p"]["real_route"])
        self.assertEqual("DENIED", sources["c2_5"]["real_route"])
        self.assertEqual("DENIED", sources["c3"]["real_route"])

    def test_missing_owner_is_typed_not_fabricated(self):
        status = degraded(DegradedState.NOT_MATERIALIZED, owner="OPT-B.C3", capability_id="c3")
        self.assertFalse(status.materialized)
        self.assertFalse(status.authorised)
        self.assertEqual(status.reason_codes, ("NOT_MATERIALIZED",))

    def test_validation_denial_precedes_locator_resolution(self):
        with self.assertRaisesRegex(ValidationResolutionDenied, "VALIDATION_DENIED_BEFORE_PROTECTED_RESOLUTION") as ctx:
            deny_validation_before_resolution({"role":"VALIDATION","path":"SECRET/PATH","count":99,"timestamp":"SECRET"})
        self.assertNotIn("SECRET", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
