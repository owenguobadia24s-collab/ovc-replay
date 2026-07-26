from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ovc.research_operations import (
    AppendOnlyViolationError,
    DraftStore,
    FrozenRecordStore,
    ResearchOperationsService,
    ResearchQueueService,
    ResearchWriteService,
)


class ROWP2ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.drafts = DraftStore(root / "var" / "drafts")
        self.records = FrozenRecordStore(root / "records")
        self.writes = ResearchWriteService(drafts=self.drafts, records=self.records, operator_id="operator-fixture")
        self.service = ResearchOperationsService(self.writes)
        self.release = "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_complete_session_without_manual_file_editing(self) -> None:
        session = self.service.open_session(
            instrument="GBPUSD",
            release_id=self.release,
            role="DISCOVERY",
            cutoff="2023-06-15T10:00:00Z",
            objective="Describe structure without later path",
            created_at="2023-06-15T10:00:00Z",
        )
        observation_draft = self.service.add_observation(
            session_id=session,
            release_id=self.release,
            cutoff="2023-06-15T10:00:00Z",
            visible_facts={"clock": "2H_A_L", "side": "BID"},
            unknowns=["later_path"],
            source_record_refs=["opt-a:fixture-bar"],
            created_at="2023-06-15T10:01:00Z",
        )
        observation = self.service.freeze_observation(draft_id=observation_draft, frozen_at="2023-06-15T10:02:00Z")
        claim = self.service.freeze_claim(
            observation_id=observation["record_id"],
            release_id=self.release,
            cutoff="2023-06-15T10:00:00Z",
            eligibility={"rule": "fixture"},
            discriminator={"field": "close_location"},
            falsifier={"rule": "opposite"},
            horizons=[{"name": "4h", "due_at": "2023-06-15T14:00:00Z"}],
            frozen_at="2023-06-15T10:03:00Z",
        )
        realization = self.service.register_realization(
            observation_id=observation["record_id"],
            claim_id=claim["record_id"],
            release_id=self.release,
            cutoff="2023-06-15T14:00:00Z",
            reference_time="2023-06-15T10:00:00Z",
            horizon="4h",
            coverage={"complete": True},
            path={"result": "neutral"},
            censoring_state="COMPLETE",
            frozen_at="2023-06-15T14:01:00Z",
        )
        evidence = self.service.adjudicate(
            observation_id=observation["record_id"],
            claim_id=claim["record_id"],
            realization_id=realization["record_id"],
            release_id=self.release,
            cutoff="2023-06-15T14:01:00Z",
            evidence_role="SUPPORT",
            admissibility="ADMISSIBLE",
            frozen_at="2023-06-15T14:02:00Z",
        )
        closed = self.service.close_session(
            draft_id=session,
            incidents=[],
            unresolved_questions=[],
            next_action="Review counterexample",
            frozen_at="2023-06-15T14:03:00Z",
        )
        self.assertEqual("EVIDENCE_ITEM", evidence["record_type"])
        self.assertEqual("CLOSED", closed["payload"]["session_state"])
        audit = self.records.iter_records("AUDIT_EVENT")
        self.assertGreaterEqual(len(audit), 8)
        self.assertTrue(all(record["lifecycle_state"] == "FROZEN" for record in audit))

    def test_frozen_record_cannot_be_overwritten(self) -> None:
        draft = self.service.add_observation(
            session_id="draft:session",
            release_id=self.release,
            cutoff="2023-06-15T10:00:00Z",
            visible_facts={},
            unknowns=[],
            source_record_refs=[],
            created_at="2023-06-15T10:00:00Z",
        )
        self.service.freeze_observation(draft_id=draft, frozen_at="2023-06-15T10:01:00Z")
        with self.assertRaises(AppendOnlyViolationError):
            self.service.freeze_observation(draft_id=draft, frozen_at="2023-06-15T10:01:00Z")

    def test_incomplete_session_queue_reads_drafts(self) -> None:
        session = self.service.open_session(
            instrument="GBPUSD",
            release_id=self.release,
            role="DISCOVERY",
            cutoff="2023-06-15T10:00:00Z",
            objective="Queue fixture",
            created_at="2023-06-15T10:00:00Z",
        )
        queue = ResearchQueueService(records=self.records, drafts=self.drafts)
        items = queue.show("incomplete-sessions", as_of="2023-06-15T11:00:00Z")
        self.assertEqual(session, items[0]["draft_id"])

    def test_validation_reference_is_metadata_only(self) -> None:
        session = self.service.open_session(
            instrument="GBPUSD",
            release_id="OPT-A.GBPUSD.VALIDATION.2025.v2",
            role="VALIDATION_METADATA_ONLY",
            cutoff="2026-01-01T00:00:00Z",
            objective="Catalogue identity only",
            created_at="2026-01-01T00:00:00Z",
        )
        record = self.drafts.read(session)
        ref = record["source_release_refs"][0]
        self.assertEqual("LOCKED_UNCONSUMED", ref["validation_access_state"])
        self.assertEqual("DENIED", ref["payload_access"])
        self.assertNotIn("payload_ref", ref)


if __name__ == "__main__":
    unittest.main()
