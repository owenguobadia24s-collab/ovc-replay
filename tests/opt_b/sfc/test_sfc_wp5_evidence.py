import unittest

from ovc.opt_b.sfc.evidence import ambiguity_rate, chronological_stability, correspondence, directional_survival, exact_cross_method, family_evidence_stream, invariant_cores, rate_record, residual_rate
from ovc.opt_b.sfc.sensitivity import declared_delta, qualify_adjacent_sensitivity, qualify_cross_method
from ovc.opt_b.sfc.v04_adapter import FROZEN_V04_GIT_BLOB, FROZEN_V04_LOGICAL_SHA256, compare_residual_semantics


def family(fid, members): return {"family_id":fid,"member_ids":members}
def catalog(cid, cfg, families, residual=(), noise=(), status="FAMILY_EVIDENCE_PRESENT", method="M1"):
    eligible=sorted({m for f in families for m in f["member_ids"]}|set(residual)|set(noise))
    return {"family_catalog_id":cid,"configuration_id":cfg,"method_id":method,"families":families,"residual_ids":list(residual),"noise_ids":list(noise),"denominator_eligible":len(eligible),"denominator_residual_noise":len(set(residual)|set(noise)),"evidence_status":status}


class SFCWP5EvidenceTests(unittest.TestCase):
    def test_f21_split_merge_correspondence_is_directional_and_explicit(self):
        left=catalog("L","C1",[family("L1",["A","B","C","D"])])
        right=catalog("R","C2",[family("R1",["A","B"]),family("R2",["C","D"])])
        corr=correspondence(left,right)
        self.assertEqual(len(corr["split_events"]),1)
        self.assertEqual(len(corr["merge_events"]),0)
        rev=correspondence(right,left)
        self.assertEqual(len(rev["merge_events"]),1)

    def test_f22_cross_method_pair_requires_shared_rep_distance_support_and_different_method(self):
        a={"representation_pack_id":"P","comparison_spec_id":"D","minimum_support":2,"family_method_id":"M1"}
        b={**a,"family_method_id":"M2"}
        self.assertTrue(qualify_cross_method(a,b)["qualified"])
        self.assertFalse(qualify_cross_method(a,{**b,"minimum_support":3})["qualified"])

    def test_f23_ambiguity_tie_has_exact_denominator(self):
        left=catalog("L","C1",[family("L1",["A","B"])])
        right=catalog("R","C2",[family("R1",["A"]),family("R2",["B"])])
        metric=ambiguity_rate(correspondence(left,right))
        self.assertEqual((metric["numerator"],metric["denominator"],metric["rate"]),(1,1,"1/1"))

    def test_f24_residual_exact_denominator_and_rational(self):
        cat=catalog("C","CFG",[family("F",["A","B"])],residual=["C"],noise=["D"])
        metric=residual_rate(cat)
        self.assertEqual((metric["numerator"],metric["denominator"],metric["rate"]),(2,4,"2/4"))

    def test_f25_directional_disappearance_is_not_forced_match(self):
        left=catalog("L","C1",[family("L1",["A","B"])])
        right=catalog("R","C2",[],residual=["A","B"],status="NO_STABLE_FAMILY")
        metric=directional_survival(correspondence(left,right))
        self.assertEqual(metric["denominator"],0)
        self.assertIsNone(metric["rate"])

    def test_f26_zero_denominator_is_not_evaluable(self):
        row=rate_record("X",0,0,left_scope="L",zero_reason="EMPTY")
        self.assertEqual(row["status"],"NOT_EVALUABLE")
        self.assertIsNone(row["rate"])
        self.assertEqual(row["reason_code"],"EMPTY")

    def test_f27_metric_records_have_no_hidden_composite(self):
        row=rate_record("X",1,2,left_scope="L")
        self.assertNotIn("composite_score",row)

    def test_f28_null_family_chain_emits_typed_evidence_stream(self):
        null=catalog("N","CFG",[],residual=["A","B"],status="NO_STABLE_FAMILY")
        metric=residual_rate(null)
        stream=family_evidence_stream(source_population_id="POP",source_c2e_stream_id="C2E",catalogs=[null],evidence_objects=[metric],evaluation_cutoff="T")
        self.assertEqual(stream["status"],"NO_STABLE_FAMILY")
        self.assertTrue(stream["evidence_object_ids"])

    def test_f29_optional_downstream_absence_does_not_change_stream(self):
        cat=catalog("N","CFG",[],residual=["A"],status="NO_STABLE_FAMILY")
        base=family_evidence_stream(source_population_id="POP",source_c2e_stream_id="C2E",catalogs=[cat],evidence_objects=[],evaluation_cutoff="T")
        self.assertEqual(base["status"],"NO_STABLE_FAMILY")
        self.assertEqual(base["authority_state"],"INACTIVE_CONFORMANCE_ONLY")

    def test_sensitivity_identity_proves_exactly_one_changed_field(self):
        a={"representation_pack_id":"P","comparison_spec_id":"D","family_method_id":"M","threshold":"0.1"}
        b={**a,"threshold":"0.2"}
        self.assertEqual(declared_delta(a,b)["changed_fields"],["threshold"])
        self.assertTrue(qualify_adjacent_sensitivity(a,b,sensitivity_field="threshold",ladder=["0.1","0.2","0.3"])["qualified"])

    def test_invariant_core_uses_co_membership_not_cross_catalog_family_ids(self):
        a=catalog("A","A",[family("F1",["X","Y"])])
        b=catalog("B","B",[family("OTHER",["X","Y"])])
        cores=invariant_cores([a,b],minimum_catalog_support=2)
        self.assertEqual(cores["cores"][0]["member_ids"],["X","Y"])

    def test_chronology_uses_single_catalog_without_half_refit(self):
        cat=catalog("C","CFG",[family("F",["A","B"])])
        metric=chronological_stability(cat,{"A":"2026-06-10T00:00:00Z","B":"2026-06-20T00:00:00Z"})
        self.assertEqual(metric["rate"],"1/1")

    def test_f34_frozen_v04_hash_and_shared_input_residual_semantics_are_exact(self):
        self.assertEqual(FROZEN_V04_GIT_BLOB,"e4f5ce02a103000a48ed98e2110b8f1a7d497fcd")
        self.assertEqual(FROZEN_V04_LOGICAL_SHA256,"371a058e26c05a351a99689ad23b7f844fbc956a6d81449fd237a2f420bf564b")
        cat=catalog("C","CFG",[family("F",["A","B"])],residual=["C"])
        receipt=compare_residual_semantics([cat])[0]
        self.assertTrue(receipt["equivalent"])
        self.assertEqual((receipt["frozen_numerator"],receipt["frozen_denominator"]),(1,3))


if __name__ == "__main__": unittest.main()
