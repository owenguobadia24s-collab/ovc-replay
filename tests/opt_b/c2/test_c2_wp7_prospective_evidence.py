from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.opt_b.validate_c2_wp7_prospective_evidence import (
    deterministic_record_id,
    validate_jsonl,
    validate_record,
)

ROOT = Path(__file__).resolve().parents[3]
BASELINE = ROOT / "fixtures/opt_b/c2/wp7/C2_PROSPECTIVE_EVIDENCE_ZERO_BASELINE.json"
REGISTRY = ROOT / "registries/research/C2_PROSPECTIVE_EVIDENCE_REGISTRY.yaml"
CONTRACT = ROOT / "contracts/opt_b/c2/C2_PROSPECTIVE_EVIDENCE_ACCUMULATION_CONTRACT_v0_2.md"


class C2WP7ProspectiveEvidenceTests(unittest.TestCase):
    def _record(self, operation_mode: str = "LIVE_PROSPECTIVE") -> dict[str, object]:
        record: dict[str, object] = {
            "schema": "ovc-c2-prospective-evidence-record/v0.2",
            "record_id": "",
            "research_line_id": "RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1",
            "record_class": "STATE_FIDELITY_REVIEW",
            "evidence_status": "OBSERVED_UNREVIEWED",
            "instrument": "GBPUSD",
            "canonical_clock": "15M",
            "price_side": "BID",
            "market_window_start_utc": "2026-07-27T09:00:00Z",
            "market_window_end_utc": "2026-07-27T09:15:00Z",
            "trigger_first_valid_at": "2026-07-27T09:15:00Z",
            "review_created_at_utc": "2026-07-27T10:00:00Z",
            "operation_mode": operation_mode,
            "author": "OWEN_VITAE",
            "active_release_id": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1",
            "active_manifest_id": "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1.r1",
            "active_manifest_sha256": "c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33",
            "source_object_ids": ["C2-STATE-EXAMPLE-001"],
            "summary": "Fixture-only state-fidelity observation.",
            "sequence_boundary_friction": False,
            "c2e_authority": "NONE",
            "probability_authority": "NONE",
            "exposure_authority": "NONE",
            "trading_authority": "NONE",
            "execution_authority": "NONE",
        }
        record["record_id"] = deterministic_record_id(record)
        return record

    def test_zero_baseline_contains_no_backfill(self) -> None:
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        self.assertEqual(baseline["counts"]["total"], 0)
        self.assertEqual(baseline["historical_backfill"], 0)
        self.assertFalse(baseline["validation_consumed"])

    def test_valid_live_record_is_exactly_bound_and_non_trading(self) -> None:
        self.assertEqual(validate_record(self._record()), [])

    def test_time_gated_replay_may_reference_pre_cutoff_market_time(self) -> None:
        record = self._record("TIME_GATED_REPLAY")
        record["market_window_start_utc"] = "2024-01-01T09:00:00Z"
        record["market_window_end_utc"] = "2024-01-01T09:15:00Z"
        record["trigger_first_valid_at"] = "2024-01-01T09:15:00Z"
        record["record_id"] = deterministic_record_id(record)
        self.assertEqual(validate_record(record), [])

    def test_non_evidentiary_replay_cannot_carry_boundary_friction(self) -> None:
        record = self._record("NON_EVIDENTIARY_REPLAY")
        record["sequence_boundary_friction"] = True
        self.assertIn(
            "NON_EVIDENTIARY_REPLAY cannot carry sequence-boundary-friction weight",
            validate_record(record),
        )

    def test_live_record_before_c2_g6_fails_closed(self) -> None:
        record = self._record()
        record["market_window_start_utc"] = "2026-07-26T19:00:00Z"
        record["market_window_end_utc"] = "2026-07-26T19:15:00Z"
        record["trigger_first_valid_at"] = "2026-07-26T19:15:00Z"
        record["review_created_at_utc"] = "2026-07-26T20:00:00Z"
        record["record_id"] = deterministic_record_id(record)
        self.assertIn(
            "LIVE_PROSPECTIVE timestamps are not strictly after C2-G6 opening",
            validate_record(record),
        )

    def test_trigger_must_be_inside_market_window(self) -> None:
        record = self._record()
        record["trigger_first_valid_at"] = "2026-07-27T09:30:00Z"
        record["record_id"] = deterministic_record_id(record)
        self.assertIn("trigger_first_valid_at is outside the market window", validate_record(record))

    def test_review_must_follow_market_window(self) -> None:
        record = self._record()
        record["review_created_at_utc"] = "2026-07-27T09:10:00Z"
        self.assertIn("review creation precedes market-window completion", validate_record(record))

    def test_old_timestamp_fields_are_rejected(self) -> None:
        record = self._record()
        record["observation_start_utc"] = record["market_window_start_utc"]
        self.assertIn("unexpected fields: observation_start_utc", validate_record(record))

    def test_non_utc_offset_is_rejected(self) -> None:
        record = self._record()
        record["market_window_start_utc"] = "2026-07-27T10:00:00+01:00"
        record["record_id"] = deterministic_record_id(record)
        self.assertTrue(any("timestamp must use UTC" in error for error in validate_record(record)))

    def test_operation_mode_changes_deterministic_identity(self) -> None:
        live = self._record("LIVE_PROSPECTIVE")
        replay = self._record("TIME_GATED_REPLAY")
        self.assertNotEqual(live["record_id"], replay["record_id"])

    def test_jsonl_counts_only_live_rows_as_prospective_evidence(self) -> None:
        records = [self._record("LIVE_PROSPECTIVE"), self._record("TIME_GATED_REPLAY")]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
            counts = validate_jsonl(path)
        self.assertEqual(counts["total"], 2)
        self.assertEqual(counts["live_prospective"], 1)
        self.assertEqual(counts["time_gated_replay"], 1)
        self.assertEqual(counts["prospective_evidence"], 1)

    def test_wrong_release_fails_closed(self) -> None:
        record = self._record()
        record["active_release_id"] = "OTHER"
        self.assertIn("record is not bound to the active C2 Discovery release", validate_record(record))

    def test_trading_authority_is_rejected(self) -> None:
        record = self._record()
        record["trading_authority"] = "ACTIVE"
        self.assertIn("trading_authority must remain NONE", validate_record(record))

    def test_registry_uses_v0_2_and_retains_boundaries(self) -> None:
        text = REGISTRY.read_text(encoding="utf-8")
        self.assertIn("c2_prospective_evidence_record_v0_2.schema.json", text)
        self.assertIn("C2_PROSPECTIVE_EVIDENCE_ACCUMULATION_CONTRACT_v0_2.md", text)
        self.assertIn("LIVE_PROSPECTIVE", text)
        self.assertIn("TIME_GATED_REPLAY", text)
        self.assertIn("NON_EVIDENTIARY_REPLAY", text)
        self.assertIn("append_mode: APPEND_ONLY", text)
        self.assertIn("c2e_authority: NONE", text)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", text)
        self.assertIn("next_gate: CAPTURE_FIRST_REAL_PROSPECTIVE_EVIDENCE_BATCH", text)

    def test_contract_rejects_legacy_seed_material(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("old 202-story programme", text)
        self.assertIn("B-STATE-0.3b", text)
        self.assertIn("cannot seed or count as WP7 prospective evidence", text)
        self.assertIn("Only this mode increments prospective-evidence counts", text)


if __name__ == "__main__":
    unittest.main()
