from __future__ import annotations

import unittest

from ovc.opt_b.srfd.family_capacity import (
    profile_family_method_equivalence,
    render_family_profile_line,
)


class SRFDIG8RWP3CapacityReceiptOutputTest(unittest.TestCase):
    def test_zzzz_emit_github_hosted_family_capacity_receipt(self) -> None:
        receipt = profile_family_method_equivalence((48, 96))
        self.assertTrue(
            all(
                method["logical_equivalence"]
                for rung in receipt["rungs"].values()
                for method in rung["methods"].values()
            )
        )
        self.assertFalse(receipt["june_market_records_read"])
        self.assertFalse(receipt["validation_consumed"])
        self.assertEqual("NONE", receipt["scientific_delta"])
        print(render_family_profile_line(receipt))


if __name__ == "__main__":
    unittest.main()
