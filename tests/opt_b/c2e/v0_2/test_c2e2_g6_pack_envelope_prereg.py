import copy
import json
from pathlib import Path
import unittest

from ovc.opt_b.c2e_v2.boundary_pack import freeze_pack
from ovc.opt_b.c2e_v2.empirical_boundary_rules import EmpiricalBoundaryRuleError, evaluate_boundary_predicates

ROOT = Path(__file__).resolve().parents[4]
PACK = ROOT / "registries/opt_b/c2e/v0_2/C2E_EMPIRICAL_BOUNDARY_PACK_JUNE_v0_1.json"
ENVELOPE = ROOT / "registries/implementation/c2e_v0_2/run_authority/C2E2_EXACT_RESOURCE_ENVELOPE_JUNE_v0_1.json"
DECISION = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-g6-prereq-20260809/C2E2_G6_PACK_ENVELOPE_OPERATOR_DECISION.json"
QA = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-g6-prereq-20260809/C2E2_G6_PACK_ENVELOPE_QA_PACKET.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_21.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"


def frame(segment="SEG.1", structural_suffix="A", parent_suffix="A"):
    return {
        "identity": {"instrument_id":"GBPUSD","side":"BID","scope_id":"LOCAL","scale_id":"15M","clock_id":"15M"},
        "chronology": {"continuity_segment_id":segment,"first_valid_time":"2026-06-01T00:15:00Z","evaluation_cutoff":"2026-06-01T00:15:00Z"},
        "structural": {
            "location_record_ids":[f"LOC.{structural_suffix}"],"motion_record_ids":[f"MOT.{structural_suffix}"],
            "organisation_record_ids":[f"ORG.{structural_suffix}"],"interaction_record_ids":[f"INT.{structural_suffix}"],
            "level_record_ids":[],"container_record_ids":[],"transition_record_ids":[],"run_record_ids":[],"relation_set_id":f"REL.{structural_suffix}"
        },
        "context": {"context_resolution_bundle_id":f"CTX.{parent_suffix}","fixed_parent_links":[f"PARENT.{parent_suffix}"],"structural_object_links":[],"parent_axis_links":[]},
        "evidence": {"dependency_results":[],"availability_status":"AVAILABLE","technical_status":"COMPUTABLE","authority_state":"READ_ONLY_SHADOW","reason_codes":[]},
        "lineage": {"parent_record_ids":[],"artifact_hashes":{"x":"y"},"source_build_commit":"abc"},
    }


