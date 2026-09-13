import json
from pathlib import Path

import pytest

from ovc.research_operations.bcwt import (
    BCWTValidationError,
    assert_r2_origin,
    compile_ledger,
    compile_mechanical_origins,
    make_consequence_pack,
    make_join_manifest,
    make_run_receipt,
    replay_digest,
)
from ovc.research_operations.canonical import canonical_sha256

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "research_operations" / "bcwt" / "v0_1"
EVENTS = json.loads((FIXTURES / "synthetic_events.json").read_text(encoding="utf-8"))
BARS = json.loads((FIXTURES / "synthetic_bars.json").read_text(encoding="utf-8"))
SOURCE = {
    "release_id": "SYNTH-R2",
    "instrument": "GBPUSD",
    "side": "BID",
    "clock": "15M",
    "provider": "SYNTHETIC",
    "role": "MECHANICAL_ASSURANCE",
}


def build():
    origins = compile_mechanical_origins(EVENTS, reference_id="OVC-BCWT-BREF-0.1")
    pack = make_consequence_pack(source_binding=SOURCE, horizons=[1, 2, 3])
    join = make_join_manifest(
        reference_id="OVC-BCWT-BREF-0.1",
        origin_set_hash=canonical_sha256(origins),
        consequence_pack_id=pack["consequence_pack_id"],
        source_binding=SOURCE,
    )
    ledger = compile_ledger(origins=origins, bars=BARS, pack=pack, join=join)
    return origins, pack, join, ledger


def test_only_final_returned_updates_are_origins():
    origins, _, _, _ = build()
    assert len(origins) == 4
    assert {o["observer_state_id"] for o in origins} == {"state-A0", "state-A1", "state-B0", "state-B1"}


def test_carried_and_internal_latent_are_not_origins():
    origins, _, _, _ = build()
    ids = {o["observer_state_id"] for o in origins}
    assert "latent-x" not in ids and "latent-y" not in ids


def test_mechanical_origin_has_no_candidate_authority():
    origins, _, _, _ = build()
    for origin in origins:
        assert_r2_origin(origin)
        assert origin["candidate_evaluation_admission_id_or_none"] is None


def test_scientific_origin_without_admission_rejected():
    origins, _, _, _ = build()
    origin = dict(origins[0])
    origin["origin_role"] = "C_ADMITTED_SCIENTIFIC_ORIGIN"
    with pytest.raises(BCWTValidationError):
        assert_r2_origin(origin)


def test_scientific_execution_even_with_ids_is_reserved():
    origins, _, _, _ = build()
    origin = dict(origins[0])
    origin["origin_role"] = "C_ADMITTED_SCIENTIFIC_ORIGIN"
    origin["candidate_generation_id_or_none"] = "cg"
    origin["candidate_occurrence_id_or_none"] = "occ"
    origin["candidate_evaluation_admission_id_or_none"] = "admit"
    with pytest.raises(PermissionError):
        assert_r2_origin(origin)


def test_pack_is_fixture_only_and_authority_none():
    _, pack, _, _ = build()
    assert pack["fixture_only"]
    assert pack["authority_effect"] == "NONE"
    assert pack["scientific_effect"] == "NONE"


def test_join_is_mechanical_only():
    _, _, join, _ = build()
    assert join["execution_role"] == "MECHANICAL_REFERENCE_ONLY"
    assert join["candidate_generation_id_or_none"] is None


def test_complete_denominator():
    origins, pack, _, ledger = build()
    assert ledger["expected_rows"] == len(origins) * len(pack["fixed_horizons_observed_bars"]) * len(pack["measurement_specs"])
    assert ledger["actual_rows"] == ledger["expected_rows"]


def test_gap_censoring_occurs():
    _, _, _, ledger = build()
    rows = [row for row in ledger["records"] if row["observer_state_id"] == "state-A1" and row["horizon_observed_bars"] >= 2]
    assert rows and all(row["terminal_status"] == "CENSORED_GAP" for row in rows)


def test_release_end_censoring_occurs():
    _, _, _, ledger = build()
    rows = [row for row in ledger["records"] if row["observer_state_id"] == "state-B1" and row["horizon_observed_bars"] >= 2]
    assert rows and all(row["terminal_status"] == "CENSORED_RELEASE_END" for row in rows)


