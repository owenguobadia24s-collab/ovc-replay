import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
G6 = ROOT / "docs/releases/occurrence-context-v0-1/oc-g6"
STATE = ROOT / "registries/implementation/occurrence_context/OVC_OC_IMPLEMENTATION_STATE_v0_8.json"
POINTER = ROOT / "registries/implementation/occurrence_context/CURRENT_IMPLEMENTATION_STATE_POINTER.json"

PROTECTED = {
    "src/ovc/opt_b/c2/state.py": "a706af2d27e50865f3148ef2254ebd5f5f662e90",
    "registries/opt_b/c2/C2_SCOPE_REGISTRY_v0_1.yaml": "6b7dcb87db35cc6d9278dea0d20d6d7f5c7fbfb5",
    "src/ovc/opt_b/c2e_v2/models.py": "80e05c0ba818e7223029823e20c77fabf39e8bbf",
    "contracts/opt_b/c2e/v0_2/C2E_STREAM_CONTRACT_v0_2.md": "2fc7cee1e6fcc8ea681f99ac6ca1079f936c80b6",
}


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class OCG6ConformancePacketTests(unittest.TestCase):
    def test_terminal_state_stops_at_operator_gate(self):
        state = json.loads(STATE.read_text())
        pointer = json.loads(POINTER.read_text())
        self.assertEqual(state["status"], "GATE_READY")
        self.assertEqual(state["current_gate"], "OC-G6")
        self.assertTrue(state["operator_decision_required"])
        self.assertIsNone(state["operator_decision"])
        self.assertEqual(pointer["next_action"], "AWAIT_EXPLICIT_OPERATOR_OC_G6_DECISION")

    def test_terminal_qa_has_all_required_design_checks_and_fixtures(self):
        qa = json.loads((G6 / "OC_G6_TERMINAL_QA_PACKET.json").read_text())
        self.assertEqual(qa["recommended_decision"], "PASS")
        self.assertEqual(qa["unresolved_blockers"], [])
        self.assertEqual(set(qa["design_qa"]), {f"OC-QA-{i:02d}" for i in range(1, 17)})
        self.assertEqual(set(qa["adversarial_fixtures"]), {f"OC-F{i:02d}" for i in range(1, 17)})
        self.assertTrue(all(value.startswith("PASS") for value in qa["design_qa"].values()))
        self.assertTrue(all(value == "PASS" for value in qa["adversarial_fixtures"].values()))

    def test_protected_upstream_blobs_are_exactly_unchanged(self):
        qa = json.loads((G6 / "OC_G6_TERMINAL_QA_PACKET.json").read_text())
        self.assertEqual(qa["protected_upstream_hashes"], PROTECTED)
        for relative, expected in PROTECTED.items():
            self.assertEqual(git_blob_sha(ROOT / relative), expected, relative)

    def test_changed_inventory_contains_no_c2p_or_validation_payload_work(self):
        inventory = json.loads((G6 / "OC_G6_CHANGED_FILE_INVENTORY.json").read_text())
        self.assertEqual(inventory["protected_upstream_files_changed"], [])
        self.assertEqual(inventory["c2p_files_changed"], [])
        self.assertEqual(inventory["validation_payload_files_changed"], [])
        self.assertFalse(inventory["raw_market_streams_committed"])
        self.assertFalse(inventory["external_large_artifacts_committed"])

    def test_reserved_authority_remains_denied(self):
        qa = json.loads((G6 / "OC_G6_TERMINAL_QA_PACKET.json").read_text())
        auth = qa["authority_checks"]
        self.assertEqual(auth["validation"], "LOCKED_UNCONSUMED")
        self.assertEqual(auth["new_instrument_market_side_clock_lattice"], "DENIED")
        self.assertEqual(auth["mcarb_scientific_activation"], "DENIED")
        self.assertEqual(auth["c2p"], "NOT_STARTED_NOT_AUTHORIZED")
        self.assertEqual(auth["probability_risk_exposure_execution_agent_write"], "NONE")


if __name__ == "__main__":
    unittest.main()
