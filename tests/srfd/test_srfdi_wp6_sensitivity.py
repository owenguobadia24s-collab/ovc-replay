from __future__ import annotations

import unittest

from ovc.opt_b.srfd.sensitivity import build_correspondence, build_invariant_cores, method_disagreement, run_configuration_grid, sensitivity_metrics


def catalog(catalog_id, method, cfg, families, residual=()):
    return {"family_catalog_id":catalog_id,"method_id":method,"configuration_id":cfg,"families":[{"family_id":fid,"member_ids":list(members)} for fid,members in families],"residual_ids":list(residual),"noise_ids":[],"evidence_status":"FAMILY_EVIDENCE_PRESENT" if families else "NO_STABLE_FAMILY"}


class SRFDIWP6SensitivityTests(unittest.TestCase):
    def test_correspondence_reports_split_and_merge_with_denominators(self) -> None:
        left = catalog("L","M","1",[("L1",("A","B","C","D"))])
        right = catalog("R","M","2",[("R1",("A","B")),("R2",("C","D"))])
        split = build_correspondence(left,right)
        self.assertEqual(1,len(split["split_events"])); self.assertEqual(1,split["left_family_denominator"]); self.assertEqual(2,split["right_family_denominator"])
        merge = build_correspondence(right,left)
        self.assertEqual(1,len(merge["merge_events"]))

    def test_invariant_core_support_has_explicit_denominator(self) -> None:
        a = catalog("A","M1","1",[("A1",("X","Y","Z"))])
        b = catalog("B","M2","2",[("B1",("X","Y")),("B2",("Z","Q"))])
        c = catalog("C","M3","3",[("C1",("X","Y","R"))])
        result = build_invariant_cores([c,a,b],minimum_catalog_support=2)
        self.assertEqual(3,result["catalog_denominator"])
        xy = next(core for core in result["cores"] if set(core["member_ids"]) >= {"X","Y"})
        self.assertEqual(3,xy["support_numerator"]); self.assertEqual(3,xy["support_denominator"])

    def test_method_disagreement_is_explicit_and_non_composite(self) -> None:
        a = catalog("A","MEDOID","1",[("F1",("X","Y"))],residual=("Z",))
        b = catalog("B","LINKAGE","1",[("F2",("X","Z"))],residual=("Y",))
        result = method_disagreement([b,a])
        self.assertGreater(result["disagreement_count"],0); self.assertEqual(3,result["record_denominator"]); self.assertIsNone(result["composite_score"])

    def test_sensitivity_metrics_keep_counts_and_no_hidden_score(self) -> None:
        a = catalog("A","M","1",[("F1",("X","Y"))],residual=("Z",))
        b = catalog("B","M","2",[],residual=("X","Y","Z"))
        metrics = sensitivity_metrics([b,a])
        self.assertEqual(["1","2"],[item["configuration_id"] for item in metrics])
        self.assertEqual("0.3333333333333333333333333333",metrics[0]["residual_rate"])
        self.assertEqual("NO_STABLE_FAMILY",metrics[1]["evidence_status"])
        self.assertTrue(all(item["composite_score"] is None for item in metrics))

    def test_configuration_grid_is_order_independent(self) -> None:
        configs = [{"configuration_id":"B","x":2},{"configuration_id":"A","x":1}]
        result = run_configuration_grid(reversed(configs),lambda cfg:{"configuration_id":cfg["configuration_id"],"value":cfg["x"]})
        self.assertEqual(["A","B"],[item["configuration_id"] for item in result])


if __name__ == "__main__":
    unittest.main()
