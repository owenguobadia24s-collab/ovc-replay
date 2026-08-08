import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
DISP = ROOT / "docs/releases/mcarb-v0-1/mcarbi-wp9/MCARBI_WP9_DECOMPOSED_SCIENTIFIC_DISPOSITION.json"
QA = ROOT / "docs/releases/mcarb-v0-1/mcarbi-wp9/MCARBI_WP9_QA_PACKET.json"
G8 = ROOT / "docs/releases/mcarb-v0-1/mcarbi-wp8/MCARBI_WP8_STAGE_A_EVIDENCE_SUMMARY.json"
EXT = ROOT / "docs/releases/mcarb-v0-1/mcarbi-wp8/MCARBI_WP8_EXTERNAL_ARTIFACT_RECEIPT.json"


class MCARBIWP9DispositionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(DISP.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.g8 = json.loads(G8.read_text())
        cls.ext = json.loads(EXT.read_text())
        cls.allowed = set(cls.d["allowed_vocabulary"])

    def test_exact_stage_a_candidate_surface_is_decomposed(self):
        self.assertEqual({x["id"] for x in self.d["candidate_dispositions"]["AL"]},
                         {"AL-01", "AL-05", "AL-07", "AL-08", "AL-09"})
        self.assertEqual({x["id"] for x in self.d["candidate_dispositions"]["VS"]},
                         {"VS-01", "VS-02", "VS-03"})
        self.assertEqual({x["id"] for x in self.d["candidate_dispositions"]["ET"]}, {
            "ET-DC@0.0005", "ET-DC@0.0010", "ET-DC@0.0020", "ET-DC@0.0040",
            "ET-X@0.0050", "ET-X@0.0100",
            "ET-VAR@0.0010", "ET-VAR@0.0020", "ET-VAR@0.0040", "ET-VAR@0.0080",
        })

    def test_every_scientific_disposition_uses_plan_vocabulary(self):
        values = [x["disposition"] for x in self.d["domain_dispositions"]]
        for domain in ("AL", "ET", "VS"):
            values.extend(x["disposition"] for x in self.d["candidate_dispositions"][domain])
        values.extend(x["disposition"] for x in self.d["pack_dispositions"])
        values.extend(x["disposition"] for x in self.d["cross_domain_interaction_dispositions"])
        values.append(self.d["module_disposition"]["disposition"])
        self.assertTrue(values)
        self.assertTrue(set(values) <= self.allowed)

    def test_all_admitted_packs_are_explicit(self):
        self.assertEqual({x["id"] for x in self.d["pack_dispositions"]},
                         {"R0", "R1", "R2", "R3", "R4", "R4X", "R5", "R6", "D-AL", "D-ET", "D-VS"})
        r0 = next(x for x in self.d["pack_dispositions"] if x["id"] == "R0")
        self.assertEqual(r0["disposition"], "NOT_EVALUABLE")
        for item in self.d["pack_dispositions"]:
            if item["id"] != "R0":
                self.assertEqual(item["disposition"], "UNRESOLVED")

    def test_cross_domain_claims_are_not_coerced_from_raw_vectors(self):
        expected = {
            "AL_GIVEN_VS_R4", "VS_GIVEN_AL_R4", "AL_GIVEN_ET_R4X", "ET_GIVEN_AL_R4X",
            "ET_GIVEN_VS_R5", "VS_GIVEN_ET_R5", "AL_ET_VS_INCREMENTAL_R6",
        }
        actual = {x["id"] for x in self.d["cross_domain_interaction_dispositions"]}
        self.assertEqual(actual, expected)
        self.assertEqual({x["disposition"] for x in self.d["cross_domain_interaction_dispositions"]}, {"NOT_EVALUABLE"})

    def test_terminal_null_is_not_forced_by_incomplete_stage_a_criteria(self):
        module = self.d["module_disposition"]
        self.assertEqual(module["disposition"], "UNRESOLVED")
        self.assertEqual(module["terminal_null_eligibility"], "NOT_ELIGIBLE_ON_STAGE_A_EVIDENCE")
        self.assertNotEqual(module["disposition"], "NO_ADDITIONAL_INFORMATION")
        not_evaluated = set(self.d["stage_a_claim_boundary"]["not_evaluated"])
        self.assertIn("long_run_chronological_stability", not_evaluated)
        self.assertIn("family_or_representation_quality", not_evaluated)
        self.assertIn("downstream_residual_reduction", not_evaluated)

    def test_no_temporal_or_method_claim_is_invented(self):
        dispositions = []
        dispositions.extend(x["disposition"] for x in self.d["domain_dispositions"])
        for domain in ("AL", "ET", "VS"):
            dispositions.extend(x["disposition"] for x in self.d["candidate_dispositions"][domain])
        dispositions.extend(x["disposition"] for x in self.d["pack_dispositions"])
        self.assertNotIn("UNSTABLE_ACROSS_TIME", dispositions)
        self.assertNotIn("METHOD_DEPENDENT", dispositions)
        self.assertIn("not tested", self.d["failure_attribution"]["temporal_stability"].lower())

    def test_evidence_hashes_and_run_identity_match_g8_court_record(self):
        self.assertEqual(self.d["source_run_id"], self.g8["run_id"])
        self.assertEqual(self.d["external_evidence"]["artifact_id"], self.ext["external_artifact"]["artifact_id"])
        self.assertEqual(self.d["external_evidence"]["artifact_archive_sha256"], self.ext["external_artifact"]["archive_sha256"])
        self.assertEqual(self.d["external_evidence"]["evidence_vector_sha256"], self.ext["derived_evidence_hashes"]["stage_a_evidence_vector_sha256"])
        self.assertEqual(self.d["external_evidence"]["record_logical_sha256"], self.ext["derived_evidence_hashes"]["stage_a_records_logical_sha256"])

    def test_dispositions_do_not_turn_exact_vector_separation_into_merit(self):
        packs = self.g8["pack_exact_vector_diagnostic"]
        self.assertEqual(packs["R1_AL"]["aux_separated_pairs"], packs["R1_AL"]["matched_noise_separated_pairs"])
        self.assertEqual(packs["R3_VS"]["aux_separated_pairs"], packs["R3_VS"]["matched_noise_separated_pairs"])
        self.assertLess(packs["R2_ET"]["aux_separated_pairs"], packs["R2_ET"]["matched_noise_separated_pairs"])
        self.assertIn("DIMENSIONALITY_ARTIFACT", self.d["failure_attribution"]["dimensionality"])

    def test_domain_and_module_recommendations_are_conservative(self):
        self.assertEqual({x["id"]: x["disposition"] for x in self.d["domain_dispositions"]},
                         {"AL": "UNRESOLVED", "ET": "UNRESOLVED", "VS": "UNRESOLVED"})
        self.assertEqual(self.d["module_disposition"]["disposition"], "UNRESOLVED")
        self.assertEqual(self.qa["recommended_cross_domain_disposition"], "NOT_EVALUABLE")
        self.assertEqual(self.qa["recommended_null_consequence"], "NO_ADDITIONAL_INFORMATION_NOT_YET_ELIGIBLE")

    def test_future_recommendation_grants_no_authority(self):
        future = self.d["future_stage_recommendation"]
        self.assertEqual(future["authority_effect"], "NONE")
        denied = set(future["does_not_authorize"])
        for item in (
            "new market run", "rerun of Stage A", "ACTIVE_DISCOVERY", "ACTIVE_DEVELOPMENT",
            "ACTIVE_VALIDATION", "new provider intake", "selector",
            "threshold/representation/family/candidate/semantic promotion", "canonical/R2 publication",
            "probability", "risk", "exposure", "trading/execution",
        ):
            self.assertIn(item, denied)

    def test_no_composite_score_or_hidden_global_rank(self):
        raw = DISP.read_text().lower()
        self.assertNotIn('"composite_score"', raw)
        self.assertNotIn('"global_score"', raw)
        self.assertNotIn('"winner"', raw)


if __name__ == "__main__":
    unittest.main()
