import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs" / "releases" / "c2e-c2g-c2p-market-grammar-v0-1" / "mg-d0"
PGN_BASE = ROOT / "docs" / "releases" / "programme-genesis-native-portfolio-v0-2"


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
        self.assertEqual(
            "UNCHANGED_READ_ONLY",
            lock["integrated_shadow_closeout"]["active_c2"],
        )
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

    def test_historical_pgn_block_is_preserved_not_rewritten(self) -> None:
        blocked = load("MG_D8_BLOCKED_QA_PACKET.json")
        freeze = load("MG_D8_DESIGN_FREEZE_PACKET.json")
        self.assertEqual("BLOCKED", blocked["status"])
        self.assertEqual("BLOCK", blocked["qa_recommendation"])
        self.assertEqual("FAIL_3_OF_352", freeze["repository_tests"]["result"])
        self.assertEqual(
            "PGN_PORTFOLIO_CENSUS_OR_ADMISSION_SCOPE_CHANGE",
            freeze["reserved_authority_delta"],
        )

    def test_post_snapshot_admission_resolves_only_mg_g0_block(self) -> None:
        resolution = load("MG_G0_POST_SNAPSHOT_ADMISSION_RESOLUTION.json")
        self.assertEqual("RESOLVED_FOR_MG_G0_RERUN", resolution["status"])
        self.assertEqual(
            "PASS_OPERATOR_ADMISSION_MATERIALISED_AND_RECEIPTED",
            resolution["resolution"],
        )
        self.assertEqual(108, resolution["snapshot_preservation"]["object_count"])
        self.assertEqual(72, resolution["snapshot_preservation"]["exclusion_count"])
        self.assertEqual(16, resolution["snapshot_preservation"]["candidate_count"])
        self.assertEqual("NONE", resolution["snapshot_preservation"]["mutation"])
        self.assertEqual(335, resolution["historical_block"]["blocked_pr"])
        self.assertEqual(
            "INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT_IMPLEMENTATION_ONLY",
            resolution["admission"]["authority"],
        )
        receipt = json.loads(
            (
                PGN_BASE
                / "post-snapshot-admissions"
                / "MG_POST_SNAPSHOT_ADMISSION_POST_MERGE_RECEIPT.json"
            ).read_text(encoding="utf-8")
        )
        self.assertTrue(receipt["effective"])
        self.assertEqual("NONE", receipt["reserved_authority"])

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

    def test_mg_g0_is_completed_and_receipt_binds_exact_merge(self) -> None:
        decision = load("MG_G0_DELEGATED_DECISION.json")
        assurance = load("MG_G0_PREDECISION_ASSURANCE_RECEIPT.json")
        receipt = load("MG_G0_POST_MERGE_RECEIPT.json")
        qa = load("MG_G0_QA_PACKET.json")
        self.assertEqual("PASS", decision["decision"])
        self.assertTrue(decision["delegated_authority"])
        self.assertFalse(decision["operator_required"])
        self.assertEqual("PASS", assurance["result"])
        self.assertEqual("COMPLETED", receipt["status"])
        self.assertTrue(receipt["effective"])
        self.assertEqual(341, receipt["pull_request"])
        self.assertEqual(
            "5eb4a21125e41c3d7ce2fe416d571aa9aa3f95f3",
            receipt["final_head"],
        )
        self.assertEqual(
            "114558efdf38f56499f6276da917190c3cb729ea",
            receipt["merge_commit"],
        )
        self.assertEqual("NONE", receipt["reserved_authority"])
        self.assertEqual("PASS_COMPLETED", qa["status"])
        self.assertEqual("PASS_COMPLETED", qa["qa_recommendation"])
        self.assertEqual([], qa["blockers"])

    def test_programme_state_routes_to_ready_mg_wp0(self) -> None:
        path = (
            ROOT
            / "registries"
            / "opt_b"
            / "market_grammar"
            / "OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc"
        )
        state = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual("READY", state["status"])
        self.assertEqual("SATISFIED_DELEGATED_DECISION", state["authority_required"])
        self.assertEqual("MG-WP0", state["next_packet"])
        self.assertEqual([], state["blockers"])
        self.assertEqual(
            "114558efdf38f56499f6276da917190c3cb729ea",
            state["merge_commit"],
        )
        packets = {item["packet_id"]: item for item in state["packets"]}
        self.assertEqual("COMPLETED", packets["MG-D0-D8"]["status"])
        self.assertEqual("READY", packets["MG-WP0"]["status"])
        for i in range(1, 11):
            self.assertEqual("PLANNED", packets[f"MG-WP{i}"]["status"])
        self.assertEqual("OPERATOR_REQUIRED", packets["MG-WP10"]["authority_required"])


if __name__ == "__main__":
    unittest.main()
