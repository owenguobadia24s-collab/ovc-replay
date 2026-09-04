from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "docs/programmes/lsiac-v0-1/adjudication/LSIAC_ACCESSION_ADJUDICATION_PROTOCOL_v0_1.json"
RECEIPT = ROOT / "docs/programmes/lsiac-v0-1/adjudication/LSIAC_ADJUDICATION_PROTOCOL_FREEZE_RECEIPT_v0_1.json"
PROTOCOL_SCHEMA = ROOT / "schemas/research_operations/lsiac_accession_adjudication_protocol_v0_1.schema.json"
RECORD_SCHEMA = ROOT / "schemas/research_operations/lsiac_accession_records_v0_1.schema.json"
CONTRACT = ROOT / "contracts/research_operations/lsiac/LSIAC_ACCESSION_ADJUDICATION_PROTOCOL_CONTRACT_v0_1.md"
FRONTIER = ROOT / "docs/programmes/lsiac-v0-1/frontier-freeze/LSIAC_ACCESSION_FRONTIER_FREEZE_RECEIPT_v0_1.json"

SOURCE_STANDING = {
    "SOURCE_EXACT", "SOURCE_DERIVED", "SOURCE_BOUND_EXTERNAL",
    "PENDING_SOURCE_BINDING", "SOURCE_CONFLICT", "LINEAGE_ALIAS",
}
EXPOSURE = {
    "FRESH_UNTOUCHED", "DISCOVERY_EXPOSED", "DEVELOPMENT_EXPOSED",
    "POST_HOC", "CONTAMINATED", "UNKNOWN",
}
HIGH_IMPACT = {
    "CANONICAL_PRINCIPLE", "CANONICAL_CAPABILITY",
    "CROSS_ARCHITECTURE_AMENDMENT_REQUIRED", "SOURCE_CONFLICT_RESOLUTION",
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def test_protocol_is_bound_to_operator_frozen_frontier() -> None:
    protocol = _load(PROTOCOL)
    frontier = _load(FRONTIER)
    assert protocol["generation_id"] == "OVC-LSIAC-ACCESSION-GEN-0001"
    assert protocol["frontier_binding"]["receipt_id"] == frontier["receipt_id"]
    assert protocol["frontier_binding"]["accession_cutoff"] == frontier["accession_cutoff"]
    assert protocol["frontier_binding"]["source_universe_manifest_sha256"] == frontier["source_universe"]["canonical_sha256"]
    assert protocol["frontier_binding"]["source_passports_sha256"] == frontier["source_universe"]["source_passports_canonical_sha256"]


def test_exact_protocol_bytes_match_freeze_receipt() -> None:
    receipt = _load(RECEIPT)
    assert receipt["protocol_content_hash"]["algorithm"] == "GIT_BLOB_SHA1"
    assert _git_blob_sha(PROTOCOL) == receipt["protocol_content_hash"]["value"]


def test_bound_contract_and_schemas_match_protocol() -> None:
    protocol = _load(PROTOCOL)
    assert _git_blob_sha(CONTRACT) == protocol["binding_contracts"]["protocol_contract"]["git_blob_sha"]
    assert _git_blob_sha(PROTOCOL_SCHEMA) == protocol["binding_contracts"]["protocol_schema"]["git_blob_sha"]
    assert _git_blob_sha(RECORD_SCHEMA) == protocol["binding_contracts"]["record_schema_pack"]["git_blob_sha"]
    _load(PROTOCOL_SCHEMA)
    _load(RECORD_SCHEMA)


def test_claim_cap_function_is_total_and_fail_closed() -> None:
    protocol = _load(PROTOCOL)
    entries = protocol["claim_strength_cap_function"]["entries"]
    pairs = {(row["source_standing"], row["exposure_state"]) for row in entries}
    assert len(entries) == 36
    assert len(pairs) == 36
    assert pairs == {(s, e) for s in SOURCE_STANDING for e in EXPOSURE}
    assert protocol["claim_strength_cap_function"]["fail_closed_rule"] == "ANY_UNLISTED_OR_INVALID_COMBINATION_IS_NOT_EVALUABLE"


def test_claim_caps_close_precision_note_edges() -> None:
    protocol = _load(PROTOCOL)
    caps = {(row["source_standing"], row["exposure_state"]): row["max_positive_claim_strength"] for row in protocol["claim_strength_cap_function"]["entries"]}
    assert caps[("SOURCE_EXACT", "DISCOVERY_EXPOSED")] == "DESCRIPTIVE_SCOPED"
    assert caps[("SOURCE_EXACT", "UNKNOWN")] == "HISTORICAL_CONTEXT_ONLY"
    assert all(caps[("SOURCE_CONFLICT", e)] == "NOT_EVALUABLE" for e in EXPOSURE)
    assert all(caps[("LINEAGE_ALIAS", e)] == "HISTORICAL_CONTEXT_ONLY" for e in EXPOSURE)
    assert all(caps[("PENDING_SOURCE_BINDING", e)] == "NOT_EVALUABLE" for e in EXPOSURE)


def test_role_cardinality_and_high_impact_review_are_explicit() -> None:
    protocol = _load(PROTOCOL)
    assert protocol["role_cardinality"]["none_rule"].startswith("NONE_MUST_BE_SINGLETON")
    assert set(protocol["role_admissibility_matrix"]) == set(protocol["closed_vocabularies"]["inheritance_role"])
    assert set(protocol["review_controls"]["high_impact_independent_review_triggers"]) == HIGH_IMPACT


def test_pass_one_cannot_make_survival_decisions() -> None:
    protocol = _load(PROTOCOL)
    forbidden = set(protocol["two_pass_review"]["PASS_1"]["forbidden_outputs"])
    assert {"FINAL_INHERITANCE_ROLE", "RETAIN_FORWARD", "DESTINATION_BINDING_SET", "ARCHITECTURE_EFFECT_SET", "SCIENTIFIC_PROMOTION"} <= forbidden
    assert protocol["two_pass_review"]["PASS_1"]["freeze_receipt_required_before_pass_2"] is True
    assert protocol["protocol_mutation_firewall"]["survival_outcomes_viewed_before_freeze"] is False
    assert protocol["authority"]["scientific_accession_decisions_created"] == 0


def test_source_durability_and_dependence_fail_closed() -> None:
    protocol = _load(PROTOCOL)
    assert protocol["durability_rules"]["verified_once_unbound"] == "NOT_LOAD_BEARING_RETRIEVABILITY_BY_ITSELF"
    assert protocol["durability_rules"]["missing_load_bearing"] == "SOURCE_BLOCKED_NO_SUBSTANTIVE_SURVIVAL_DECISION"
    assert protocol["dependence_and_aggregation"]["default_multi_source_scope"] == "INTERSECTION"
    assert protocol["dependence_and_aggregation"]["dependence_graph_required"] is True
    assert protocol["dependence_and_aggregation"]["authority_aggregation"].startswith("FORBIDDEN")


def test_frontier_incident_and_protocol_mutation_require_forward_reentry() -> None:
    protocol = _load(PROTOCOL)
    assert "REPAIR_OR_SUPERSEDE_GENERATION_FORWARD_ONLY" in protocol["failure_rules"]["FRONTIER_INTEGRITY_INCIDENT"]
    assert protocol["failure_rules"]["PROTOCOL_MUTATION_AFTER_OUTCOME"] == "SUCCESSOR_ACCESSION_GENERATION_OR_EXPLORATORY_REINSPECTION"
    assert protocol["rollback"].startswith("FORWARD_ONLY")
