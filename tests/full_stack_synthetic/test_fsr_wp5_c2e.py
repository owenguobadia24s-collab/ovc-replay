from __future__ import annotations

import dataclasses
import tempfile
import unittest
from pathlib import Path

from ovc.opt_a.fsr_synthetic import build_opt_a_fixture, c1_handoff_records
from ovc.opt_b.c1.builder import build as build_c1
from ovc.opt_b.c2_vnext.fsr_rehearsal_strict import run_fsr_c2_vnext_strict
from ovc.opt_b.market_grammar.fsr_c2e_adapter import c2e_inputs, run_fsr_c2e

REPO_ROOT = Path(__file__).resolve().parents[2]


def _c1_stream(handoff: list[dict]) -> list[dict]:
    output: list[dict] = []
    for clock in ("15M", "2H_A_L"):
        for side in ("BID", "ASK"):
            group = sorted(
                (item for item in handoff if item["clock_id"] == clock and item["price_side"] == side),
                key=lambda item: item["open_time"],
            )
            prior = None
            for current in group:
                output.append(dataclasses.asdict(build_c1(current, prior)))
                prior = current
    return output


class FSRWP5C2ETests(unittest.TestCase):
    def test_existing_shadow_c2e_consumes_only_fresh_c2_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            opt_a = build_opt_a_fixture(Path(root) / "fixture", repo_root=REPO_ROOT)
            c1 = _c1_stream(c1_handoff_records(opt_a))
            c2 = run_fsr_c2_vnext_strict(opt_a, c1)
            first = run_fsr_c2e(c2)
            second = run_fsr_c2e(c2)

            self.assertEqual(first["logical_sha256"], second["logical_sha256"])
            self.assertEqual(first["source_c2_logical_sha256"], c2["logical_sha256"])
            self.assertEqual(set(first["input_counts"]), {"BID", "ASK"})
            self.assertGreater(first["input_counts"]["BID"], 0)
            self.assertGreater(first["input_counts"]["ASK"], 0)
            self.assertGreaterEqual(first["episode_count"], 4)
            self.assertGreaterEqual(first["boundary_counts"].get("RESET", 0), 2)
            self.assertGreaterEqual(first["status_counts"].get("CENSORED", 0), 2)
            self.assertGreaterEqual(first["status_counts"].get("OPEN_AT_CUTOFF", 0), 2)
            self.assertFalse(first["hidden_construction_consumed"])
            self.assertEqual(first["authority"]["canonical_episode_definition"], "NONE")
            self.assertEqual(first["authority"]["c2g_promotion"], "NONE")
            self.assertEqual(first["authority"]["validation_consumption"], "DENIED")
            self.assertEqual(first["authority"]["publication"], "NONE")

            for side in ("BID", "ASK"):
                inputs = c2e_inputs(c2, side=side)
                self.assertEqual(len(inputs), first["input_counts"][side])
                self.assertEqual(len({item["first_valid_time"] for item in inputs}), len(inputs))
                self.assertEqual(len({item["record_id"] for item in inputs}), len(inputs))
                self.assertTrue(all(len(item["source_sha256"]) == 64 for item in inputs))
                self.assertTrue(all(item["parent_record_id"] is None for item in inputs))
                resets = [item for item in inputs if item["reset_reason"]]
                self.assertGreaterEqual(len(resets), 1)

            for ledger in first["ledgers"]:
                self.assertEqual(ledger["authority_state"], "SHADOW_EXPERIMENT")
                self.assertEqual(ledger["source_release_id"], opt_a["fixture_id"])
                self.assertEqual(ledger["instrument_id"], "GBPUSD")
                self.assertEqual(ledger["scope_id"], "FSR.REVISED_C2.LOCAL")
                self.assertEqual(ledger["clock_id"], "15M")
                self.assertTrue(all(episode["semantic_state"] == "NEUTRAL_NON_SEMANTIC_NON_PREDICTIVE" for episode in ledger["episodes"]))


if __name__ == "__main__":
    unittest.main()
