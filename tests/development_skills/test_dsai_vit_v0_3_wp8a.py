from __future__ import annotations
import unittest
from ovc.development.skills.vit_shadow import ShadowPrediction, compare_shadow_prediction, q3_shadow_pass

class DsaiVitV03Wp8ATests(unittest.TestCase):
    def test_exact_shadow_tree_prediction_passes_without_vit_write(self):
        p=ShadowPrediction("P","WP","pr:1","a"*40,"b"*40,"c"*40,"receipt",False)
        c=compare_shadow_prediction(p,"d"*40,"c"*40,complete_receipt_chain=True)
        self.assertTrue(q3_shadow_pass((c,)))
        self.assertFalse(c.physical_write_performed_by_vit)

    def test_mismatch_missing_receipt_and_empty_fail(self):
        p=ShadowPrediction("P","WP","pr:1","a"*40,"b"*40,"c"*40,"receipt",False)
        self.assertFalse(q3_shadow_pass((compare_shadow_prediction(p,"d"*40,"e"*40,complete_receipt_chain=True),)))
        self.assertFalse(q3_shadow_pass((compare_shadow_prediction(p,"d"*40,"c"*40,complete_receipt_chain=False),)))
        self.assertFalse(q3_shadow_pass(()))

if __name__ == "__main__":
    unittest.main()
