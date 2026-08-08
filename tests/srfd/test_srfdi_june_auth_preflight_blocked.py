from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.orchestration import OrchestrationError, authority_guard

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_1.json"
MERGE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9/SRFDI_G9_MERGE_RECEIPT.json"
PREFLIGHT = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth/SRFDI_JUNE_AUTH_SOURCE_POPULATION_PREFLIGHT.json"
BLOCKER = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth/SRFDI_G_JUNE_AUTH_BLOCKER_PACKET.json"
REPRESENTATION = ROOT / "src/ovc/opt_b/srfd/representation.py"


class SRFDIJuneAuthPreflightBlockedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state = json.loads(STATE.read_text())
        cls.merge = json.loads(MERGE.read_text())
        cls.preflight = json.loads(PREFLIGHT.read_text())
        cls.blocker = json.loads(BLOCKER.read_text())

    def test_g9_is_completed_and_exact_preregistration_remains_frozen(self) -> None:
        self.assertEqual("d56986b90796b5547bc2b5d17146e6c7b62f43cf", self.merge["merge_commit"])
        self.assertEqual("PREREGISTRATION_FREEZE", self.merge["decision"])
        self.assertEqual(
            "76a18f79596772343f398256582dab9c37e219d01345c606204230c554599792",
            self.merge["preregistration"]["byte_sha256"],
        )
        self.assertEqual(
            "a832daad99b6df49199eced0c35632b15974f86b58a8e6481350294a87d3d32e",
            self.merge["preregistration"]["logical_sha256"],
        )
        wp9 = next(item for item in self.state["packets"] if item["packet_id"] == "SRFDI-WP9")
        self.assertEqual("COMPLETED", wp9["status"])
        self.assertEqual(self.merge["merge_commit"], wp9["merge_commit"])

    def test_read_only_source_preflight_reproduces_reference_count_but_does_not_bind_it(self) -> None:
        diagnostic = self.preflight["diagnostic_population"]
        self.assertEqual(9420, diagnostic["source_record_count"])
        self.assertEqual(8598, diagnostic["upstream_target_eligible_count"])
        self.assertEqual(8598, diagnostic["unique_target_c2_state_ids"])
        self.assertEqual(0, diagnostic["duplicate_target_c2_state_ids"])
        self.assertEqual(822, diagnostic["upstream_context_only_count"])
        self.assertEqual(4996, diagnostic["all_five_axes_evaluated_count"])
        self.assertEqual(3602, diagnostic["one_or_more_axes_not_evaluated_count"])
        self.assertEqual("NOT_BINDABLE", self.preflight["binding_disposition"])
        self.assertTrue(diagnostic["hash_status"].startswith("NON_BINDING_DIAGNOSTIC"))

    def test_real_source_schema_is_not_the_fixture_generic_srfd_source_schema(self) -> None:
        missing = set(self.preflight["observed_source_schema"]["srfd_generic_source_fields_not_present"])
        self.assertEqual(
            {"record_id", "structural", "computability_status", "representation_schema", "source_quality"},
            missing,
        )
        source = REPRESENTATION.read_text()
        self.assertIn('record.get("record_id"', source)
        self.assertIn('record.get("structural")', source)
        self.assertNotIn("c2_state_id", source)

    def test_june_authority_gate_is_blocked_and_authority_remains_denied(self) -> None:
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.state["current_gate"])
        self.assertEqual("BLOCKED", self.state["status"])
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual("BLOCKED", self.blocker["status"])
        self.assertFalse(self.blocker["gate_ready"])
        self.assertEqual("BLOCK", self.blocker["qa"]["result"])
        self.assertEqual("BLOCK", self.blocker["recommended_gate_decision"])
        self.assertEqual(
            ["AUTHORIZE_JUNE", "DEFER", "BLOCK", "QUARANTINE"],
            self.blocker["allowed_gate_decisions"],
        )
        self.assertEqual("DENIED", self.blocker["authority_effect"]["june_execution"])
        self.assertEqual("LOCKED_UNCONSUMED", self.blocker["authority_effect"]["validation_2025"])

    def test_existing_orchestration_still_fail_closes_june_execution(self) -> None:
        with self.assertRaisesRegex(OrchestrationError, "AUTH_JUNE_NOT_AUTHORISED"):
            authority_guard("june_market_benchmark")

    def test_smallest_resolution_cannot_silently_change_frozen_science(self) -> None:
        work = " ".join(self.blocker["smallest_lawful_resolution"]["required_work"])
        self.assertIn("read-only mapping", work)
        self.assertIn("eligible-ID/exclusion-ledger hashing", work)
        self.assertIn("fail-closed bounded-run authority verifier", work)
        self.assertIn("new operator-governed preregistration version", work)
        self.assertEqual("PRESERVE_DO_NOT_MERGE", self.blocker["authority_effect"]["pr_371"])


if __name__ == "__main__":
    unittest.main()