def test_flat_path_explicit():
    _, _, _, ledger = build()
    row = [r for r in ledger["records"] if r["observer_state_id"] == "state-B0" and r["horizon_observed_bars"] == 1 and r["measurement_spec_id"] == "SIGNED_EFFICIENCY"][0]
    assert row["terminal_status"] == "OBSERVED"
    assert row["measurement_state"] == "FLAT_PATH"
    assert row["value"] is None


def test_reversal_rate_can_be_not_evaluable():
    _, _, _, ledger = build()
    row = [r for r in ledger["records"] if r["observer_state_id"] == "state-B0" and r["horizon_observed_bars"] == 1 and r["measurement_spec_id"] == "REVERSAL_RATE"][0]
    assert row["terminal_status"] == "NOT_EVALUABLE"
    assert row["measurement_state"] == "INSUFFICIENT_SIGN_PAIRS"


def test_signed_displacement_exact():
    _, _, _, ledger = build()
    row = [r for r in ledger["records"] if r["observer_state_id"] == "state-A0" and r["horizon_observed_bars"] == 2 and r["measurement_spec_id"] == "SIGNED_DISPLACEMENT_TICKS"][0]
    assert row["value"] == 1


def test_gross_travel_exact():
    _, _, _, ledger = build()
    row = [r for r in ledger["records"] if r["observer_state_id"] == "state-A0" and r["horizon_observed_bars"] == 2 and r["measurement_spec_id"] == "GROSS_CLOSE_TRAVEL_TICKS"][0]
    assert row["value"] == 3


def test_max_excursions_exact():
    _, _, _, ledger = build()
    up = [r for r in ledger["records"] if r["observer_state_id"] == "state-A0" and r["horizon_observed_bars"] == 2 and r["measurement_spec_id"] == "MAX_UP_EXCURSION_TICKS"][0]
    down = [r for r in ledger["records"] if r["observer_state_id"] == "state-A0" and r["horizon_observed_bars"] == 2 and r["measurement_spec_id"] == "MAX_DOWN_EXCURSION_TICKS"][0]
    assert up["value"] == 4 and down["value"] == 1


def test_replay_digest_deterministic_and_matches_chat_side_receipt():
    first = build()
    second = build()
    assert replay_digest(*first) == replay_digest(*second)
    assert replay_digest(*first) == "4accba3e6b8fdbfdbe005dfd03c64fe908b2dc4ffef2f5dfe9bf7973bf7dc6a3"


def test_origin_logical_ids_deterministic():
    first = compile_mechanical_origins(EVENTS, reference_id="OVC-BCWT-BREF-0.1")
    second = compile_mechanical_origins(EVENTS, reference_id="OVC-BCWT-BREF-0.1")
    assert [item["logical_id"] for item in first] == [item["logical_id"] for item in second]


def test_duplicate_final_state_fails():
    bad = EVENTS + [dict(EVENTS[0])]
    with pytest.raises(BCWTValidationError):
        compile_mechanical_origins(bad, reference_id="OVC-BCWT-BREF-0.1")


def test_duplicate_horizon_fails():
    with pytest.raises(BCWTValidationError):
        make_consequence_pack(source_binding=SOURCE, horizons=[1, 1])


def test_cross_segment_never_bridged():
    _, _, _, ledger = build()
    rows = [row for row in ledger["records"] if row["observer_state_id"] == "state-A1" and row["horizon_observed_bars"] == 2]
    assert all(row["value"] is None for row in rows)


def test_all_rows_authority_and_scientific_none():
    _, _, _, ledger = build()
    assert all(row["authority_effect"] == "NONE" and row["scientific_effect"] == "NONE" for row in ledger["records"])


def test_run_receipt_exact_and_mechanical():
    origins, pack, join, ledger = build()
    receipt = make_run_receipt(reference_id="OVC-BCWT-BREF-0.1", origins=origins, pack=pack, join=join, ledger=ledger)
    assert receipt["execution_role"] == "MECHANICAL_REFERENCE_ONLY"
    assert receipt["expected_rows"] == receipt["actual_rows"] == 96
    assert receipt["replay_digest"] == "4accba3e6b8fdbfdbe005dfd03c64fe908b2dc4ffef2f5dfe9bf7973bf7dc6a3"


def test_unadmitted_source_role_is_hard_denied():
    source = dict(SOURCE)
    source["role"] = "FRESH_SCIENTIFIC"
    with pytest.raises(PermissionError):
        make_consequence_pack(source_binding=source, horizons=[1])
