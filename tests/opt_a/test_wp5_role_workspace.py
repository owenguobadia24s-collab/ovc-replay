from decimal import Decimal
from pathlib import Path

import pytest

from ovc.opt_a.role_workspace import (
    Bar,
    RoleWorkspaceError,
    _aggregate_exact,
    _canonical_json_sha256,
    _validate_role_lock,
)


def _bar(minute: int, close: str) -> Bar:
    value = Decimal(close)
    return Bar(
        timestamp_ms=minute * 60_000,
        open=value,
        high=value + Decimal("0.0002"),
        low=value - Decimal("0.0002"),
        close=value,
        volume=Decimal("1"),
    )


def test_exact_15m_aggregation_preserves_ohlcv() -> None:
    bars = [_bar(index, f"1.{1000 + index}") for index in range(15)]
    output, quarantine = _aggregate_exact(bars, minutes=15)

    assert quarantine == []
    assert len(output) == 1
    assert output[0].timestamp_ms == 0
    assert output[0].open == bars[0].open
    assert output[0].high == max(item.high for item in bars)
    assert output[0].low == min(item.low for item in bars)
    assert output[0].close == bars[-1].close
    assert output[0].volume == Decimal("15")


def test_incomplete_bucket_is_quarantined_not_filled() -> None:
    bars = [_bar(index, "1.2500") for index in range(15) if index != 7]
    output, quarantine = _aggregate_exact(bars, minutes=15)

    assert output == []
    assert quarantine == [
        {
            "bucket_start": 0,
            "clock_minutes": 15,
            "expected_count": 15,
            "observed_count": 14,
            "reason": "INCOMPLETE_OR_NONCONTIGUOUS_M1_BUCKET",
        }
    ]


def test_two_hour_a_l_bucket_requires_120_exact_m1_rows() -> None:
    bars = [_bar(index, "1.2500") for index in range(120)]
    output, quarantine = _aggregate_exact(bars, minutes=120)

    assert len(output) == 1
    assert quarantine == []
    assert output[0].volume == Decimal("120")


def test_validation_workspace_default_deny() -> None:
    with pytest.raises(RoleWorkspaceError, match="LOCKED_UNCONSUMED"):
        _validate_role_lock("VALIDATION", allow_validation=False)

    _validate_role_lock("VALIDATION", allow_validation=True)


def test_manifest_hash_is_canonical() -> None:
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}
    assert _canonical_json_sha256(left) == _canonical_json_sha256(right)
