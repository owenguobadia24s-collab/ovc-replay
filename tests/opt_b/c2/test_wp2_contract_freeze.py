from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / "contracts" / "opt_b" / "c2"
S = ROOT / "schemas" / "opt_b" / "c2"
R = ROOT / "registries" / "opt_b" / "c2"
G = ROOT / "docs" / "releases" / "opt-b-c2-v2" / "wp2" / "WP2_GATE_PACKET.json"
F = ROOT / "fixtures" / "opt_b" / "c2" / "wp2" / "C2_HANDOFF_FIXTURE_PACK.json"

class C2WP2ContractFreezeTests(unittest.TestCase):
    def test_gate_and_authority(self):
        gate = json.loads(G.read_text())
        self.assertEqual(gate["decision"], "PASS_C2_CONTRACT_SCHEMA_REGISTRY_AND_PARAMETER_FREEZE")
        self.assertEqual(gate["blocking_issues"], 0)
        self.assertEqual(gate["authority_delta"]["market_replay"], "DENIED_PENDING_C2_G2_AND_OPERATOR_APPROVAL")
        self.assertEqual(gate["authority_delta"]["selector"], "NONE")
        self.assertEqual(gate["authority_delta"]["validation_consumption"], "LOCKED_UNCONSUMED")

    def test_required_artifact_families_exist(self):
        self.assertGreaterEqual(len(list(C.glob("*.md"))), 8)
        self.assertEqual(len(list(S.glob("*.schema.json"))), 11)
        for name in ["C2_AXIS_REGISTRY_v0_1.yaml","C2_STATE_VALUE_REGISTRY_v0_1.yaml","C2_MEASUREMENT_REGISTRY_v0_1.yaml","C2_LEVEL_TYPE_REGISTRY_v0_1.yaml","C2_CONTAINER_TYPE_REGISTRY_v0_1.yaml","C2_RELATION_REGISTRY_v0_1.yaml","C2_SCOPE_REGISTRY_v0_1.yaml","C2_PARAMETER_PACK_v0_1.yaml","C2_REASON_CODE_AND_QA_REGISTRY_v0_1.yaml"]:
            self.assertTrue((R / name).is_file(), name)

    def test_no_hidden_winner_or_runtime_thresholds(self):
        state_schema = json.loads((S / "c2_parallel_state_v0_1.schema.json").read_text())
        self.assertIn("not", state_schema)
        params = (R / "C2_PARAMETER_PACK_v0_1.yaml").read_text()
        self.assertIn("runtime_editing: PROHIBITED", params)
        axes = (R / "C2_AXIS_REGISTRY_v0_1.yaml").read_text()
        self.assertIn("overall_state", axes)
        self.assertIn("winning_state", axes)

    def test_synthetic_valid_and_invalid_handoffs(self):
        pack = json.loads(F.read_text())
        self.assertTrue(pack["synthetic"])
        self.assertEqual(pack["market_authority"], "NONE")
        expected = {case["expected"] for case in pack["cases"]}
        self.assertIn("ACCEPT", expected)
        self.assertIn("REJECT", expected)
        self.assertIn("CENSORED", expected)

if __name__ == "__main__":
    unittest.main()