class C2E2G6PackEnvelopePreregTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK.read_text())
        cls.envelope = json.loads(ENVELOPE.read_text())
        cls.decision = json.loads(DECISION.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_operator_instruction_exact_and_bounded(self):
        self.assertEqual(self.decision["operator_command"], 'OVC APPROVE CREATION OF     EMPIRICAL_BOUNDARY_PACK AND      EXACT_C2E_RESOURCE_ENVELOPE OBJECTS, THEN CONTINUE G6')
        self.assertEqual(self.decision["decision"], "APPROVE_CREATION_AND_CONTINUE_G6")
        self.assertEqual(self.decision["authority_delta"]["wp6_execution"], "NOT_YET_EFFECTIVE_UNTIL_FRESH_G6_DECISION_MERGED")
        self.assertEqual(self.decision["authority_delta"]["active_boundary_pack"], "NONE")
        self.assertEqual(self.decision["authority_delta"]["validation"], "DENIED")

    def test_empirical_pack_reconstructs_exactly_and_is_inactive(self):
        frozen = freeze_pack(self.pack)
        self.assertEqual(frozen["boundary_pack_id"], 'C2E.BOUNDARY.PACK.22461197d5c711871ba568e850dcbcc1')
        self.assertEqual(frozen["logical_sha256"], '22461197d5c711871ba568e850dcbcc1741da9b5bdc6c2aa41af54a56e145ecd')
        self.assertEqual(self.pack["authority"], "CANDIDATE")
        self.assertFalse(self.pack["active"])
        self.assertFalse(self.pack["canonical"])
        self.assertEqual(self.pack["metadata"]["thresholds"], [])
        self.assertFalse(self.pack["metadata"]["outcome_or_family_tuning"])

    def test_pack_has_exact_full_compatibility_surface(self):
        candidate_types = {row["candidate_type"] for row in self.pack["rules"]}
        self.assertEqual(len(candidate_types), 6)
        self.assertEqual(len(self.pack["compatibility_matrix"]), 15)
        pairs = {tuple(sorted((row["candidate_type_a"],row["candidate_type_b"]))) for row in self.pack["compatibility_matrix"]}
        self.assertEqual(len(pairs), 15)
        self.assertEqual(self.pack["ownership"]["peer_mode"], "SINGLE_OWNER")
        self.assertFalse(self.pack["topology"]["split"])
        self.assertFalse(self.pack["topology"]["merge"])

    def test_threshold_free_predicates_cover_birth_continue_phase_parent_gap_release(self):
        first = frame()
        born = evaluate_boundary_predicates(first)
        self.assertIn("C2E.RULE.JUNE.BASELINE.BIRTH.v1", born["matched_rules"])
        same = evaluate_boundary_predicates(frame(), first)
        self.assertIn("C2E.RULE.JUNE.BASELINE.CONTINUATION.v1", same["matched_rules"])
        phase = evaluate_boundary_predicates(frame(structural_suffix="B"), first)
        self.assertIn("C2E.RULE.JUNE.BASELINE.PHASE_MUTATION.v1", phase["matched_rules"])
        parent = evaluate_boundary_predicates(frame(parent_suffix="B"), first)
        self.assertIn("C2E.RULE.JUNE.BASELINE.RE_PARENT.v1", parent["matched_rules"])
        gap = evaluate_boundary_predicates(frame(segment="SEG.2"), first)
        self.assertIn("C2E.RULE.JUNE.BASELINE.CENSOR_GAP.v1", gap["matched_rules"])
        self.assertIn("C2E.RULE.JUNE.BASELINE.BIRTH.v1", gap["matched_rules"])
        release = evaluate_boundary_predicates(frame(), first, release_end=True)
        self.assertEqual(release["matched_rules"], ["C2E.RULE.JUNE.BASELINE.CENSOR_RELEASE_END.v1"])
        self.assertEqual(release["thresholds_used"], [])

    def test_forbidden_downstream_or_outcome_inputs_fail_closed(self):
        bad = frame()
        bad["outcome"] = "UP"
        with self.assertRaisesRegex(EmpiricalBoundaryRuleError, "PROHIBITED_BOUNDARY_INPUT"):
            evaluate_boundary_predicates(bad)

    def test_exact_resource_envelope_is_bound_and_fail_closed(self):
        limits = self.envelope["limits"]
        self.assertEqual(limits, {"max_wall_clock_seconds":14400,"max_peak_rss_bytes":17179869184,"max_external_output_bytes":10737418240,"worker_count":1})
        self.assertEqual(self.envelope["boundary_pack_binding"]["boundary_pack_id"], 'C2E.BOUNDARY.PACK.22461197d5c711871ba568e850dcbcc1')
        self.assertEqual(self.envelope["boundary_pack_binding"]["logical_sha256"], '22461197d5c711871ba568e850dcbcc1741da9b5bdc6c2aa41af54a56e145ecd')
        self.assertFalse(self.envelope["authority"]["effective_run_authority"])
        self.assertEqual(self.envelope["capacity_semantics"]["on_exceed"], "CAPACITY_EXCEEDED_SAFE_STOP")

    def test_qa_state_and_pointer_preserve_no_activation(self):
        self.assertEqual(self.qa["qa_disposition"], "PASS")
        self.assertEqual(self.state["status"], "APPROVED")
        self.assertEqual(self.state["authority"]["active_boundary_pack"], "NONE")
        self.assertEqual(self.state["authority"]["c2e_activation"], "DENIED")
        self.assertEqual(self.state["authority"]["wp6_execution"], "DENIED_NOT_STARTED")
        self.assertEqual(self.pointer["candidate_boundary_pack"], 'C2E.BOUNDARY.PACK.22461197d5c711871ba568e850dcbcc1')
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
        self.assertIn(self.pointer["wp6_execution"], {"DENIED_NOT_STARTED", "AUTHORIZED_PENDING_MERGE_ASSURANCE", "AUTHORIZED_NOT_STARTED", "BLOCKED_NOT_STARTED"})
        self.assertIn(self.pointer["status"], {"APPROVED", "QA_REVIEW", "BLOCKED"})


if __name__ == "__main__":
    unittest.main()
