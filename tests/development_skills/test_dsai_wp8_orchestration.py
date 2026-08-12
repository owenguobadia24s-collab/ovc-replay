from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.development.skills.orchestration import (
    build_capability_execution_graph,
    build_continuation_record,
    build_packet_eligibility_record,
    build_packet_graph_snapshot,
    build_remediation_cycle_record,
    build_run_intent,
    build_scope_resolution,
    evaluate_side_effect_barrier,
    orch0_shadow,
    orch1_assisted_plan,
)
from ovc.development.skills.release import build_skill_release_bundle


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/development_skills/wp8_orch0_cases_v0_1.json"
CANDIDATES = ROOT / "registries/development/skills/orchestration_candidates_v0_1.json"
BASELINE = "a69bf6c1c7a2febcaf5db71eddbf1ac43083ea3a"
ENVIRONMENT = "windows-local-python311"
TRUSTED = {
    "PACKET_PREFLIGHT": "OVC-SKILL-001@0.1.0+sha256:6609c3cffb8be1b81da4870e6d6c752057c7deed4e35f7d5eabaaca5e0f440f7",
    "AUTHORITY_RESOLUTION": "OVC-SKILL-002@0.1.0+sha256:6d56ba0c93e467a6c07c359eb8167d3fc6fe70ec43b788038ba1d03059fb55f9",
    "SCOPE_CLASSIFICATION": "OVC-SKILL-003@0.1.0+sha256:1c0fb033ef0bbebba84fca0bb749b5551d70f61f7ae3325928bc617fcefb8ce7",
    "PREREQUISITE_RESOLUTION": "OVC-SKILL-004@0.1.0+sha256:dd2929f4768037e7c9ae34b525614c753edf5ed68394915c4d0f0b2ef1356859",
    "TEST_PLAN": "OVC-SKILL-020@0.1.0+sha256:d87a5ac2fd9547d0e1a7869d8ec52ef59c6ebb4f746be549ad295859db3ae1e7",
    "QA_EVALUATION": "OVC-SKILL-022@0.1.0+sha256:566f63d4c31c4666d36ff432235ff70c69a82e0eff26790e81b851e70fc1bb6e",
    "EVIDENCE_AUDIT": "OVC-SKILL-023@0.1.0+sha256:f1893af4791c4c3fb7c91357cfd363c879e7695080dec2e31c93102414fbbfbe",
    "GATE_EVALUATION": "OVC-SKILL-024@0.1.0+sha256:be6b62b8a85426563fcb389a944ae1764473bf550477b8492a98b7dab755a831",
}


