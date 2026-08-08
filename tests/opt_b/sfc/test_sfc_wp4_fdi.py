import copy
import unittest

from ovc.opt_b.sfc.fdi import FamilyMethodSpec, assignment, build_catalog, catalog_id, deterministic_star_assign, family_id


class SFCWP4FDITests(unittest.TestCase):
    def setUp(self):
        self.method=FamilyMethodSpec("MEDOID_STAR_CONFORMANCE","0.1","CFG.SYN","PACK","SPEC",minimum_support=2)
        self.kw={"population_id":"POP","representation_pack_id":"PACK","comparison_spec_id":"SPEC","method":self.method,"evaluation_cutoff":"2026-06-01T00:00:00Z"}
        self.dist=[
            {"status":"EVALUATED","value":"0.1","left_representation_id":"A","right_representation_id":"B"},
            {"status":"EVALUATED","value":"0.2","left_representation_id":"A","right_representation_id":"C"},
            {"status":"EVALUATED","value":"0.8","left_representation_id":"B","right_representation_id":"C"},
        ]

    def test_f16_family_result_is_order_invariant(self):
        first=deterministic_star_assign(self.dist,occurrence_ids=["A","B","C"],threshold="0.25",**self.kw)
        second=deterministic_star_assign(list(reversed(self.dist)),occurrence_ids=["C","B","A"],threshold="0.25",**self.kw)
        self.assertEqual(first["logical_hash"],second["logical_hash"])
        self.assertEqual(first["family_catalog_id"],second["family_catalog_id"])

    def test_f17_exact_tie_is_explicit_ambiguous(self):
        cid=catalog_id(population_id="POP",representation_pack_id="PACK",comparison_spec_id="SPEC",method=self.method)
        f1=family_id(population_id="POP",representation_pack_id="PACK",comparison_spec_id="SPEC",method=self.method,member_ids=["A","B"])
        f2=family_id(population_id="POP",representation_pack_id="PACK",comparison_spec_id="SPEC",method=self.method,member_ids=["A","C"])
        row=assignment("A",cid,"AMBIGUOUS",[f2,f1],reason_codes=["EXACT_TIE"])
        self.assertEqual(row["status"],"AMBIGUOUS")
        self.assertEqual(row["family_ids"],[f1,f2])

    def test_f18_residual_noise_singleton_are_preserved(self):
        cid=catalog_id(population_id="POP",representation_pack_id="PACK",comparison_spec_id="SPEC",method=self.method)
        rows=[assignment("A",cid,"RESIDUAL"),assignment("B",cid,"NOISE"),assignment("C",cid,"SINGLETON")]
        cat=build_catalog(population_id="POP",representation_pack_id="PACK",comparison_spec_id="SPEC",method=self.method,family_members={},assignments=rows,eligible_ids=["A","B","C"],evaluation_cutoff="T")
        self.assertEqual(cat["residual_ids"],["A","B","C"])
        self.assertEqual(cat["noise_ids"],["B"])
        self.assertEqual(cat["singleton_ids"],["C"])

    def test_f19_zero_family_catalog_is_lawful(self):
        cid=catalog_id(population_id="POP",representation_pack_id="PACK",comparison_spec_id="SPEC",method=self.method)
        rows=[assignment("A",cid,"SINGLETON")]
        cat=build_catalog(population_id="POP",representation_pack_id="PACK",comparison_spec_id="SPEC",method=self.method,family_members={},assignments=rows,eligible_ids=["A"],evaluation_cutoff="T")
        self.assertEqual(cat["families"],[])
        self.assertEqual(cat["evidence_status"],"NO_STABLE_FAMILY")

    def test_f20_full_residual_catalog_has_exact_null_family_evidence(self):
        cid=catalog_id(population_id="POP",representation_pack_id="PACK",comparison_spec_id="SPEC",method=self.method)
        rows=[assignment(x,cid,"RESIDUAL") for x in ["A","B","C"]]
        cat=build_catalog(population_id="POP",representation_pack_id="PACK",comparison_spec_id="SPEC",method=self.method,family_members={},assignments=rows,eligible_ids=["A","B","C"],evaluation_cutoff="T")
        self.assertEqual(cat["denominator_assigned"],0)
        self.assertEqual(cat["denominator_residual_noise"],3)
        self.assertEqual(cat["evidence_status"],"NO_STABLE_FAMILY")

    def test_catalog_and_family_ids_are_catalog_scoped_not_reused_by_label(self):
        m2=FamilyMethodSpec("MEDOID_STAR_CONFORMANCE","0.1","CFG.OTHER","PACK","SPEC")
        self.assertNotEqual(catalog_id(population_id="POP",representation_pack_id="PACK",comparison_spec_id="SPEC",method=self.method),catalog_id(population_id="POP",representation_pack_id="PACK",comparison_spec_id="SPEC",method=m2))


if __name__ == "__main__": unittest.main()
