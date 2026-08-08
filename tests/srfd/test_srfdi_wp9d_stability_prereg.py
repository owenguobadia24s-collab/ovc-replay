from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.stability_metrics_v04 import (
    ambiguity_rate,
    chronological_stability,
    family_survival_rate,
    qualifies_adjacent_sensitivity,
    qualifies_cross_method,
    residual_rate,
    validate_metric_registry,
)
from ovc.opt_b.srfd.wp10_preflight import validate_frozen_stability_metric_rules

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "registries/research/srfd/stability_metric_specs_v0_4.json"
PREREG = ROOT / "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_4.json"
V03 = ROOT / "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_3.json"


def catalog(*families: tuple[str, list[str]], residual: list[str] | None = None, noise: list[str] | None = None) -> dict:
    return {
        "families": [{"family_id": family_id, "member_ids": members} for family_id, members in families],
        "residual_ids": residual or [],
        "noise_ids": noise or [],
    }


class SRFDIWP9DStabilityPreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(REGISTRY.read_text())
        cls.prereg = json.loads(PREREG.read_text())
        cls.v03 = json.loads(V03.read_text())

    def test_registry_and_preregistration_are_exactly_hash_bound(self) -> None:
        self.assertEqual(
            "69994c70e44a9057e364ba5251bc8d4d7e3b85de507af9847012f67f004461a3",
            validate_metric_registry(self.registry),
        )
        self.assertEqual(self.registry["stability_metric_specs"], self.prereg["stability_metric_specs"])
        self.assertEqual(self.registry["metric_order"], self.prereg["stability_metrics"])
        self.assertEqual("STABILITY_AND_AMBIGUITY_METRIC_EXECUTION_SPECIFICATION_ONLY", self.prereg["supersession"]["supersession_scope"])
        self.assertEqual("acb27ff21d4df6da6ea72972bda7a6ee1ce28a7f06827b949f55d8b03ec04bb5", self.prereg["supersession"]["base_preregistration_logical_sha256"])
        validate_frozen_stability_metric_rules(self.prereg)

    def test_v03_remains_immutable_and_all_other_surfaces_are_declared_unchanged(self) -> None:
        self.assertEqual("SEGMENTATION_EXECUTION_SPECIFICATION_ONLY", self.v03["supersession"]["supersession_scope"])
        inherited = self.prereg["inherited_frozen_surfaces"]
        self.assertEqual("UNCHANGED", inherited["representation_grid"])
        self.assertEqual("UNCHANGED", inherited["distance_grid"])
        self.assertEqual("UNCHANGED", inherited["family_method_grid"])
        self.assertEqual("UNCHANGED", inherited["sensitivity_family_parameter_ladders"])
        self.assertEqual("UNCHANGED_FROZEN_V0_3", inherited["segmentation_execution_specification"])
        self.assertEqual("UNCHANGED", inherited["source_binding_procedure"])
        self.assertEqual("UNCHANGED", inherited["population_binding_procedure"])

    def test_residual_rate_has_explicit_population_denominator(self) -> None:
        result = residual_rate(catalog(("F1", ["a", "b"]), residual=["c"], noise=["d"]))
        self.assertEqual((2, 4, "2/4"), (result["numerator"], result["denominator"], result["rate"]))
        empty = residual_rate(catalog())
        self.assertIsNone(empty["rate"])
        self.assertEqual("EMPTY_ASSIGNMENT_DOMAIN", empty["reason_code"])

    def test_ambiguity_is_exact_best_jaccard_tie_without_forced_winner(self) -> None:
        left = catalog(("A", ["a", "b"]), residual=["z"])
        right = catalog(("X", ["a"]), ("Y", ["b"]), residual=["z"])
        result = ambiguity_rate(left, right)
        self.assertEqual((2, 2, "2/2"), (result["numerator"], result["denominator"], result["rate"]))
        self.assertEqual(["X", "Y"], result["ambiguous_families"][0]["counterpart_family_ids"])
        self.assertEqual("1/2", result["ambiguous_families"][0]["max_jaccard"])
        self.assertNotIn("z", str(result["ambiguous_families"]))

    def test_cross_sensitivity_uses_full_anchor_containment_and_adjacent_rungs_only(self) -> None:
        left = catalog(("A", ["a", "b"]), ("B", ["c"]))
        right = catalog(("X", ["a", "b", "d"]), ("Y", ["c"]))
        result = family_survival_rate(left, right, metric_id="CROSS_SENSITIVITY_SURVIVAL_WITH_DENOMINATOR")
        self.assertEqual((2, 2, "2/2"), (result["numerator"], result["denominator"], result["rate"]))
        base = {"representation_id":"R1", "distance_id":"GOWER_MIXED", "family_method_id":"M", "parameters":{"radius":"0.04", "minimum_support":2}}
        adjacent = {**base, "parameters":{"radius":"0.08", "minimum_support":2}}
        jumped = {**base, "parameters":{"radius":"0.16", "minimum_support":2}}
        ladders = {"radius":["0.04","0.08","0.16"], "minimum_support":[2,4,8]}
        self.assertTrue(qualifies_adjacent_sensitivity(base, adjacent, ladders))
        self.assertFalse(qualifies_adjacent_sensitivity(base, jumped, ladders))

    def test_cross_method_requires_exact_member_set_and_shared_support(self) -> None:
        left = catalog(("A", ["a", "b"]), ("B", ["c"]))
        right = catalog(("X", ["a", "b"]), ("Y", ["c", "d"]))
        result = family_survival_rate(left, right, metric_id="CROSS_METHOD_CORRESPONDENCE_WITH_DENOMINATOR")
        self.assertEqual((1, 2, "1/2"), (result["numerator"], result["denominator"], result["rate"]))
        a = {"representation_id":"R1", "distance_id":"GOWER_MIXED", "family_method_id":"M1", "shared_minimum_support":4}
        b = {**a, "family_method_id":"M2"}
        c = {**b, "shared_minimum_support":8}
        self.assertTrue(qualifies_cross_method(a, b))
        self.assertFalse(qualifies_cross_method(a, c))

    def test_chronological_metric_is_fixed_temporal_span_not_refit(self) -> None:
        fam = catalog(("A", ["a", "b"]), ("B", ["c"]), residual=["r"])
        times = {
            "a":"2026-06-02T00:00:00Z",
            "b":"2026-06-20T00:00:00Z",
            "c":"2026-06-03T00:00:00Z",
            "r":"2026-06-25T00:00:00Z",
        }
        result = chronological_stability(fam, times)
        self.assertEqual((1, 2, "1/2"), (result["numerator"], result["denominator"], result["rate"]))
        self.assertEqual(
            [["2026-06-01T00:00:00Z", "2026-06-16T00:00:00Z"], ["2026-06-16T00:00:00Z", "2026-07-01T00:00:00Z"]],
            result["chronology_partitions"],
        )
        self.assertIn("NOT_INDEPENDENT_HALF_SAMPLE_REFIT_STABILITY", result["interpretation"])

    def test_candidate_preserves_unused_authority_and_no_result_exposure(self) -> None:
        self.assertFalse(self.prereg["authority_transition"]["current_v0_3_token_consumed"])
        self.assertFalse(self.prereg["construction_firewall"]["june_benchmark_started"])
        self.assertFalse(self.prereg["construction_firewall"]["june_scientific_outputs_inspected"])
        self.assertEqual("DENIED", self.prereg["construction_firewall"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.prereg["construction_firewall"]["validation_2025"])


if __name__ == "__main__":
    unittest.main()
