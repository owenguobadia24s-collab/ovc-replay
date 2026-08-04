import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/governance/build_pgn_wp2_census.py"
PCCR = ROOT / "registries/research_operations/planned_closure_continuity/PCCR_G0_PREPARATION_STATE_v0_1.json"
STATIC_CENSUS = ROOT / "registries/governance/programme_genesis/pgn_census/PGN_PORTFOLIO_CENSUS_v0_1.json"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_pgn_wp2_census", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class NativeGenesisPortfolioWP2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_builder()
        cls.census = cls.module.build_census(ROOT)
        cls.static = load_json(STATIC_CENSUS)

    def test_exact_legacy_adoption_population_is_seven(self) -> None:
        census = self.census
        self.assertEqual(7, census["adoption_target_count"])
        self.assertEqual(set(self.module.EXPECTED_TARGETS), {item["programme_id"] for item in census["adoption_targets"]})
        self.assertEqual([], census["blockers"])
        for dossier in census["adoption_targets"]:
            self.assertTrue((ROOT / dossier["source"]["path"]).is_file())
            self.assertEqual(64, len(dossier["source"]["sha256"]))
            self.assertFalse(dossier["candidate_constructed"])
            self.assertEqual("NONE", dossier["authority_effect"])
            self.assertEqual("PROPOSED_PENDING_PGN_G2A_AND_PGN_G3", dossier["classification_status"])

    def test_materialised_census_matches_deterministic_source_identity(self) -> None:
        self.assertEqual(self.census["census_sha256"], self.static["builder_census_sha256"])
        generated = {item["programme_id"]: item for item in self.census["adoption_targets"]}
        materialised = {item["programme_id"]: item for item in self.static["adoption_targets"]}
        self.assertEqual(set(generated), set(materialised))
        for programme_id in generated:
            self.assertEqual(generated[programme_id]["source"]["path"], materialised[programme_id]["source_path"])
            self.assertEqual(generated[programme_id]["source"]["sha256"], materialised[programme_id]["source_sha256"])
            self.assertEqual(generated[programme_id]["candidate_class_recommendation"], materialised[programme_id]["candidate_class_recommendation"])
            self.assertFalse(materialised[programme_id]["candidate_constructed"])
            self.assertEqual("NONE", materialised[programme_id]["authority_effect"])

    def test_review_groups_are_progressive_and_maximum_three(self) -> None:
        groups = self.census["proposed_review_groups"]
        static_groups = self.static["proposed_review_groups"]
        self.assertEqual([item["group_id"] for item in groups], [item["group_id"] for item in static_groups])
        flattened = []
        for group in static_groups:
            self.assertGreaterEqual(group["candidate_count"], 1)
            self.assertLessEqual(group["candidate_count"], 3)
            self.assertEqual(group["candidate_count"], len(group["candidate_ids"]))
            self.assertTrue(group["acknowledgement_required_before_next_group"])
            self.assertEqual("NONE", group["adoption_effect"])
            flattened.extend(group["candidate_ids"])
        self.assertEqual(set(self.module.EXPECTED_TARGETS), set(flattened))
        self.assertEqual(len(flattened), len(set(flattened)))

    def test_pccr_is_explicitly_non_admitted_and_excluded(self) -> None:
        self.assertTrue(PCCR.is_file())
        item = self.static["non_admitted_objects"][0]
        self.assertEqual("PCCR-G0-PREPARATION", item["object_id"])
        self.assertEqual("NOT_ADMITTED_PROPOSAL_PREPARATION", item["classification"])
        self.assertFalse(item["candidate_constructed"])
        self.assertNotIn(item["object_id"], {target["programme_id"] for target in self.static["adoption_targets"]})

    def test_existing_native_and_current_pgn_programmes_are_not_conversion_targets(self) -> None:
        targets = {item["programme_id"] for item in self.static["adoption_targets"]}
        self.assertNotIn("OVC-PG-v0.2", targets)
        self.assertNotIn("OVC-PG-NATIVE-PORTFOLIO-v0.2", targets)
        self.assertEqual("ALREADY_NATIVE_EXCLUDED_FROM_CONVERSION", self.static["existing_native_programmes"][0]["disposition"])
        self.assertEqual("CURRENT_RATIFIED_PROGRAMME_NOT_A_LEGACY_CONVERSION_TARGET", self.static["current_governance_programmes"][0]["disposition"])

    def test_census_has_no_candidate_or_adoption_authority(self) -> None:
        self.assertEqual("NONE", self.static["authority_effect"])
        self.assertEqual("DENIED_PENDING_PGN_G2A", self.static["candidate_construction_authority"])
        self.assertEqual("DENIED_PENDING_PGN_G3", self.static["native_adoption_authority"])
        self.assertEqual("DENIED_PENDING_PGN_G5", self.static["cross_programme_edge_authority"])
        self.assertEqual("OPERATOR_REVIEW_AND_ACKNOWLEDGE_OR_ADJUST_CENSUS_AT_PGN_G2A", self.static["next_action"])
        self.assertEqual([], self.static["blockers"])

    def test_census_is_deterministic_and_printable(self) -> None:
        again = self.module.build_census(ROOT)
        self.assertEqual(self.census, again)
        self.assertEqual(64, len(self.census["census_sha256"]))
        print("PGN_WP2_CENSUS=" + json.dumps(self.census, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
