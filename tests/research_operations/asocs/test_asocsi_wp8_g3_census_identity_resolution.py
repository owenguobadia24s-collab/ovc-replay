from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP5 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp5"
WP6 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp6"
WP7 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp7"
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"
STATE = ROOT / "records/research_operations/asocs"
POINTER = ROOT / "registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json"

FROZEN_CENSUS = "c49f34e7af19f0110d24377a54ab8f0bd3fb183e83e924de07bf39cd586de2c7"
FROZEN_COMPACT = "b8b4caeca0c9e234339c07053bac6c65040d0cb14c9abfca08590526e5b4a3da"
FROZEN_ORDERED = "bcd571f567068035592bb0d868747cfe85e8aaa01155b1fa8c798f488f6ef0d7"
FROZEN_TRACES = "22c856efdd24083d5339d2082ad9714597e326a6f40655bfb82b0afa9899f7dc"
FROZEN_G4 = "ff6eb37724aea5b2706666903f7b5a1bc063af8ef9026f4496429b5e33fa15fe"
SOURCE_SHA = "210233ec5761bf82998172832bb554ddf10dfeb3099f6bc6488d5bb0f6bec4f2"
CHECKPOINT_SHA = "d55055d81777777d67b47f1603cc0d0a77bca019ae990bf0b52cee0c7733e6c5"
TWO_RUN_SHA = "58c61b000b3be78ee35d9e6a1d383d5fceb03e3c1d09390f3d83c6be4f7f4cd6"

CHECKPOINTS = [
    {"count": 4392, "prefix_sha256": "91004c82e3a4134a32b1afe4e41559652b978589b8043e9abe9f7e818ccf0709"},
    {"count": 8784, "prefix_sha256": "d005f3225ea5a268fc9a223995f5cadfbb6611f374002eca02df266407b781ee"},
    {"count": 13176, "prefix_sha256": "c99129aa61f5471f8e7574471fb190057def3efa918a72014e58a3232b607632"},
    {"count": 17568, "prefix_sha256": "8ea8eabd040a0bc193a34ff792c49f7eb83739c72c5caa69f7234a88159e6f0c"},
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def historical_json_bytes(value: dict) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        + b"\n"
    )


def test_historical_external_json_serializer_is_exactly_reproduced() -> None:
    checkpoint_manifest = {
        "schema": "ovc-asocs-g3-checkpoint-manifest/v0_1",
        "census_sha256": FROZEN_CENSUS,
        "checkpoints": CHECKPOINTS,
    }
    checkpoint_bytes = historical_json_bytes(checkpoint_manifest)
    assert len(checkpoint_bytes) == 544
    assert hashlib.sha256(checkpoint_bytes).hexdigest() == CHECKPOINT_SHA

    two_run = {
        "logical_equal": True,
        "ordered_trace_ids_equal": True,
        "run_a": FROZEN_CENSUS,
        "run_b": FROZEN_CENSUS,
        "schema": "ovc-asocs-g3-two-run-equality/v0_1",
        "source_sha256": SOURCE_SHA,
    }
    two_run_bytes = historical_json_bytes(two_run)
    assert len(two_run_bytes) == 333
    assert hashlib.sha256(two_run_bytes).hexdigest() == TWO_RUN_SHA


def test_census_identity_resolution_fails_closed_on_missing_provenance() -> None:
    evidence = load(WP8 / "ASOCSI_WP8_G3_CENSUS_IDENTITY_RESOLUTION_EVIDENCE_v0_1.json")
    assert evidence["frozen"]["census_sha256"] == FROZEN_CENSUS
    assert evidence["frozen"]["compact_census_manifest"] == {
        "byte_size": 2712,
        "sha256": FROZEN_COMPACT,
    }
    assert evidence["recovery_search"]["original_compact_manifest_recovered"] is False
    assert evidence["recovery_search"]["exact_historical_generation_program_recovered"] is False
    assert evidence["bounded_reconstruction_search"]["result"] == "NO_EXACT_MATCH"
    assert evidence["resolution_result"] == "BLOCK_REQUIRED_ARTIFACT_OR_PROVENANCE_UNAVAILABLE"
    assert evidence["meaning_bearing_change"] is False

    qa = load(WP8 / "ASOCSI_WP8_G3_CENSUS_IDENTITY_RESOLUTION_QA_v0_1.json")
    assert qa["qa_recommendation"] == "BLOCK"
    assert qa["checks"]["checkpoint_external_json_serializer"] == "PASS_EXACT"
    assert qa["checks"]["two_run_external_json_serializer"] == "PASS_EXACT"
    assert qa["checks"]["frozen_census_sha256"] == "FAIL_UNRESOLVED_HISTORICAL_CONSTRUCTION"

    decision = load(WP8 / "ASOCSI_WP8_G3_CENSUS_IDENTITY_RESOLUTION_DECISION_v0_1.json")
    assert decision["decision"] == "BLOCK"
    assert decision["authority_delta"] == "NONE"
    assert decision["operator_decision_required"] is False
    assert decision["next_packet"] is None
    assert decision["mandatory_stop"] == "REQUIRED_ARTIFACT_OR_NON_REPRODUCIBLE_PROVENANCE"


