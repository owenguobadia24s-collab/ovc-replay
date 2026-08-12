from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from ovc.development.skills.assurance import audit_evidence, evaluate_gate, evaluate_qa, plan_tests
from ovc.development.skills.governance import shadow_authority_resolver, shadow_preflight, shadow_prerequisite_resolver, shadow_scope_guard
from ovc.development.skills.qualification import build_composition_qualification_record, build_skill_qualification_record, run_evaluation_suite

ROOT = Path(__file__).resolve().parents[2]
QPACK = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp7/DSAI_G7_FINAL_QUALIFICATION_READINESS_CANDIDATE.json"
E5PASS = ROOT / "records/development/skills/DSAI_G7_E5_OPERATOR_PASS_20260812T124000+0100.json"
ENV = ROOT / "fixtures/development_skills/wp2_windows_environment_v0_1.json"

class DSAIG7FinalCompositionReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qpack = json.loads(QPACK.read_text())
        cls.e5 = json.loads(E5PASS.read_text())
        cls.env = json.loads(ENV.read_text())
        cls.env_hash = hashlib.sha256(json.dumps(cls.env, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def test_e5_independent_pass_is_materialised_without_authority_effect(self):
        self.assertEqual(self.e5["evaluation_layer"], "E5")
        self.assertEqual(self.e5["decision"], "PASS")
        self.assertEqual(self.e5["decision_authority"], "HUMAN_OPERATOR")
        self.assertEqual(self.e5["corpus"]["accepted"], 42)
        self.assertEqual(self.e5["corpus"]["amended"], 0)
        self.assertEqual(self.e5["findings"]["false_allows"], 0)
        self.assertEqual(self.e5["findings"]["false_blocks"], 0)
        self.assertEqual(self.e5["authority_effect"], "QUALIFICATION_EVIDENCE_ONLY_NO_TRUSTED_PROMOTION")

    def test_all_eight_exact_g7_tuples_have_closed_e1_e6_and_current_environment(self):
        self.assertEqual(self.qpack["exact_tuple_count"], 8)
        self.assertEqual(self.qpack["environment"]["hash"], self.env_hash)
        self.assertEqual(self.qpack["stale_qualifications"], 0)
        self.assertEqual(self.qpack["known_false_allows"], 0)
        self.assertEqual(self.qpack["trusted_promotions"], [])
        for row in self.qpack["exact_tuples"]:
            self.assertEqual(set(row["evaluation_layers"].values()), {"PASS"})
            layers = {
                "E1":{"status":"PASS","evidence_ids":[f"{row['skill_id']}.E1.CONTRACT_REGISTRY"]},
                "E2":{"status":"PASS","evidence_ids":[f"{row['skill_id']}.E2.GOLDEN"]},
                "E3":{"status":"PASS","evidence_ids":[f"{row['skill_id']}.E3.NEGATIVE_REFUSAL"]},
                "E4":{"status":"PASS","evidence_ids":["records/development/skills/DSAI_G7_E4_OPERATOR_PASS_20260812T115600+0100.json"]},
                "E5":{"status":"PASS","evidence_ids":["records/development/skills/DSAI_G7_E5_OPERATOR_PASS_20260812T124000+0100.json"]},
                "E6":{"status":"PASS","evidence_ids":[f"{row['skill_id']}.E6.9FAULT_FULL_SURFACE"]},
            }
            suite = run_evaluation_suite(suite_id=f"DSAI-G7-FINAL.{row['skill_id']}", layer_evidence=layers)
            self.assertEqual(suite["status"], "PASS")
            self.assertTrue(suite["evidence_closed"])
            q = build_skill_qualification_record(skill_release_id=row["release_id"], capability_id=row["capability_id"], environment_id=row["environment_id"], knowledge_pack_hash=row["knowledge_pack_hash"], environment_hash=self.env_hash, suite_result=suite, requested_maturity="QUALIFIED", current_knowledge_pack_hash=row["knowledge_pack_hash"], current_environment_hash=self.env_hash)
            self.assertEqual(q["qualification_status"], "QUALIFIED")
            self.assertFalse(q["stale"])
            self.assertFalse(q["trusted_promoted"])

    def test_composition_is_qualified_but_never_self_promotes(self):
        members=[]
        for row in self.qpack["exact_tuples"]:
            layers={layer:{"status":"PASS","evidence_ids":[f"{row['skill_id']}.{layer}"]} for layer in ("E1","E2","E3","E4","E5","E6")}
            suite=run_evaluation_suite(suite_id=f"DSAI-G7-COMP.{row['skill_id']}", layer_evidence=layers)
            members.append(build_skill_qualification_record(skill_release_id=row["release_id"], capability_id=row["capability_id"], environment_id=row["environment_id"], knowledge_pack_hash=row["knowledge_pack_hash"], environment_hash=self.env_hash, suite_result=suite, requested_maturity="QUALIFIED", current_knowledge_pack_hash=row["knowledge_pack_hash"], current_environment_hash=self.env_hash))
        comp=build_composition_qualification_record(composition_id=self.qpack["composition"]["composition_id"], member_qualifications=members, composition_evidence_status="PASS")
        self.assertEqual(comp["status"], "QUALIFIED")
        self.assertFalse(comp["trusted_promoted"])
        self.assertEqual(set(self.qpack["composition"]["member_skill_ids"]), {row["skill_id"] for row in self.qpack["exact_tuples"]})

    def test_shadow_packet_replay_preserves_operator_reserved_trusted_boundary(self):
        pre=shadow_preflight({"repository_sha":"846619997d61d86f541b58d6dce2cfdf073c0192","plan_id":"OVC-DSAI-IMPLEMENTATION-PLAN-0.2","packet_id":"DSAI-WP7","source_precedence_resolved":True,"scope_status":"BOUNDED","prerequisites_complete":True})
        auth=shadow_authority_resolver(recorded_authority={"implementation":"BOUNDED"}, requested_delta="TRUSTED_PROMOTION")
        scope=shadow_scope_guard(requested_paths=["docs/releases/development-skills-architecture-v0-1/dsai-wp7/DSAI_G7_CONSOLIDATED_TRUSTED_PROMOTION_DECISION_PACKET.json"], allowed_prefixes=["docs/releases/development-skills-architecture-v0-1/dsai-wp7"])
        prereq=shadow_prerequisite_resolver(required=["DSAI-G6"], observed={"DSAI-G6":"COMPLETED"})
        tests=plan_tests(changed_paths=["docs/releases/development-skills-architecture-v0-1/dsai-wp7"], direct_tests=["tests/development_skills/test_dsai_g7_final_composition_readiness.py"], impact_known=False)
        qa=evaluate_qa([{"status":"PASS","assertion":"E1-E6_CLOSED"},{"status":"PASS","assertion":"COMPOSITION_QUALIFIED"}])
        evidence=audit_evidence([{"sha256":"a"*64,"stale":False}])
        gate=evaluate_gate(gate_title="DSAI-G7 TRUSTED promotion", acceptance_conditions=[True,True,True,True,True], qa_status="PASS", authority_delta="TRUSTED_PROMOTION")
        self.assertEqual(pre["disposition"], "PASS")
        self.assertEqual(auth["disposition"], "BLOCK")
        self.assertEqual(scope["disposition"], "PASS")
        self.assertEqual(prereq["disposition"], "PASS")
        self.assertTrue(tests["widened"])
        self.assertEqual(qa["acceptance_result"], "PASS")
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(gate["acceptance_result"], "PASS")
        self.assertEqual(gate["authority_result"], "OPERATOR_REQUIRED")
        self.assertFalse(gate["auto_ratifiable"])
        self.assertFalse(gate["authority_granted"])

if __name__ == "__main__":
    unittest.main()
