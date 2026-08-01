from __future__ import annotations

import unittest

from ovc.opt_b.c1.adapter import adapt as adapt_price_parent
from ovc.opt_b.c2.adapter import accept_c1_record
from ovc.research_operations.prospective_source import full_month_mdr_replay as subject
from ovc.research_operations.prospective_source.models import ProspectiveBar


def complete_bar() -> ProspectiveBar:
    return ProspectiveBar(
        bar_id="pd-june-fm-corr2:test-bar",
        clock="15M",
        side="BID",
        start_utc="2026-06-01T00:00:00Z",
        end_utc="2026-06-01T00:15:00Z",
        open="1.25000",
        high="1.25100",
        low="1.24900",
        close="1.25050",
        volume="1",
        parent_source_object_ids=("RPS.M1BAR.TEST",),
        quality_state="COMPLETE",
    )


class PDJuneFullMonthMDRWP2Corr2Tests(unittest.TestCase):
    def test_replay_ids_use_frozen_prospective_namespaces(self) -> None:
        self.assertTrue(subject.PRICE_SET_ID.startswith("RPS.PRICESET."))
        self.assertTrue(subject.SOURCE_MANIFEST_ID.startswith("RPS.SOURCE-MANIFEST."))
        self.assertTrue(subject.C1_SET_ID.startswith("RPS.C1SET."))
        self.assertTrue(subject.C1_MANIFEST_ID.startswith("RPS.C1MANIFEST."))

    def test_price_payload_is_accepted_by_frozen_c1_adapter(self) -> None:
        payload = subject.price_payload(complete_bar(), "SRC.DUKASCOPY.TEST")
        self.assertTrue(payload["source_bar_id"].startswith("rps-price:"))
        accepted = adapt_price_parent(payload)
        self.assertEqual(accepted.release_id, subject.PRICE_SET_ID)
        self.assertEqual(accepted.manifest_id, subject.SOURCE_MANIFEST_ID)
        self.assertEqual(accepted.authority_state, subject.DERIVED_AUTHORITY)

    def test_generated_c1_record_is_accepted_by_frozen_c2_adapter(self) -> None:
        records, reset_count = subject.build_c1_records(
            [complete_bar()],
            "SRC.DUKASCOPY.TEST",
        )
        self.assertEqual(reset_count, 0)
        self.assertEqual(len(records), 1)
        accepted = accept_c1_record(records[0])
        self.assertEqual(
            accepted["handoff_status"],
            "ACCEPTED_RPS_TIME_GATED_REPLAY_WITH_EXACT_PRICE_PARENT",
        )
        self.assertEqual(accepted["c1_release_id"], subject.C1_SET_ID)
        self.assertEqual(accepted["opt_a_release_id"], subject.PRICE_SET_ID)
        self.assertTrue(accepted["source_bar_id"].startswith("rps-price:"))


if __name__ == "__main__":
    unittest.main()
