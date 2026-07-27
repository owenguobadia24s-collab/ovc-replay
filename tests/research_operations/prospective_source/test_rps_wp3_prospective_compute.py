from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from ovc.opt_b.c1.adapter import InputRejected
from ovc.opt_b.c1.builder import build as build_c1
from ovc.opt_b.c2.adapter import HandoffError, accept_c1_record
from ovc.research_operations.prospective_source.aggregation import aggregate_m1
from ovc.research_operations.prospective_source.models import ProspectiveBar, SourceBar
from ovc.research_operations.prospective_source.prospective_compute import (
    AUTHORITY_GATE,
    ComputeError,
    build_c1_records,
    execute,
    process_scope,
    prospective_price_payload,
)


UTC = timezone.utc


def stamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def complete_bars(count: int, *, side: str = "BID") -> list[ProspectiveBar]:
    start = datetime(2026, 6, 22, tzinfo=UTC)
    result: list[ProspectiveBar] = []
    for index in range(count):
        opened = start + timedelta(minutes=15 * index)
        closed = opened + timedelta(minutes=15)
        base = Decimal("1.15000") + Decimal(index) / Decimal("100000")
        result.append(
            ProspectiveBar(
                bar_id=f"RPS.BAR.TEST.{side}.{index:04d}",
                clock="15M",
                side=side,
                start_utc=stamp(opened),
                end_utc=stamp(closed),
                open=format(base, "f"),
                high=format(base + Decimal("0.00020"), "f"),
                low=format(base - Decimal("0.00010"), "f"),
                close=format(base + Decimal("0.00005"), "f"),
                volume="10",
                parent_source_object_ids=tuple(
                    f"RPS.M1BAR.TEST.{side}.{index:04d}.{minute:02d}"
                    for minute in range(15)
                ),
                quality_state="COMPLETE",
            )
        )
    return result


class RpsWp3ProspectiveComputeTests(unittest.TestCase):
    def test_m1_gap_produces_unavailable_parent_without_fill(self) -> None:
        start = datetime(2026, 6, 22, tzinfo=UTC)
        rows = []
        for index in range(120):
            if index == 31:
                continue
            price = Decimal("1.15000") + Decimal(index) / Decimal("100000")
            rows.append(
                SourceBar(
                    object_id=f"RPS.M1BAR.TEST.{index:03d}",
                    timestamp_utc=stamp(start + timedelta(minutes=index)),
                    side="BID",
                    open=price,
                    high=price + Decimal("0.00010"),
                    low=price - Decimal("0.00010"),
                    close=price,
                    volume=Decimal("1"),
                )
            )
        fifteen = aggregate_m1(
            rows,
            clock="15M",
            side="BID",
            admissible_cutoff_utc=stamp(start + timedelta(hours=2)),
        )
        two_h = aggregate_m1(
            rows,
            clock="2H_A_L",
            side="BID",
            admissible_cutoff_utc=stamp(start + timedelta(hours=2)),
        )
        self.assertEqual(len(fifteen), 8)
        self.assertEqual(
            sum(item.quality_state == "QUARANTINED_INCOMPLETE_PARENT_SET" for item in fifteen),
            1,
        )
        self.assertEqual(two_h[0].quality_state, "QUARANTINED_INCOMPLETE_PARENT_SET")
        self.assertIsNone(two_h[0].close)

    def test_c1_prospective_profile_reuses_exact_formula_engine(self) -> None:
        bar = complete_bars(1)[0]
        payload = prospective_price_payload(bar, "SRC.DUKASCOPY.GBPUSD.M1.BID.TEST")
        result = build_c1(payload)
        self.assertTrue(result.record_id.startswith("c1:"))
        self.assertEqual(result.formula_registry_id, "C1.FORMULAS.v0.1")
        self.assertEqual(result.categorical["direction"], "UP")
        self.assertEqual(result.authority_state, "NONE")

        invalid = dict(payload)
        invalid["release_membership"] = True
        with self.assertRaisesRegex(InputRejected, "PROSPECTIVE_RELEASE_MEMBERSHIP_DENIED"):
            build_c1(invalid)

    def test_c2_prospective_profile_uses_actual_state_engine(self) -> None:
        records = build_c1_records(
            complete_bars(40),
            "SRC.DUKASCOPY.GBPUSD.M1.BID.TEST",
        )
        accepted = accept_c1_record(records[0])
        self.assertEqual(
            accepted["handoff_status"],
            "ACCEPTED_RPS_TIME_GATED_REPLAY_WITH_EXACT_PRICE_PARENT",
        )
        states, transitions, _ = process_scope(
            records,
            scope="GBPUSD-15M-LOCAL-v0.1",
        )
        self.assertEqual(len(states), 40)
        self.assertGreater(len(transitions), 0)
        self.assertEqual(states[-1]["operation_mode"], "TIME_GATED_REPLAY")
        self.assertEqual(states[-1]["live_prospective_append"], "DENIED")
        self.assertEqual(
            states[-1]["active_c2_model_release_id"],
            "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1",
        )

        invalid = dict(records[0])
        invalid["selector_eligibility"] = "ACTIVE"
        with self.assertRaisesRegex(HandoffError, "PROSPECTIVE_SELECTOR_AUTHORITY_DENIED"):
            accept_c1_record(invalid)

    def test_incomplete_bar_cannot_enter_c1(self) -> None:
        bar = complete_bars(1)[0]
        incomplete = ProspectiveBar(
            **{
                **bar.__dict__,
                "close": None,
                "quality_state": "QUARANTINED_INCOMPLETE_PARENT_SET",
            }
        )
        with self.assertRaisesRegex(ComputeError, "incomplete parent cannot enter C1"):
            prospective_price_payload(incomplete, "SRC.TEST")

    def test_external_compute_is_denied_in_ci_before_source_access(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ComputeError, "prohibited in CI"):
                execute(
                    Path(temp),
                    authority_gate=AUTHORITY_GATE,
                    environ={"CI": "true"},
                )

    def test_wrong_gate_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ComputeError, "exact delegated authority binding"):
                execute(
                    Path(temp),
                    authority_gate="RPS-G3",
                    environ={"CI": "true"},
                )


if __name__ == "__main__":
    unittest.main()
