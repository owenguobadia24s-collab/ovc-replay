from __future__ import annotations

import unittest

from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_ledger import LedgerPlacement, VirtualIntegrationLedger
from ovc.development.skills.vit_qualification import (
    VITRebuildManifest,
    build_rebuild_manifest,
    rebuild_ledger,
    run_q0_q1_reference_qualification,
    synthetic_authority_laundering_fixture,
    synthetic_false_commutativity_fixture,
    synthetic_split_brain_fixture,
)


class DsaiVitV03Wp6Tests(unittest.TestCase):
    def test_q0_q1_zero_tolerance_reference_report_passes(self) -> None:
        report = run_q0_q1_reference_qualification()
        self.assertTrue(report.q0_mechanical_pass)
        self.assertTrue(report.q1_adversarial_pass)
        self.assertTrue(report.zero_safety_violations)
        self.assertTrue(report.zero_reference_disagreements)
        self.assertTrue(report.zero_false_operator_allows)
        self.assertTrue(report.zero_duplicate_effective_materialisations)
        self.assertEqual(report.optimized_path_status,"REFERENCE_ONLY_NOT_APPLICABLE")

    def test_ledger_rebuild_is_deterministic(self) -> None:
        ledger = VirtualIntegrationLedger()
        placement = LedgerPlacement("p","a"*40,"b"*40,"profile",0,"dep","auth")
        ledger.append(placement)
        manifest = build_rebuild_manifest(ledger)
        rebuilt = rebuild_ledger(manifest)
        self.assertEqual(rebuilt.placements, ledger.placements)
        self.assertEqual(build_rebuild_manifest(rebuilt).manifest_id, manifest.manifest_id)

    def test_orphan_frontier_fails_closed(self) -> None:
        manifest = VITRebuildManifest((),"missing")
        with self.assertRaises(VitContractError):
            rebuild_ledger(manifest)

    def test_adversarial_authority_conflict_and_split_brain_are_denied(self) -> None:
        self.assertNotEqual(synthetic_false_commutativity_fixture(),"COMMUTATIVE")
        self.assertEqual(synthetic_authority_laundering_fixture(),"WAITING_OPERATOR_AUTHORITY")
        self.assertEqual(synthetic_split_brain_fixture(),("LEASE_VALID","LEASE_UNAVAILABLE"))


if __name__ == "__main__":
    unittest.main()
