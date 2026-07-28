from __future__ import annotations

import unittest

from ovc.research_operations.pattern_discovery import pilot_corrective_rerun as corrective
from ovc.research_operations.pattern_discovery import pilot_discovery as pilot


class C1CG5PilotCorrectiveRerunTests(unittest.TestCase):
    def tearDown(self) -> None:
        for name, value in corrective._ORIGINAL_VALUES.items():
            setattr(pilot, name, value)
        pilot.load_governed_authority = corrective._ORIGINAL_LOAD_AUTHORITY

    def test_corrective_identity_is_new_noncanonical_namespace(self) -> None:
        corrective.configure()
        self.assertEqual(pilot.AUTHORITY_GATE, "C1C-G5")
        self.assertEqual(pilot.NEXT_GATE, "C1C-G5-CORRECTIVE-PILOT-REVIEW")
        self.assertEqual(pilot.PILOT_NAMESPACE, "PD.PILOT.GBPUSD.20260622_20260625.v2")
        self.assertNotEqual(pilot.PILOT_NAMESPACE, corrective._ORIGINAL_VALUES["PILOT_NAMESPACE"])
        self.assertEqual(pilot.ACTIVE_C2_RELEASE, "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2")
        self.assertEqual(
            pilot.C2_MANIFEST_ID,
            "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2.r1",
        )
        self.assertIn("PILOT_ONLY", pilot.PILOT_BANNER)
        self.assertIn("NON_PROMOTABLE", pilot.PILOT_BANNER)
        self.assertIn("C1C_CORRECTIVE_RERUN", pilot.PILOT_BANNER)

    def test_source_and_signing_bindings_remain_exact(self) -> None:
        corrective.configure()
        self.assertEqual(pilot.RUN_ID, "RPS.RUN.7aeb551335d766ee3bf503e6")
        self.assertEqual(pilot.BINDING_ID, "RPS.BINDING.32fb3003efa072916c11e907")
        self.assertEqual(pilot.ACCEPTANCE_ID, "RPS.REPLAY-ACCEPT.0844eddf74e144ced487cc48")
        self.assertEqual(pilot.SIGNING_BINDING_ID, "RPS.SIGNING.50092c28981fef08f53a6cb5")
        self.assertEqual(pilot.OPERATION_MODE, "TIME_GATED_REPLAY")
        self.assertEqual(pilot.RESEARCH_ROLE, "PILOT_DISCOVERY")

    def test_new_namespace_changes_all_public_pilot_ids(self) -> None:
        source = "fixed-engine-identity"
        pilot.PILOT_NAMESPACE = str(corrective._ORIGINAL_VALUES["PILOT_NAMESPACE"])
        old = pilot._pilot_id("CANDIDATE", source)
        corrective.configure()
        new = pilot._pilot_id("CANDIDATE", source)
        self.assertNotEqual(old, new)
        self.assertTrue(new.startswith("PDPILOT-CANDIDATE-"))


if __name__ == "__main__":
    unittest.main()
