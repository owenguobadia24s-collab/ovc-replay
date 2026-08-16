from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CENSUS = ROOT / "registries/research_operations/p2cti/P2CTII_BOOTSTRAP_SOURCE_CENSUS_v0_1.json"
AUTH = ROOT / "registries/research_operations/p2cti/P2CTII_AUTHORITY_FRONTIER_v0_1.json"
ROOT_BINDING = ROOT / "registries/research_operations/p2cti/P2CTII_EXTERNAL_ARTIFACT_ROOT_BINDING_v0_1.json"
PACKET = ROOT / "docs/programmes/p2cti-v0-1/wp0/P2CTII_WP0_IMPLEMENTATION_PACKET_v0_1.json"
STATE = ROOT / "records/research_operations/p2cti/P2CTII_PROGRAMME_STATE_v0_1.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_exact_30_subject_census_and_classes():
    census = load(CENSUS)
    members = census["members"]
    ids = [m["subject_id"] for m in members]
    assert len(members) == 30
    assert len(set(ids)) == 30
    counts = {}
    for member in members:
        counts[member["subject_class"]] = counts.get(member["subject_class"], 0) + 1
        assert len(member["source_sha256"]) == 64
        assert member["drive_file_id"]
        assert member["drive_folder_id"]
    assert counts == {
        "EXTERNAL_THEORY_RECORD": 7,
        "IN_HOUSE_THEORY_RECORD": 19,
        "ARCHITECTURE_NEED_SEED": 4,
    }


def test_architecture_need_seeds_are_not_theory_records():
    census = load(CENSUS)
    seeds = [m for m in census["members"] if m["subject_class"] == "ARCHITECTURE_NEED_SEED"]
    assert [m["subject_id"] for m in seeds] == [
        "TH-OVC-INH-0020-v0.1",
        "TH-OVC-INH-0021-v0.1",
        "TH-OVC-INH-0022-v0.1",
        "TH-OVC-INH-0023-v0.1",
    ]
    assert all(m["source_state"] == "UNTESTED_DEFERRED_SEED" for m in seeds)


def test_owner_authority_is_non_transitive():
    auth = load(AUTH)
    assert auth["p2cti_g0"]["operational_read_only_activation"].startswith("DENIED_UNTIL_")
    assert auth["p2cti_g0"]["continuous_intake_writes"].startswith("DENIED_UNTIL_")
    assert auth["owner_frontiers"]["path2_external"]["inheritance_to_p2cti"] == "PROHIBITED"
    assert auth["owner_frontiers"]["ec1"]["inheritance_to_p2cti"] == "PROHIBITED"
    assert auth["owner_frontiers"]["path2_external"]["p2_6_candidate_formation"] == "NOT_AUTHORISED"
    assert auth["owner_frontiers"]["ec1"]["candidate_freeze"] == "NONE"
    assert auth["owner_frontiers"]["rccr"]["owner_capability_activation"] == "DENIED"
    assert auth["owner_frontiers"]["shared_systems"]["service_activation"] == "NONE"
    assert auth["non_transitivity"]["owner_authority_transfers_to_p2cti"] is False
    assert "VALIDATION" in auth["explicit_non_grants"]


def test_external_root_is_non_authoritative_and_non_destructive():
    binding = load(ROOT_BINDING)
    assert binding["provider"] == "GOOGLE_DRIVE"
    assert binding["external_artifact_root"]["folder_id"] == "1s-I8kQkelxB1ZYS0vKVKCeNL1XZSBdZS"
    assert binding["retention"] == "NON_DESTRUCTIVE_FORWARD_SUPERSESSION_ONLY"
    assert "NO_AUTHORITY_FROM_STORAGE" in binding["prohibitions"]


def test_wp0_packet_is_vit_routed_and_has_no_authority_expansion():
    packet = load(PACKET)
    state = load(STATE)
    assert packet["status"] in {"QA_REVIEW", "APPROVED", "COMPLETED"}
    assert packet["routing"]["route_class"] == "VIT_MANDATORY"
    assert packet["authority_delta"] == "NONE_BEYOND_OPERATOR_APPROVED_G0_ENVELOPE"
    assert packet["acceptance"]["material_semantic_contradiction_found"] is False
    assert packet["acceptance"]["authority_inheritance_to_p2cti"] is False
    assert packet["blockers"] == []
    assert packet["next_packet"] == "P2CTII-WP1"
    assert state["authority_delta"] == "NONE"
    completed = {item["packet_id"] for item in state.get("completed_packets", [])}
    assert state["packet_id"] == "P2CTII-WP0" or "P2CTII-WP0" in completed
