from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.research_operations.prospective_source.authority import (
    AuthoritySnapshot,
    authority_from_mapping,
    load_repository_authority_snapshot,
)


ROOT = Path(__file__).resolve().parents[3]
ACTIVATION_PATH = (
    ROOT
    / "registries"
    / "research_operations"
    / "prospective_source"
    / "RPS_G4_ACTIVE_AUTHORITY_v0_1.json"
)
GATE_STATE_PATH = (
    ROOT
    / "registries"
    / "research_operations"
    / "prospective_source"
    / "RPS_G4_GATE_STATE_v0_1.json"
)
WP4_STATE_PATH = (
    ROOT
    / "registries"
    / "research_operations"
    / "prospective_source"
    / "RPS_WP4_COMMAND_STATE_v0_1.json"
)
RPS_REGISTRY_PATH = (
    ROOT
    / "registries"
    / "research_operations"
    / "prospective_source"
    / "REAL_PROSPECTIVE_SOURCE_IMPLEMENTATION_REGISTRY_v0_1.yaml"
)
PD_REGISTRY_PATH = (
    ROOT
    / "registries"
    / "research_operations"
    / "pattern_discovery"
    / "PATTERN_DISCOVERY_IMPLEMENTATION_REGISTRY_v0_3.yaml"
)
EVIDENCE_REGISTRY_PATH = ROOT / "registries" / "research" / "C2_PROSPECTIVE_EVIDENCE_REGISTRY.yaml"


