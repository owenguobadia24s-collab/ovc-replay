import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-d0"
PGN_BASE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2"
STATE = ROOT / "registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc"


def load(name: str):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


class MarketGrammarDesignProgrammeTests(unittest.TestCase):
    def test_shadow_evidence_lock_is_inactive_and_exact(self) -> None:
        lock = load("MG_D0_VERIFIED_SHADOW_EVIDENCE_LOCK.json")
        replay = lock["revised_c2_replay"]
        self.assertEqual("PASS", lock["status"])
        self.assertEqual("126a703b89bfef8fc60a4beb1248b20b424621334c8fff254c122555e44663f8", replay["binding_sha256"])
        self.assertEqual("3f1089e3a4eefe94147c8c2f912e77899e4ed21fe8b3b8b85993e47bf7151ee7", replay["logical_population_sha256"])
        self.assertEqual(replay["counts"]["requested"], replay["counts"]["computable"] + replay["counts"]["censored"] + replay["counts"]["not_evaluable"])
        self.assertEqual("UNCHANGED_READ_ONLY", lock["integrated_shadow_closeout"]["active_c2"])

    def test_c2e_supersession_preserves_activation_denial(self) -> None:
        record = load("MG_D0_OPERATOR_SCOPE_AND_C2E_SUPERSESSION.json")
        self.assertEqual("LIMITED_IMMUTABLE_SUPERSESSION", record["authority_effect"])
        self.assertIn("C2E_ACTIVATION", record["preserved_denials"])
        self.assertIn("C2E_AUTHORITATIVE_CONSUMPTION", record["preserved_denials"])

    def test_historical_pgn_block_is_preserved(self) -> None:
        blocked = load("MG_D8_BLOCKED_QA_PACKET.json")
        freeze = load("MG_D8_DESIGN_FREEZE_PACKET.json")
        self.assertEqual("BLOCKED", blocked["status"])
        self.assertEqual("BLOCK", blocked["qa_recommendation"])
        self.assertEqual("FAIL_3_OF_352", freeze["repository_tests"]["result"])

    def test_post_snapshot_admission_is_effective_and_non_reserved(self) -> None:
        resolution = load("MG_G0_POST_SNAPSHOT_ADMISSION_RESOLUTION.json")
        self.assertEqual("RESOLVED_FOR_MG_G0_RERUN", resolution["status"])
        self.assertEqual(108, resolution["snapshot_preservation"]["object_count"])
        self.assertEqual(72, resolution["snapshot_preservation"]["exclusion_count"])
        self.assertEqual(16, resolution["snapshot_preservation"]["candidate_count"])
        receipt = json.loads((PGN_BASE / "post-snapshot-admissions/MG_POST_SNAPSHOT_ADMISSION_POST_MERGE_RECEIPT.json").read_text(encoding="utf-8"))
        self.assertTrue(receipt["effective"])
        self.assertEqual("NONE", receipt["reserved_authority"])

    def test_implementation_registry_forbids_reverse_and_outcome_dependencies(self) -> None:
        path = ROOT / "registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_IMPLEMENTATION_REGISTRY_v0_1.jsonc"
        registry = json.loads(path.read_text(encoding="utf-8"))
        prohibited = set(registry["forbidden_dependencies"])
        self.assertIn("C2E_READS_C2G", prohibited)
        self.assertIn("C2G_REWRITES_C2_OR_C2E", prohibited)
        self.assertIn("OUTCOME_INPUT_TO_C2E_C2G_C2P_CONSTRUCTION", prohibited)

    def test_mg_g0_is_completed(self) -> None:
        decision = load("MG_G0_DELEGATED_DECISION.json")
        receipt = load("MG_G0_POST_MERGE_RECEIPT.json")
        qa = load("MG_G0_QA_PACKET.json")
        self.assertEqual("PASS", decision["decision"])
        self.assertTrue(decision["delegated_authority"])
        self.assertEqual("COMPLETED", receipt["status"])
        self.assertEqual("114558efdf38f56499f6276da917190c3cb729ea", receipt["merge_commit"])
        self.assertEqual("PASS_COMPLETED", qa["status"])

    def test_programme_state_routes_from_completed_wp0_to_ready_wp1(self) -> None:
        state = json.loads(STATE.read_text(encoding="utf-8"))
        self.assertEqual("READY", state["status"])
        self.assertEqual("MG-WP1", state["next_packet"])
        self.assertEqual([], state["blockers"])
        packets = {item["packet_id"]: item for item in state["packets"]}
        self.assertEqual("COMPLETED", packets["MG-D0-D8"]["status"])
        self.assertEqual("COMPLETED", packets["MG-WP0"]["status"])
        self.assertEqual("READY", packets["MG-WP1"]["status"])
        for index in range(2, 11):
            self.assertEqual("PLANNED", packets[f"MG-WP{index}"]["status"])
        self.assertEqual("OPERATOR_REQUIRED", packets["MG-WP10"]["authority_required"])


if __name__ == "__main__":
    unittest.main()
