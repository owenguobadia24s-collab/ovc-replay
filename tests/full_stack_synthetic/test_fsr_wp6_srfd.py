from __future__ import annotations

import dataclasses
import tempfile
import unittest
from pathlib import Path

from ovc.opt_a.fsr_synthetic import build_opt_a_fixture, c1_handoff_records
from ovc.opt_b.c1.builder import build as build_c1
from ovc.opt_b.c2_vnext.fsr_rehearsal_strict import run_fsr_c2_vnext_strict
from ovc.opt_b.market_grammar.fsr_c2e_adapter import run_fsr_c2e
from ovc.opt_b.srfd.fsr_adapter import _representation_sets, run_fsr_srfd

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


class FSRWP6SRFDTests(unittest.TestCase):
    def test_fixture_local_method_neutral_benchmark_preserves_non_authority(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            opt_a = build_opt_a_fixture(Path(root) / "fixture", repo_root=REPO_ROOT)
            c1 = _c1_stream(c1_handoff_records(opt_a))
            c2 = run_fsr_c2_vnext_strict(opt_a, c1)
            c2e = run_fsr_c2e(c2)
            sets, metadata = _representation_sets(c2, c2e)
            first = run_fsr_srfd(c2, c2e)
            second = run_fsr_srfd(c2, c2e)

            self.assertEqual(first["logical_sha256"], second["logical_sha256"])
            self.assertEqual(set(first["representation_counts"]), {f"R{i}" for i in range(1, 10)})
            self.assertTrue(all(first["representation_counts"][f"R{i}"] > 0 for i in range(1, 10)))
            self.assertFalse(metadata["real_source_mapping_blocker_resolved"])
            self.assertEqual(metadata["mapping_authority"], "FSR_FIXTURE_ADAPTER_ONLY")
            self.assertTrue(all(item["first_valid_time"] >= metadata["fit_cutoff"] for item in sets["R4"]))

            for key in ("R1_L1", "R1_L2", "R1_GOWER", "R2_L1", "R3_DTW", "R4_L1", "R5_DTW", "R6_L1", "R7_L1", "R9_GOWER"):
                self.assertIn(key, first["distance_counts"])
                self.assertGreater(first["distance_counts"][key], 0)
                self.assertGreater(first["distance_status_counts"][key].get("COMPUTED", 0), 0)

            family = first["family_benchmark"]
            methods = {item["method_id"] for item in family["catalogs"]}
            self.assertEqual(methods, {"GREEDY_LEXICOGRAPHIC_MEDOID_STAR", "COMPLETE_LINKAGE", "AVERAGE_LINKAGE", "BOUNDED_PAM"})
            self.assertGreaterEqual(len(family["catalogs"]), 8)
            self.assertGreater(len(family["correspondences"]), 0)
            self.assertGreaterEqual(family["invariant_cores"]["catalog_denominator"], 8)
            self.assertGreaterEqual(family["method_disagreement"]["method_count"], 8)
            self.assertGreaterEqual(family["residual_count"], 0)
            self.assertTrue(set(family["evidence_status_counts"]).issubset({"FAMILY_EVIDENCE_PRESENT", "NO_STABLE_FAMILY"}))

            self.assertFalse(first["hidden_construction_consumed"])
            self.assertEqual(first["authority"]["real_source_field_mapping"], "UNRESOLVED_NOT_CHANGED")
            for field in (
                "canonical_representation", "canonical_normalization", "canonical_distance",
                "canonical_sensitivity", "canonical_family_method", "canonical_family", "selector", "publication",
            ):
                self.assertEqual(first["authority"][field], "NONE")
            self.assertEqual(first["authority"]["validation_consumption"], "DENIED")


if __name__ == "__main__":
    unittest.main()
