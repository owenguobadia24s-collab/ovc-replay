import copy
import hashlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
WP5 = ROOT / "docs/programmes/c2s-sptoi-v0-1/wp5"


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def test_core_wp5_objects_validate_against_exact_schemas():
    jsonschema = pytest.importorskip("jsonschema")
    pairs = [
        (
            "docs/programmes/c2s-sptoi-v0-1/wp5/C2S_SPTOI_WP5_TVX_EMPIRICAL_GRAMMAR_EVIDENCE_SOURCE_COMPLETENESS_MANIFEST_v0_1.json",
            "schemas/research_operations/spto/TVX_EMPIRICAL_GRAMMAR_EVIDENCE_SOURCE_COMPLETENESS_MANIFEST_v0_1.schema.json",
        ),
        (
            "docs/programmes/c2s-sptoi-v0-1/wp5/C2S_SPTOI_WP5_TVX_ANALYSIS_REPRODUCTION_PACK_v0_1.json",
            "schemas/research_operations/spto/TVX_ANALYSIS_REPRODUCTION_PACK_v0_1.schema.json",
        ),
        (
            "docs/programmes/c2s-sptoi-v0-1/wp5/C2S_SPTOI_WP5_C0C_SOURCE_CROSS_EXPORT_CONCORDANCE_RECEIPT_v0_1.json",
            "schemas/research_operations/spto/C0C_SOURCE_CROSS_EXPORT_CONCORDANCE_RECEIPT_v0_1.schema.json",
        ),
    ]
    for record_path, schema_path in pairs:
        jsonschema.Draft202012Validator(load(schema_path)).validate(load(record_path))


def test_exact_required_round_denominator_and_known_export_hashes_are_bound():
    manifest = load(
        "docs/programmes/c2s-sptoi-v0-1/wp5/"
        "C2S_SPTOI_WP5_TVX_EMPIRICAL_GRAMMAR_EVIDENCE_SOURCE_COMPLETENESS_MANIFEST_v0_1.json"
    )
    required = {"R9X", "R16", "R21", *(f"R{n}" for n in range(22, 32))}
    assert set(manifest["required_rounds"]) == required
    assert {item["round_id"] for item in manifest["sources"]} == required
    by_round = {item["round_id"]: item for item in manifest["sources"]}
    assert by_round["R9X"]["expected_sha256"] == "2a6ba57635f092c85d84872cc03c1e0ee6397e6a305d02b7e5889312eb0f7ba4"
    assert by_round["R16"]["expected_sha256"] == "b78ab74c50930c60017285ecb0c4369322e9cf7cb2b7c3a03770434664f24be5"
    assert by_round["R21"]["expected_sha256"] == "244738668a579f0047b05de070d32620dc15f3ea3fb92e618a1dc8d8de7858c4"


def test_recovery_candidates_never_become_exact_or_define_missing_mechanics():
    manifest = load(
        "docs/programmes/c2s-sptoi-v0-1/wp5/"
        "C2S_SPTOI_WP5_TVX_EMPIRICAL_GRAMMAR_EVIDENCE_SOURCE_COMPLETENESS_MANIFEST_v0_1.json"
    )
    assert manifest["status"] == "PARTIAL_SOURCE_LIMITED"
    assert manifest["source_policy"]["prose_may_define_missing_mechanics"] is False
    assert manifest["source_policy"]["reconstruction_admissible"] is False
    assert not any(item["disposition"] == "ADMITTED_EXACT" for item in manifest["sources"])
    reconstructed = [item for item in manifest["sources"] if "reconstruct" in item.get("notes", "").lower()]
    assert reconstructed
    assert all(item["disposition"] == "NOT_ADMITTED_RECOVERY_ONLY" for item in reconstructed)


