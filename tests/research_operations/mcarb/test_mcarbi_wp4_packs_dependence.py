import unittest
from decimal import Decimal
from ovc.research_operations.mcarb.pack import PackDefinition, compile_pack, nested_ablation_field_sets
from ovc.research_operations.mcarb.dependence import pearson, rank_correlation, dependence_result
from ovc.research_operations.mcarb.controls import stratified_shuffle, matched_complexity_noise, preserve_stratum_multisets

class MCARBIWP4Test(unittest.TestCase):
    def r6(self):
        return PackDefinition(
            pack_id="R6",
            field_ids=("P.loc","AL-01","ET-X","VS-01"),
            field_domains=(("P.loc","PRICE"),("AL-01","AL"),("ET-X","ET"),("VS-01","VS")),
        )

    def test_compile_pack_never_includes_hidden_available_fields(self):
        out=compile_pack(self.r6(),{"P.loc":"x","AL-01":"1","ET-X":"UP","VS-01":"0.1","FUTURE":"forbidden"})
        self.assertEqual([x["field_id"] for x in out["fields"]],["P.loc","AL-01","ET-X","VS-01"])
        self.assertEqual(out["ignored_available_field_ids"],["FUTURE"])

    def test_r6_has_r4x_nested_ablation(self):
        ab=nested_ablation_field_sets(self.r6())
        self.assertEqual(ab["R4X"],("P.loc","AL-01","ET-X"))
        self.assertEqual(ab["VS"],("P.loc","AL-01","ET-X"))

    def test_dependence_methods_and_comparability(self):
        self.assertEqual(pearson([1,2,3],[2,4,6]),Decimal(1))
        self.assertEqual(rank_correlation([10,20,30],[7,8,9]),Decimal(1))
        blocked=dependence_result(result_id="D1",left_field_id="a",right_field_id="b",
            left=[1,2],right=[1,2],method="PEARSON",comparability_left="A",comparability_right="B")
        self.assertEqual(blocked["n_comparable"],0)
        self.assertIn("NOT_COMPARABLE",blocked["reason_codes"])
        with self.assertRaises(ValueError):
            dependence_result(result_id="D2",left_field_id="a",right_field_id="b",
                left=[1,2],right=[1,2],method="MUTUAL_INFORMATION",comparability_left="A",comparability_right="A")

    def test_shuffle_preserves_slot_side_missingness_strata(self):
        values=[1,2,3,4,5,6]
        strata=["A|BID|OK","A|BID|OK","B|BID|OK","B|BID|OK","A|ASK|MISSING","A|ASK|MISSING"]
        shuffled=stratified_shuffle(values,strata,seed_id="CTRL-1")
        self.assertTrue(preserve_stratum_multisets(values,shuffled,strata))
        self.assertEqual(shuffled,stratified_shuffle(values,strata,seed_id="CTRL-1"))

    def test_matched_noise_has_exact_dimension_and_is_deterministic(self):
        a=matched_complexity_noise(["x","y"],dimensions=4,seed_id="N1")
        b=matched_complexity_noise(["x","y"],dimensions=4,seed_id="N1")
        self.assertEqual(a,b)
        self.assertTrue(all(len(v)==4 for v in a.values()))

if __name__ == "__main__":
    unittest.main()
