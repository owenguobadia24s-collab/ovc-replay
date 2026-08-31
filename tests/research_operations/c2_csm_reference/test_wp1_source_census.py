from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "contracts/research_operations/c2_csm_reference"
SCHEMAS = ROOT / "schemas/research_operations/c2_csm_reference"
RECORDS = ROOT / "records/research_operations/c2_csm_reference"
SPTO_RECORDS = ROOT / "records/research_operations/spto"
FIXTURES = ROOT / "fixtures/research_operations/c2_csm_reference"
WP1 = ROOT / "docs/programmes/c2s-sptoi-v0-1/wp1"
POINTER = ROOT / "registries/implementation/c2s_sptoi_v0_1/CURRENT_STATE_POINTER.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp1_json_surface_parses_and_schema_is_closed() -> None:
    paths = [
        *CONTRACTS.glob("*.json"),
        *SCHEMAS.glob("*.json"),
        *RECORDS.glob("*.json"),
        *FIXTURES.glob("*.json"),
        *WP1.glob("*.json"),
        SPTO_RECORDS / "C2S_SPTOI_SOURCE_COMPLETENESS_MATRIX_v0_1.json",
        SPTO_RECORDS / "C2S_SPTOI_PROGRAMME_STATE_v0_1.json",
        POINTER,
    ]
    assert paths
    for path in paths:
        assert isinstance(load(path), dict), path
    schema = load(SCHEMAS / "c2_csm_reference_source_completeness_manifest_v0_1.schema.json")
    assert schema["additionalProperties"] is False
    assert schema["properties"]["authority_effect"]["const"] == "NONE_REFERENCE_CONFORMANCE_ONLY"


def test_primary_source_is_exact_hash_bound_and_external() -> None:
    manifest = load(RECORDS / "C2CSM_REFERENCE_SOURCE_COMPLETENESS_MANIFEST_v0_1.json")
    source = manifest["primary_source"]
    assert manifest["source_completeness_status"] == "SOURCE_COMPLETE_IMPLEMENTATION_BOUND_PARITY_PENDING"
    assert manifest["missing_source_components"] == []
    assert source == {
        "artifact_name": "OVC_C2_CSM_P3R5T2S2_DEV.txt",
        "sha256": "88bfab773f72817ee9e87228066bcaa223d62aef0fb802dd9261c1a11bce03fd",
        "size_bytes": 114875,
        "line_count": 2556,
        "source_confidence": "SOURCE_EXACT",
        "implementation_binding": "EXACT_IMPLEMENTATION_BOUND",
        "external_artifact_path": "c2s-sptoi/sources/sha256/88bfab773f72817ee9e87228066bcaa223d62aef0fb802dd9261c1a11bce03fd/OVC_C2_CSM_P3R5T2S2_DEV.txt",
    }
    assert not (ROOT / source["artifact_name"]).exists()
    assert re.fullmatch(r"[0-9a-f]{64}", source["sha256"])


def test_all_load_bearing_semantic_families_are_exact_implementation_bound() -> None:
    manifest = load(RECORDS / "C2CSM_REFERENCE_SOURCE_COMPLETENESS_MANIFEST_v0_1.json")
    families = {item["family_id"]: item for item in manifest["semantic_families"]}
    assert set(families) == {
        "P3_FORMATION_LIFECYCLE",
        "R5_BOUNDARY_ROLE_SUCCESSION",
        "T2_ATOMIC_COMPOUND_TRANSITIONS",
        "S2_SNAPSHOT_SUCCESSION_LEDGER",
    }
    for item in families.values():
        assert item["source_confidence"] == "SOURCE_EXACT"
        assert item["implementation_binding"] == "EXACT_IMPLEMENTATION_BOUND"
        assert item["load_bearing"] is True
        assert item["status"] == "SOURCE_BOUND_PARITY_PENDING"


def test_r5_is_typed_publication_only_and_not_used_to_infer_mechanics() -> None:
    manifest = load(RECORDS / "C2CSM_REFERENCE_SOURCE_COMPLETENESS_MANIFEST_v0_1.json")
    lineage = {item["revision_id"]: item for item in manifest["library_lineage"]}
    assert set(lineage) == {f"C2LIB-0001-R{revision}" for revision in range(1, 6)}
    for revision in range(1, 5):
        item = lineage[f"C2LIB-0001-R{revision}"]
        assert item["source_confidence"] == "SOURCE_EXACT"
        assert item["implementation_binding"] == "EXACT_IMPLEMENTATION_BOUND"
        assert item["load_bearing"] is True
    r5 = lineage["C2LIB-0001-R5"]
    assert r5["semantic_delta"] == "NONE_TYPED_PUBLICATION_ONLY"
    assert r5["implementation_binding"] == "EXACT_EVIDENCE_ONLY"
    assert r5["load_bearing"] is False


