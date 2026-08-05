import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKET = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp10/CEAR_G10_OPERATOR_DECISION_PACKET.json"
QA = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp10/CEAR_G10_GATE_READY_QA_PACKET.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_CEAR_G10_GATE_READY_STATE_v0_3.jsonc"


def load(path):
    return json.loads(path.read_text())


class CEARG10GateReadyTests(unittest.TestCase):
    def test_gate_ready_operator_required_and_wp11_locked(self):
        packet, state = load(PACKET), load(STATE)
        self.assertEqual(packet["gate_status"], "GATE_READY")
        self.assertTrue(state["operator_decision_required"])
        self.assertEqual(state["wp11_status"], "LOCKED_PENDING_CEAR_G10_OPERATOR_DECISION")
        self.assertEqual(state["main_merge_status"], "PROHIBITED_PENDING_OPERATOR_DECISION")

    def test_exact_external_binding_and_population(self):
        packet = load(PACKET)
        evidence = packet["external_evidence"]
        self.assertEqual(evidence["google_drive_file_id"], "1xffbDKFIGEK8MLNH-eh3UdhBueASHTU4")
        self.assertEqual(evidence["size_bytes"], 214135)
        self.assertEqual(evidence["raw_sha256"], "6228282d2fc19542877e12add9d922040eac49ed345488e2dd33cedcf3cb4944")
        self.assertEqual(evidence["internal_content_sha256"], "4a21f3db44f8a6587ff863bb24fc6fe213f73ea9cf47d9d6cd69ba2e82b16fc2")
        self.assertEqual(evidence["population"]["requested"], 33320)
        self.assertEqual(evidence["reproducibility"], {"determinism": "PASS", "restart": "PASS", "two_clean_runs": "PASS"})

    def test_all_14_candidate_slots_are_explicit_and_research_only(self):
        packet = load(PACKET)
        candidates = packet["candidate_dispositions"]
        self.assertEqual(len(candidates), 14)
        self.assertEqual(len({x["functional_candidate_id"] for x in candidates}), 14)
        self.assertEqual(len({x["rule_candidate_id"] for x in candidates}), 14)
        for candidate in candidates:
            self.assertEqual(candidate["recommended_functional_decision"], "PASS")
            self.assertEqual(candidate["recommended_rule_decision"], "PASS")
            self.assertEqual(candidate["clock_2h_matches"], 0)

    def test_legacy_defers_are_independent_and_qa_has_no_blocker(self):
        packet, qa = load(PACKET), load(QA)
        self.assertEqual([x["recommended_decision"] for x in packet["legacy_mapping_dispositions"]], ["DEFER", "DEFER"])
        self.assertEqual(packet["recommended_decision"]["overall"], "PASS")
        self.assertEqual(qa["blocking_warnings"], [])

    def test_reserved_authority_remains_denied(self):
        packet, state = load(PACKET), load(STATE)
        denied = set(packet["explicitly_not_authorised"])
        self.assertIn("SELECTOR_ACTIVATION_OR_REPLACEMENT", denied)
        self.assertIn("CANONICAL_OR_R2_PUBLICATION", denied)
        self.assertIn("AGENT_WRITE_AUTHORITY", denied)
        self.assertEqual(state["authority"]["discovery_method"], "CANDIDATE_NOT_ADMITTED")
        self.assertEqual(state["authority"]["research_consumer_permission"], "NONE")


if __name__ == "__main__":
    unittest.main()