class DSAIWP8OrchestrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.candidate = json.loads(CANDIDATES.read_text(encoding="utf-8"))["entries"][0]

    def _state(self):
        return {
            "programme_id": "OVC-DSAI-v0.1",
            "current_packet": "DSAI-WP7",
            "next_packet": "DSAI-WP8",
        }

    def _graph(self, missing_prerequisite=False):
        prereqs = ["DSAI-G7"] if not missing_prerequisite else ["DSAI-G7", "NONEXISTENT"]
        return build_packet_graph_snapshot(
            programme_id="OVC-DSAI-v0.1",
            baseline_main=BASELINE,
            packets=[{
                "packet_id": "DSAI-WP8",
                "prerequisites": prereqs,
                "required_capabilities": list(TRUSTED),
                "gate_class": "AUTO_EXECUTABLE",
                "authority_delta": "NONE",
                "packet_class": "IMPLEMENTATION",
            }],
        )

    def _records(self, *, missing_prerequisite=False, missing_capability=False):
        graph = self._graph(missing_prerequisite=missing_prerequisite)
        eligibility = build_packet_eligibility_record(
            packet_id="DSAI-WP8",
            packet_graph=graph,
            completed_prerequisites=["DSAI-G7"],
            authority_prerequisites=["G7_TRUSTED_CONTROL_SET"],
            satisfied_authority=["G7_TRUSTED_CONTROL_SET"],
        )
        resolution = dict(TRUSTED)
        if missing_capability:
            resolution.pop("GATE_EVALUATION")
        capability_graph = build_capability_execution_graph(
            packet_id="DSAI-WP8", required_capabilities=list(TRUSTED), resolution=resolution
        )
        return graph, eligibility, capability_graph

    def _run(self, case):
        if case.get("driver") == "ORCH1":
            return orch1_assisted_plan(
                packet_class=case["packet_class"],
                enabled_packet_classes=["LOW_RISK_IMPLEMENTATION"],
                g8c_authority_effective=case["g8c_authority_effective"],
            )
        graph, eligibility, capability_graph = self._records(
            missing_prerequisite=case.get("missing_prerequisite", False),
            missing_capability=case.get("missing_capability", False),
        )
        intent = build_run_intent(
            command=case["command"],
            scope={"programme_id": "OVC-DSAI-v0.1", "packet_ids": ["DSAI-WP8"]},
            continuation_record_id="WP8.CONTINUE.001" if case["command"] == "CONTINUE" else None,
        )
        continuation = None
        if case.get("continuation_source") == "DURABLE_REPOSITORY_EVIDENCE":
            continuation = build_continuation_record(
                programme_id="OVC-DSAI-v0.1",
                run_id="HISTORICAL.WP8",
                current_packet="DSAI-WP8",
                next_action="RESUME_DSAI_WP8",
                baseline_main=BASELINE,
                evidence_refs=["registries/implementation/dsai/OVC_DSAI_STATE_v0_17.json"],
            )
        return orch0_shadow(
            run_intent=intent,
            programme_state=self._state(),
            packet_graph=graph,
            packet_eligibility=eligibility,
            capability_graph=capability_graph,
            baseline_main=BASELINE,
            current_main=case.get("current_main", BASELINE),
            environment_id=ENVIRONMENT,
            next_gate_class=case.get("gate_class", "AUTO_EXECUTABLE"),
            next_authority_delta=case.get("authority_delta", "NONE"),
            continuation_record=continuation,
        )

    def test_all_frozen_fixture_cases_match_expected_disposition(self):
        for case in self.fixture["cases"]:
            with self.subTest(case_id=case["case_id"]):
                result = self._run(case)
                self.assertEqual(result["status"], case["expected_status"])
                expected_reason = case.get("expected_reason")
                if expected_reason:
                    reasons = result.get("reason_codes", [])
                    reasons += result.get("stop_record", {}).get("reason_codes", [])
                    reasons += result.get("barrier_record", {}).get("reason_codes", [])
                    self.assertIn(expected_reason, reasons)
                if case.get("automatic_merge") is False:
                    self.assertFalse(result["automatic_merge"])

    def test_orch0_never_writes_or_merges(self):
        for case in self.fixture["cases"]:
            if case.get("driver") == "ORCH1":
                continue
            result = self._run(case)
            self.assertEqual(result.get("writes_performed"), [])
            self.assertFalse(result.get("merge_requested"))
            self.assertFalse(result.get("merge_performed"))
            self.assertEqual(result.get("authority_effect"), "NONE")

    def test_run_intent_and_scope_are_deterministic_and_fail_closed(self):
        intent1 = build_run_intent(command="run", scope={"programme_id": "OVC-DSAI-v0.1", "packet_ids": ["DSAI-WP8"]})
        intent2 = build_run_intent(command="RUN", scope={"programme_id": "OVC-DSAI-v0.1", "packet_ids": ["DSAI-WP8"]})
        self.assertEqual(intent1["record_id"], intent2["record_id"])
        mismatch = build_scope_resolution(run_intent=intent1, programme_state={"programme_id": "OTHER"})
        self.assertEqual(mismatch["status"], "BLOCKED")
        self.assertIn("SCOPE_PROGRAMME_MISMATCH", mismatch["reason_codes"])
        with self.assertRaises(ValueError):
            build_run_intent(command="APPROVE", scope={"programme_id": "OVC-DSAI-v0.1"})

    def test_main_head_churn_revalidates_before_side_effect_barriers(self):
        for barrier in ("B1_MUTATION", "B3_INTEGRATION"):
            record = evaluate_side_effect_barrier(
                barrier=barrier, baseline_main=BASELINE, current_main="new-main"
            )
            self.assertEqual(record["status"], "REVALIDATE_REQUIRED")
            self.assertIn("MAIN_HEAD_CHURN", record["reason_codes"])
        remote = evaluate_side_effect_barrier(
            barrier="B2_REMOTE_WRITE", baseline_main=BASELINE, current_main=BASELINE, remote_write_authorized=False
        )
        self.assertEqual(remote["status"], "BLOCKED")

    def test_operator_authority_transition_always_stops_in_shadow(self):
        record = evaluate_side_effect_barrier(
            barrier="B4_AUTHORITY_TRANSITION",
            baseline_main=BASELINE,
            current_main=BASELINE,
            gate_class="OPERATOR_REQUIRED",
            authority_delta="TRUSTED_PROMOTION",
        )
        self.assertEqual(record["status"], "NEEDS_AUTHORITY")
        self.assertIn("OPERATOR_REQUIRED_RESERVED_DELTA", record["reason_codes"])

    def test_remediation_cannot_weaken_frozen_boundaries(self):
        ok = build_remediation_cycle_record(
            run_id="R1", cycle=1, failure_class="CORRECTABLE_FAILURE", action="REGENERATE_FIXTURE", status="PASS"
        )
        self.assertEqual(ok["authority_effect"], "NONE")
        for forbidden in ("CONTRACT_WEAKEN", "AUTHORITY_EXPAND", "TEST_WEAKEN", "EVIDENCE_DELETE"):
            with self.assertRaises(ValueError):
                build_remediation_cycle_record(run_id="R1", cycle=1, failure_class="X", action=forbidden, status="PASS")

    def test_packet_executor_release_identity_is_exact_and_still_non_trusted(self):
        fields = {
            "capability_ids": ["PACKET_EXECUTION"],
            "implementation_entrypoint": "ovc.development.skills.orchestration:orch0_shadow",
            "input_contract_id": "DSAI.WP8.PACKET_EXECUTION.INPUT.v1",
            "output_contract_id": "ovc-dsai-orch0-shadow-result/v1",
            "execution_mode": "ORCH_0_SHADOW_ONLY",
            "tool_profile_id": "WP8-ORCH0-NO-WRITE",
            "write_permission": "DENY",
            "merge_permission": "DENY",
            "determinism": "DETERMINISTIC_GIVEN_SNAPSHOT",
            "failure_policy": "FAIL_CLOSED",
            "knowledge_pack_id": "OVC-KP-DSAI-ORCHESTRATION-v0.1",
            "knowledge_pack_hash": "4d1163e1dd678a723d812389ee3b52edbe2480e76e25e672e3c79fb9a568401b",
        }
        release = build_skill_release_bundle(
            skill_id="OVC-SKILL-030",
            logical_name="ovc-packet-executor",
            semantic_version="0.1.0",
            fields=fields,
            field_classification=None,
            source_refs=["OVC-DSA-DESIGN-SPEC-0.1-REVISED-1-RATIFIED#9-10", "OVC-DSAI-IMPLEMENTATION-PLAN-0.2#15"],
        )
        self.assertEqual(release["release_id"], self.candidate["release_id"])
        self.assertEqual(self.candidate["maturity"], "QUALIFIED")
        self.assertEqual(self.candidate["write_permission"], "DENY")
        self.assertEqual(self.candidate["merge_permission"], "DENY")


if __name__ == "__main__":
    unittest.main()
