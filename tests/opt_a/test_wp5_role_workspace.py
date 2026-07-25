from decimal import Decimal
from pathlib import Path

import pytest

from ovc.opt_a.role_workspace import (
    Bar,
    RoleWorkspaceError,
    _aggregate_exact,
    _canonical_json_sha256,
    _coverage_summary,
    _portable_relative_path,
    _validate_role_lock,
    _write_bars,
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
            "missing_timestamp_count": 1,
            "missing_timestamps_ms": [7 * 60_000],
            "unexpected_timestamp_count": 0,
            "unexpected_timestamps_ms": [],
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


def test_workspace_paths_are_portable_and_root_relative(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    output = workspace / "observations" / "M1" / "BID" / "sample.csv"
    record = _write_bars(output, [_bar(0, "1.2500")], relative_to=workspace)

    assert record["path"] == "observations/M1/BID/sample.csv"
    assert not Path(record["path"]).is_absolute()
    assert _portable_relative_path(output, relative_to=workspace) == record["path"]


def test_workspace_path_escape_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(RoleWorkspaceError, match="escapes its root"):
        _portable_relative_path(
            tmp_path / "outside.csv", relative_to=tmp_path / "workspace"
        )


def test_coverage_summary_uses_integer_counts_and_rates() -> None:
    observations = [
        {"clock": "M1", "price_side": "BID", "row_count": 15},
        {"clock": "15M", "price_side": "BID", "row_count": 3},
    ]
    quarantine = [
        {"clock": "15M", "price_side": "BID"},
    ]

    summary = _coverage_summary(observations, quarantine)
    assert summary["M1"]["BID"] == {
        "accepted_bucket_count": 15,
        "quarantined_bucket_count": 0,
        "candidate_bucket_count": 15,
        "acceptance_rate_ppm": 1_000_000,
    }
    assert summary["15M"]["BID"] == {
        "accepted_bucket_count": 3,
        "quarantined_bucket_count": 1,
        "candidate_bucket_count": 4,
        "acceptance_rate_ppm": 750_000,
    }
