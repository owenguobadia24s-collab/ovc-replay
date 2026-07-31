from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from ovc.research_operations.storage import DraftStore, FrozenRecordStore, ResearchWriteService
from ovc.research_operations.v0_4.annotation_friction_service import (
    BOUNDARY_RECORD,
    FRICTION_RECORD,
    REVIEW_RECORD,
    RO4AnnotationFrictionService,
    RO4AppendAuthority,
    RO4AuthorityDisabled,
    RO4RecordError,
)

T0 = "2026-06-03T10:00:00Z"
T1 = "2026-06-03T10:15:00Z"
T2 = "2026-06-03T10:30:00Z"
MANIFEST = "a" * 64
LOGICAL = "b" * 64
SEQUENCE = "RO4.SEQUENCE.TEST.001"
RELEASE = "OPT-B.C2.GBPUSD.DISCOVERY.2026-06.v2"


class RO4G4Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.records = FrozenRecordStore(root / "records")
        self.writes = ResearchWriteService(
            drafts=DraftStore(root / "drafts"), records=self.records, operator_id="operator-test"
        )
        self.service = RO4AnnotationFrictionService(
            writes=self.writes, authority=RO4AppendAuthority.synthetic_enabled()
        )

    def tearDown(self):
        self.temp.cleanup()

    def boundary(self, **overrides):
        values = dict(
            source_sequence_id=SEQUENCE,
            source_release_id=RELEASE,
            manifest_sha256=MANIFEST,
            clock="15M",
            side="BID",
            member_ids=["state-1", "state-2"],
            member_first_valid_times=[T0, T1],
            operation_mode="TIME_GATED_REPLAY",
            admissible_cutoff=T1,
            annotation="PROPOSED_START",
            rationale="The source transition begins at the first listed member.",
            frozen_at=T2,
        )
        values.update(overrides)
        return self.service.append_boundary_annotation(**values)

    def test_disabled_authority_blocks_before_any_write(self):
        disabled = RO4AppendAuthority(
            enabled=False,
            status="DISABLED_PENDING_RO4_G4",
            service_version="v0.1",
            accepted_record_types=frozenset({BOUNDARY_RECORD, FRICTION_RECORD, REVIEW_RECORD}),
            gate_decision_id=None,
            concentration_status="PASS",
            acknowledgement_record_id=None,
            console_write_state="PROHIBITED",
        )
        service = RO4AnnotationFrictionService(writes=self.writes, authority=disabled)
        with self.assertRaises(RO4AuthorityDisabled):
            service.append_boundary_annotation(
                source_sequence_id=SEQUENCE, source_release_id=RELEASE, manifest_sha256=MANIFEST,
                clock="15M", side="BID", member_ids=["a", "b"], member_first_valid_times=[T0, T1],
                operation_mode="TIME_GATED_REPLAY", admissible_cutoff=T1, annotation="PROPOSED_START",
                rationale="bounded", frozen_at=T2,
            )
        self.assertEqual([], self.records.iter_records())

    def test_registry_rejects_enabled_without_gate_decision(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "authority.json"
            path.write_text(json.dumps({
                "enabled": True, "status": "APPROVED_RO4_G4", "service_version": "v0.1",
                "accepted_record_types": [BOUNDARY_RECORD], "gate_decision_id": None,
                "signature_diversity_status": "PASS", "acknowledgement_record_id": None,
                "console_write_state": "PROHIBITED",
            }), encoding="utf-8")
            with self.assertRaises(RO4RecordError):
                RO4AppendAuthority.from_registry(path)

    def test_concentration_warning_requires_acknowledgement(self):
        authority = RO4AppendAuthority(
            enabled=False, status="DISABLED_PENDING_RO4_G4", service_version="v0.1",
            accepted_record_types=frozenset({BOUNDARY_RECORD}), gate_decision_id=None,
            concentration_status="SIGNATURE_CONCENTRATION_WARNING", acknowledgement_record_id=None,
            console_write_state="PROHIBITED",
        )
        with self.assertRaises(RO4RecordError):
            authority.validate_registry()

    def test_boundary_append_is_frozen_audited_and_source_bound(self):
        record = self.boundary()
        self.assertEqual(BOUNDARY_RECORD, record["record_type"])
        self.assertEqual("FROZEN", record["lifecycle_state"])
        self.assertEqual(SEQUENCE, record["payload"]["source_sequence_id"])
        self.assertEqual("DENIED", record["payload"]["c2_mutation"])
        audits = self.records.iter_records("AUDIT_EVENT")
        self.assertEqual(1, len(audits))
        self.assertEqual("ro4.annotate-boundary", audits[0]["payload"]["action"])

    def test_exact_replay_is_idempotent(self):
        first = self.boundary()
        second = self.boundary()
        self.assertEqual(first, second)
        self.assertEqual(1, len(self.records.iter_records(BOUNDARY_RECORD)))
        self.assertEqual(1, len(self.records.iter_records("AUDIT_EVENT")))

    def test_post_cutoff_member_is_rejected(self):
        with self.assertRaisesRegex(RO4RecordError, "POST_CUTOFF"):
            self.boundary(member_first_valid_times=[T0, T2], admissible_cutoff=T1)

    def test_invalid_annotation_and_semantic_key_are_rejected(self):
        with self.assertRaises(RO4RecordError):
            self.boundary(annotation="BREAKOUT")
        original = self.boundary()
        replacement = deepcopy(original)
        replacement.update({"lifecycle_state": "DRAFT", "authority_state": "DRAFT", "frozen_at": None, "content_sha256": None})
        replacement.pop("record_id", None)
        replacement["payload"]["semantic_label"] = "reversal"
        with self.assertRaisesRegex(RO4RecordError, "FORBIDDEN_AUTHORITY_FIELD"):
            self.service.supersede(original["record_id"], replacement, frozen_at="2026-06-03T11:00:00Z")

    def test_supersession_preserves_original_and_links_successor(self):
        original = self.boundary()
        replacement = deepcopy(original)
        replacement.update({
            "lifecycle_state": "DRAFT", "authority_state": "DRAFT", "frozen_at": None,
            "created_at": "2026-06-03T11:00:00Z", "content_sha256": None,
        })
        replacement.pop("record_id", None)
        replacement["payload"]["rationale"] = "Correction: the proposed boundary is uncertain."
        replacement["payload"]["annotation"] = "UNCERTAIN"
        replacement["lineage"]["supersedes"] = None
        successor = self.service.supersede(original["record_id"], replacement, frozen_at="2026-06-03T11:00:00Z")
        self.assertEqual(original, self.records.read(original["record_id"]))
        self.assertEqual(original["record_id"], successor["lineage"]["supersedes"])
        self.assertNotEqual(original["record_id"], successor["record_id"])

    def test_friction_is_research_evidence_not_c2e_authority(self):
        record = self.service.append_friction_record(
            source_sequence_id=SEQUENCE,
            source_release_id=RELEASE,
            source_first_valid_times=[T0, T1],
            operation_mode="TIME_GATED_REPLAY",
            admissible_cutoff=T1,
            reason_code="BOUNDARY_AMBIGUITY",
            evidence_refs=["evidence-1"],
            counterexample_refs=["control-1"],
            remediation_ref="remediation-1",
            rationale="Two blinded reviews placed different starts.",
            frozen_at=T2,
        )
        self.assertEqual(FRICTION_RECORD, record["record_type"])
        self.assertEqual("DENIED_PENDING_RO4_G6_AND_SEPARATE_PLAN", record["payload"]["c2e_opening"])
        self.assertEqual("DENIED", record["payload"]["pd_population_write"])

    def test_prospective_review_keeps_post_cutoff_ids_absent(self):
        record = self.service.append_prospective_review(
            source_sequence_id=SEQUENCE,
            source_release_and_manifest={"release_id": RELEASE, "manifest_sha256": MANIFEST},
            operation_mode="TIME_GATED_REPLAY",
            admissible_cutoff=T1,
            admissible={"state_ids": ["s1", "s2"], "transition_ids": ["t1"], "sequence_ids": [SEQUENCE]},
            post_cutoff_hidden_count=3,
            logical_hash=LOGICAL,
            source_first_valid_times=[T0, T1],
            frozen_at=T2,
        )
        self.assertEqual(REVIEW_RECORD, record["record_type"])
        self.assertNotIn("post_cutoff_ids", record["payload"])
        self.assertEqual("LOCKED_UNCONSUMED", record["payload"]["validation_consumption"])

    def test_bad_sequence_hash_and_friction_reason_fail_closed(self):
        with self.assertRaises(RO4RecordError):
            self.boundary(source_sequence_id="PD.CANDIDATE.1")
        with self.assertRaises(RO4RecordError):
            self.service.append_friction_record(
                source_sequence_id=SEQUENCE, source_release_id=RELEASE,
                source_first_valid_times=[T0], operation_mode="TIME_GATED_REPLAY",
                admissible_cutoff=T1, reason_code="OPEN_C2E", evidence_refs=["e1"],
                counterexample_refs=[], remediation_ref=None, rationale="", frozen_at=T2,
            )


if __name__ == "__main__":
    unittest.main()
