from __future__ import annotations

from pathlib import Path

import pytest

from scripts.run_c2p2_rs0_r3_storage_scaling import run_measurement, run_scaling_point


@pytest.mark.parametrize("count", [8, 16, 32])
def test_unique_geometry_fixture_has_exact_quadratic_evidence_growth(
    count: int, tmp_path: Path
) -> None:
    result = run_scaling_point(count, tmp_path / f"n-{count}")
    expected = count * (count - 1) // 2

    assert result["expected_evidence_vectors"] == expected
    assert result["observed_evidence_vectors"] == expected
    assert result["evidence_vector_formula_status"] == "PASS"
    assert result["telemetry"]["table_row_counts"]["tracklets"] == count
    assert result["telemetry"]["table_row_counts"]["assertions"] == 0
    assert result["telemetry"]["table_row_counts"]["candidates"] == count
    assert result["telemetry"]["table_row_counts"]["decisions"] == count
    assert result["telemetry"]["table_row_counts"]["processed_source_ids"] == count
    assert result["runtime_spool_database_bytes"] > 0
    assert result["telemetry"]["page_count"] > 0
    assert result["telemetry"]["allocated_page_bytes"] >= result["runtime_spool_database_bytes"]


def test_measurement_is_synthetic_only_and_authority_neutral(tmp_path: Path) -> None:
    output = tmp_path / "measurement.json"
    payload = run_measurement(output, tmp_path / "work", [8, 16])

    assert payload["authority_effect"] == "NONE_SYNTHETIC_NON_EVIDENTIARY_MECHANICAL_ONLY"
    assert payload["real_source_read"] is False
    assert payload["fresh_run_token"] == "NONE"
    assert payload["real_source_execution_authority"] == "NONE"
    assert payload["selection"] == "NONE"
    assert payload["activation"] == "NONE"
    assert payload["validation"] == "LOCKED_UNCONSUMED"
    assert output.exists()