def test_source_confidence_contract_forbids_derived_semantics() -> None:
    contract = load(CONTRACTS / "C2CSM_REFERENCE_SOURCE_CONFIDENCE_CONTRACT_v0_1.json")
    assert set(contract["source_confidence"]) == {"SOURCE_EXACT", "SOURCE_DERIVED", "MISSING"}
    assert set(contract["implementation_binding"]) == {
        "EXACT_IMPLEMENTATION_BOUND",
        "EXACT_EVIDENCE_ONLY",
        "DERIVED_NON_IMPLEMENTATION",
        "UNAVAILABLE",
    }
    assert contract["binding_rule"]["required_source_confidence"] == "SOURCE_EXACT"
    assert contract["binding_rule"]["required_implementation_binding"] == "EXACT_IMPLEMENTATION_BOUND"
    assert "EVIDENTIARY_JOURNAL" in contract["prohibited_substitutes"]


def test_fixture_census_reconciles_historical_anchors_without_raw_reconstruction() -> None:
    census = load(FIXTURES / "C2CSM_REFERENCE_FIXTURE_CENSUS_v0_1.json")
    anchors = census["historical_anchors"]
    assert anchors["development"] == {"cases": 15, "bars": 1392, "objects": 245}
    assert anchors["holdout"] == {"cases": 10, "bars": 936, "objects": 163, "integrity_pass_cases": 10}
    assert anchors["combined"] == {"cases": 25, "bars": 2328, "objects": 408}
    assert anchors["development"]["cases"] + anchors["holdout"]["cases"] == anchors["combined"]["cases"]
    assert anchors["development"]["bars"] + anchors["holdout"]["bars"] == anchors["combined"]["bars"]
    assert anchors["development"]["objects"] + anchors["holdout"]["objects"] == anchors["combined"]["objects"]
    assert census["raw_case_inputs_effect"] == "PARITY_EXECUTION_PENDING_WP3; NO_AGGREGATE_TO_RAW_RECONSTRUCTION"
    assert len(census["historical_source_artifacts"]) == 16


def test_parity_contract_stays_pending_until_wp2_wp3() -> None:
    parity = load(CONTRACTS / "C2CSM_REFERENCE_PARITY_CONTRACT_v0_1.json")
    assert parity["parity_status_at_wp1"] == "CONTRACT_FROZEN_EXECUTION_PENDING_WP2_WP3"
    assert "FRESH_PROCESS_REPLAY" in parity["required_modes"]
    assert "CHECKPOINT_RESTART_REPLAY" in parity["required_modes"]
    assert "SERIALIZED_OUTPUT_IDENTITY" in parity["required_modes"]


def test_source_completeness_matrix_does_not_preempt_later_source_requests() -> None:
    matrix = load(SPTO_RECORDS / "C2S_SPTOI_SOURCE_COMPLETENESS_MATRIX_v0_1.json")
    families = {item["family_id"]: item for item in matrix["families"]}
    assert len(families) == 11
    assert families["A_HISTORICAL_C2_REFERENCE"]["status"] == "SOURCE_CONFLICT_QUARANTINED"
    assert families["A_HISTORICAL_C2_REFERENCE"]["parity_status"] == "BLOCKED_WP3_CANDIDATE_DIVERGES_IN_FIVE_CASES_AND_FULL_EXPECTED_OUTPUTS_UNAVAILABLE"
    assert families["A_HISTORICAL_C2_REFERENCE"]["missing_components"]
    assert families["A_HISTORICAL_C2_REFERENCE"]["source_request_packet"].endswith("C2S_SPTOI_WP3_SOURCE_REQUEST_PACKET_v0_1.json")
    for family_id, item in families.items():
        if family_id != "A_HISTORICAL_C2_REFERENCE":
            assert item["status"] == "NOT_YET_LOAD_BEARING"
            assert item["load_bearing_now"] is False
    assert matrix["policy"]["source_limited_continuation_requires_explicit_operator_instruction"] is True


def test_g1_auto_pass_is_preserved_after_rolling_state_advances_to_wp3_source_recovery() -> None:
    decision = load(WP1 / "C2S_SPTOI_G1_DELEGATED_DECISION_v0_1.json")
    qa = load(WP1 / "C2S_SPTOI_WP1_QA_PACKET_v0_1.json")
    state = load(SPTO_RECORDS / "C2S_SPTOI_PROGRAMME_STATE_v0_1.json")
    pointer = load(POINTER)
    assert decision["gate_class"] == "AUTO"
    assert decision["decision"] == "PASS"
    assert decision["authority_delta"] == "NONE_REFERENCE_ONLY_MACHINERY"
    assert qa["result"] == "PASS"
    assert qa["checks"]["source_derived_semantics_used"] is False
    assert state["packet_id"] == pointer["current_packet"] == "C2S-SPTOI-WP3"
    assert state["next_packet"] == pointer["next_packet"] == "C2S-SPTOI-WP3"
    assert state["protected_source"] == pointer["protected_source"] == "DENIED"
    assert state["parity_status"] == "BLOCKED_WP3_CANDIDATE_DIVERGES_IN_FIVE_CASES_AND_FULL_EXPECTED_OUTPUTS_UNAVAILABLE"
    assert state["validation"] == "LOCKED_UNCONSUMED"
    assert state["semantic_authority"] == "NONE"
