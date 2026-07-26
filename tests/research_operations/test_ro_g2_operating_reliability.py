from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FINAL_PACKET = ROOT / "docs/releases/research-operations-foundation/ro-g2/RO_G2_GATE_PACKET.json"
CANDIDATE_PACKET = ROOT / "docs/releases/research-operations-foundation/ro-wp2/RO_G2_CANDIDATE_GATE_PACKET.json"
DECISION = ROOT / "docs/releases/research-operations-foundation/ro-g2/RO_G2_OPERATOR_DECISION.md"
AUTHORITY = ROOT / "registries/authority/ACTIVE_AUTHORITY.yaml"
IMPLEMENTATION = ROOT / "registries/research_operations/RESEARCH_OPERATIONS_IMPLEMENTATION_REGISTRY_v0_1.yaml"
COMMANDS = ROOT / "registries/research_operations/RESEARCH_OPERATIONS_COMMAND_REGISTRY_v0_1.json"


class ROG2OperatingReliabilityTests(unittest.TestCase):
    def test_candidate_and_final_gate_packets_are_complete_pass(self) -> None:
        candidate = json.loads(CANDIDATE_PACKET.read_text(encoding="utf-8"))
        final = json.loads(FINAL_PACKET.read_text(encoding="utf-8"))
        self.assertEqual(candidate["operator_disposition"], "PENDING_REVIEW")
        self.assertEqual(len(candidate["checks"]), 7)
        self.assertTrue(all(item["status"] == "PASS" for item in candidate["checks"]))
        self.assertEqual(final["gate_id"], "RO-G2")
        self.assertEqual(final["operator_disposition"], "PASS")
        self.assertEqual(len(final["checks"]), 10)
        self.assertTrue(all(item["status"] == "PASS" for item in final["checks"]))
        self.assertEqual(final["authority_delta"]["ro_wp3"], "AUTHORISED_FOR_BUILD")

    def test_command_surface_has_no_delete_or_remote_side_effect(self) -> None:
        registry = json.loads(COMMANDS.read_text(encoding="utf-8"))
        commands = {item["command"] for item in registry["commands"]}
        self.assertEqual(len(commands), 12)
        self.assertFalse(any(" delete" in command for command in commands))
        self.assertEqual(registry["network_operations"], "NONE")
        self.assertEqual(registry["git_operations"], "NONE")
        self.assertEqual(registry["r2_operations"], "NONE")
        self.assertEqual(registry["market_classification"], "NONE")

    def test_authority_delta_is_bounded_and_structurally_nested(self) -> None:
        authority = AUTHORITY.read_text(encoding="utf-8")
        implementation = IMPLEMENTATION.read_text(encoding="utf-8")
        decision = DECISION.read_text(encoding="utf-8")

        self.assertIn("state: RO_G2_PASS_WP3_BUILD_AUTHORISED", authority)
        self.assertIn("ro_wp3: AUTHORISED_FOR_BUILD", authority)
        self.assertIn("service_activation: BOUNDED_LOCAL_OPERATIONS_APPROVED", authority)
        self.assertIn("cli: APPROVED_BOUNDED_LOCAL_OPERATION", authority)
        self.assertIn("artifact_catalogue: APPROVED_READ_VERIFY_REPORT_LOCAL", authority)
        self.assertIn("qa_runner: AUTHORISED_FOR_BUILD_NOT_ACTIVE", authority)
        self.assertIn("read_model: AUTHORISED_FOR_BUILD_NOT_ACTIVE", authority)
        self.assertIn("console: AUTHORISED_FOR_BUILD_NOT_ACTIVE", authority)
        self.assertIn("status: PASS_RO_WP3_BUILD_AUTHORISED", implementation)
        self.assertIn("PASS — BOUNDED LOCAL OPERATIONS APPROVED; RO-WP3 AUTHORISED FOR BUILD", decision)

        lines = authority.splitlines()
        ro_index = lines.index("  research_operations:")
        c2_index = lines.index("  opt_b_c2_v2:")
        block = lines[ro_index + 1:c2_index]
        self.assertTrue(block)
        self.assertTrue(all(line.startswith("    ") or not line for line in block))

        for denied in (
            "validation_consumption: LOCKED_UNCONSUMED",
            "active_research: NONE",
            "market_authority: NONE",
            "probability_authority: NONE",
            "exposure_authority: NONE",
            "execution_authority: NONE",
            "agent_authority: NONE",
        ):
            self.assertIn(denied, authority)

    def test_required_wp2_reliability_evidence_remains_present(self) -> None:
        required = (
            "tests/research_operations/test_ro_wp2_service.py",
            "tests/research_operations/test_ro_wp2_catalogue.py",
            "tests/research_operations/test_ro_wp2_cli.py",
            "contracts/research_operations/RESEARCH_CLI_AND_APPEND_ONLY_SERVICE_CONTRACT_v0_1.md",
            "contracts/research_operations/ARTIFACT_CATALOGUE_AND_PATH_SAFETY_CONTRACT_v0_1.md",
        )
        for rel in required:
            self.assertTrue((ROOT / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
