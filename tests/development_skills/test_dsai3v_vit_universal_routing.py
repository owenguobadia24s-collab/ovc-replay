from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ovc.development.identity import canonical_sha256
from ovc.development.skills.siq_core import WAIT, build_queue_state, queue_head
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_routing import (
    REGISTERED_EXCEPTION,
    UNLAWFUL,
    VIT_MANDATORY,
    classify_main_movement,
    validate_vit_lineage_record,
)
from tools.ci.vit_routing_preflight import check_pull_request_event

ROOT = Path(__file__).resolve().parents[2]
REGISTER = ROOT / "registries/development/skills/VIT_ROUTING_COVERAGE_REGISTER_v0_1.json"
AUDIT = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/universal-routing/DSAI3V_VIT_ROUTING_AUDIT_v0_1.json"


def lineage_record(programme: str = "PROGRAMME", packet: str = "PACKET") -> dict:
    authority_manifest_id = "2" * 64
    dependency_frontier_id = "3" * 64
    pip = {
        "schema_version": "packet-integration-payload/v0.1",
        "programme_id": programme,
        "packet_id": packet,
        "logical_changes": [{"path": "records/example.json", "operation": "ADD", "content_sha256": "1" * 64}],
        "authority_manifest_id": authority_manifest_id,
        "dependency_frontier_id": dependency_frontier_id,
        "completion_transition": {"status": "COMPLETED"},
    }
    pip_id = canonical_sha256(pip)
    predecessor = {"tree_sha": "a" * 40, "profile": "git-tree-v1"}
    result = {"tree_sha": "b" * 40, "profile": "git-tree-v1"}
    generation = {
        "train_generation_id": "TRAIN-1",
        "ordinal": 1,
        "predecessor_tree": predecessor,
        "payload_id": pip_id,
        "result_tree": result,
        "authority_manifest_id": authority_manifest_id,
        "dependency_frontier_id": dependency_frontier_id,
    }
    generation_id = canonical_sha256(generation)
    placement = {
        "payload_id": pip_id,
        "predecessor_tree": predecessor["tree_sha"],
        "result_tree": result["tree_sha"],
        "apply_profile": "REFERENCE_APPLY",
        "ordinal": 1,
        "dependency_frontier_id": dependency_frontier_id,
        "authority_manifest_id": authority_manifest_id,
    }
    placement_id = canonical_sha256(placement)
    return {
        "schema": "ovc-vit-routing-lineage/v1",
        "status": "ADMITTED",
        "programme_id": programme,
        "packet_id": packet,
        "route_class": "VIT_MANDATORY",
        "pip": pip,
        "pip_id": pip_id,
        "generation": generation,
        "generation_id": generation_id,
        "placement": placement,
        "placement_id": placement_id,
        "routing": {
            "controller": "DSAI_VIT_PHYSICAL_CONTROLLER",
            "physical_gateway": "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY",
            "route_class": "VIT_MANDATORY",
        },
    }


