from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-full-month-mdr"
INDEX = BASE / "PD_JUNE_FULL_MONTH_MDR_WP1_SOURCE_ACCEPTANCE_INDEX.json"
QA = BASE / "PD_JUNE_FULL_MONTH_MDR_WP1_SOURCE_ACCEPTANCE_QA_PACKET.json"
DECISION = BASE / "PD_JUNE_FULL_MONTH_MDR_G1_DELEGATED_DECISION.json"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_PROGRAMME_STATE_v0_1.json"
SCHEMA = ROOT / "schemas" / "research_operations" / "pattern_discovery" / "pd_june_full_month_mdr_wp1_source_acceptance_v0_1.schema.json"

EXPECTED_COMPACT = {
    "source-slice-manifest.json": (2693, "8080b8def035cb37940b89054287d0c61756149aa7cb4711fc462a0ebbdc1f87"),
    "provider-request-plan.json": (17235, "fe96d91aef7c81ff3a510e7a843aa78b4ee3047960f2629cd19b7ece2f3a018a"),
    "provider-request-receipt.json": (41677, "01127118963b6c59d4a3a15659c2cf2853696cf5d4881dab8af8cb761ef5f57c"),
    "source-object-inventory.json": (3046, "fe340583cea9384a7d76ca1eafb60749643a70fd287ee45ee1507c6ad638cc2f"),
    "coverage-gap-duplicate-qa.json": (44707, "da2c14105955ff8055d29976210a304495bc6c207e4faaf6b74bda8a87f6fb55"),
    "bid-ask-reconciliation.json": (1175, "9a6575477535f69349303bf42ee3dd86226852ca7681beea3e251d0b62228b3c"),
    "native-h1-reconciliation.json": (2497, "4129b2ca9b44ca37ccd73e741208af5a581ad493ba00ba85cd19ecf68ffc49d0"),
    "freeze-receipt.json": (1325, "349aeca597968dd907b33ffe0d281950ad7fdd272db809299d11fe2485d25dca"),
}

EXPECTED_SOURCE = {
    "SRC.DUKASCOPY.GBPUSD.H1.ASK.20260530_20260703.v1": (573, 36025, "a25dcf89cb35afbbc6fb722e7f379511ceb83af0a5f1fc1b32c94e8adc304e5d"),
    "SRC.DUKASCOPY.GBPUSD.H1.BID.20260530_20260703.v1": (573, 35893, "b6116ea784be785089e881c8b8a69c8d5d202cb57f3d058f71d159071bd51c24"),
    "SRC.DUKASCOPY.GBPUSD.M1.ASK.20260530_20260703.v1": (34565, 2165135, "bc643e62ebbc35940f93aaaaead147b6f9170b1a030a473436b2dc84d6992057"),
    "SRC.DUKASCOPY.GBPUSD.M1.BID.20260530_20260703.v1": (34565, 2164613, "d704b3bac2d51e839505ee5bc2ba7589ce44310353bbb6a464a1850fe1af5789"),
}


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected object: {path}")
    return value


def validate() -> None:
    for path in (INDEX, QA, DECISION, STATE, SCHEMA):
        if not path.is_file():
            raise AssertionError(f"missing packet artifact: {path}")
    index = load(INDEX)
    qa = load(QA)
    decision = load(DECISION)
    state = load(STATE)
    schema = load(SCHEMA)

    assert index["schema"] == "ovc-pd-june-full-month-mdr-wp1-source-acceptance-index/v1"
    assert index["source_slice_id"] == "RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1"
    assert index["target_start_utc"] == "2026-06-01T00:00:00Z"
    assert index["target_end_exclusive_utc"] == "2026-07-01T00:00:00Z"
    assert index["source_window_start_utc"] == "2026-05-30T00:00:00Z"
    assert index["source_window_end_exclusive_utc"] == "2026-07-03T00:00:00Z"
    manifest = index["manifest"]
    assert manifest["logical_sha256"] == "1578b555f3d5aa2822b603141261f86a047096030e5faacd4380ef2c6d4f52e3"
    assert manifest["file_sha256"] == "8080b8def035cb37940b89054287d0c61756149aa7cb4711fc462a0ebbdc1f87"
    assert manifest["frozen"] is True
    assert manifest["coverage_state"] == "ACCEPTED_WITH_EXPLICIT_PAIRED_PROVIDER_ABSENCE_AND_CENSORING"
    assert manifest["release_status"] == "NOT_A_RELEASE"
    assert manifest["selector_eligibility"] == "NONE"
    assert manifest["r2_publication"] == "DENIED"
    assert manifest["validation_consumption"] == "DENIED"

    compact = {item["name"]: (item["size_bytes"], item["sha256"]) for item in index["compact_files"]}
    assert compact == EXPECTED_COMPACT
    sources = {item["object_id"]: (item["row_count"], item["size_bytes"], item["sha256"]) for item in index["source_objects"]}
    assert sources == EXPECTED_SOURCE

    source_qa = index["qa"]
    assert source_qa["provider_request"] == {"compressed_bytes": 595554, "observed_transport_objects": 72, "planned_objects": 72, "state": "PASS"}
    assert source_qa["m1"]["rows_per_side"] == 34565
    assert source_qa["m1"]["absent_timestamps_per_side"] == 138
    assert source_qa["m1"]["gap_runs_per_side"] == 95
    assert source_qa["m1"]["exact_bid_ask_timestamp_set"] is True
    assert source_qa["m1"]["duplicates"] == 0
    assert source_qa["m1"]["non_monotonic"] == 0
    assert source_qa["native_h1"]["compared_per_side"] == 483
    assert source_qa["native_h1"]["ohlc_mismatches"] == 0
    assert source_qa["post_target_context"]["complete_h1_hours_per_side"] == 42
    assert source_qa["post_target_context"]["censored_h1_hours_per_side"] == 6
    assert source_qa["post_target_context"]["repair_performed"] is False

    assert decision["decision"] == "PASS"
    assert decision["decision_authority"] == "DELEGATED_BY_OPERATOR_APPROVED_PLAN_AND_A2"
    assert decision["reserved_authority_delta"] == "NONE"
    assert decision["next_packet"] == "PD-JUNE-FM-WP2"
    assert qa["authority_delta"] == "LOCAL_FROZEN_SOURCE_ACCEPTANCE_ONLY"

    # Programme state may lawfully advance beyond WP1. Preserve exact WP1
    # source identity and merge binding rather than requiring a stale packet ID.
    assert state["packet_id"] in {"PD-JUNE-FM-WP1", "PD-JUNE-FM-WP2"}
    assert state["source_slice_id"] == index["source_slice_id"]
    assert state["source_manifest_logical_sha256"] == manifest["logical_sha256"]
    if state["packet_id"] == "PD-JUNE-FM-WP1":
        assert state["next_packet"] == "PD-JUNE-FM-WP2"
    else:
        assert state["source_acceptance_merge_commit"] == "39da5213ff3931cf9a22760a3ee3529d4fc43c30"
        assert state["next_packet"] == "PD-JUNE-FM-WP3"
    assert state["provider_execution_in_ci"] == "DENIED"
    assert state["canonical_2021_2023_discovery"] == "DEFERRED_NOT_AUTHORISED"
    assert schema["properties"]["source_slice_id"]["const"] == index["source_slice_id"]


if __name__ == "__main__":
    validate()
    print("PD-JUNE-FM-WP1 source acceptance validation: PASS")
