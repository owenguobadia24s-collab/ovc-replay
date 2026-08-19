from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from ovc.research_operations.asocs.source import (
    ASOCSSourceQualificationError,
    CLAIM_CLASS_MORPHOLOGY,
    EXPECTED_HEADER,
    exact_interface_evaluability_matrix,
    parse_decimal,
    parse_literal_timestamp,
    qualify_source,
)


def _write_source(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "audit.csv"
    path.write_text(
        ",".join(EXPECTED_HEADER) + "\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
        newline="",
    )
    return path


def _sha(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_literal_timestamp_is_exact_and_timezone_naive() -> None:
    value = parse_literal_timestamp("20260102", "03:04:05")
    assert value == datetime(2026, 1, 2, 3, 4, 5)
    assert value.tzinfo is None
    with pytest.raises(ASOCSSourceQualificationError):
        parse_literal_timestamp("2026-01-02", "03:04:05")
    with pytest.raises(ASOCSSourceQualificationError):
        parse_literal_timestamp("20260102", "3:04:05")


def test_decimal_parser_is_locale_independent_and_exact() -> None:
    assert str(parse_decimal("1.34660", "Open")) == "1.34660"
    with pytest.raises(ASOCSSourceQualificationError):
        parse_decimal("1,34660", "Open")
    with pytest.raises(ASOCSSourceQualificationError):
        parse_decimal(" 1.34660", "Open")


def test_qualification_freezes_unresolved_side_clock_and_out_of_role(tmp_path: Path) -> None:
    path = _write_source(tmp_path, [
        "20251231,23:59:00,1.10,1.20,1.00,1.15,1",
        "20260101,00:00:00,1.15,1.25,1.10,1.20,2",
        "20260101,00:02:00,1.20,1.30,1.15,1.25,3",
        "20260701,00:00:00,1.25,1.35,1.20,1.30,4",
    ])
    result = qualify_source(path, expected_sha256=_sha(path), expected_row_count=4)
    assert result.manifest.target_row_count == 2
    assert result.manifest.adjacent_gap_count_target == 1
    assert result.provenance.price_side == "UNRESOLVED_SINGLE_STREAM"
    assert result.provenance.timestamp_timezone == "SOURCE_TIMEZONE_UNRESOLVED"
    assert result.provenance.role == "ASOCS_AUDIT_OUT_OF_ROLE_H1_2026"
    assert not result.provenance.selector_eligible
    assert not result.provenance.ec1_eligible
    assert result.claim_class.claim_class == CLAIM_CLASS_MORPHOLOGY
    assert not result.claim_class.exact_active_interface_authorized


def test_hash_header_duplicate_order_and_ohlc_fail_closed(tmp_path: Path) -> None:
    good = _write_source(tmp_path, [
        "20260101,00:00:00,1.10,1.20,1.00,1.15,1",
        "20260101,00:01:00,1.15,1.25,1.10,1.20,2",
    ])
    with pytest.raises(ASOCSSourceQualificationError, match="SOURCE_HASH_MISMATCH"):
        qualify_source(good, expected_sha256="0" * 64)

    bad_header = tmp_path / "bad_header.csv"
    bad_header.write_text("Time,Date,Open,High,Low,Close,Volume\n", encoding="utf-8")
    with pytest.raises(ASOCSSourceQualificationError, match="HEADER_MISMATCH"):
        qualify_source(bad_header, expected_sha256=_sha(bad_header))

    duplicate = _write_source(tmp_path, [
        "20260101,00:00:00,1.10,1.20,1.00,1.15,1",
        "20260101,00:00:00,1.15,1.25,1.10,1.20,2",
    ])
    with pytest.raises(ASOCSSourceQualificationError, match="DUPLICATE_TIMESTAMPS"):
        qualify_source(duplicate, expected_sha256=_sha(duplicate))

    nonmono = _write_source(tmp_path, [
        "20260101,00:01:00,1.10,1.20,1.00,1.15,1",
        "20260101,00:00:00,1.15,1.25,1.10,1.20,2",
    ])
    with pytest.raises(ASOCSSourceQualificationError, match="NON_MONOTONIC_TIMESTAMPS"):
        qualify_source(nonmono, expected_sha256=_sha(nonmono))

    ohlc = _write_source(tmp_path, ["20260101,00:00:00,1.30,1.20,1.00,1.15,1"])
    with pytest.raises(ASOCSSourceQualificationError, match="OHLC_ENVELOPE_ERROR"):
        qualify_source(ohlc, expected_sha256=_sha(ohlc))


def test_exact_interface_matrix_is_per_construct_and_non_transitive() -> None:
    rows = exact_interface_evaluability_matrix()
    assert len(rows) == 13
    assert {row["construct"] for row in rows} >= {
        "C1_ARITHMETIC_PRIMITIVES", "C2_LEVEL", "C2_CONTAINER", "C2_RELATION",
        "C2_TRANSITION", "C2_PARENT_CONTEXT", "C2_COMPUTABILITY", "C2E_EPISODE", "C2E_PHASE",
    }
    assert all(row["exact_active_interface"] == "NOT_EVALUABLE_EXACT_ACTIVE_INTERFACE" for row in rows)
    assert all(row["morphology_route"] == "TO_BE_PROVEN_OR_FAIL_CLOSED_IN_ASOCSI_WP4" for row in rows)
    assert all(row["authority_effect"] == "NONE" for row in rows)


def test_wp1_records_freeze_claim_class_and_non_authorities() -> None:
    import json
    root = Path(__file__).resolve().parents[3]
    claim = json.loads((root / "docs/programmes/asocs-v0-1/implementation/wp1/ASOCS_CLAIM_CLASS_DECISION_v0_1.json").read_text(encoding="utf-8"))
    provenance = json.loads((root / "docs/programmes/asocs-v0-1/implementation/wp1/ASOCS_SOURCE_PROVENANCE_ASSESSMENT_v0_1.json").read_text(encoding="utf-8"))
    matrix = json.loads((root / "docs/programmes/asocs-v0-1/implementation/wp1/ASOCS_EXACT_INTERFACE_EVALUABILITY_MATRIX_v0_1.json").read_text(encoding="utf-8"))
    assert claim["claim_class"] == "ASOCS_SINGLE_STREAM_MORPHOLOGY_COHERENCE"
    assert claim["active_provider"] is False
    assert claim["selector_eligible"] is False
    assert claim["ec1_eligible"] is False
    assert provenance["price_side"] == "UNRESOLVED_SINGLE_STREAM"
    assert provenance["timestamp_timezone_status"] == "UNRESOLVED"
    assert matrix["target_replay_started"] is False
    assert all(row["authority_effect"] == "NONE" for row in matrix["rows"])
