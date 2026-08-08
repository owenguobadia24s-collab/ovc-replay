import copy
import unittest

from ovc.opt_b.sfc.comparison import (
    BASE_DIMENSIONS,
    ComparabilityDomain,
    ComparisonSpec,
    SFCComparisonError,
    build_surface,
    compare,
    decide_comparability,
    equivalent,
    pair_id,
    semantic_cache_key,
)


def rep(name, x, y):
    return {"representation_id": name, "representation_pack_id":"PACK","scale_id":"2H","structural_normalized":{"X":str(x),"Y":str(y)},"logical_hash":name+"HASH"}


def meta():
    return {"instrument_id":"GBPUSD","side":"BID","units":"DIMENSIONLESS","clock_scale":"2H","representation_schema":"PACK","source_quality":"SYNTHETIC_VALID","normalization_transport":"FROZEN","context_binding":"STRATIFICATION_ONLY","chronology_basis":"AS_OF_FVT","missingness_policy":"EXPLICIT_MASK"}


class SFCWP3ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.domain = ComparabilityDomain("DOMAIN")
        self.spec = ComparisonSpec("SPEC","DISTANCE","EUCLIDEAN",("X","Y"))
        self.left = rep("REP.A",0,0)
        self.right = rep("REP.B",3,4)

    def test_f09_each_base_dimension_rejects_before_pair_id(self):
        for dimension in BASE_DIMENSIONS:
            left, right = meta(), meta()
            right[dimension] = right[dimension] + ".DIFF"
            decision = decide_comparability(left,right,self.domain,evaluation_cutoff="2026-06-01T00:00:00Z")
            self.assertEqual(decision["status"],"NOT_COMPARABLE", dimension)
            with self.assertRaises(SFCComparisonError):
                pair_id("A","B",decision=decision,spec=self.spec)
            result = compare(self.left,self.right,left_meta=left,right_meta=right,domain=self.domain,spec=self.spec,evaluation_cutoff="2026-06-01T00:00:00Z")
            self.assertIsNone(result["pair_id"])
            self.assertIsNone(result["value"])

    def test_f09_interactions_produce_typed_multi_reason_admission_result(self):
        pairs = [("normalization_transport","chronology_basis"),("normalization_transport","context_binding"),("context_binding","chronology_basis")]
        for a,b in pairs:
            left,right=meta(),meta(); right[a]+=".X"; right[b]+=".Y"
            decision=decide_comparability(left,right,self.domain,evaluation_cutoff="2026-06-01T00:00:00Z")
            self.assertEqual(decision["status"],"NOT_COMPARABLE")
            self.assertEqual(len(decision["reason_codes"]),2)

    def test_f09d_domain_change_changes_admission_identity(self):
        left,right=meta(),meta(); right["context_binding"]="DIFFERENT"
        expanded=decide_comparability(left,right,self.domain,evaluation_cutoff="2026-06-01T00:00:00Z")
        legacy=ComparabilityDomain("LEGACY", tuple(x for x in BASE_DIMENSIONS if x!="context_binding"))
        old=decide_comparability(left,right,legacy,evaluation_cutoff="2026-06-01T00:00:00Z")
        self.assertEqual((old["status"],expanded["status"]),("ADMIT","NOT_COMPARABLE"))

    def test_f10_hand_computed_euclidean_and_manhattan_goldens(self):
        result=compare(self.left,self.right,left_meta=meta(),right_meta=meta(),domain=self.domain,spec=self.spec,evaluation_cutoff="2026-06-01T00:00:00Z")
        self.assertEqual(result["value"],"5.0")
        man=ComparisonSpec("MAN","DISTANCE","MANHATTAN",("X","Y"))
        self.assertEqual(compare(self.left,self.right,left_meta=meta(),right_meta=meta(),domain=self.domain,spec=man,evaluation_cutoff="2026-06-01T00:00:00Z")["value"],"7")

    def test_f11_only_declared_properties_are_asserted(self):
        self.assertIn("SYMMETRIC",self.spec.declared_properties)
        self.assertNotIn("TRIANGLE", ComparisonSpec("COS","SIMILARITY","COSINE",("X","Y"),declared_properties=("BOUNDED",)).declared_properties)

    def test_f12_pair_id_is_order_invariant_for_symmetric_spec(self):
        decision=decide_comparability(meta(),meta(),self.domain,evaluation_cutoff="2026-06-01T00:00:00Z")
        self.assertEqual(pair_id("A","B",decision=decision,spec=self.spec),pair_id("B","A",decision=decision,spec=self.spec))

    def test_f13_tolerance_boundaries(self):
        self.assertTrue(equivalent("1.0","1.001",kind="ABS_TOL",abs_tolerance="0.001"))
        self.assertFalse(equivalent("1.0","1.0011",kind="ABS_TOL",abs_tolerance="0.001"))
        self.assertTrue(equivalent("100","101",kind="REL_TOL",rel_tolerance="0.01"))

    def test_f14_tiled_surface_reconstructs_logical_pair_order(self):
        records=[]
        for i in range(5):
            r=rep(f"R{i}",i,0)
            records.append(compare(self.left,r,left_meta=meta(),right_meta=meta(),domain=self.domain,spec=self.spec,evaluation_cutoff="2026-06-01T00:00:00Z"))
        surface=build_surface(records,population_id="POP",representation_pack_id="PACK",spec=self.spec,domain=self.domain,tile_size=2)
        reconstructed=[pid for tile in surface["tile_manifest"] for pid in tile["pair_ids"]]
        self.assertEqual(reconstructed,surface["pair_index"])

    def test_f15_semantic_cache_invalidates_on_spec_or_domain_change(self):
        base=semantic_cache_key(["a","b"],self.spec,self.domain)
        changed_spec=semantic_cache_key(["a","b"],ComparisonSpec("SPEC2","DISTANCE","MANHATTAN",("X","Y")),self.domain)
        changed_domain=semantic_cache_key(["a","b"],self.spec,ComparabilityDomain("DOMAIN2"))
        self.assertNotEqual(base,changed_spec)
        self.assertNotEqual(base,changed_domain)


if __name__ == "__main__":
    unittest.main()
