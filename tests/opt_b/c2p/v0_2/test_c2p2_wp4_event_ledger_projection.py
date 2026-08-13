from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from ovc.opt_b.c2p_v0_2.assertion import create_object_assertion
from ovc.opt_b.c2p_v0_2.canonical import canonical_bytes
from ovc.opt_b.c2p_v0_2.events import (
    EVENT_FIELDS,
    EventBuildError,
    build_assertion_genesis_event,
    build_event,
    canonical_event_bytes,
    event_record_hash,
)
from ovc.opt_b.c2p_v0_2.ledger import (
    CanonicalEventLedger,
    LedgerQuarantinedError,
)
from ovc.opt_b.c2p_v0_2.persistence import (
    EventJournal,
    PersistenceIntegrityError,
    SnapshotProjectionStore,
)
from ovc.opt_b.c2p_v0_2.projection import (
    ProjectionIntegrityError,
    project_assertion_stream,
    snapshot_identity,
    verify_snapshot,
)

ROOT = Path(__file__).resolve().parents[4]
PACK = json.loads(
    (ROOT / "fixtures/opt_b/c2p/v0_2/packs/C2P_SYNTH_OBJECTPACK_MINIMAL_A_v1.json").read_text(encoding="utf-8")
)
FIXTURES = json.loads(
    (ROOT / "fixtures/opt_b/c2p/v0_2/golden/C2P2_WP4_EVENT_LEDGER_FIXTURES_v1.json").read_text(encoding="utf-8")
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def assertion(seed: str = "A"):
    members = [digest(f"{seed}-candidate-{index}") for index in range(3)]
    decision_id = digest(f"{seed}-decision")
    tracklet = {
        "object_pack_id": PACK["object_pack_id"],
        "state": "CONFIRMED",
        "member_candidate_ids": members,
        "first_valid_time": "2026-01-01T00:03:00Z",
        "evaluation_cutoff": "2026-01-01T00:05:00Z",
        "structural_role_id": "LEVEL",
        "geometry_kind_id": "POINT_REFERENCE",
        "hard_scope": {
            "instrument": "SYNTH",
            "side": "SYNTH",
            "scale": "STEP",
            "partition": seed,
        },
    }
    decision = {
        "object_pack_id": PACK["object_pack_id"],
        "terminal_decision": "NEW",
        "candidate_id": members[-1],
        "decision_id": decision_id,
        "first_valid_time": "2026-01-01T00:04:00Z",
        "evaluation_cutoff": "2026-01-01T00:05:00Z",
    }
    return create_object_assertion(tracklet, decision, PACK)


def genesis(seed: str = "A"):
    obj = assertion(seed)
    event = build_assertion_genesis_event(
        obj,
        PACK,
        market_effective_start="2026-01-01T00:00:00Z",
        market_effective_end=None,
        evaluation_cutoff="2026-01-01T00:05:00Z",
        geometry={"coordinate": f"{100 + len(seed)}.000"},
        state_payload={"fixture_structure_key": seed},
        source_hashes=[digest(f"{seed}-source-2"), digest(f"{seed}-source-1")],
    )
    return obj, event


def update_event(first, *, evaluation_state="MISSING", coordinate="102.0"):
    return build_event(
        stream_id=first["stream_id"],
        sequence_no=1,
        event_type="ASSERTION_UPDATED",
        object_pack=PACK,
        market_effective_start="2026-01-01T00:06:00Z",
        market_effective_end=None,
        first_valid_time="2026-01-01T00:07:00Z",
        evaluation_cutoff="2026-01-01T00:08:00Z",
        decision_id=digest("update-decision"),
        parent_event_ids=[first["event_id"]],
        source_hashes=[digest("update-source")],
        payload={
            "geometry": {"coordinate": coordinate},
            "state_payload": {"fixture_structure_key": "A", "revision": 1},
            "evaluation_state": evaluation_state,
        },
        prior_event_hash=event_record_hash(first),
    )


class C2P2WP4EventLedgerProjectionTests(unittest.TestCase):
    def test_genesis_event_identity_matches_wp3_assertion_reference_and_schemas(self):
        obj, event_a = genesis()
        _, event_b = genesis()
        self.assertEqual(event_a, event_b)
        self.assertEqual(event_a["event_id"], obj["genesis_event_id"])
        self.assertEqual(set(event_a), EVENT_FIELDS)
        snapshot = project_assertion_stream([event_a])
        self.assertEqual(
            set(snapshot),
            {
                "schema",
                "snapshot_id",
                "projection_schema_version",
                "object_assertion_id",
                "event_frontier_hash",
                "event_frontier_sequence",
                "geometry",
                "state_payload",
                "lifecycle_state",
                "observability_state",
                "evaluation_state",
                "market_effective_start",
                "market_effective_end",
                "first_valid_time",
                "evaluation_cutoff",
            },
        )
        self.assertEqual(snapshot["object_assertion_id"], obj["object_assertion_id"])
        self.assertEqual(snapshot["event_frontier_hash"], event_record_hash(event_a))
        self.assertEqual(snapshot["lifecycle_state"], "ACTIVE")

    def test_append_is_idempotent_and_caller_mutation_cannot_rewrite_history(self):
        _, event = genesis()
        ledger = CanonicalEventLedger()
        first = ledger.append(event)
        original_bytes = ledger.canonical_export_bytes()
        second = ledger.append(event)
        self.assertEqual(first.disposition, "APPENDED")
        self.assertEqual(second.disposition, "IDEMPOTENT")
        self.assertEqual(ledger.event_count, 1)
        event["payload"]["geometry"]["coordinate"] = "999"
        self.assertEqual(ledger.canonical_export_bytes(), original_bytes)
        self.assertEqual(ledger.stream_events(first.stream_id)[0]["payload"]["geometry"]["coordinate"], "101.000")

    def test_sequence_prior_hash_and_collision_fail_closed_quarantine(self):
        _, first = genesis()
        ledger = CanonicalEventLedger()
        ledger.append(first)
        bad = build_event(
            stream_id=first["stream_id"],
            sequence_no=2,
            event_type="ASSERTION_UPDATED",
            object_pack=PACK,
            market_effective_start="2026-01-01T00:06:00Z",
            market_effective_end=None,
            first_valid_time="2026-01-01T00:07:00Z",
            evaluation_cutoff="2026-01-01T00:08:00Z",
            decision_id=digest("bad-decision"),
            parent_event_ids=[first["event_id"]],
            source_hashes=[digest("bad-source")],
            payload={"state_payload": {"revision": 2}},
            prior_event_hash=event_record_hash(first),
        )
        with self.assertRaisesRegex(LedgerQuarantinedError, "C2P_STREAM_SEQUENCE_VIOLATION"):
            ledger.append(bad)
        self.assertTrue(ledger.is_quarantined)
        self.assertEqual(ledger.quarantine_record["reason"], "C2P_STREAM_SEQUENCE_VIOLATION")
        with self.assertRaisesRegex(LedgerQuarantinedError, "ALREADY_QUARANTINED"):
            ledger.append(first)

        collision_ledger = CanonicalEventLedger()
        collision_ledger.append(first)
        collision = json.loads(canonical_event_bytes(first).decode("utf-8"))
        collision["payload"]["geometry"]["coordinate"] = "998"
        with self.assertRaisesRegex(LedgerQuarantinedError, "C2P_EVENT_ID_CONFLICT"):
            collision_ledger.append(collision)

    def test_late_source_correction_requires_new_ledger_generation(self):
        _, original = genesis()
        corrected = build_event(
            stream_id=original["stream_id"],
            sequence_no=original["sequence_no"],
            event_type=original["event_type"],
            object_pack=PACK,
            market_effective_start=original["market_effective_start"],
            market_effective_end=original["market_effective_end"],
            first_valid_time=original["first_valid_time"],
            evaluation_cutoff=original["evaluation_cutoff"],
            decision_id=original["decision_id"],
            parent_event_ids=original["parent_event_ids"],
            source_hashes=[digest("corrected-source-2"), digest("corrected-source-1")],
            payload=original["payload"],
            prior_event_hash=original["prior_event_hash"],
            expected_event_id=original["event_id"],
        )
        self.assertEqual(corrected["source_hashes"], sorted(corrected["source_hashes"]))
        self.assertEqual(canonical_event_bytes(corrected), canonical_bytes(corrected))
        # ASSERTION_GENESIS retains the exact WP3 logical genesis reference,
        # while the full canonical event record/frontier changes.
        original_ledger = CanonicalEventLedger.from_events([original])
        original_bytes = original_ledger.canonical_export_bytes()
        with self.assertRaisesRegex(LedgerQuarantinedError, "C2P_EVENT_ID_CONFLICT"):
            original_ledger.append(corrected)
        self.assertEqual(original_ledger.quarantine_record["reason"], "C2P_EVENT_ID_CONFLICT")
        self.assertEqual(original_ledger.canonical_export_bytes(), original_bytes)

        corrected_ledger = CanonicalEventLedger.from_events([corrected])
        self.assertEqual(corrected["event_id"], original["event_id"])
        self.assertNotEqual(corrected_ledger.global_digest(), hashlib.sha256(original_bytes).hexdigest())
        self.assertNotEqual(corrected_ledger.canonical_export_bytes(), original_bytes)

    def test_snapshot_rebuild_and_orthogonal_state_axes(self):
        _, first = genesis()
        update = update_event(first)
        censored = build_event(
            stream_id=first["stream_id"],
            sequence_no=2,
            event_type="CENSORED_AT_RUN_END",
            object_pack=PACK,
            market_effective_start="2026-01-01T00:09:00Z",
            market_effective_end="2026-01-01T00:10:00Z",
            first_valid_time="2026-01-01T00:10:00Z",
            evaluation_cutoff="2026-01-01T00:10:00Z",
            decision_id=None,
            parent_event_ids=[update["event_id"]],
            source_hashes=[digest("run-end-source")],
            payload={"evaluation_state": "NOT_EVALUABLE"},
            prior_event_hash=event_record_hash(update),
        )
        snapshot_a = project_assertion_stream([first, update, censored])
        snapshot_b = project_assertion_stream([censored, first, update])
        self.assertEqual(snapshot_a, snapshot_b)
        self.assertEqual(snapshot_a["lifecycle_state"], "ACTIVE")
        self.assertEqual(snapshot_a["observability_state"], "CENSORED")
        self.assertEqual(snapshot_a["evaluation_state"], "NOT_EVALUABLE")
        self.assertIsNone(snapshot_a["market_effective_end"])
        self.assertTrue(verify_snapshot(snapshot_a, [first, update, censored]))

        with self.assertRaisesRegex(EventBuildError, "CENSORING_CANNOT_MUTATE_LIFECYCLE"):
            build_event(
                stream_id=first["stream_id"],
                sequence_no=2,
                event_type="CENSORED_AT_RUN_END",
                object_pack=PACK,
                market_effective_start="2026-01-01T00:09:00Z",
                market_effective_end=None,
                first_valid_time="2026-01-01T00:10:00Z",
                evaluation_cutoff="2026-01-01T00:10:00Z",
                decision_id=None,
                payload={"lifecycle_state": "RETIRED"},
                prior_event_hash=event_record_hash(update),
            )

    def test_journal_reload_preserves_bytes_and_corruption_is_quarantined(self):
        _, first = genesis()
        update = update_event(first)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ledger.jsonl"
            journal = EventJournal(path)
            journal.append_event(first)
            after_first = journal.raw_bytes()
            self.assertEqual(journal.append_event(first).disposition, "IDEMPOTENT")
            self.assertEqual(journal.raw_bytes(), after_first)
            journal.append_event(update)
            original = journal.raw_bytes()
            rebuilt = journal.load_ledger()
            self.assertEqual(rebuilt.canonical_export_bytes(), original)
            self.assertTrue(rebuilt.verify_integrity())

            path.write_bytes(original.replace(b'"coordinate":"102.0"', b'"coordinate":"777.0"'))
            with self.assertRaisesRegex(PersistenceIntegrityError, "SEAL_MISMATCH|EVENT_ID_MISMATCH"):
                journal.load_ledger()

    def test_snapshot_projection_store_cannot_be_a_second_state_authority(self):
        _, first = genesis()
        update = update_event(first)
        ledger = CanonicalEventLedger.from_events([update, first])
        with tempfile.TemporaryDirectory() as temporary:
            store = SnapshotProjectionStore(Path(temporary) / "snapshots.json")
            payload = store.rebuild_from_ledger(ledger)
            self.assertFalse(hasattr(store, "write_snapshot"))
            self.assertEqual(store.read_verified(ledger), payload)
            raw = json.loads(store.path.read_text(encoding="utf-8"))
            raw["snapshots"][0]["lifecycle_state"] = "RETIRED"
            store.path.write_bytes(canonical_bytes(raw))
            with self.assertRaisesRegex(ProjectionIntegrityError, "LEDGER_MISMATCH"):
                store.read_verified(ledger)
            repaired = store.rebuild_from_ledger(ledger)
            self.assertEqual(repaired["snapshots"][0]["lifecycle_state"], "ACTIVE")

    def test_independent_stream_concurrency_order_is_canonical(self):
        _, event_a = genesis("A")
        _, event_b = genesis("BBBB")
        ledger_ab = CanonicalEventLedger.from_events([event_a, event_b])
        ledger_ba = CanonicalEventLedger.from_events([event_b, event_a])
        self.assertEqual(ledger_ab.canonical_export_bytes(), ledger_ba.canonical_export_bytes())
        self.assertEqual(ledger_ab.global_digest(), ledger_ba.global_digest())
        self.assertEqual(ledger_ab.seal(), ledger_ba.seal())

    def test_projection_schema_generation_changes_snapshot_identity_not_event_ledger(self):
        _, first = genesis()
        snapshot = project_assertion_stream([first])
        fields = {
            key: snapshot[key]
            for key in (
                "geometry",
                "state_payload",
                "lifecycle_state",
                "observability_state",
                "evaluation_state",
                "market_effective_start",
                "market_effective_end",
                "first_valid_time",
                "evaluation_cutoff",
            )
        }
        future_id = snapshot_identity(
            projection_schema_version="v0.3-test",
            object_assertion_id=snapshot["object_assertion_id"],
            event_frontier_hash=snapshot["event_frontier_hash"],
            event_frontier_sequence=snapshot["event_frontier_sequence"],
            snapshot_fields=fields,
        )
        self.assertNotEqual(snapshot["snapshot_id"], future_id)
        ledger = CanonicalEventLedger.from_events([first])
        before = ledger.canonical_export_bytes()
        self.assertEqual(before, ledger.canonical_export_bytes())

    def test_canonical_decimal_and_order_perturbation_are_byte_equivalent(self):
        _, first = genesis()
        common = dict(
            stream_id=first["stream_id"],
            sequence_no=1,
            event_type="ASSERTION_UPDATED",
            object_pack=PACK,
            market_effective_start="2026-01-01T00:06:00Z",
            market_effective_end=None,
            first_valid_time="2026-01-01T00:07:00Z",
            evaluation_cutoff="2026-01-01T00:08:00Z",
            decision_id=digest("decimal-decision"),
            parent_event_ids=[first["event_id"]],
            source_hashes=[digest("decimal-source")],
            prior_event_hash=event_record_hash(first),
        )
        event_a = build_event(payload={"b": Decimal("1.2300"), "a": "x"}, **common)
        event_b = build_event(payload={"a": "x", "b": Decimal("1.23")}, **common)
        self.assertEqual(event_a["event_id"], event_b["event_id"])
        self.assertEqual(canonical_event_bytes(event_a), canonical_event_bytes(event_b))

    def test_fixture_pack_is_exact_synthetic_wp4_scope(self):
        ids = {item["fixture_id"] for item in FIXTURES["fixtures"]}
        self.assertEqual(
            ids,
            {
                "C2P2-F16",
                "C2P2-F36",
                "C2P2-F37",
                "C2P2-F38",
                "C2P2-F39",
                "C2P2-F40",
                "C2P2-F46",
            },
        )
        late_source = next(item for item in FIXTURES["fixtures"] if item["fixture_id"] == "C2P2-F36")
        self.assertTrue(late_source["canonical_event_required"])
        self.assertEqual(late_source["source_hash_order"], "LEXICOGRAPHIC")
        self.assertEqual(late_source["expected_quarantine_reason"], "C2P_EVENT_ID_CONFLICT")
        self.assertEqual(FIXTURES["object_pack_id"], PACK["object_pack_id"])
        self.assertEqual(FIXTURES["authority"]["activation"], "NONE")
        self.assertEqual(FIXTURES["authority"]["real_source"], "FORBIDDEN")
        self.assertEqual(FIXTURES["authority"]["validation"], "FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
