import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

class MCARBIWP2ContractsTest(unittest.TestCase):
    def load(self, relative):
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def test_pack_registry_is_explicit_and_has_r4x(self):
        doc = self.load("registries/research/mcarb/MCARB_REPRESENTATION_PACK_REGISTRY_v0_1.json")
        ids = {entry["pack_id"] for entry in doc["entries"]}
        self.assertEqual(ids, {"R0","R1","R2","R3","R4","R4X","R5","R6","D-AL","D-ET","D-VS"})
        self.assertFalse(doc["implicit_catalogue_inclusion"])
        r6 = next(x for x in doc["entries"] if x["pack_id"] == "R6")
        self.assertIn("R4X", r6["nested_ablation_requires"])

    def test_candidate_domain_counts_match_g1(self):
        al = self.load("registries/research/mcarb/MCARB_AL_MEASUREMENT_REGISTRY_v0_1.json")
        et = self.load("registries/research/mcarb/MCARB_ET_METHOD_REGISTRY_v0_1.json")
        vs = self.load("registries/research/mcarb/MCARB_VS_VARIANT_REGISTRY_v0_1.json")
        self.assertEqual((len(al["entries"]), len(et["entries"]), len(vs["entries"])), (20,6,18))
        self.assertEqual(al["source_outcome"], "AL_SOURCE_PARTIAL")
        self.assertEqual(next(x for x in al["entries"] if x["candidate_id"]=="AL-10")["status"], "BLOCKED")

    def test_reason_and_missingness_contract(self):
        doc = self.load("registries/research/mcarb/MCARB_REASON_MISSINGNESS_REGISTRY_v0_1.json")
        for required in ("TICK_SOURCE_UNPROVEN","PROXY_UNVALIDATED","VALIDATION_ACCESS_DENIED","AUTHORITY_RESERVED"):
            self.assertIn(required, doc["reason_codes"])
        self.assertIn("RETROSPECTIVE_ONLY", doc["missingness_states"])

    def test_schemas_have_no_extra_properties_and_explicit_authority(self):
        for name in ("auxiliary_measurement_v0_1.json","auxiliary_variant_spec_v0_1.json","auxiliary_representation_pack_v0_1.json","auxiliary_dependence_result_v0_1.json","auxiliary_proxy_quality_result_v0_1.json"):
            doc = self.load("schemas/research/mcarb/" + name)
            self.assertFalse(doc["additionalProperties"])
            self.assertIn("authority", doc["required"])

    def test_normalization_registry_has_no_future_refit(self):
        doc = self.load("registries/research/mcarb/MCARB_NORMALIZATION_REGISTRY_v0_1.json")
        self.assertIn("CENTERED_FUTURE_WINDOW", doc["prohibited"])
        self.assertIn("RUN_WIDE_REFIT_ON_EVALUATION_PERIOD", doc["prohibited"])

if __name__ == "__main__":
    unittest.main()
