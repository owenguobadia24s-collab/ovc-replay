from __future__ import annotations
import json
from pathlib import Path
import unittest
from ovc.development.skills import REQUIRED_EVALUATION_LAYERS, age_gate_readiness, assess_parallel_qualification_independence, assess_requalification, build_composition_qualification_record, build_impact_assessment, build_incident_record, build_operator_gate_readiness_record, build_skill_qualification_record, consolidate_gate_readiness, evaluate_corpus_qualification_readiness, qualification_velocity, run_evaluation_suite, run_fault_injection
from ovc.development.skills.registry import validate_against_schema
ROOT=Path(__file__).resolve().parents[2]
def evidence(status="PASS"):
    return {layer:{"status":status,"evidence_ids":[f"{layer}.1"]} for layer in REQUIRED_EVALUATION_LAYERS}
class DSAIWP6QualificationRuntimeTests(unittest.TestCase):
    def test_e1_e6_all_required_and_missing_evidence_blocks(self):
        result=run_evaluation_suite(suite_id="BASE",layer_evidence=evidence()); self.assertEqual(result["status"],"PASS"); self.assertEqual(result["aggregate_score"],1.0)
        partial=evidence(); partial.pop("E6"); result2=run_evaluation_suite(suite_id="BASE",layer_evidence=partial); self.assertEqual(result2["status"],"BLOCK"); self.assertIn("E6",result2["missing_layers"])
    def test_aggregate_score_cannot_override_mandatory_blocker_or_false_allow(self):
        rows=evidence(); rows["E4"]={"status":"PASS","evidence_ids":["E4.1"],"mandatory_blocker":True}; self.assertEqual(run_evaluation_suite(suite_id="BASE",layer_evidence=rows)["status"],"BLOCK")
        rows=evidence(); rows["E4"]={"status":"PASS","evidence_ids":["E4.1"],"false_allow":True}; result=run_evaluation_suite(suite_id="BASE",layer_evidence=rows); self.assertEqual(result["status"],"BLOCK"); self.assertGreater(result["aggregate_score"],0.8)
    def test_qualification_is_capability_environment_scoped_and_never_self_trusted(self):
        suite=run_evaluation_suite(suite_id="BASE",layer_evidence=evidence())
        qualified=build_skill_qualification_record(skill_release_id="SKILL@1",capability_id="AUTHORITY_RESOLUTION",environment_id="ENV1",knowledge_pack_hash="a"*64,environment_hash="b"*64,suite_result=suite); self.assertEqual(qualified["qualification_status"],"QUALIFIED"); self.assertFalse(qualified["trusted_promoted"])
        trusted=build_skill_qualification_record(skill_release_id="SKILL@1",capability_id="AUTHORITY_RESOLUTION",environment_id="ENV1",knowledge_pack_hash="a"*64,environment_hash="b"*64,suite_result=suite,requested_maturity="TRUSTED"); self.assertEqual(trusted["qualification_status"],"GATE_REQUIRED"); self.assertEqual(trusted["max_maturity_without_operator_gate"],"QUALIFIED"); self.assertFalse(trusted["trusted_promoted"])
    def test_knowledge_environment_release_drift_marks_stale(self):
        suite=run_evaluation_suite(suite_id="BASE",layer_evidence=evidence()); q=build_skill_qualification_record(skill_release_id="SKILL@1",capability_id="C",environment_id="ENV",knowledge_pack_hash="a"*64,environment_hash="b"*64,suite_result=suite)
        for kwargs in [dict(current_skill_release_id="SKILL@2",current_knowledge_pack_hash="a"*64,current_environment_hash="b"*64),dict(current_skill_release_id="SKILL@1",current_knowledge_pack_hash="c"*64,current_environment_hash="b"*64),dict(current_skill_release_id="SKILL@1",current_knowledge_pack_hash="a"*64,current_environment_hash="c"*64)]: self.assertEqual(assess_requalification(q,**kwargs)["status"],"STALE_REQUALIFICATION_REQUIRED")
    def test_wp3_unreviewed_adversarial_seed_blocks_real_qualification_e4_readiness(self):
        corpus=json.loads((ROOT/"fixtures/development_skills/wp3_adversarial_corpus_v0_1.json").read_text()); ready=evaluate_corpus_qualification_readiness(corpus["curation_records"]); self.assertEqual(ready["status"],"BLOCK"); self.assertIn("INDEPENDENT_HUMAN_REVIEW_MISSING",ready["reason_codes"])
    def test_composition_requires_individual_qualification_and_composition_evidence(self):
        suite=run_evaluation_suite(suite_id="BASE",layer_evidence=evidence()); q=build_skill_qualification_record(skill_release_id="S",capability_id="C",environment_id="E",knowledge_pack_hash="a"*64,environment_hash="b"*64,suite_result=suite)
        self.assertEqual(build_composition_qualification_record(composition_id="X",member_qualifications=[q],composition_evidence_status="PASS")["status"],"QUALIFIED"); self.assertEqual(build_composition_qualification_record(composition_id="X",member_qualifications=[q],composition_evidence_status="FAIL")["status"],"BLOCKED")
    def test_fault_injection_all_fails_closed(self):
        fixture=json.loads((ROOT/"fixtures/development_skills/wp6_qualification_faults_v0_1.json").read_text()); self.assertTrue(all(run_fault_injection(scenario=s)["observed_status"]=="BLOCK" for s in fixture["faults"]))
    def test_incident_s1_s4_and_impact(self):
        s1=build_incident_record(qualification_id="Q",severity="S1",reason_codes=["OBS"]); s3=build_incident_record(qualification_id="Q",severity="S3",reason_codes=["SEC"]); s4=build_incident_record(qualification_id="Q",severity="S4",reason_codes=["CRIT"]); self.assertFalse(s1["quarantine_required"]); self.assertTrue(s3["quarantine_required"]); self.assertFalse(s3["revocation_required"]); self.assertTrue(s4["revocation_required"]); self.assertTrue(build_impact_assessment(incident_id=s4["incident_id"],dependent_qualification_ids=["Q2"])["requires_review"])
    def test_gate_readiness_slo_has_zero_authority_effect_and_stale_candidate_blocks(self):
        row=build_operator_gate_readiness_record(gate_id="G7",authority_kind="TRUSTED_PROMOTION",candidate_sha="a"*40,qualification_ids=["Q1"],evidence_closed=True,gate_ready_at="2026-08-11T10:00:00Z",review_target_at="2026-08-11T11:00:00Z"); self.assertEqual(row["status"],"GATE_READY"); self.assertFalse(row["authority_granted"])
        aged=age_gate_readiness(row,now="2026-08-11T12:00:00Z",current_candidate_sha="a"*40); self.assertEqual(aged["review_slo_state"],"AGED"); self.assertFalse(aged["auto_approve"]); self.assertFalse(aged["auto_promote"]); self.assertFalse(aged["auto_activate"]); self.assertEqual(aged["authority_effect"],"NONE")
        stale=age_gate_readiness(row,now="2026-08-11T12:00:00Z",current_candidate_sha="b"*40); self.assertTrue(stale["candidate_stale"]); self.assertEqual(stale["status"],"BLOCKED")
    def test_same_authority_consolidation_only_and_traceable(self):
        a=build_operator_gate_readiness_record(gate_id="G7A",authority_kind="TRUSTED_PROMOTION",candidate_sha="a"*40,qualification_ids=["Q1"],evidence_closed=True,gate_ready_at="2026-08-11T10:00:00Z",review_target_at="2026-08-11T11:00:00Z"); b=build_operator_gate_readiness_record(gate_id="G7B",authority_kind="TRUSTED_PROMOTION",candidate_sha="b"*40,qualification_ids=["Q2"],evidence_closed=True,gate_ready_at="2026-08-11T10:00:00Z",review_target_at="2026-08-11T11:00:00Z"); self.assertEqual(consolidate_gate_readiness([a,b],group_id="X")["status"],"PASS")
        c=build_operator_gate_readiness_record(gate_id="G9",authority_kind="ORCH_2",candidate_sha="c"*40,qualification_ids=["Q3"],evidence_closed=True,gate_ready_at="2026-08-11T10:00:00Z",review_target_at="2026-08-11T11:00:00Z")
        with self.assertRaisesRegex(ValueError,"same authority kind"): consolidate_gate_readiness([a,c],group_id="BAD")
    def test_parallel_qualification_requires_independent_fixtures_envs_stores(self):
        good=[{"fixture_ids":["F1"],"environment_ids":["E1"],"evidence_store_ids":["S1"]},{"fixture_ids":["F2"],"environment_ids":["E2"],"evidence_store_ids":["S2"]}]; self.assertEqual(assess_parallel_qualification_independence(good)["status"],"PASS"); bad=[good[0],{"fixture_ids":["F1"],"environment_ids":["E2"],"evidence_store_ids":["S2"]}]; self.assertEqual(assess_parallel_qualification_independence(bad)["status"],"BLOCK")
    def test_velocity_integrity_and_schemas(self):
        row=qualification_velocity(completed=4,elapsed_minutes=120,requalification_count=1,failed_count=1); self.assertEqual(row["qualifications_per_hour"],2.0); self.assertEqual(row["authority_effect"],"NONE")
        for name in ("evaluation_suite_registry_v0_1.schema.json","skill_qualification_record_v0_1.schema.json","operator_gate_readiness_record_v0_1.schema.json","skill_incident_record_v0_1.schema.json"):
            schema=json.loads((ROOT/"schemas/development/skills"/name).read_text()); self.assertEqual(schema["$schema"],"https://json-schema.org/draft/2020-12/schema"); self.assertFalse(schema["additionalProperties"])
        suite=run_evaluation_suite(suite_id="BASE",layer_evidence=evidence()); q=build_skill_qualification_record(skill_release_id="S",capability_id="C",environment_id="E",knowledge_pack_hash="a"*64,environment_hash="b"*64,suite_result=suite); validate_against_schema(q,json.loads((ROOT/"schemas/development/skills/skill_qualification_record_v0_1.schema.json").read_text()))
if __name__=="__main__": unittest.main()
