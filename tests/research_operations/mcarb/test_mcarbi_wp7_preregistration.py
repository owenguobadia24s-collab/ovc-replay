import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
PREREG = ROOT / "docs/releases/mcarb-v0-1/mcarbi-wp7/MCARBI_WP7_STAGE_A_PREREGISTRATION.json"
PARAMS = ROOT / "registries/research/mcarb/MCARB_STAGE_A_PARAMETER_REGISTRY_v0_1.json"
ET_REG = ROOT / "registries/research/mcarb/MCARB_ET_METHOD_REGISTRY_v0_1.json"
VS_REG = ROOT / "registries/research/mcarb/MCARB_VS_VARIANT_REGISTRY_v0_1.json"
AL_REG = ROOT / "registries/research/mcarb/MCARB_AL_MEASUREMENT_REGISTRY_v0_1.json"
PACK_REG = ROOT / "registries/research/mcarb/MCARB_REPRESENTATION_PACK_REGISTRY_v0_1.json"

class MCARBIWP7PreregistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads(PREREG.read_text())
        cls.p = json.loads(PARAMS.read_text())

    def test_authority_firewall_and_g6_population(self):
        self.assertEqual(self.m["status"], "PROPOSED_FREEZE_PENDING_OPERATOR_ACK")
        self.assertEqual(self.m["authority_firewall"]["stage_a_execution"],
                         "DENIED_UNTIL_MCARBI_G_STAGE_A_AUTH_AUTHORIZE_STAGE_A")
        self.assertEqual(self.m["population"]["validation_2025"], "LOCKED_UNCONSUMED")
        self.assertEqual(self.m["authority_firewall"]["provider_intake"], "DENIED")
        self.assertEqual(self.m["authority_firewall"]["pr_371"], "PRESERVE_DO_NOT_MERGE")
        self.assertEqual(self.m["population"]["interval"], "[2023-11-01T00:00:00Z,2024-01-01T00:00:00Z)")
        self.assertEqual(self.m["population"]["paired_2h"], 449)
        self.assertEqual(self.m["population"]["paired_side_records"], 898)
        self.assertEqual(self.m["population"]["eligible_days"], 43)
        self.assertGreaterEqual(self.m["population"]["minimum_slot_days"], 15)

    def test_normalization_is_pre_evaluation_and_causal(self):
        r = self.m["normalization_reference"]
        self.assertEqual(r["interval"], "[2023-09-01T00:00:00Z,2023-11-01T00:00:00Z)")
        self.assertEqual(r["evaluation_or_future_value_in_reference"], "BLOCK")
        self.assertEqual(r["partition"], ["side", "2H_A_L_slot"])
        self.assertEqual(r["minimum_n"], 15)

    def test_candidate_set_is_exact_g1_g6_core(self):
        et = {e["candidate_id"] for e in json.loads(ET_REG.read_text())["entries"]}
        vs = {e["candidate_id"] for e in json.loads(VS_REG.read_text())["entries"]}
        al = {e["candidate_id"] for e in json.loads(AL_REG.read_text())["entries"]}
        self.assertEqual(set(self.m["parameters"]) & et, {"ET-DC","ET-X","ET-VAR"})
        self.assertEqual(set(self.m["parameters"]) & vs, {"VS-01","VS-02","VS-03"})
        self.assertEqual(set(self.m["parameters"]) & al, {"AL-01","AL-05","AL-07","AL-08","AL-09"})
        self.assertNotIn("AL-10", self.m["parameters"])
        self.assertNotIn("AL-11", self.m["parameters"])

    def test_no_hidden_threshold_or_variant(self):
        self.assertEqual(self.p["ET-DC"]["thresholds"], ["0.0005","0.0010","0.0020","0.0040"])
        self.assertEqual(self.p["ET-X"]["steps"], ["0.0050","0.0100"])
        self.assertEqual(self.p["ET-VAR"]["targets"], ["0.0010","0.0020","0.0040","0.0080"])
        self.assertEqual(self.p["undeclared_parameter_policy"], "BLOCK")
        self.assertEqual(self.m["dependence"]["mutual_information"], "OMITTED_NOT_PREREGISTERED")

    def test_pack_matrix_matches_registry_and_has_no_implicit_fields(self):
        registered = {e["pack_id"] for e in json.loads(PACK_REG.read_text())["entries"]}
        self.assertEqual(set(self.m["packs"]), registered)
        self.assertFalse(self.m["pack_rule"]["implicit_catalogue_inclusion"])
        self.assertEqual(self.m["pack_rule"]["missingness"], "ABSTAIN_REQUIRED_FIELD_MISSING")
        self.assertEqual(self.m["packs"]["R4X"], ["PRICE","AL","ET"])
        self.assertEqual(self.m["packs"]["R6"], ["PRICE","AL","ET","VS"])
        self.assertEqual(self.m["dependence"]["nested"]["R6"], ["R1","R2","R3","R4","R4X","R5","R0"])

    def test_no_outcome_selection_sampling_or_imputation(self):
        self.assertFalse(self.m["dependence"]["outcome_selection"])
        self.assertEqual(self.m["capacity"]["sampling"], "PROHIBITED")
        self.assertEqual(self.m["comparability"]["imputation"], "PROHIBITED")
        self.assertEqual(self.m["stop_rules"]["validation_access"], "BLOCK_QUARANTINE")

if __name__ == "__main__":
    unittest.main()
