from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.research_operations.p1cdi.test_p1cdii_wp1_schemas import validate_contract


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs/programmes/p1cdi-v0-1/wp4"
STATE = ROOT / "records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_1.json"
REVIEW4_SHA256 = "c93d4c78e5c4623736846151504ff0f67dcf9a37b530efde81251f5a753557ce"
AUTHORITY_ID = "225cd309071f059aa144e30a919c79608ca0e163b14abb5f96b90d238b365738"
DEPENDENCY_ID = "c5423d964ebcf385e2294b25f1c02dfbce5a7b4f99ff322dcaa4f6b66dad0e0b"
BLOCKERS = [
    "P1CDII_G4_ALG_FRESH_REVIEW_4_BLOCK_001_DIRECT_ROOT_FAST_PATH_DOES_NOT_PROVE_FIRST_GENERATION_BINDING",
    "P1CDII_G4_ALG_FRESH_REVIEW_4_BLOCK_002_WRAPS_EXPOSES_UNGUARDED_CORRESPONDENCE_ENTRYPOINT",
]


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def test_remediation_5_pass_is_bounded_and_routes_only_fresh_review_5() -> None:
    review = BASE / "P1CDII_G4_ALG_FRESH_INDEPENDENT_REVIEW_4_PACKET_v0_1.json"
    implementation = json.loads((BASE / "P1CDII_WP4_REMEDIATION_5_IMPLEMENTATION_PACKET_v0_1.json").read_text())
    qa = json.loads((BASE / "P1CDII_WP4_REMEDIATION_5_QA_PACKET_v0_1.json").read_text())
    decision = json.loads((BASE / "P1CDII_WP4_REMEDIATION_5_DECISION_v0_1.json").read_text())
    authority = json.loads((BASE / "P1CDII_WP4_REMEDIATION_5_AUTHORITY_MANIFEST_v0_1.json").read_text())
    dependency = json.loads((BASE / "P1CDII_WP4_REMEDIATION_5_DEPENDENCY_FRONTIER_v0_1.json").read_text())
    state = json.loads(STATE.read_text())

    assert hashlib.sha256(review.read_bytes()).hexdigest() == REVIEW4_SHA256
    assert implementation["immutable_review_4_block"]["packet_sha256"] == REVIEW4_SHA256
    assert implementation["immutable_review_4_block"]["blockers"] == BLOCKERS
    assert implementation["implementation_commit"] == "e6a0c5c035920fa58281c247cd0b056b6da62be1"
    assert implementation["implementation_tree"] == "e46d08a53633a26abdc13143c10952a006041cb6"
    assert implementation["remediation"]["frozen_contract_change"] == "NONE"
    assert implementation["authority"]["authority_delta"] == "NONE"
    assert implementation["authority"]["remediation_author_may_issue_g4_alg_pass"] is False
    assert canonical_sha256(authority) == AUTHORITY_ID
    assert canonical_sha256(dependency) == DEPENDENCY_ID

    assert qa["status"] == "PASS_PENDING_EXACT_FINAL_INTEGRATION"
    assert qa["qa_recommendation"] == "PASS_CONDITIONAL_ON_EXACT_FINAL_REQUIRED_ASSURANCE"
    assert qa["checks"]["deterministic_series_id_not_root_proof"] == "PASS"
    assert qa["checks"]["wrapped_original_escape"] == "PASS_REMOVED"
    assert qa["g4_alg_decision"] == "UNRESOLVED_REQUIRES_FRESH_CONFLICT_FREE_REVIEW_5"
    assert qa["remediation_author_may_issue_g4_alg_pass"] is False
    assert qa["successor_beyond_wp4_authorised"] is False

    assert decision["decision"] == "PASS_REMEDIATION"
    assert decision["authority_delta"] == "NONE"
    assert decision["authority_manifest_id"] == AUTHORITY_ID
    assert decision["dependency_frontier_id"] == DEPENDENCY_ID
    assert decision["p1cdii_g4_alg"]["current_status"] == "UNRESOLVED"
    assert decision["p1cdii_g4_alg"]["fresh_conflict_free_review_5_required"] is True
    assert decision["p1cdii_g4_alg"]["remediation_author_eligible_to_issue_g4_alg_pass"] is False
    assert decision["successor_beyond_wp4_authorised"] is False
    assert decision["next_packet"] == "P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-5"

    remediation = state["packets"]["P1CDII-WP4-REMEDIATION-5"]
    review5 = state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-5"]
    assert state["status"] == "GATE_READY"
    assert remediation["status"] == "COMPLETED"
    assert remediation["authority_required"] == "AUTO_EXECUTABLE"
    assert remediation["authority_delta"] == "NONE"
    assert remediation["blockers"] == []
    assert review5["status"] == "READY"
    assert review5["authority_required"] == "INDEPENDENT_BLOCKING"
    assert review5["authority_delta"] == "NONE"
    assert state["blockers"] == []
    assert state["next_packet"] == "P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-5"
    assert state["authority"]["operational_read_only"] == "DENIED"
    assert state["authority"]["continuous_intake"] == "DENIED"

    validate_contract(
        json.loads(
            (ROOT / "schemas/research_operations/p1cdi/p1cdii_programme_state_v0_1.schema.json").read_text()
        ),
        state,
    )