class RpsG4ActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.activation = json.loads(ACTIVATION_PATH.read_text(encoding="utf-8"))
        cls.gate_state = json.loads(GATE_STATE_PATH.read_text(encoding="utf-8"))
        cls.wp4_state = json.loads(WP4_STATE_PATH.read_text(encoding="utf-8"))
        cls.rps_registry = RPS_REGISTRY_PATH.read_text(encoding="utf-8")
        cls.pd_registry = PD_REGISTRY_PATH.read_text(encoding="utf-8")
        cls.evidence_registry = EVIDENCE_REGISTRY_PATH.read_text(encoding="utf-8")

    def test_exact_approved_bindings_are_active(self) -> None:
        expected = {
            "source_binding_id": "RPS.BINDING.32fb3003efa072916c11e907",
            "signing_binding_id": "RPS.SIGNING.50092c28981fef08f53a6cb5",
            "operator_id": "OVC.OPERATOR.PRIMARY.LOCAL.V1",
            "active_model_release_id": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1",
            "research_line_id": "RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1",
        }
        for key, value in expected.items():
            self.assertEqual(self.activation[key], value)
        self.assertEqual(
            self.activation["decision_merge_commit"],
            "b52fa297faa1b593fe9aaaf5d36a1b4e39a50eac",
        )
        self.assertEqual(self.activation["status"], "ACTIVE_RESEARCH_TRIAGE_APPROVED")
        self.assertEqual(
            self.activation["activation_scope"],
            "ONE_BOUNDED_PD_WP5_FIRST_LIVE_PROSPECTIVE_OPERATION",
        )

    def test_repository_authority_enables_triage_but_not_unresolved_append(self) -> None:
        snapshot = load_repository_authority_snapshot(ROOT)
        self.assertTrue(snapshot.triage_enabled)
        self.assertFalse(snapshot.live_append_enabled)
        self.assertEqual(snapshot.authority_label, "ACTIVE_RESEARCH_TRIAGE")
        self.assertFalse(snapshot.candidate_source_resolved)
        self.assertEqual(snapshot.evidence_sequence, 0)

    def test_only_resolved_live_candidate_can_enable_append(self) -> None:
        resolved = AuthoritySnapshot(
            **{
                **load_repository_authority_snapshot(ROOT).__dict__,
                "candidate_source_resolved": True,
            }
        )
        self.assertTrue(resolved.triage_enabled)
        self.assertTrue(resolved.live_append_enabled)
        self.assertEqual(
            resolved.authority_label,
            "ACTIVE_RESEARCH_TRIAGE_APPEND_ENABLED",
        )

        replay = AuthoritySnapshot(
            **{
                **resolved.__dict__,
                "operation_mode": "TIME_GATED_REPLAY",
            }
        )
        self.assertFalse(replay.triage_enabled)
        self.assertFalse(replay.live_append_enabled)
        self.assertEqual(replay.authority_label, "TIME_GATED_REPLAY_NON_EVIDENTIARY")

    def test_any_missing_global_binding_fails_closed(self) -> None:
        base = dict(self.activation)
        for field in (
            "rps_g4_approved",
            "operator_key_bound",
            "bridge_healthy",
            "write_authority",
        ):
            with self.subTest(field=field):
                value = dict(base)
                value[field] = False
                self.assertFalse(authority_from_mapping(value).triage_enabled)
        for field in ("source_binding_id", "signing_binding_id", "operator_id"):
            with self.subTest(field=field):
                value = dict(base)
                value[field] = None
                self.assertFalse(authority_from_mapping(value).triage_enabled)

    def test_broader_authorities_remain_denied(self) -> None:
        expected = {
            "time_gated_replay_backfill": "DENIED",
            "automatic_evidence_creation": False,
            "agent_write_authority": "NONE",
            "active_novelty_ranking": "NONE",
            "semantic_promotion": "NONE",
            "selector_mutation": "DENIED",
            "release_mutation": "DENIED",
            "r2_publication": "DENIED",
            "validation_consumption": "DENIED",
            "probability_authority": "NONE",
            "risk_authority": "NONE",
            "exposure_authority": "NONE",
            "trading_authority": "NONE",
            "execution_authority": "NONE",
        }
        for key, value in expected.items():
            self.assertEqual(self.activation[key], value)
        self.assertEqual(self.activation["first_operation_limit"], 1)
        self.assertEqual(self.activation["next_gate"], "PD-G5")

    def test_gate_and_wp4_states_close_at_pd_wp5(self) -> None:
        self.assertEqual(self.gate_state["gate_status"], "APPROVED")
        self.assertEqual(self.gate_state["packet_status"], "COMPLETED")
        self.assertTrue(self.gate_state["active_research_triage"])
        self.assertFalse(self.gate_state["live_append_enabled"])
        self.assertEqual(self.gate_state["next_packet"], "PD-WP5")
        self.assertEqual(self.gate_state["next_gate"], "PD-G5")
        self.assertEqual(self.wp4_state["packet_status"], "COMPLETED")
        self.assertTrue(self.wp4_state["active_research_triage"])
        self.assertFalse(self.wp4_state["live_append_enabled"])
        self.assertEqual(self.wp4_state["next_packet"], "PD-WP5")

    def test_all_programme_registries_reference_exact_active_state(self) -> None:
        required = (
            "RPS.BINDING.32fb3003efa072916c11e907",
            "RPS.SIGNING.50092c28981fef08f53a6cb5",
            "OVC.OPERATOR.PRIMARY.LOCAL.V1",
            "READY_AWAITING_NEW_LIVE_PROSPECTIVE_CANDIDATE",
            "PD-G5",
        )
        for registry in (
            self.rps_registry,
            self.pd_registry,
            self.evidence_registry,
        ):
            for value in required:
                self.assertIn(value, registry)
        self.assertIn("status: READY", self.rps_registry)
        self.assertIn("status: READY", self.pd_registry)
        self.assertIn("replay_backfill: DENIED", self.evidence_registry)

    def test_no_private_key_or_live_payload_is_embedded(self) -> None:
        combined = "\n".join(
            (
                ACTIVATION_PATH.read_text(encoding="utf-8"),
                self.rps_registry,
                self.pd_registry,
                self.evidence_registry,
            )
        )
        self.assertNotIn("BEGIN OPENSSH PRIVATE KEY", combined)
        self.assertNotIn("M1_BID.csv", combined)
        self.assertNotIn("c2_states/", combined)
        self.assertNotIn("C:\\Users\\", combined)


if __name__ == "__main__":
    unittest.main()
