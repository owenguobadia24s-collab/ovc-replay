from __future__ import annotations

from copy import deepcopy
import unittest

from ovc.opt_b.srfd.representation import (
    NormalizationPack,
    RepresentationError,
    RepresentationPack,
    check_comparable,
    compile_population,
    compile_representation,
    fit_minmax_normalization,
)


class SRFDIWP2RepresentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = [
            {"record_id":"C2.1","first_valid_time":"2026-06-01T00:00:00Z","structural":{"location":"0.2","motion":"0.4"},"instrument":"GBPUSD","side":"BID","units":"DIMENSIONLESS","clock":"2H_A_L","representation_schema":"C2.FX","source_quality":"COMPLETE"},
            {"record_id":"C2.2","first_valid_time":"2026-06-01T02:00:00Z","structural":{"location":"0.8","motion":"0.6"},"instrument":"GBPUSD","side":"BID","units":"DIMENSIONLESS","clock":"2H_A_L","representation_schema":"C2.FX","source_quality":"COMPLETE"},
        ]
        self.raw_pack = RepresentationPack("REP.RAW.1","SRFDI-R1","R0",("location","motion"),"FIXTURE_SAME_DOMAIN_v0_1")

    def test_population_is_order_independent_and_exclusions_visible(self) -> None:
        values = self.records + [{"record_id":"C2.X","first_valid_time":"2026-06-01T04:00:00Z","structural":{},"computability_status":"NOT_EVALUABLE","not_evaluable_reason":"SOURCE_GAP"}]
        first = compile_population(values, population_name="fixture")
        second = compile_population(reversed(values), population_name="fixture")
        self.assertEqual(first["population_id"], second["population_id"])
        self.assertEqual(["C2.X"], [item["record_id"] for item in first["exclusions"]])

    def test_raw_representation_does_not_mutate_source(self) -> None:
        source = deepcopy(self.records[0])
        before = deepcopy(source)
        output = compile_representation(source,self.raw_pack,source_population_id="POP.FX")
        self.assertEqual(before, source)
        self.assertEqual({"location":"0.2","motion":"0.4"}, output["structural_raw"])
        self.assertEqual({}, output["structural_normalized"])

    def test_missing_required_dimension_fails_without_zero_imputation(self) -> None:
        source = deepcopy(self.records[0]); source["structural"].pop("motion")
        with self.assertRaisesRegex(RepresentationError,"REP_REQUIRED_DIMENSION_MISSING"):
            compile_representation(source,self.raw_pack,source_population_id="POP.FX")
        missing_pack = RepresentationPack("REP.MISS.1","SRFDI-R8","R8",("location","motion"),"FIXTURE_SAME_DOMAIN_v0_1")
        output = compile_representation(source,missing_pack,source_population_id="POP.FX")
        self.assertEqual(["motion"], output["missingness"])
        self.assertNotIn("motion", output["structural_raw"])
        self.assertTrue(output["comparison_only"]["missingness_mask"]["motion"])

    def test_normalization_fit_is_frozen_and_cutoff_safe(self) -> None:
        norm = fit_minmax_normalization(self.records,("location","motion"),fit_population_id="POP.FIT",fit_cutoff="2026-06-01T02:00:00Z")
        pack = RepresentationPack("REP.NORM.1","SRFDI-R4","R1",("location","motion"),"FIXTURE_SAME_DOMAIN_v0_1")
        output = compile_representation(self.records[0],pack,source_population_id="POP.FX",normalization_pack=norm)
        self.assertEqual("0", output["structural_normalized"]["location"])
        self.assertEqual("0", output["structural_normalized"]["motion"])
        self.assertEqual("0.2", output["structural_raw"]["location"])
        later = [*self.records,{"record_id":"C2.3","first_valid_time":"2026-06-01T04:00:00Z","structural":{"location":"1","motion":"1"}}]
        with self.assertRaisesRegex(RepresentationError,"REP_NORMALIZATION_FIT_CUTOFF_INVALID"):
            fit_minmax_normalization(later,("location",),fit_population_id="POP.BAD",fit_cutoff="2026-06-01T02:00:00Z")

    def test_forbidden_outcome_source_is_denied(self) -> None:
        source = {**self.records[0],"outcome":"UP"}
        with self.assertRaisesRegex(RepresentationError,"AUTH_SCOPE_EXPANSION"):
            compile_representation(source,self.raw_pack,source_population_id="POP.FX")

    def test_comparability_blocks_before_distance_surface(self) -> None:
        left = self.records[0]
        right = {**self.records[1],"instrument":"XAUUSD"}
        comparable, reason = check_comparable(left,right)
        self.assertFalse(comparable)
        self.assertEqual("COMP_NOT_COMPARABLE_INSTRUMENT", reason)
        comparable, reason = check_comparable(left,self.records[1])
        self.assertTrue(comparable); self.assertIsNone(reason)

    def test_all_representation_classes_are_constructible(self) -> None:
        for index in range(1,10):
            kwargs = {"representation_pack_id":f"REP.{index}","implementation_class_id":f"SRFDI-R{index}","architecture_candidate_id":"FX","required_fields":(),"comparability_domain_id":"FIXTURE_SAME_DOMAIN_v0_1"}
            self.assertEqual(f"SRFDI-R{index}", RepresentationPack(**kwargs).implementation_class_id)


if __name__ == "__main__":
    unittest.main()