class Dsai3vUniversalRoutingTests(unittest.TestCase):
    def test_coverage_register_classifies_every_actuator(self) -> None:
        record = json.loads(REGISTER.read_text(encoding="utf-8"))
        self.assertEqual(record["unregistered_bypass_policy"], "FAIL_CLOSED")
        rows = record["actuators"]
        ids = [row["actuator_id"] for row in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(row["route_class"] in {VIT_MANDATORY, REGISTERED_EXCEPTION, UNLAWFUL} for row in rows))
        route = {row["actuator_id"]: row["route_class"] for row in rows}
        self.assertEqual(route["SIQ_QUEUE_CANDIDATE_ADMISSION"], VIT_MANDATORY)
        self.assertEqual(route["OPERATOR_REQUIRED_GATE_PACKET"], VIT_MANDATORY)
        self.assertEqual(route["LEGACY_FRESH_MAIN_RECONCILE"], UNLAWFUL)

    def test_lineage_is_content_addressed_and_tamper_fails(self) -> None:
        record = lineage_record()
        validated = validate_vit_lineage_record(record)
        self.assertEqual(validated.pip_id, record["pip_id"])
        self.assertEqual(validated.generation_id, record["generation_id"])
        self.assertEqual(validated.placement_id, record["placement_id"])
        tampered = json.loads(json.dumps(record))
        tampered["generation"]["ordinal"] = 2
        with self.assertRaises(VitContractError):
            validate_vit_lineage_record(tampered)

    def test_unrelated_main_advance_is_zero_payload_rebuild(self) -> None:
        pip = "d" * 64
        result = classify_main_movement(
            previous_pip_id=pip,
            current_pip_id=pip,
            dependency_frontier_changed=False,
            authority_changed=False,
            packet_local_defect_changed_payload=False,
        )
        self.assertEqual(result["disposition"], "PLACEMENT_RECOMPUTE_ONLY")
        self.assertFalse(result["payload_rebuild_required"])
        self.assertTrue(result["assurance_renewal_required"])

    def test_identity_bearing_packet_defect_requires_payload_rebuild(self) -> None:
        result = classify_main_movement(
            previous_pip_id="d" * 64,
            current_pip_id="e" * 64,
            dependency_frontier_changed=False,
            authority_changed=False,
            packet_local_defect_changed_payload=True,
        )
        self.assertEqual(result["disposition"], "PAYLOAD_REBUILD_REQUIRED")
        self.assertTrue(result["payload_rebuild_required"])

    def test_historical_cases_separate_bypass_from_real_payload_change(self) -> None:
        audit = json.loads(AUDIT.read_text(encoding="utf-8"))
        cases = {row["case_id"]: row for row in audit["stale_main_case_reproduction"]}
        self.assertEqual(cases["PATH2-944-945"]["classification"], "VIT_BYPASS")
        self.assertFalse(cases["PATH2-944-945"]["payload_rebuild_required"])
        self.assertEqual(cases["C2P2-946-948"]["classification"], "VIT_BYPASS")
        self.assertEqual(cases["C2P2-948-951"]["classification"], "LEGITIMATE_PAYLOAD_REBUILD")
        self.assertTrue(cases["C2P2-948-951"]["payload_rebuild_required"])
        self.assertEqual(cases["RCCR-949-950"]["classification"], "VIT_BYPASS")
        self.assertFalse(cases["RCCR-949-950"]["operator_required_is_exception"])

    def test_siq_candidate_without_lineage_fails_closed(self) -> None:
        candidate = {
            "packet_id": "DIRECT",
            "plan_id": "PLAN",
            "candidate_head_sha": "a" * 40,
            "baseline_main_sha": "b" * 40,
            "ready_sequence": 1,
            "implementation_complete": True,
            "qa_status": "PASS",
            "authority_delta": "NONE",
            "gate_class": "AUTO_EXECUTABLE",
            "preliminary_assurance_pass": True,
            "rollback_defined": True,
            "dependency_footprint_pinned": True,
        }
        state = build_queue_state([candidate])
        self.assertEqual(state.candidates[0].queue_state, WAIT)
        self.assertIn("VIT_LINEAGE_REQUIRED", state.candidates[0].reason_codes)
        self.assertIsNone(queue_head(state))

    def test_pr_preflight_accepts_valid_lineage_and_rejects_missing(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            register_path = root / "registries/development/skills/VIT_ROUTING_COVERAGE_REGISTER_v0_1.json"
            register_path.parent.mkdir(parents=True)
            register_path.write_text(json.dumps({"unregistered_bypass_policy":"FAIL_CLOSED","registered_pr_exceptions":[]}), encoding="utf-8")
            lineage_path = root / "records/vit/lineage.json"
            lineage_path.parent.mkdir(parents=True)
            lineage_path.write_text(json.dumps(lineage_record()), encoding="utf-8")
            event = {"number":1,"pull_request":{"body":"VIT-Lineage-Ref: records/vit/lineage.json","head":{"sha":"a"*40,"ref":"feature"}}}
            result = check_pull_request_event(root=root, event=event)
            self.assertTrue(result.startswith("VIT_MANDATORY:PACKET:"))
            missing = {"number":2,"pull_request":{"body":"","head":{"sha":"b"*40,"ref":"feature2"}}}
            with self.assertRaises(RuntimeError):
                check_pull_request_event(root=root, event=missing)


if __name__ == "__main__":
    unittest.main()
