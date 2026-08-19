from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from ovc.development.skills.cers.persistent_service import PersistentTimingPolicy
from ovc.development.skills.cers.qualification import (
    derive_timing_freeze,
    run_persistent_qualification,
)


ROOT = Path(__file__).resolve().parents[3]


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class CersPersistentSupervisorWp5Tests(unittest.TestCase):
    def setUp(self):
        self.evidence_path = (
            ROOT
            / "docs/releases/development-skills-v0-3/cers-persistent-supervisor/wp5/"
            "CERS_PS_WP5_OBSERVED_QUALIFICATION_v0_1.json"
        )
        self.evidence = json.loads(self.evidence_path.read_text(encoding="utf-8"))
        self.limits = load(
            "registries/development/skills/cers/CERS_PERSISTENT_OPERATIONAL_LIMITS_v0_1.json"
        )

    def test_observed_evidence_is_pass_without_incident_or_warning(self):
        self.assertEqual(self.evidence["status"], "PASS")
        self.assertEqual(self.evidence["qualification"]["iterations"], 1000)
        self.assertEqual(set(self.evidence["qualification"]["assertions"].values()), {"PASS"})
        self.assertEqual(self.evidence["pilot_capacity_source"]["incidents"], [])
        self.assertEqual(self.evidence["authority_effect"], "NONE_SHADOW_QUALIFICATION_ONLY")

    def test_short_replay_reproves_every_adversarial_assertion(self):
        replay = run_persistent_qualification(iterations=20)
        self.assertEqual(set(replay["assertions"].values()), {"PASS"})
        self.assertEqual(replay["authority_effect"], "NONE_SHADOW_QUALIFICATION_ONLY")

    def test_timing_values_are_exactly_derived_from_observations(self):
        derived = derive_timing_freeze(
            self.evidence["qualification"],
            pilot_duration_seconds=self.evidence["pilot_capacity_source"]["duration_seconds"],
            pilot_heartbeat_sequence=self.evidence["pilot_capacity_source"]["recorded_heartbeat_sequence"],
        )
        self.assertEqual(derived, self.evidence["frozen_timing"])
        for field in (
            "sweep_cadence_seconds",
            "heartbeat_cadence_seconds",
            "liveness_threshold_seconds",
            "reclaim_after_seconds",
            "provider_backoff_seconds",
        ):
            self.assertEqual(derived[field], self.limits["timing"][field])

    def test_frozen_policy_is_runtime_valid_and_bounded(self):
        timing = self.limits["timing"]
        policy = PersistentTimingPolicy(
            status="FROZEN_QUALIFIED",
            sweep_cadence_seconds=timing["sweep_cadence_seconds"],
            heartbeat_cadence_seconds=timing["heartbeat_cadence_seconds"],
            liveness_threshold_seconds=timing["liveness_threshold_seconds"],
            reclaim_after_seconds=timing["reclaim_after_seconds"],
            provider_backoff_seconds=tuple(timing["provider_backoff_seconds"]),
        )
        self.assertTrue(policy.activation_ready)
        self.assertGreaterEqual(policy.reclaim_after_seconds, policy.liveness_threshold_seconds)

    def test_capacity_is_the_exact_prior_pilot_envelope(self):
        pilot = load(
            "docs/releases/development-skills-v0-3/cers-conformance/wp6/"
            "CERS_WP6_LIVE_PILOT_RUN_v0_1.json"
        )
        capacity = self.limits["capacity"]
        self.assertEqual(capacity["worker_concurrency"], pilot["worker_concurrency"])
        self.assertEqual(capacity["max_speculative_depth"], pilot["max_speculative_depth"])
        self.assertEqual(capacity["visible_train_cap"], pilot["visible_train_cap"])
        self.assertTrue(capacity["no_increase_over_proven_pilot"])

    def test_evidence_hash_and_physical_path_are_frozen(self):
        digest = hashlib.sha256(self.evidence_path.read_bytes()).hexdigest()
        self.assertEqual(digest, self.limits["qualification_evidence_sha256"])
        self.assertEqual(
            self.limits["physical_integration"],
            {
                "controller": "DSAI_VIT_PHYSICAL_CONTROLLER",
                "gateway": "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY",
                "parallel_physical_merge": False,
            },
        )

    def test_wp5_advances_only_to_operator_gate_or_completed_activation(self):
        pointer = load("registries/implementation/dsai3v_cers_v0_1/CURRENT_STATE_POINTER.json")
        state = load(pointer["current_state"])
        self.assertEqual(state["plan_id"], "OVC-DSAI3V-CERS-PERSISTENT-SUPERVISOR-ACTIVATION-PLAN-0.1-RATIFIED")

        if pointer["status"] == "COMPLETED":
            self.assertIsNone(pointer["next_packet"])
            self.assertEqual(pointer["decision"], "PASS")
            self.assertEqual(pointer["persistent_run"], "ACTIVATED")
            self.assertEqual(pointer["persistent_general_dispatch"], "ALLOWED_EXACT_ADMITTED_SCOPE_ONLY")
            self.assertEqual(pointer["post_pilot_dispatch_state"], "RUN")
            self.assertEqual(state["decision_authority"], "OPERATOR")
            self.assertIn(
                state["authority_delta"],
                {
                    "PERSISTENT_RUN_FOR_EXACT_ADMITTED_SCOPE_ONLY",
                    "PERSISTENT_UNATTENDED_INVOCATION_ADMISSION_EXPANSION_FOR_EXACT_P2CTI_ASOCSI_GRT2_SCOPE_ONLY",
                },
            )
            self.assertTrue(state["reserved_authority_unchanged"])
        else:
            self.assertIn(pointer["status"], {"GATE_PREPARATION", "GATE_READY"})
            if pointer["status"] == "GATE_PREPARATION":
                self.assertEqual(pointer["next_packet"], "CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION")
            else:
                self.assertIsNone(pointer["next_packet"])
                self.assertEqual(pointer["decision"], "PENDING_OPERATOR")
            self.assertEqual(state["authority_required"], "OPERATOR_REQUIRED")
            self.assertEqual(
                state["persistent_general_dispatch"],
                "DENIED_PENDING_CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION",
            )
            self.assertEqual(state["post_pilot_dispatch_state"], "DISABLE_NEW_DISPATCH")

        self.assertEqual(self.limits["repository_rules"]["merge_capability"], "NONE")


if __name__ == "__main__":
    unittest.main()
