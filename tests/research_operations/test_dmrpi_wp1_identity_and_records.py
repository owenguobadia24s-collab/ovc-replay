from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from ovc.research_operations.dmrp import (
    DMRPRecordValidationError,
    FrozenScientificRecordMutationError,
    assert_frozen_record_not_rewritten,
    identity_plane_manifest,
    make_dmrp_record,
    semantic_sha256,
    superseding_record,
    verify_dmrp_record,
)

ROOT = Path(__file__).resolve().parents[2]


class DMRPIWP1Tests(unittest.TestCase):
    def payload(self) -> dict:
        return {
            "study_id": "SYNTH.STUDY",
            "protocol_version": "0.1-R2",
            "research_mode": "PATH_1_EMPIRICAL",
            "research_role": "DISCOVERY",
            "instrument": "SYNTHETIC",
            "sides": ["BID"],
            "clocks": ["SYNTH"],
            "interval": "SYNTHETIC",
            "validation_access_state": "LOCKED_UNCONSUMED",
        }

    def record(self, **kwargs):
        return make_dmrp_record(
            "DMRP_STUDY", self.payload(), created_at=kwargs.get("created_at", "2026-01-01T00:00:00Z"),
            admissible_cutoff="2026-01-01T00:00:00Z", physical_attempt_id=kwargs.get("attempt"),
            irof_semantic_run_id=kwargs.get("irof"), artifact_refs=tuple(kwargs.get("artifact_refs", ())),
        )

    def test_scientific_identity_is_stable_across_physical_envelope(self) -> None:
        a = self.record(created_at="2026-01-01T00:00:00Z", attempt="host-a/worker-1")
        b = self.record(created_at="2026-01-02T00:00:00Z", attempt="host-b/worker-9", artifact_refs=({"path":"/tmp/x"},))
        self.assertEqual(a["semantic_sha256"], b["semantic_sha256"])
        self.assertNotEqual(a["record_sha256"], b["record_sha256"])
        self.assertNotEqual(a["record_id"], b["record_id"])

    def test_meaning_change_changes_semantic_identity(self) -> None:
        changed = self.payload(); changed["instrument"] = "OTHER_SYNTHETIC"
        self.assertNotEqual(semantic_sha256("DMRP_STUDY", self.payload()), semantic_sha256("DMRP_STUDY", changed))

    def test_identity_planes_are_explicit_and_non_transitive(self) -> None:
        record = self.record(attempt="attempt-1", irof="IROF.RUN.synthetic")
        planes = identity_plane_manifest(record)
        self.assertEqual(planes["scientific_object_identity"], record["semantic_sha256"])
        self.assertEqual(planes["research_operations_record_identity"], record["record_id"])
        self.assertEqual(planes["irof_semantic_run_identity"], "IROF.RUN.synthetic")
        self.assertEqual(planes["physical_attempt_or_artifact_identity"], "attempt-1")
        self.assertEqual(len(set(planes.values())), 4)

    def test_record_round_trip_and_authority_firewall(self) -> None:
        record = self.record()
        verify_dmrp_record(json.loads(json.dumps(record)))
        self.assertEqual(record["authority_state"], "NONE")
        self.assertEqual(record["authority_effect"], "NONE")
        with self.assertRaises(DMRPRecordValidationError):
            make_dmrp_record("DMRP_STUDY", self.payload(), created_at="x", admissible_cutoff="x", authority_state="ACTIVE")

    def test_nonfinite_scientific_value_rejected(self) -> None:
        payload = self.payload(); payload["bad"] = math.nan
        with self.assertRaises(ValueError):
            semantic_sha256("DMRP_STUDY", payload)

    def test_frozen_record_requires_forward_successor(self) -> None:
        old = self.record()
        changed = self.payload(); changed["instrument"] = "OTHER_SYNTHETIC"
        new = superseding_record(old, changed, created_at="2026-01-02T00:00:00Z", admissible_cutoff="2026-01-02T00:00:00Z")
        with self.assertRaises(FrozenScientificRecordMutationError):
            assert_frozen_record_not_rewritten(old, new)
        self.assertEqual(new["lineage"]["supersedes"], old["record_id"])

    def test_v01_schema_is_preserved_and_v02_is_additive(self) -> None:
        v1 = json.loads((ROOT / "schemas/research_operations/research_records_v0_1.schema.json").read_text())
        v2 = json.loads((ROOT / "schemas/research_operations/research_records_v0_2.schema.json").read_text())
        self.assertEqual(v1["title"], "OVC Research Operations records v0.1")
        self.assertEqual(v1["$defs"]["Envelope"]["properties"]["schema_version"]["const"], "0.1")
        self.assertEqual(v2["$defs"]["Envelope"]["properties"]["schema_version"]["const"], "0.2")
        self.assertIn("DMRPStudy", v2["$defs"])

    def test_question_registry_is_complete_and_frozen(self) -> None:
        registry = json.loads((ROOT / "registries/research_operations/EC1_RESEARCH_QUESTION_REGISTRY_v0_1.json").read_text())
        self.assertEqual([q["question_id"] for q in registry["questions"]], [f"EC1-Q{i:02d}" for i in range(1, 11)])
        self.assertTrue(all(q["text"] for q in registry["questions"]))
        self.assertEqual(registry["authority_effect"], "NONE")

    def test_synthetic_fixture_has_no_market_authority(self) -> None:
        pack = json.loads((ROOT / "fixtures/research_operations/dmrp_wp1/SYNTHETIC_RECORDS.json").read_text())
        self.assertEqual(pack["status"], "SYNTHETIC_NON_AUTHORITATIVE")
        self.assertEqual(pack["market_authority"], "NONE")
        self.assertEqual(pack["real_source_authority"], "NONE")


if __name__ == "__main__":
    unittest.main()
