from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from ovc.development.skills.assurance import audit_evidence, evaluate_gate, evaluate_qa, plan_tests
from ovc.development.skills.governance import (
    shadow_authority_resolver,
    shadow_preflight,
    shadow_prerequisite_resolver,
    shadow_scope_guard,
)
from ovc.development.skills.qualification import (
    build_composition_qualification_record,
    build_skill_qualification_record,
    run_evaluation_suite,
    run_fault_injection,
)


ROOT = Path(__file__).resolve().parents[2]
FAULTS = ("CORRUPT_MANIFEST", "STALE_HASH", "DENIED_TOOL", "KILLED_TEST", "INVALID_CACHE")
G7_IDS = {
    "OVC-SKILL-001", "OVC-SKILL-002", "OVC-SKILL-003", "OVC-SKILL-004",
    "OVC-SKILL-020", "OVC-SKILL-022", "OVC-SKILL-023", "OVC-SKILL-024",
}


def sha256_json(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class DSAIG7AllSkillEvidenceClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = json.loads((ROOT / "fixtures/development_skills/g7_all_skill_independent_review_worksheet_v0_1.json").read_text())
        self.packet = json.loads((ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp7/DSAI_G7_ALL_SKILL_QUALIFICATION_EXECUTION_PACKET.json").read_text())
        self.environment = json.loads((ROOT / "fixtures/development_skills/wp2_windows_environment_v0_1.json").read_text())
        self.environment_hash = sha256_json(self.environment)
        self.releases = []
        for path in (
            "registries/development/skills/governance_candidates_v0_1.json",
            "registries/development/skills/first_generation_candidates_v0_1.json",
        ):
            registry = json.loads((ROOT / path).read_text())
            self.releases.extend(registry["entries"])

    def test_exact_release_inventory_is_complete_and_packet_executor_is_not_fabricated(self) -> None:
        self.assertEqual(len(self.releases), 14)
        self.assertEqual({row["skill_id"] for row in self.review["skill_reviews"]}, {row["skill_id"] for row in self.releases})
        self.assertEqual(self.review["deferred_catalogue_skills"], [{
            "skill_id": "OVC-SKILL-030", "logical_name": "ovc-packet-executor",
            "reason": "NOT_IMPLEMENTED_EXACT_RELEASE_UNAVAILABLE", "qualification_result": "NOT_EVALUABLE",
            "promotion_gate": "DSAI-G8B",
        }])
        self.assertEqual(self.packet["trusted_promotions"], [])

    def test_e6_fault_injection_is_bound_to_every_exact_release(self) -> None:
        bindings = 0
        for release in self.releases:
            for scenario in FAULTS:
                with self.subTest(skill=release["skill_id"], scenario=scenario):
                    result = run_fault_injection(scenario=scenario)
                    self.assertEqual(result["observed_status"], "BLOCK")
                    self.assertTrue(result["fail_closed"])
                    self.assertEqual(result["authority_effect"], "NONE")
                    bindings += 1
        self.assertEqual(bindings, 70)
        self.assertEqual(self.packet["assurance"]["E6"]["exact_release_bindings"], 70)

    def test_no_exact_release_can_be_promoted_while_independent_e4_e5_are_open(self) -> None:
        for release in self.releases:
            knowledge_hash = release.get("knowledge_pack_hash") or hashlib.sha256(release["release_id"].encode()).hexdigest()
            layers = {
                "E1": {"status": "PASS", "evidence_ids": [f"{release['skill_id']}.E1"]},
                "E2": {"status": "PASS", "evidence_ids": [f"{release['skill_id']}.E2"]},
                "E3": {"status": "PASS", "evidence_ids": [f"{release['skill_id']}.E3"]},
                "E4": {"status": "PASS", "evidence_ids": ["G7.108.MECHANICAL"], "mandatory_blocker": True},
                "E5": {"status": "BLOCK", "evidence_ids": ["G7.E5.INDEPENDENT_REFERENCE_PENDING"], "mandatory_blocker": True},
                "E6": {"status": "PASS", "evidence_ids": [f"{release['skill_id']}.E6.5FAULTS"]},
            }
            suite = run_evaluation_suite(suite_id=f"G7.ALL.{release['skill_id']}", layer_evidence=layers)
            self.assertEqual(suite["status"], "BLOCK", release["skill_id"])
            for capability_id in release["capability_ids"]:
                q = build_skill_qualification_record(
                    skill_release_id=release["release_id"], capability_id=capability_id,
                    environment_id=self.environment["base_environment_id"],
                    knowledge_pack_hash=knowledge_hash, environment_hash=self.environment_hash,
                    suite_result=suite, requested_maturity="TRUSTED",
                )
                self.assertEqual(q["qualification_status"], "BLOCKED")
                self.assertFalse(q["trusted_promoted"])

    def test_review_worksheet_preserves_independent_human_e4_and_e5_as_pending(self) -> None:
        self.assertEqual(self.review["adversarial_suite"]["effective_cases"], 108)
        self.assertEqual(self.review["adversarial_suite"]["effective_families"], 18)
        self.assertEqual(self.review["adversarial_suite"]["mechanical_status"], "PASS")
        for row in self.review["skill_reviews"]:
            self.assertEqual(row["e4_independent_review"]["status"], "PENDING")
            self.assertIsNone(row["e4_independent_review"]["reviewer_role"])
            self.assertEqual(row["e4_independent_review"]["review_effort_minutes"], 0)
            self.assertEqual(row["e5_independent_reference_check"]["status"], "PENDING")
            self.assertIsNone(row["e5_independent_reference_check"]["reviewer_role"])
            self.assertEqual(row["e5_independent_reference_check"]["review_effort_minutes"], 0)

    def test_g7_control_composition_shadow_replay_preserves_reserved_authority(self) -> None:
        preflight = shadow_preflight({
            "repository_sha": "a" * 40, "plan_id": "OVC-DSAI-IMPLEMENTATION-PLAN-0.2", "packet_id": "DSAI-WP7",
            "source_precedence_resolved": True, "scope_status": "IN_SCOPE", "prerequisites_complete": True,
        })
        authority = shadow_authority_resolver(recorded_authority={"implementation": "BOUNDED"}, requested_delta="TRUSTED_PROMOTION")
        scope = shadow_scope_guard(
            requested_paths=["docs/releases/development-skills-architecture-v0-1/dsai-wp7/packet.json"],
            allowed_prefixes=["docs/releases/development-skills-architecture-v0-1/dsai-wp7"],
        )
        prerequisites = shadow_prerequisite_resolver(required=["DSAI-G6"], observed={"DSAI-G6": "COMPLETED"})
        test_plan = plan_tests(changed_paths=["src/ovc/development/skills/qualification.py"], direct_tests=["tests/development_skills"], impact_known=False)
        qa = evaluate_qa([{"status": "PASS", "assertion": "MECHANICAL_ASSURANCE"}])
        evidence = audit_evidence([{"sha256": "a" * 64, "stale": False}])
        gate = evaluate_gate(
            gate_title="DSAI-G7 TRUSTED promotion", acceptance_conditions=[True], qa_status="PASS",
            authority_delta="TRUSTED_PROMOTION",
        )
        self.assertEqual(preflight["disposition"], "PASS")
        self.assertEqual(authority["disposition"], "BLOCK")
        self.assertIn("OPERATOR_REQUIRED_RESERVED_DELTA", authority["reason_codes"])
        self.assertEqual(scope["disposition"], "PASS")
        self.assertEqual(prerequisites["disposition"], "PASS")
        self.assertTrue(test_plan["widened"])
        self.assertIn("REPOSITORY_WIDE_SUITE", test_plan["selected_tests"])
        self.assertEqual(qa["acceptance_result"], "PASS")
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(gate["authority_result"], "OPERATOR_REQUIRED")
        self.assertFalse(gate["authority_granted"])
        self.assertFalse(gate["auto_ratifiable"])

    def test_g7_formal_composition_qualification_remains_blocked_until_member_evidence_closes(self) -> None:
        blocked_members = []
        for row in self.review["skill_reviews"]:
            if row["skill_id"] not in G7_IDS:
                continue
            blocked_members.append({
                "qualification_id": f"PENDING.{row['skill_id']}", "qualification_status": "BLOCKED", "stale": False,
            })
        composition = build_composition_qualification_record(
            composition_id="DSAI-G7-CONTROL-COMPOSITION-v0.1",
            member_qualifications=blocked_members,
            composition_evidence_status="PASS",
        )
        self.assertEqual(len(blocked_members), 8)
        self.assertEqual(composition["status"], "BLOCKED")
        self.assertFalse(composition["trusted_promoted"])

    def test_execution_packet_is_fail_closed_and_preserves_later_reserved_gates(self) -> None:
        self.assertEqual(self.packet["qualification_disposition"], "BLOCK_PENDING_INDEPENDENT_E4_E5")
        self.assertEqual(self.packet["later_reserved_gates"]["OVC-SKILL-014"], "DSAI-G9A")
        self.assertEqual(self.packet["later_reserved_gates"]["OVC-SKILL-030"], "DSAI-G8B")
        self.assertEqual(self.packet["authority"]["trusted_skills"], [])
        self.assertEqual(self.packet["authority"]["orch_1"], "INACTIVE")
        self.assertEqual(self.packet["authority"]["orch_2"], "INACTIVE")


if __name__ == "__main__":
    unittest.main()