def test_frozen_trace_science_and_g4_g5_evidence_remain_unchanged() -> None:
    evidence = load(WP8 / "ASOCSI_WP8_G3_CENSUS_IDENTITY_RESOLUTION_EVIDENCE_v0_1.json")
    assert evidence["frozen"]["observation_traces"]["sha256"] == FROZEN_TRACES
    assert evidence["frozen"]["observation_traces"]["byte_size"] == 10995130
    assert evidence["frozen"]["observation_traces"]["record_count"] == 17568
    assert evidence["frozen"]["ordered_trace_ids_sha256"] == FROZEN_ORDERED
    assert evidence["lineage_proof"] == {
        "g4_review_population_sha256": FROZEN_G4,
        "g5_status": "FROZEN",
        "g5_human_payload_mutation": "NONE",
        "g5_reveal_started": False,
        "result": "PASS_UNCHANGED",
    }

    g3 = load(WP5 / "ASOCSI_G3_CENSUS_FREEZE_v0_1.json")
    assert g3["census_sha256"] == FROZEN_CENSUS
    assert g3["external_artifacts"]["compact_census_manifest"]["sha256"] == FROZEN_COMPACT
    assert g3["external_artifacts"]["observation_traces"]["sha256"] == FROZEN_TRACES

    g4 = load(WP6 / "ASOCSI_G4_REVIEW_POPULATION_FREEZE_v0_1.json")
    assert g4["review_population_sha256"] == FROZEN_G4
    assert g4["g3_census_sha256"] == FROZEN_CENSUS

    g5 = load(WP7 / "ASOCSI_G5_BLIND_EVIDENCE_FREEZE_v0_1.json")
    assert g5["status"] == "FROZEN"
    assert g5["identity_integrity"]["human_payload_mutation"] == "NONE"
    assert g5["blindness"]["reveal_started"] is False


def test_programme_state_stops_without_inventing_a_successor() -> None:
    pointer = load(POINTER)
    expected = (
        "records/research_operations/asocs/"
        "ASOCSI_PROGRAMME_STATE_v0_24_WP8_G3_CENSUS_IDENTITY_PROVENANCE_BLOCKED.json"
    )
    assert pointer == {
        "current_state": expected,
        "next_packet": None,
        "packet_id": "ASOCSI-WP8-G3-CENSUS-IDENTITY-RESOLUTION",
        "programme_id": "OVC-ASOCS-6M-v0.1",
        "status": "BLOCKED",
    }

    state = load(ROOT / expected)
    assert state["status"] == "BLOCKED"
    assert state["authority_delta"] == "NONE"
    assert state["blockers"] == ["G3_FROZEN_CENSUS_IDENTITY_PROVENANCE_UNAVAILABLE"]
    assert state["next_packet"] is None
    assert state["preserved"] == {
        "g3_frozen_generation": True,
        "g4_review_population": True,
        "g5_human_evidence": True,
    }
    assert state["human_adjudication_started"] is False
    assert state["stage1_reveal_started"] is False


def test_authority_manifest_forbids_waiver_replacement_or_reveal() -> None:
    authority = load(WP8 / "ASOCSI_WP8_G3_CENSUS_IDENTITY_RESOLUTION_AUTHORITY_v0_1.json")
    assert authority["authority_delta"] == "NONE"
    assert authority["scientific_effect"] == "NONE"
    for denied in (
        "WAIVE_FROZEN_G3_IDENTITY_REQUIREMENT",
        "AMEND_FROZEN_G3_CONTRACT",
        "REPLACE_FROZEN_G3",
        "START_STAGE1_REVEAL",
        "SEMANTIC_REMEDIATION",
        "VALIDATION",
        "EXPOSURE",
        "EXECUTION",
    ):
        assert denied in authority["non_grants"]
