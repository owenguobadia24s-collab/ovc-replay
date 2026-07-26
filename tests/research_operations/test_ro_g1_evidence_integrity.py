from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ovc.research_operations import (
    DuplicateRecordIdError,
    FrozenRecordMutationError,
    RecordIdRegistry,
    RecordValidationError,
    canonical_json_bytes,
    derive_reproducibility_state,
    freeze_record,
    supersede_record,
    validate_record,
    verify_frozen_record,
)

ROOT = Path(__file__).resolve().parents[2]
GATE_PACKET = ROOT / "docs/releases/research-operations-foundation/ro-g1/RO_G1_GATE_PACKET.json"
DECISION = ROOT / "docs/releases/research-operations-foundation/ro-g1/RO_G1_OPERATOR_DECISION.md"
AUTHORITY = ROOT / "registries/authority/ACTIVE_AUTHORITY.yaml"
IMPLEMENTATION = ROOT / "registries/research_operations/RESEARCH_OPERATIONS_IMPLEMENTATION_REGISTRY_v0_1.yaml"


def observation() -> dict:
    return {
        "record_type": "OBSERVATION_SNAPSHOT",
        "schema_version": "0.1",
        "lifecycle_state": "DRAFT",
        "created_at": "2023-06-15T10:00:00Z",
        "frozen_at": None,
        "operator_id": "ro-g1-review",
        "admissible_cutoff": "2023-06-15T10:00:00Z",
        "source_release_refs": [
            {
                "release_id": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
                "first_valid_time": "2023-06-15T10:00:00Z",
            }
        ],
        "artifact_refs": [],
        "missingness": [],
        "lineage": {"parent": [], "derived_from": [], "supersedes": None, "adjudicates": []},
        "authority_state": "DRAFT",
        "reproducibility_state": "REPRODUCIBLE",
        "payload": {
            "session_id": "ro-g1-fixture",
            "visible_facts": {"clock": "2H_A_L", "side": "BID"},
            "unknowns": ["later_path"],
            "source_record_refs": ["opt-a:fixture-bar"],
        },
        "content_sha256": None,
    }


class ROG1EvidenceIntegrityTests(unittest.TestCase):
    def test_gate_packet_is_complete_pass(self) -> None:
        packet = json.loads(GATE_PACKET.read_text(encoding="utf-8"))
        self.assertEqual(packet["gate_id"], "RO-G1")
        self.assertEqual(packet["operator_disposition"], "PASS")
        self.assertEqual(len(packet["checks"]), 10)
        self.assertTrue(all(check["status"] == "PASS" for check in packet["checks"]))
        self.assertEqual(packet["authority_delta"]["ro_wp2"], "AUTHORISED_FOR_BUILD")

    def test_valid_chain_freezes_verifies_and_supersedes(self) -> None:
        first = freeze_record(observation(), frozen_at="2023-06-15T10:00:00Z")
        verify_frozen_record(first)
        predecessor_bytes = canonical_json_bytes(first)
        replacement = observation()
        replacement["payload"]["unknowns"].append("context")
        predecessor, successor = supersede_record(
            first,
            replacement,
            frozen_at="2023-06-15T10:05:00Z",
        )
        self.assertEqual(canonical_json_bytes(predecessor), predecessor_bytes)
        self.assertEqual(successor["lineage"]["supersedes"], first["record_id"])
        self.assertNotEqual(successor["record_id"], first["record_id"])

    def test_cutoff_and_validation_isolation_fail_closed(self) -> None:
        post_cutoff = observation()
        post_cutoff["source_release_refs"][0]["first_valid_time"] = "2023-06-15T10:00:01Z"
        with self.assertRaises(RecordValidationError) as cutoff_ctx:
            validate_record(post_cutoff)
        self.assertEqual(cutoff_ctx.exception.code, "POST_CUTOFF_REFERENCE")

        locked = observation()
        locked["source_release_refs"] = [
            {
                "release_id": "OPT-A.GBPUSD.VALIDATION.2025.v2",
                "validation_access_state": "LOCKED_UNCONSUMED",
                "payload_access": "DENIED",
                "payload_ref": "r2://forbidden",
                "first_valid_time": "2023-06-15T10:00:00Z",
            }
        ]
        with self.assertRaises(RecordValidationError) as validation_ctx:
            validate_record(locked)
        self.assertEqual(validation_ctx.exception.code, "VALIDATION_PAYLOAD_ACCESS_DENIED")

    def test_frozen_mutation_and_duplicate_id_reject(self) -> None:
        frozen = freeze_record(observation(), frozen_at="2023-06-15T10:00:00Z")
        mutated = copy.deepcopy(frozen)
        mutated["payload"]["visible_facts"]["side"] = "ASK"
        with self.assertRaises(FrozenRecordMutationError) as mutation_ctx:
            verify_frozen_record(mutated)
        self.assertEqual(mutation_ctx.exception.incident["incident_code"], "FROZEN_MUTATION")

        registry = RecordIdRegistry()
        registry.add(frozen["record_id"])
        with self.assertRaises(DuplicateRecordIdError):
            registry.add(frozen["record_id"])

    def test_missing_artifact_states_remain_visible(self) -> None:
        self.assertEqual(
            derive_reproducibility_state([{"required": True, "availability": "MISSING"}]),
            "NOT_REPRODUCIBLE",
        )
        self.assertEqual(
            derive_reproducibility_state(
                [
                    {"required": True, "availability": "VERIFIED"},
                    {"required": True, "availability": "MISSING"},
                ]
            ),
            "PARTIALLY_AVAILABLE",
        )

    def test_authority_delta_is_build_only(self) -> None:
        authority = AUTHORITY.read_text(encoding="utf-8")
        implementation = IMPLEMENTATION.read_text(encoding="utf-8")
        decision = DECISION.read_text(encoding="utf-8")
        self.assertIn("state: RO_G1_PASS_WP2_BUILD_AUTHORISED", authority)
        self.assertIn("ro_wp2: AUTHORISED_FOR_BUILD", authority)
        self.assertIn("durable_write_service: DENIED_PENDING_RO_WP2_IMPLEMENTATION", authority)
        self.assertIn("status: RO_G1_PASS_WP2_BUILD_AUTHORISED", implementation)
        self.assertIn("PASS — RO-WP2 AUTHORISED FOR BUILD", decision)
        for denied in (
            "active_research: NONE",
            "market_authority: NONE",
            "probability_authority: NONE",
            "exposure_authority: NONE",
            "execution_authority: NONE",
            "agent_authority: NONE",
        ):
            self.assertIn(denied, authority)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", authority)


if __name__ == "__main__":
    unittest.main()
