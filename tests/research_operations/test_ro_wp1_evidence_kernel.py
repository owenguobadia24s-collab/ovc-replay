from __future__ import annotations

import copy
import unittest

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


def observation() -> dict:
    return {
        "record_type": "OBSERVATION_SNAPSHOT",
        "schema_version": "0.1",
        "lifecycle_state": "DRAFT",
        "created_at": "2023-06-15T10:00:00Z",
        "frozen_at": None,
        "operator_id": "fixture-operator",
        "admissible_cutoff": "2023-06-15T10:00:00Z",
        "source_release_refs": [{"release_id": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2", "first_valid_time": "2023-06-15T10:00:00Z"}],
        "artifact_refs": [],
        "missingness": [],
        "lineage": {"parent": [], "derived_from": [], "supersedes": None, "adjudicates": []},
        "authority_state": "DRAFT",
        "reproducibility_state": "REPRODUCIBLE",
        "payload": {"session_id": "fixture-session", "visible_facts": {"clock": "2H_A_L", "side": "BID"}, "unknowns": ["later_path"], "source_record_refs": ["opt-a:fixture-bar"]},
        "content_sha256": None,
    }


class ROWP1EvidenceKernelTests(unittest.TestCase):
    def test_canonical_serialization_is_byte_identical(self) -> None:
        self.assertEqual(canonical_json_bytes({"b": 2, "a": [3, 1]}), canonical_json_bytes({"a": [3, 1], "b": 2}))

    def test_model_refs_are_optional(self) -> None:
        record = observation()
        self.assertNotIn("model_refs", record)
        validate_record(record)

    def test_freeze_is_deterministic_and_verifiable(self) -> None:
        first = freeze_record(observation(), frozen_at="2023-06-15T10:00:00Z")
        second = freeze_record(observation(), frozen_at="2023-06-15T10:00:00Z")
        self.assertEqual(first, second)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        verify_frozen_record(first)

    def test_post_cutoff_reference_is_rejected(self) -> None:
        record = observation()
        record["source_release_refs"][0]["first_valid_time"] = "2023-06-15T10:00:01Z"
        with self.assertRaises(RecordValidationError) as ctx:
            validate_record(record)
        self.assertEqual(ctx.exception.code, "POST_CUTOFF_REFERENCE")

    def test_frozen_mutation_emits_incident(self) -> None:
        frozen = freeze_record(observation(), frozen_at="2023-06-15T10:00:00Z")
        frozen["payload"]["visible_facts"]["side"] = "ASK"
        with self.assertRaises(FrozenRecordMutationError) as ctx:
            verify_frozen_record(frozen)
        self.assertEqual(ctx.exception.incident["incident_code"], "FROZEN_MUTATION")

    def test_duplicate_deterministic_id_is_rejected(self) -> None:
        frozen = freeze_record(observation(), frozen_at="2023-06-15T10:00:00Z")
        registry = RecordIdRegistry()
        registry.add(frozen["record_id"])
        with self.assertRaises(DuplicateRecordIdError):
            registry.add(frozen["record_id"])

    def test_missing_artifact_states_are_explicit(self) -> None:
        self.assertEqual(derive_reproducibility_state([{"required": True, "availability": "MISSING"}]), "NOT_REPRODUCIBLE")
        self.assertEqual(derive_reproducibility_state([{"required": True, "availability": "VERIFIED"}, {"required": True, "availability": "MISSING"}]), "PARTIALLY_AVAILABLE")

    def test_supersession_preserves_predecessor_bytes(self) -> None:
        original = freeze_record(observation(), frozen_at="2023-06-15T10:00:00Z")
        before = copy.deepcopy(original)
        replacement = observation()
        replacement["payload"]["unknowns"].append("context")
        predecessor, successor = supersede_record(original, replacement, frozen_at="2023-06-15T10:05:00Z")
        self.assertEqual(original, before)
        self.assertEqual(predecessor, original)
        self.assertEqual(successor["lineage"]["supersedes"], original["record_id"])

    def test_locked_validation_metadata_allowed_payload_denied(self) -> None:
        record = observation()
        record["source_release_refs"] = [{"release_id": "OPT-A.GBPUSD.VALIDATION.2025.v2", "validation_access_state": "LOCKED_UNCONSUMED", "payload_access": "DENIED", "first_valid_time": "2023-06-15T10:00:00Z"}]
        validate_record(record)
        record["source_release_refs"][0]["payload_ref"] = "r2://forbidden"
        with self.assertRaises(RecordValidationError) as ctx:
            validate_record(record)
        self.assertEqual(ctx.exception.code, "VALIDATION_PAYLOAD_ACCESS_DENIED")


if __name__ == "__main__":
    unittest.main()
