from __future__ import annotations

import dataclasses
import tempfile
import unittest
from pathlib import Path

from ovc.opt_a.fsr_synthetic import build_opt_a_fixture, c1_handoff_records
from ovc.opt_b.c1.builder import build as build_c1
from ovc.opt_b.c2_vnext.fsr_rehearsal_strict import run_fsr_c2_vnext_strict
from ovc.opt_b.market_grammar.fsr_c2e_adapter import run_fsr_c2e
from ovc.opt_b.market_grammar.fsr_grammar_adapter import run_fsr_market_grammar
from ovc.opt_b.srfd.fsr_adapter import run_fsr_srfd

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


class FSRWP8MarketGrammarTests(unittest.TestCase):
    def test_existing_shadow_grammar_is_not_relabelled_as_forward_c2p_or_c3(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            opt_a = build_opt_a_fixture(Path(root) / "fixture", repo_root=REPO_ROOT)
            c1 = _c1_stream(c1_handoff_records(opt_a))
            c2 = run_fsr_c2_vnext_strict(opt_a, c1)
            c2e = run_fsr_c2e(c2)
            srfd = run_fsr_srfd(c2, c2e)
            first = run_fsr_market_grammar(c2, c2e, srfd)
            second = run_fsr_market_grammar(c2, c2e, srfd)

            self.assertEqual(first["logical_sha256"], second["logical_sha256"])
            self.assertFalse(first["hidden_construction_consumed"])
            self.assertEqual(first["authority"]["forward_c3_authority"], "NONE")
            self.assertEqual(first["authority"]["forward_c2p_authority"], "NONE")
            self.assertTrue(first["authority"]["legacy_parser_namespace_only"])
            self.assertEqual(first["authority"]["canonical_grammar"], "NONE")
            self.assertEqual(first["authority"]["semantic_promotion"], "NONE")
            self.assertEqual(first["authority"]["publication"], "NONE")
            self.assertEqual(first["authority"]["validation_consumption"], "DENIED")

            if first["status"] == "EXECUTED_SHADOW":
                self.assertGreater(first["grammar_count"], 0)
                self.assertEqual(first["grammar_count"], len(first["parse_results"]))
                self.assertTrue(all(item["canonical"] is False for item in first["grammar_releases"]))
                self.assertTrue(all(item["published"] is False for item in first["grammar_releases"]))
                self.assertTrue(all(item["authority_state"] == "SHADOW_EXPERIMENT" for item in first["grammar_releases"]))
                self.assertTrue(all(item["forward_c2p_interpretation"] == "PROHIBITED_NAMESPACE_REUSE" for item in first["parse_results"]))
                self.assertTrue(all(item["legacy_parser_id"].startswith("C2P.PARSE.") for item in first["parse_results"]))
                self.assertTrue(all(item["first_valid_time"] for item in first["parse_results"]))
                self.assertTrue(set(first["parse_status_counts"]).issubset({"GRAMMAR_MATCH", "PARTIAL_MATCH", "NO_MATCH", "AMBIGUOUS_MATCH"}))
            else:
                self.assertIn(first["status"], {"NOT_REACHED_NO_FAMILY_EVIDENCE", "NOT_REACHED_NO_LAWFUL_SEED"})
                self.assertEqual(first["grammar_count"], 0)


if __name__ == "__main__":
    unittest.main()
