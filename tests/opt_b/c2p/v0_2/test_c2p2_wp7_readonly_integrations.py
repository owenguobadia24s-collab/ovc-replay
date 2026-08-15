from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from ovc.opt_b.c2p_v0_2.assertion import create_object_assertion
from ovc.opt_b.c2p_v0_2.events import build_assertion_genesis_event
from ovc.opt_b.c2p_v0_2.integrations import (
    IntegrationReadError,
    build_c25_reference,
    build_c3_entity_temporal_reference,
    build_console_read_model,
    build_esl_optional_reference,
    build_research_operations_view,
)
from ovc.opt_b.c2p_v0_2.projection import project_assertion_stream


ROOT = Path(__file__).resolve().parents[4]
PACK = json.loads((ROOT / "fixtures/opt_b/c2p/v0_2/packs/C2P_SYNTH_OBJECTPACK_MINIMAL_A_v1.json").read_text(encoding="utf-8"))
FIXTURES = json.loads((ROOT / "fixtures/opt_b/c2p/v0_2/golden/C2P2_WP7_READONLY_INTEGRATION_FIXTURES_v1.json").read_text(encoding="utf-8"))


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def snapshot() -> dict:
    members = [digest(f"wp7-member-{index}") for index in range(3)]
    tracklet = {
        "object_pack_id": PACK["object_pack_id"], "state": "CONFIRMED",
        "member_candidate_ids": members, "first_valid_time": "2026-01-01T00:03:00Z",
        "evaluation_cutoff": "2026-01-01T00:05:00Z", "structural_role_id": "LEVEL",
        "geometry_kind_id": "POINT_REFERENCE",
        "hard_scope": {"instrument": "SYNTH", "side": "BID", "scale": "15M", "partition": "WP7"},
    }
    decision = {
        "object_pack_id": PACK["object_pack_id"], "terminal_decision": "NEW",
        "candidate_id": members[-1], "decision_id": digest("wp7-decision"),
        "first_valid_time": "2026-01-01T00:04:00Z", "evaluation_cutoff": "2026-01-01T00:05:00Z",
    }
    obj = create_object_assertion(tracklet, decision, PACK)
    event = build_assertion_genesis_event(
        obj, PACK, market_effective_start="2026-01-01T00:00:00Z", market_effective_end=None,
        evaluation_cutoff="2026-01-01T00:05:00Z", geometry={"coordinate": "101.000"},
        state_payload={"fixture_structure_key": "wp7"}, source_hashes=[digest("wp7-source")],
    )
    return project_assertion_stream([event])


class C2P2WP7ReadonlyIntegrationTests(unittest.TestCase):
    def test_fixture_catalogue_and_synthetic_firewall(self):
        self.assertEqual([item["id"] for item in FIXTURES["fixtures"]], [f"F{number}" for number in range(30, 37)])
        self.assertEqual(PACK["status"], "SYNTHETIC_ONLY_NONEMPIRICAL")
        self.assertFalse(PACK["activation_eligible"])

    def test_esl_optional_reference_available_and_absent_are_fail_honest(self):
        current = snapshot()
        available = build_esl_optional_reference(current, availability_state="AVAILABLE")
        self.assertEqual(available["object_assertion_reference"]["object_assertion_id"], current["object_assertion_id"])
        self.assertFalse(available["persistence_synthesized"])
        absent = build_esl_optional_reference(None, availability_state="NOT_AVAILABLE", reason_code="C2P_OPTIONAL_NOT_BOUND")
        self.assertIsNone(absent["object_assertion_reference"])
        self.assertTrue(absent["base_structural_occurrence_remains_lawful"])
        with self.assertRaisesRegex(IntegrationReadError, "AVAILABLE_REQUIRES_ASSERTION"):
            build_esl_optional_reference(None, availability_state="AVAILABLE")
        with self.assertRaisesRegex(IntegrationReadError, "ABSENCE_CANNOT_CARRY_ASSERTION"):
            build_esl_optional_reference(current, availability_state="NOT_AVAILABLE")

    def test_c25_requires_declared_dependency_and_never_grants_identity_authority(self):
        current = snapshot()
        reference = build_c25_reference(current, event_definition_id="C25.SYNTH.EVENT.v1", dependency_manifest_id="deps-1", dependency_declared=True)
        self.assertEqual(reference["reference"]["object_assertion_id"], current["object_assertion_id"])
        self.assertIsNone(reference["tracklet_reference"])
        self.assertEqual(reference["identity_owner"], "C2P")
        self.assertFalse(reference["auto_retarget"])
        self.assertFalse(reference["persistence_inference"])
        with self.assertRaisesRegex(IntegrationReadError, "DEPENDENCY_NOT_DECLARED"):
            build_c25_reference(current, event_definition_id="C25.SYNTH.EVENT.v1", dependency_manifest_id="deps-1", dependency_declared=False)

    def test_c3_reference_preserves_effective_and_knowledge_chronology_without_repair(self):
        current = snapshot()
        reference = build_c3_entity_temporal_reference(current)
        self.assertEqual(reference["entity_ref"]["logical_id"], current["object_assertion_id"])
        self.assertEqual(reference["knowledge_chronology"]["first_valid_time"], current["first_valid_time"])
        self.assertFalse(reference["persistence_inference"])
        self.assertFalse(reference["identity_repair"])
        self.assertFalse(reference["auto_retarget"])

    def test_research_operations_and_console_are_read_only_source_bound_views(self):
        current = snapshot()
        research = build_research_operations_view(current)
        console = build_console_read_model(current)
        self.assertEqual(research["record_class"], "DERIVED_READ_ONLY_EVIDENCE_VIEW")
        self.assertFalse(research["durable_research_write_performed"])
        self.assertTrue(research["source_owned"])
        self.assertTrue(console["read_only"])
        self.assertEqual(console["write_capabilities"], [])
        self.assertEqual(console["frontier"]["hash"], current["event_frontier_hash"])
        self.assertEqual(console["state_axes"]["lifecycle"], current["lifecycle_state"])

    def test_non_snapshot_or_unavailable_c25_reference_fails_closed(self):
        with self.assertRaisesRegex(IntegrationReadError, "SNAPSHOT_SCHEMA_INVALID"):
            build_c3_entity_temporal_reference({"schema": "c2p-tracklet/v0.2"})
        current = snapshot()
        current["evaluation_state"] = "NOT_EVALUABLE"
        with self.assertRaisesRegex(IntegrationReadError, "REFERENCE_NOT_AVAILABLE"):
            build_c25_reference(current, event_definition_id="C25.SYNTH.EVENT.v1", dependency_manifest_id="deps-1", dependency_declared=True)


if __name__ == "__main__":
    unittest.main()
