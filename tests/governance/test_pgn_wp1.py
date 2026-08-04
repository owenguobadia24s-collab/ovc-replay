import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts/governance/programme_genesis/PGN_PORTFOLIO_ADOPTION_CONTROL_CONTRACT_v0_1.md"
SCHEMA = ROOT / "schemas/governance/programme_genesis/pgn_native_adoption_bundle_v0_1.schema.json"
REGISTRY = ROOT / "registries/governance/programme_genesis/PGN_CONTROL_PROFILE_REGISTRY_v0_1.json"
VALID_GROUP = ROOT / "fixtures/governance/programme_genesis/pgn_valid_review_group_v0_1.json"
INVALID_GROUP = ROOT / "fixtures/governance/programme_genesis/pgn_invalid_review_group_four_candidates_v0_1.json"
CHALLENGED_EDGE = ROOT / "fixtures/governance/programme_genesis/pgn_challenged_edge_downgraded_v0_1.json"
PREVIEW = ROOT / "fixtures/governance/programme_genesis/pgn_advisory_preview_invocation_v0_1.json"


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class NativeGenesisPortfolioWP1Tests(unittest.TestCase):
    def test_contract_preserves_all_operator_boundaries(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        for required in (
            "PGN-G2A",
            "one to three candidates",
            "48-hour challenge window",
            "immediately changes the effective classification to `ADAPTER_INFERRED`",
            "Bulk suppression is prohibited",
            "No POST, PUT, PATCH, DELETE",
            "non-binding advisory evidence only",
            "at least two distinct programme sources",
            "soft target of 60 seconds",
            "authority_effect=NONE",
        ):
            self.assertIn(required, text)

    def test_schema_freezes_maximum_three_and_fail_closed_challenge(self) -> None:
        schema = load(SCHEMA)
        defs = schema["$defs"]
        self.assertEqual(3, defs["review_group"]["properties"]["candidate_ids"]["maxItems"])
        then = defs["edge_challenge"]["allOf"][0]["then"]["properties"]
        self.assertEqual("ADAPTER_INFERRED", then["effective_source_kind"]["const"])
        self.assertEqual(False, then["satisfies_hard_prerequisite"]["const"])
        self.assertEqual(48, defs["edge_challenge"]["properties"]["challenge_window_hours"]["const"])
        self.assertEqual(60, defs["rebuild_evidence"]["properties"]["soft_target_seconds"]["const"])

    def test_review_fixtures_expose_valid_and_invalid_group_sizes(self) -> None:
        valid = load(VALID_GROUP)["review_group"]
        invalid = load(INVALID_GROUP)["review_group"]
        self.assertLessEqual(len(valid["candidate_ids"]), 3)
        self.assertEqual("NONE", valid["adoption_effect"])
        self.assertGreater(len(invalid["candidate_ids"]), 3)

    def test_challenged_edge_cannot_satisfy_hard_prerequisite(self) -> None:
        edge = load(CHALLENGED_EDGE)["edge_challenge"]
        self.assertTrue(edge["challenged"])
        self.assertEqual("ADAPTER_INFERRED", edge["effective_source_kind"])
        self.assertIn(edge["effective_hardness"], {"SOFT", "INFORMATIONAL"})
        self.assertFalse(edge["satisfies_hard_prerequisite"])
        self.assertEqual(48, edge["challenge_window_hours"])

    def test_preview_is_permanently_advisory_and_logged(self) -> None:
        preview = load(PREVIEW)["preview_invocation"]
        self.assertTrue(preview["disclaimer_acknowledged"])
        self.assertIn("non-binding advisory evidence only", preview["disclaimer"])
        self.assertEqual("NONE", preview["authority_effect"])
        self.assertFalse(preview["gate_satisfaction"])
        self.assertFalse(preview["operator_review_blocked"])

    def test_registry_freezes_corpus_performance_and_route_controls(self) -> None:
        registry = load(REGISTRY)
        self.assertEqual("FROZEN_CANDIDATE", registry["status"])
        self.assertEqual(3, registry["review_protocol"]["maximum_candidates_per_group"])
        self.assertEqual(2, registry["shadow_corpus"]["minimum_distinct_negative_programme_sources"])
        self.assertEqual(1, registry["shadow_corpus"]["minimum_adversarial_case_sets"])
        self.assertFalse(registry["shadow_corpus"]["implementation_team_may_be_sole_curator"])
        self.assertEqual(60, registry["read_model_performance"]["soft_target_seconds"])
        self.assertEqual(["GET"], registry["control_plane"]["allowed_methods"])
        self.assertEqual(["POST", "PUT", "PATCH", "DELETE"], registry["control_plane"]["prohibited_methods"])
        self.assertFalse(registry["census"]["candidate_construction_before_acknowledgement"])


if __name__ == "__main__":
    unittest.main()
