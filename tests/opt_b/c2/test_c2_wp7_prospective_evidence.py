from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.opt_b.validate_c2_wp7_prospective_evidence import deterministic_record_id, validate_record

ROOT = Path(__file__).resolve().parents[3]
BASELINE = ROOT / "fixtures/opt_b/c2/wp7/C2_PROSPECTIVE_EVIDENCE_ZERO_BASELINE.json"
REGISTRY = ROOT / "registries/research/C2_PROSPECTIVE_EVIDENCE_REGISTRY.yaml"
CONTRACT = ROOT / "contracts/opt_b/c2/C2_PROSPECTIVE_EVIDENCE_ACCUMULATION_CONTRACT_v0_1.md"


class C2WP7ProspectiveEvidenceTests(unittest.TestCase):
    def _record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "schema": "ovc-c2-prospective-evidence-record/v0.1",
            "record_id": "",
            "research_line_id": "RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1",
            "record_class": "STATE_FIDELITY_REVIEW",
            "evidence_status": "OBSERVED_UNREVIEWED",
            "instrument": "GBPUSD",
            "canonical_clock": "15M",
            "price_side": "BID",
            "observation_start_utc": "2026-07-27T09:00:00Z",
            "observation_end_utc": "2026-07-27T09:15:00Z",
            "created_at_utc": "2026-07-27T10:00:00Z",
            "author": "OWEN_VITAE",
            "active_release_id": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1",
            "active_manifest_id": "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1.r1",
            "active_manifest_sha256": "c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33",
            "source_object_ids": ["C2-STATE-EXAMPLE-001"],
            "summary": "Fixture-only state-fidelity observation.",
            "prospective": True,
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

    def test_valid_record_is_exactly_bound_and_non_trading(self) -> None:
        self.assertEqual(validate_record(self._record()), [])

    def test_wrong_release_fails_closed(self) -> None:
        record = self._record()
        record["active_release_id"] = "OTHER"
        self.assertIn("record is not bound to the active C2 Discovery release", validate_record(record))

    def test_trading_authority_is_rejected(self) -> None:
        record = self._record()
        record["trading_authority"] = "ACTIVE"
        self.assertIn("trading_authority must remain NONE", validate_record(record))

    def test_registry_is_append_only_and_c2e_deferred(self) -> None:
        text = REGISTRY.read_text(encoding="utf-8")
        self.assertIn("append_mode: APPEND_ONLY", text)
        self.assertIn("c2e_authority: NONE", text)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", text)
        self.assertIn("next_gate: C2_G7_PROSPECTIVE_EVIDENCE_OPERATION_ACCEPTANCE", text)

    def test_contract_rejects_legacy_seed_material(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("old 202-story programme", text)
        self.assertIn("B-STATE-0.3b", text)
        self.assertIn("cannot seed or count as WP7 evidence", text)


if __name__ == "__main__":
    unittest.main()
