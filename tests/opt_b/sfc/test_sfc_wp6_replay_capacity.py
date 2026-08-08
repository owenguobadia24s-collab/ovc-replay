import unittest

from ovc.opt_b.sfc.evidence import family_evidence_stream, residual_rate
from ovc.opt_b.sfc.replay import build_g2_block, build_replay_manifest, capacity_guard, checkpoint_state, dependency_status, enforce_june_interlock, propagate_quarantine, resume_remaining


def null_catalog():
    return {"family_catalog_id":"CAT.NULL","configuration_id":"CFG.NULL","families":[],"residual_ids":["A","B"],"noise_ids":[],"denominator_eligible":2,"denominator_residual_noise":2,"evidence_status":"NO_STABLE_FAMILY"}


class SFCWP6ReplayCapacityTests(unittest.TestCase):
    def manifest(self):
        return build_replay_manifest(source_stream_id="C2E.SYN",pack_ids=["P2","P1"],spec_ids=["D1"],configuration_ids=["C2","C1"],rule_pack_ids=["OVC-SRFD-STABILITY-METRIC-SPECS-0.4"],code_hashes={"sfc":"abc"},schema_hashes={"sfc":"def"},upstream_receipt_id="UPSTREAM.READY",external_inventory=[{"name":"fixture","sha256":"00"}],checkpoints=[])

    def test_restart_resume_is_deterministic_and_order_independent(self):
        m1=self.manifest(); m2=self.manifest()
        self.assertEqual(m1,m2)
        cp=checkpoint_state(m1,completed_ids=["B","A"],partial_evidence=[{"x":1},{"y":2}],last_source_fvt="T2")
        self.assertEqual(resume_remaining(["D","C","B","A"],cp),["C","D"])
        self.assertEqual(resume_remaining(["A","D","B","C"],cp),["C","D"])

    def test_f30_capacity_failure_never_samples_or_drops_methods(self):
        row=capacity_guard(population_id="POP",eligible_count=100,pair_count=4950,family_grid_count=20,limits={"eligible_count":50,"pair_count":1000,"family_grid_count":10})
        self.assertEqual(row["status"],"CAPACITY_EXCEEDED")
        self.assertFalse(row["sampling_applied"])
        self.assertEqual(row["methods_dropped"],[])
        self.assertFalse(row["sensitivity_changed"])
        self.assertTrue(row["population_preserved"])
        self.assertEqual(row["eligible_count"],100)

    def test_f31_quarantine_propagates(self):
        self.assertEqual(propagate_quarantine("READY","QUARANTINED","READY"),"QUARANTINED")
        self.assertEqual(propagate_quarantine("READY","READY"),"READY")

    def test_f32_positive_and_null_family_stream_paths_are_typed(self):
        positive={"family_catalog_id":"CAT.POS","configuration_id":"CFG.POS","families":[{"family_id":"F","member_ids":["A","B"]}],"residual_ids":[],"noise_ids":[],"denominator_eligible":2,"denominator_residual_noise":0,"evidence_status":"FAMILY_EVIDENCE_PRESENT"}
        pmetric=residual_rate(positive)
        pstream=family_evidence_stream(source_population_id="POP",source_c2e_stream_id="C2E",catalogs=[positive],evidence_objects=[pmetric],evaluation_cutoff="T")
        self.assertEqual(pstream["status"],"FAMILY_EVIDENCE_PRESENT")
        n=null_catalog(); nstream=family_evidence_stream(source_population_id="POP",source_c2e_stream_id="C2E",catalogs=[n],evidence_objects=[residual_rate(n)],evaluation_cutoff="T")
        self.assertEqual(nstream["status"],"NO_STABLE_FAMILY")

    def test_f35_bounded_stress_preserves_full_identity_without_scope_drift(self):
        ids=[f"R{i:04d}" for i in range(500)]
        m=self.manifest(); cp=checkpoint_state(m,completed_ids=ids[:250],partial_evidence=[],last_source_fvt="T")
        remaining=resume_remaining(list(reversed(ids)),cp)
        self.assertEqual(len(remaining),250)
        self.assertEqual(remaining[0],"R0250")
        ok=capacity_guard(population_id="POP",eligible_count=500,pair_count=124750,family_grid_count=10,limits={"eligible_count":500,"pair_count":124750,"family_grid_count":10})
        self.assertEqual(ok["status"],"SUCCESS")
        self.assertTrue(ok["population_preserved"])

    def test_f36_forced_capacity_fail_is_deterministic(self):
        a=capacity_guard(population_id="POP",eligible_count=3,pair_count=3,family_grid_count=2,limits={"eligible_count":2,"pair_count":2,"family_grid_count":1})
        b=capacity_guard(population_id="POP",eligible_count=3,pair_count=3,family_grid_count=2,limits={"family_grid_count":1,"pair_count":2,"eligible_count":2})
        self.assertEqual(a["logical_hash"],b["logical_hash"])
        self.assertEqual(a["status"],"CAPACITY_EXCEEDED")

    def test_f37_exact_g2_block_never_falls_back(self):
        row=build_g2_block(observed_upstream_state="UNAVAILABLE",missing_artifacts=["EpisodeSnapshot"],expected_upstream_evidence=["C2E_TO_SRI_STREAM_HANDOFF"])
        self.assertEqual(row["gate_id"],"SFC-G2")
        self.assertEqual(row["reason_code"],"BLOCK_UPSTREAM")
        self.assertEqual(row["no_fallback_assertion"],"HISTORICAL_MG_C2E_FORBIDDEN")

    def test_f38_june_interlock_denies_fresh_authority_prep_and_run(self):
        for action in ("SRFDI-G-JUNE-AUTH-PREP","SRFDI-G-JUNE-AUTH","JUNE_SCIENTIFIC_RUN","FRESH_JUNE_RUN_TOKEN"):
            row=enforce_june_interlock("DENY",action)
            self.assertEqual(row["status"],"DENIED")
            self.assertEqual(row["reason_code"],"SFC_SRFD_JUNE_INTERLOCK_ACTIVE")
        self.assertEqual(enforce_june_interlock("DENY","SRFD_HISTORICAL_CLOSEOUT")["status"],"ALLOWED")

    def test_f39_unknown_dependency_is_never_coerced_to_ready(self):
        self.assertEqual(dependency_status("UNKNOWN"),"UNKNOWN")
        self.assertEqual(dependency_status("UNAVAILABLE"),"UNAVAILABLE")
        self.assertNotEqual(dependency_status("UNKNOWN"),"READY")


if __name__ == "__main__": unittest.main()
