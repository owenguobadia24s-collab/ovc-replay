from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.stability_metrics_v04 import logical_sha256, validate_metric_registry

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9d"
PREREG = ROOT / "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_4.json"
REGISTRY = ROOT / "registries/research/srfd/stability_metric_specs_v0_4.json"
MANIFEST = BASE / "SRFD_JUNE_RUN_MANIFEST_v0_4_CANDIDATE.json"
QA = BASE / "SRFDI_WP9D_QA_PACKET.json"
ASSURANCE = BASE / "SRFDI_WP9D_ASSURANCE_RECEIPT.json"
GATE = BASE / "SRFDI_G9D_FREEZE_OPERATOR_PACKET.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_9_CANDIDATE.json"
HISTORICAL_PREFREEZE_STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_8.json"


class SRFDIWP9DGateReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prereg = json.loads(PREREG.read_text())
        cls.registry = json.loads(REGISTRY.read_text())
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.assurance = json.loads(ASSURANCE.read_text())
        cls.gate = json.loads(GATE.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.historical_prefreeze_state = json.loads(HISTORICAL_PREFREEZE_STATE.read_text())

    def test_scientific_hashes_are_exact_and_mutually_bound(self) -> None:
        self.assertEqual("371a058e26c05a351a99689ad23b7f844fbc956a6d81449fd237a2f420bf564b", validate_metric_registry(self.registry))
        self.assertEqual("f0da6203124a6aeaa83f89e3f27b2fc980754f874ae96e631009dfc9048f2fa3", logical_sha256(self.prereg))
        self.assertEqual("70763e69281b3980eebf0ed7a2008c78ef29e5e463a5694110eec5ca027fb529", logical_sha256(self.manifest))
        self.assertEqual(self.registry["metric_order"], self.prereg["stability_metrics"])
        self.assertEqual(self.prereg["stability_metrics"], self.manifest["candidate_sets"]["stability_metrics"])

    def test_gate_is_one_operator_reserved_freeze_decision(self) -> None:
        self.assertEqual("SRFDI-G9D-FREEZE", self.gate["gate_id"])
        self.assertTrue(self.gate["operator_decision_required"])
        self.assertEqual("PREREGISTRATION_FREEZE", self.gate["recommended_decision"])
        self.assertEqual("OVC APPROVE SRFDI-G9D-FREEZE PREREGISTRATION_FREEZE", self.gate["exact_operator_command"])
        self.assertEqual("STABILITY_AND_AMBIGUITY_METRIC_EXECUTION_SPECIFICATION_ONLY", self.gate["approved_candidate_if_frozen"]["supersession_scope"])

    def test_qa_and_assurance_pass_without_market_execution(self) -> None:
        self.assertEqual("PASS", self.qa["qa_result"])
        self.assertEqual("PREREGISTRATION_FREEZE", self.qa["recommended_disposition"])
        self.assertEqual("PASS", self.assurance["result"])
        self.assertEqual(535, self.assurance["repository_suite"]["test_count"])
        firewall = self.assurance["scientific_firewall"]
        self.assertFalse(firewall["june_benchmark_started"])
        self.assertFalse(firewall["june_scientific_outputs_generated_or_inspected"])
        self.assertFalse(firewall["v0_3_authority_token_consumed"])
        self.assertEqual("DENIED", firewall["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", firewall["validation_2025"])

    def test_candidate_state_is_gate_ready_but_non_authoritative(self) -> None:
        self.assertEqual("CANDIDATE_NONAUTHORITATIVE_PENDING_OPERATOR_FREEZE", self.state["state_role"])
        self.assertEqual("GATE_READY_SUBJECT_TO_FINAL_EXACT_HEAD_CI", self.state["status"])
        self.assertEqual("SRFDI-G9D-FREEZE", self.state["current_gate"])
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual("UNCONSUMED", self.state["authority"]["v0_3_authority_token"])
        self.assertEqual("DENIED", self.state["authority"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.state["authority"]["validation_2025"])

    def test_historical_prefreeze_authority_is_preserved_after_freeze(self) -> None:
        # The current pointer is intentionally mutable. The immutable v0.8 record is
        # the historical proof of the authority state that existed before G9D.
        self.assertEqual("BLOCKED_PRE_RUN", self.historical_prefreeze_state["status"])
        self.assertEqual("SRFDI-WP10-v0.3", self.historical_prefreeze_state["active_packet"])
        self.assertFalse(self.historical_prefreeze_state["exact_bindings"]["authority_token_consumed"])
        self.assertEqual("DENIED", self.historical_prefreeze_state["authority"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.historical_prefreeze_state["authority"]["validation_2025"])

    def test_inert_manifest_never_reuses_v03_authority(self) -> None:
        self.assertEqual("CANDIDATE_NO_RUN_AUTHORITY", self.manifest["status"])
        self.assertTrue(self.manifest["authority"]["june_execution"].startswith("DENIED"))
        self.assertEqual("DENIED", self.manifest["authority"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.manifest["authority"]["validation_2025"])


if __name__ == "__main__":
    unittest.main()
