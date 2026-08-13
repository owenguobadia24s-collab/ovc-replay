from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.opt_b.c2p_v0_2.adapters import read_synthetic_source
from ovc.opt_b.c2p_v0_2.candidate import extract_candidate
from ovc.opt_b.c2p_v0_2.chronology import ChronologyError, validate_causal_times
from ovc.opt_b.c2p_v0_2.tracklet import TrackletError, append_candidate, censor_tracklet, expire_tracklet, open_tracklet

ROOT = Path(__file__).resolve().parents[4]
PACK = json.loads((ROOT / "fixtures/opt_b/c2p/v0_2/packs/C2P_SYNTH_OBJECTPACK_MINIMAL_A_v1.json").read_text(encoding="utf-8"))


def source(step: int, *, structure: str = "L1", partition: str = "P1", available: bool = True):
    return {
        "candidate_present": True,
        "source_available": available,
        "source_lineage_envelope_id": f"SYNTH.LINEAGE.{step}",
        "source_refs": [f"SYNTH:C2:{step}", f"SYNTH:C2E:{step}"],
        "market_effective_start": f"2026-01-01T00:{step:02d}:00Z",
        "market_effective_end": None,
        "first_valid_time": f"2026-01-01T00:{step:02d}:01Z",
        "evaluation_cutoff": f"2026-01-01T00:{step:02d}:02Z",
        "fixture_partition_id": partition,
        "fixture_structure_key": structure,
        "fixture_step": step,
        "coordinate_class": "C1",
        "identity_defining_geometry": {"coordinate": str(100 + step)},
    }


class C2P2WP2CandidateTrackletTests(unittest.TestCase):
    def test_candidate_is_deterministic_and_source_bound(self):
        a = extract_candidate(source(1), PACK)
        b = extract_candidate(source(1), PACK)
        self.assertEqual(a.candidate, b.candidate)
        self.assertEqual(a.computability, "AVAILABLE")
        self.assertEqual(len(a.candidate["candidate_id"]), 64)
        self.assertEqual(a.candidate["hard_scope"], {"instrument": "SYNTH", "side": "SYNTH", "scale": "STEP", "partition_id": "P1"})
        self.assertEqual(a.candidate["source_refs"], ["SYNTH:C2:1", "SYNTH:C2E:1"])

    def test_missing_or_unavailable_source_fails_closed(self):
        missing = source(1)
        del missing["fixture_structure_key"]
        result = read_synthetic_source(missing, PACK)
        self.assertIsNone(result.candidate)
        self.assertEqual(result.computability, "NOT_EVALUABLE")
        unavailable = read_synthetic_source(source(1, available=False), PACK)
        self.assertIsNone(unavailable.candidate)
        self.assertEqual(unavailable.computability, "SOURCE_UNAVAILABLE")

    def test_forbidden_reverse_or_semantic_source_fields_are_rejected(self):
        bad = source(1)
        bad["raw_price"] = "1.2500"
        bad["family_label"] = "FAMILY_X"
        result = read_synthetic_source(bad, PACK)
        self.assertIsNone(result.candidate)
        self.assertEqual(result.reason_codes, ("C2P_FORBIDDEN_SOURCE_FIELD:family_label", "C2P_FORBIDDEN_SOURCE_FIELD:raw_price"))

    def test_causal_time_validation_rejects_hindsight_and_invalid_interval(self):
        with self.assertRaisesRegex(ChronologyError, "C2P_FVT_AFTER_CUTOFF"):
            validate_causal_times(market_effective_start="2026-01-01T00:00:00Z", market_effective_end=None, first_valid_time="2026-01-01T00:00:03Z", evaluation_cutoff="2026-01-01T00:00:02Z")
        with self.assertRaisesRegex(ChronologyError, "C2P_EFFECTIVE_END_BEFORE_START"):
            validate_causal_times(market_effective_start="2026-01-01T00:00:02Z", market_effective_end="2026-01-01T00:00:01Z", first_valid_time="2026-01-01T00:00:02Z", evaluation_cutoff="2026-01-01T00:00:03Z")

    def test_tracklet_stages_are_distinct_and_confirmation_requires_three_members(self):
        candidates = [extract_candidate(source(i), PACK).candidate for i in (1, 2, 3)]
        tracklet = open_tracklet(candidates[0], PACK)
        self.assertEqual(tracklet["state"], "OPEN")
        self.assertEqual(tracklet["member_candidate_ids"], [candidates[0]["candidate_id"]])
        tracklet = append_candidate(tracklet, candidates[1], PACK)
        self.assertEqual(tracklet["state"], "OPEN")
        tracklet = append_candidate(tracklet, candidates[2], PACK)
        self.assertEqual(tracklet["state"], "CONFIRMED")
        self.assertEqual(tracklet["decision_frontier"]["evaluated_candidate_count"], 3)
        self.assertNotEqual(tracklet["tracklet_id"], candidates[0]["candidate_id"])

    def test_equal_competitor_preserves_ambiguity_and_no_promotion(self):
        candidates = [extract_candidate(source(i), PACK).candidate for i in (1, 2, 3)]
        tracklet = open_tracklet(candidates[0], PACK)
        tracklet = append_candidate(tracklet, candidates[1], PACK)
        tracklet = append_candidate(tracklet, candidates[2], PACK, equally_lawful_competitor=True)
        self.assertEqual(tracklet["state"], "AMBIGUOUS")
        self.assertEqual(tracklet["evaluation_state"], "AMBIGUOUS")
        self.assertNotEqual(tracklet["state"], "PROMOTED")

    def test_hard_scope_mismatch_duplicate_censor_and_expiry_are_fail_honest(self):
        c1 = extract_candidate(source(1), PACK).candidate
        c2 = extract_candidate(source(2, partition="P2"), PACK).candidate
        tracklet = open_tracklet(c1, PACK)
        with self.assertRaisesRegex(TrackletError, "C2P_HARD_SCOPE_MISMATCH"):
            append_candidate(tracklet, c2, PACK)
        with self.assertRaisesRegex(TrackletError, "C2P_DUPLICATE_CANDIDATE"):
            append_candidate(tracklet, c1, PACK)
        censored = censor_tracklet(tracklet, cutoff="2026-01-01T00:05:00Z")
        self.assertEqual(censored["state"], "CENSORED")
        self.assertEqual(censored["observability_state"], "CENSORED")
        self.assertNotEqual(censored["state"], "EXPIRED")
        with self.assertRaisesRegex(TrackletError, "C2P_EXPLICIT_EXPIRY_SIGNAL_REQUIRED"):
            expire_tracklet(tracklet, cutoff="2026-01-01T00:06:00Z", explicit_signal=False)
        expired = expire_tracklet(tracklet, cutoff="2026-01-01T00:06:00Z", explicit_signal=True)
        self.assertEqual(expired["state"], "EXPIRED")


if __name__ == "__main__":
    unittest.main()