def test_c0b_and_c0c_are_receipt_concordant_but_never_byte_equivalent_or_joinable():
    lineage = load(
        "docs/programmes/c2s-sptoi-v0-1/wp5/C2S_SPTOI_WP5_C0B_C0C_SOURCE_LINEAGE_v0_1.json"
    )
    receipt = load(
        "docs/programmes/c2s-sptoi-v0-1/wp5/"
        "C2S_SPTOI_WP5_C0C_SOURCE_CROSS_EXPORT_CONCORDANCE_RECEIPT_v0_1.json"
    )
    assert lineage["c0b"]["state"] == "C0B_RECEIPT_CONCORDANT"
    assert lineage["c0b"]["byte_equivalent"] is False
    assert lineage["c0c"]["byte_equivalent"] is False
    assert lineage["c0c"]["cross_export_join_eligible"] is False
    assert receipt["concordance_state"] == "RECEIPT_CONCORDANT_NOT_BYTE_REPRODUCED"
    assert receipt["current_reproduction"] == "NOT_EXECUTED_RAW_EXPORT_BYTES_ABSENT"
    assert receipt["join_eligibility"] is False


def test_reproduction_is_withheld_not_failed_or_synthesised():
    pack = load(
        "docs/programmes/c2s-sptoi-v0-1/wp5/C2S_SPTOI_WP5_TVX_ANALYSIS_REPRODUCTION_PACK_v0_1.json"
    )
    assert pack["execution_status"] == "NOT_EXECUTED_SOURCE_INCOMPLETE"
    assert pack["executed_analyses"] == []
    assert pack["outputs"] == []
    assert pack["interpretation"] == "NOT_A_REPRODUCTION_FAILURE_OR_MISMATCH"


def test_gate_and_programme_state_advance_only_the_bounded_wp6_scope():
    pointer = load("registries/implementation/c2s_sptoi_v0_1/CURRENT_STATE_POINTER.json")
    state = load("records/research_operations/spto/C2S_SPTOI_PROGRAMME_STATE_v0_6.json")
    gate = load("docs/programmes/c2s-sptoi-v0-1/wp5/C2S_SPTOI_G5_DELEGATED_DECISION_v0_1.json")
    previous = load("records/research_operations/spto/C2S_SPTOI_PROGRAMME_STATE_v0_5.json")
    assert previous["packet_id"] == "C2S-SPTOI-WP4-REENTRY"
    assert pointer["current_packet"].startswith("C2S-SPTOI-WP")
    assert pointer["current_packet"] not in {"C2S-SPTOI-WP0", "C2S-SPTOI-WP1", "C2S-SPTOI-WP2", "C2S-SPTOI-WP3", "C2S-SPTOI-WP4-REENTRY"}
    if pointer["current_packet"] == "C2S-SPTOI-WP5":
        assert pointer["next_packet"] == "C2S-SPTOI-WP6"
    else:
        assert pointer["next_packet"] != pointer["current_packet"]
    assert state["supersedes_state"].endswith("C2S_SPTOI_PROGRAMME_STATE_v0_5.json")
    assert gate["decision"] == "PASS_PARTIAL_SOURCE_LIMITED"
    assert gate["authority_delta"] == "WP6_GENERIC_SOURCE_FREE_OR_EXACT_SOURCE_SUPPORTED_MECHANICS_ONLY"
    assert state["protected_source_access"] == "NONE"
    assert state["validation"] == "LOCKED_UNCONSUMED"
    assert state["candidate_freeze"] == "NONE"


def test_authority_and_dependency_frontier_content_identities_are_exact():
    authority = load("docs/programmes/c2s-sptoi-v0-1/wp5/C2S_SPTOI_WP5_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load("docs/programmes/c2s-sptoi-v0-1/wp5/C2S_SPTOI_WP5_DEPENDENCY_FRONTIER_v0_1.json")
    assert hashlib.sha256(canonical(authority["authority_manifest"])).hexdigest() == authority["authority_manifest_id"]
    frontier_body = copy.deepcopy(frontier)
    frontier_id = frontier_body.pop("dependency_frontier_id")
    assert hashlib.sha256(canonical(frontier_body)).hexdigest() == frontier_id
