from __future__ import annotations

import unittest

from ovc.development.skills.vit_shadow import ShadowPrediction, compare_shadow_prediction, q3_shadow_pass


class DsaiVitV03Wp8ATests(unittest.TestCase):
    def test_exact_shadow_tree_prediction_passes_without_vit_write(self) -> None:
        prediction = ShadowPrediction("P","WP","pr:1","a"*40,"b"*40,"c"*40,"receipt:predicted",False)
        comparison = compare_shadow_prediction(prediction,"d"*40,"c"*40,complete_receipt_chain=True)
        self.assertTrue(comparison.tree_equal)
        self.assertFalse(comparison.mismatch_attributable_to_vit)
        self.assertFalse(comparison.physical_write_performed_by_vit)
        self.assertTrue(q3_shadow_pass((comparison,)))

    def test_shadow_mismatch_or_missing_receipt_fails(self) -> None:
        prediction = ShadowPrediction("P","WP","pr:1","a"*40,"b"*40,"c"*40,"receipt:predicted",False)
        mismatch = compare_shadow_prediction(prediction,"d"*40,"e"*40,complete_receipt_chain=True)
        missing = compare_shadow_prediction(prediction,"d"*40,"c"*40,complete_receipt_chain=False)
        self.assertFalse(q3_shadow_pass((mismatch,)))
        self.assertFalse(q3_shadow_pass((missing,)))

    def test_empty_shadow_population_cannot_pass(self) -> None:
        self.assertFalse(q3_shadow_pass(()))


if __name__ == "__main__":
    unittest.main()
