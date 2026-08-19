from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GATE_PATH = (
    ROOT
    / "docs/releases/development-skills-v0-3/cers-persistent-supervisor/activation/"
    "CERS_G_PERSISTENT_SUPERVISOR_ACTIVATION_GATE_PACKET_v0_1.json"
)
QA_PATH = (
    ROOT
    / "docs/releases/development-skills-v0-3/cers-persistent-supervisor/activation/"
    "CERS_G_PERSISTENT_SUPERVISOR_ACTIVATION_GATE_READY_QA_v0_1.json"
)
TARGET_QUALIFICATION_PATH = (
    ROOT
    / "docs/releases/development-skills-v0-3/cers-persistent-supervisor/wp5/"
    "CERS_PS_WP5_TARGET_RUNTIME_QUALIFICATION_v0_1.json"
)


def load(relative: str | Path):
    path = relative if isinstance(relative, Path) else ROOT / relative
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    payload = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()


class CersPersistentSupervisorActivationGateReadyTests(unittest.TestCase):
    def setUp(self):
        self.gate = load(GATE_PATH)
        self.qa = load(QA_PATH)
        self.target = load(TARGET_QUALIFICATION_PATH)
        self.pointer = load(
            "registries/implementation/dsai3v_cers_v0_1/CURRENT_STATE_POINTER.json"
        )
        self.state = load(self.pointer["current_state"])

    def test_gate_is_ready_but_operator_decision_and_run_are_absent(self):
        self.assertEqual(self.gate["status"], "GATE_READY")
        self.assertEqual(self.gate["decision"], "PENDING_OPERATOR")
        self.assertEqual(self.gate["authority_required"], "OPERATOR_REQUIRED")
        self.assertEqual(self.gate["persistent_run"], "NOT_ACTIVATED")
        self.assertEqual(
            self.gate["terminal_instruction"],
            "STOP_WITHOUT_RUN_AND_AWAIT_OPERATOR_DECISION",
        )
        self.assertFalse(
            self.gate["exact_proposed_activation_delta"]["automatic_activation_from_this_packet"]
        )

    def test_target_executor_runtime_family_is_exactly_qualified(self):
        self.assertEqual(self.target["status"], "PASS")
        self.assertEqual(self.target["executor_environment_binding"], "windows-local-python311")
        self.assertEqual(self.target["environment"]["python_family"], "3.11")
        self.assertEqual(self.target["environment"]["python"], "3.11.9")
        self.assertEqual(self.target["qualification"]["iterations"], 1000)
        self.assertEqual(set(self.target["qualification"]["assertions"].values()), {"PASS"})
        self.assertEqual(self.target["qualification"]["blocking_warnings"], [])
        self.assertEqual(self.target["qualification"]["incidents"], [])
        self.assertEqual(
            sha256(TARGET_QUALIFICATION_PATH),
            self.gate["runtime"]["target_runtime_qualification_sha256"],
        )

    def test_target_runtime_confirms_without_changing_frozen_values(self):
        limits = load(
            "registries/development/skills/cers/CERS_PERSISTENT_OPERATIONAL_LIMITS_v0_1.json"
        )
        expected_capacity = {k: limits["capacity"][k] for k in (
            "worker_concurrency", "max_speculative_depth", "visible_train_cap"
        )}
        expected_timing = {k: limits["timing"][k] for k in (
            "sweep_cadence_seconds", "heartbeat_cadence_seconds",
            "liveness_threshold_seconds", "reclaim_after_seconds",
            "provider_backoff_seconds",
        )}
        self.assertEqual(
            {k: self.target["frozen_capacity_confirmed"][k] for k in expected_capacity},
            expected_capacity,
        )
        self.assertEqual(
            {k: self.target["frozen_timing_confirmed"][k] for k in expected_timing},
            expected_timing,
        )
        self.assertFalse(
            self.target["frozen_timing_confirmed"]["changed_by_target_runtime_qualification"]
        )

    def test_runtime_and_registry_git_blobs_are_exact(self):
        artifact_records = self.gate["runtime"]["artifacts"] + [
            {
                "path": self.gate["admission"]["registry"],
                "git_blob": self.gate["admission"]["registry_git_blob"],
            },
            {
                "path": self.gate["packet_executor"]["binding_record"],
                "git_blob": self.gate["packet_executor"]["binding_git_blob"],
            },
            {
                "path": self.gate["actions_and_side_effects"]["registry"],
                "git_blob": self.gate["actions_and_side_effects"]["registry_git_blob"],
            },
        ]
        for record in artifact_records:
            self.assertEqual(git_blob(ROOT / record["path"]), record["git_blob"])

    def test_admission_is_explicit_inactive_and_future_safe(self):
        admission = self.gate["admission"]
        self.assertEqual(admission["status"], "INACTIVE_PREACTIVATION")
        self.assertEqual(admission["unknown_or_absent_programme"], "DENY")
        self.assertFalse(admission["future_programme_auto_admission"])
        self.assertEqual(len(admission["admitted_set"]), 1)
        self.assertEqual(
            admission["admitted_set"][0]["canonical_sha256"],
            "48c43fed5c6c5a5797701f401c73025acbd7930961bf281b296473436ba92287",
        )
        self.assertEqual(len(self.gate["exclusions"]), 5)

    def test_repository_and_physical_paths_cannot_merge_or_write_main(self):
        rules = self.gate["repository_ref_and_write_domain_rules"]
        physical = self.gate["physical_integration"]
        self.assertFalse(rules["direct_main_mutation"])
        self.assertEqual(rules["main_write_capability"], "NONE")
        self.assertEqual(rules["merge_capability"], "NONE")
        self.assertFalse(rules["parallel_physical_merge"])
        self.assertFalse(rules["force_push"])
        self.assertFalse(rules["history_rewrite"])
        self.assertEqual(physical["controller"], "DSAI_VIT_PHYSICAL_CONTROLLER")
        self.assertEqual(physical["gateway"], "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY")
        self.assertEqual(physical["final_integration_lease_count"], 1)
        self.assertFalse(physical["CERS_can_physically_integrate_or_merge"])

    def test_all_g0_g5_assurance_and_referenced_evidence_are_present(self):
        assurance = self.gate["g0_g5_assurance"]
        self.assertEqual([entry["gate"] for entry in assurance], [
            "CERS-PS-G0", "CERS-PS-G1", "CERS-PS-G2",
            "CERS-PS-G3", "CERS-PS-G4", "CERS-PS-G5",
        ])
        self.assertEqual({entry["result"] for entry in assurance}, {"PASS"})
        evidence = self.gate["qa_and_adversarial_evidence"]
        for relative in evidence["wp0_wp5_qa_packets"] + evidence["wp0_wp5_decisions"]:
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_gate_qa_is_content_addressed_and_has_no_blocker(self):
        self.assertEqual(sha256(GATE_PATH), self.qa["gate_packet_sha256"])
        self.assertEqual(self.qa["status"], "PASS_GATE_READY")
        self.assertEqual(set(self.qa["checks"].values()), {"PASS"})
        self.assertEqual(self.qa["blockers"], [])
        self.assertEqual(self.qa["incidents"], [])

    def test_pointer_and_state_preserve_denied_dispatch_at_gate_ready(self):
        for record in (self.gate["current_effective_authority"], self.pointer, self.state):
            self.assertEqual(
                record["persistent_general_dispatch"],
                "DENIED_PENDING_CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION",
            )
            self.assertEqual(record["post_pilot_dispatch_state"], "DISABLE_NEW_DISPATCH")
        self.assertEqual(self.pointer["status"], "GATE_READY")
        self.assertIsNone(self.pointer["next_packet"])
        self.assertEqual(self.state["decision"], "PENDING_OPERATOR")
        self.assertEqual(self.state["activation_gate"]["authority_effect"], "NONE_GATE_PREPARATION_ONLY")

    def test_reserved_authority_is_explicitly_unchanged(self):
        unchanged = self.gate["exact_proposed_activation_delta"]["does_not_change"]
        joined = " ".join(unchanged)
        for reserved in (
            "Programme authority", "Future programme admission", "Direct-main",
            "ACTIVE_DISCOVERY", "Scientific", "publication", "Validation",
            "risk", "trading", "market-execution", "Irreversible",
        ):
            self.assertIn(reserved, joined)
        self.assertTrue(self.state["reserved_authority_unchanged"])


if __name__ == "__main__":
    unittest.main()
