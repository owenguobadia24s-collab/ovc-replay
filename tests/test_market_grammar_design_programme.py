import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs" / "releases" / "c2e-c2g-c2p-market-grammar-v0-1" / "mg-d0"


def load(name: str):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


class MarketGrammarDesignProgrammeTests(unittest.TestCase):
    def test_shadow_evidence_lock_is_inactive_and_exact(self) -> None:
        lock = load("MG_D0_VERIFIED_SHADOW_EVIDENCE_LOCK.json")
        self.assertEqual("PASS", lock["status"])
        replay = lock["revised_c2_replay"]
        self.assertEqual(
            "126a703b89bfef8fc60a4beb1248b20b424621334c8fff254c122555e44663f8",
            replay["binding_sha256"],
        )
        self.assertEqual(
            "3f1089e3a4eefe94147c8c2f912e77899e4ed21fe8b3b8b85993e47bf7151ee7",
            replay["logical_population_sha256"],
        )
        self.assertEqual(
            replay["counts"]["requested"],
            replay["counts"]["computable"]
            + replay["counts"]["censored"]
            + replay["counts"]["not_evaluable"],
        )
        self.assertEqual("UNCHANGED_READ_ONLY", lock["integrated_shadow_closeout"]["active_c2"])
        self.assertIn("NO_MARKET_OR_ACTIVATION_AUTHORITY", lock["authority_effect"])

    def test_c2e_supersession_is_narrow_and_preserves_activation_denial(self) -> None:
        record = load("MG_D0_OPERATOR_SCOPE_AND_C2E_SUPERSESSION.json")
        self.assertEqual(
            "C2E-G1.OPERATOR.BLOCK.20260803T194600+0100",
            record["supersedes_decision_id"],
        )
        self.assertIn("C2E_ACTIVATION", record["preserved_denials"])
        self.assertIn("C2E_AUTHORITATIVE_CONSUMPTION", record["preserved_denials"])
        self.assertEqual("LIMITED_IMMUTABLE_SUPERSESSION", record["authority_effect"])

    def test_design_freeze_is_blocked_at_governing_pgn_boundary(self) -> None:
        packet = load("MG_D8_DESIGN_FREEZE_PACKET.json")
        self.assertEqual("PASS_VERIFIED_SHADOW_EVIDENCE", packet["precondition"])
        self.assertEqual("BLOCK", packet["qa_recommendation"])
        self.assertEqual("BLOCKED", packet["status"])
        self.assertEqual(
            "PGN_PORTFOLIO_CENSUS_OR_ADMISSION_SCOPE_CHANGE",
            packet["reserved_authority_delta"],
        )
        self.assertEqual("FAIL_3_OF_347", packet["repository_tests"]["result"])

    def test_implementation_registry_prohibits_reverse_and_outcome_dependencies(self) -> None:
        path = (
            ROOT
            / "registries"
            / "opt_b"
            / "market_grammar"
            / "OVC_MARKET_GRAMMAR_IMPLEMENTATION_REGISTRY_v0_1.jsonc"
        )
        registry = json.loads(path.read_text(encoding="utf-8"))
        prohibited = set(registry["forbidden_dependencies"])
        self.assertIn("C2E_READS_C2G", prohibited)
        self.assertIn("C2G_REWRITES_C2_OR_C2E", prohibited)
        self.assertIn("OUTCOME_INPUT_TO_C2E_C2G_C2P_CONSTRUCTION", prohibited)

    def test_programme_state_blocks_all_implementation_packets(self) -> None:
        path = (
            ROOT
            / "registries"
            / "opt_b"
            / "market_grammar"
            / "OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc"
        )
        state = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual("BLOCKED", state["status"])
        self.assertIsNone(state["next_packet"])
        packets = {item["packet_id"]: item for item in state["packets"]}
        self.assertEqual("BLOCKED", packets["MG-D0-D8"]["status"])
        for i in range(11):
            self.assertEqual("PLANNED", packets[f"MG-WP{i}"]["status"])
        self.assertEqual("OPERATOR_REQUIRED", packets["MG-WP10"]["authority_required"])


if __name__ == "__main__":
    unittest.main()
