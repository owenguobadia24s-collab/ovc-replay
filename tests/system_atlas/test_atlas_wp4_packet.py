from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ovc.development.identity import canonical_sha256


ROOT = Path(__file__).resolve().parents[2]
WP4 = ROOT / "docs/programmes/system-atlas-v0-1/wp4"
STATE = ROOT / "registries/implementation/system_atlas_v0_1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp4_gate_is_independent_non_operator_pass() -> None:
    gate = load(WP4 / "ATLAS_G4_ALG_GATE_PACKET.json")
    request = load(WP4 / "ATLAS_G4_ALG_REVIEW_REQUEST.json")
    assert gate["gate_class"] == "INDEPENDENT_REVIEW_BLOCKING_NON_OPERATOR"
    assert gate["recommended_decision"] == "PASS"
    assert gate["independent_review_status"] == "PASS_ELIGIBLE_IMPLEMENTATION_INDEPENDENT"
    assert gate["blockers"] == []
    assert request["status"] == "COMPLETED_PASS"
    assert request["operator_substitution_permitted"] is False
    assert request["self_attestation_permitted"] is False
    assert request["required_verdict"] == "ELIGIBLE_INDEPENDENT_PASS"


def test_wp4_vit_bindings_are_canonical() -> None:
    for name in ("ATLAS_WP4_VIT_AUTHORITY_MANIFEST.json", "ATLAS_WP4_VIT_DEPENDENCY_FRONTIER.json"):
        binding = load(WP4 / name)
        assert binding["logical_id"] == canonical_sha256(binding["payload"])


def test_wp4_packet_preserves_read_only_boundaries() -> None:
    packet = load(WP4 / "ATLAS_WP4_IMPLEMENTATION_PACKET.json")
    assert packet["canonical_assertions_emitted"] == 0
    assert packet["owner_or_authority_state_published"] is False
    assert packet["optimized_resolver_accepted"] is False
    assert packet["research_console_source_admitted"] is False
    assert packet["grt_authority_activated"] is False
    assert packet["shared_systems_authority_activated"] is False
    assert packet["changed_scientific_semantics"] is False
    assert packet["write_authority_created"] is False
    assert packet["validation_consumed"] is False
    assert packet["canonical_publication"] is False


def test_wp4_review_evidence_identity_is_bound() -> None:
    qa = load(WP4 / "ATLAS_WP4_QA_PACKET.json")
    request = load(WP4 / "ATLAS_G4_ALG_REVIEW_REQUEST.json")
    expected = "2cf3879276cb8676890b631880222ad2c704760e3455b80ab482cd4647b0a1e6"
    assert qa["external_algorithm_review_evidence"]["sha256"] == expected
    assert request["review_evidence"]["sha256"] == expected
    assert qa["checks"]["canonical_assertions"] == "PASS_ZERO_AT_ATLAS_G4_ALG_CLOSEOUT"


def test_wp4_external_review_is_exact_and_scope_valid() -> None:
    binding_path = ROOT / "registries/system_atlas/ATLAS_INDEPENDENT_REVIEWER_BINDING_v0_1.json"
    review_path = WP4 / "ATLAS_G4_ALG_INDEPENDENT_REVIEW_RECORD.json"
    binding = load(binding_path)
    review = load(review_path)
    assert hashlib.sha256(binding_path.read_bytes()).hexdigest() == "9a77b3910d1d4ac5e50215f147687012da5e7e1464124f0c036ae9d48924163b"
    assert hashlib.sha256(review_path.read_bytes()).hexdigest() == "023ee896732d37b6c5228056fa7e81f4a1e46ca44420dc5b37f66e5ad43d92df"
    assert binding["implementation_author_conflict_status"] == "NO_RESOLVER_IMPLEMENTATION_AUTHOR_CONFLICT"
    assert binding["scope_status"]["ATLAS-G4-ALG_PREDICATE_OWNER_AUTHORITY_ALGORITHMS"] == "BOUND_ELIGIBLE_REVIEW_COMPLETED"
    assert binding["scope_status"]["Q6-IND_GOVERNANCE_SECURITY_VISUAL_OPERATIONAL_REVIEW"] == "NOT_REVIEWED_NOT_SATISFIED_BY_THIS_BINDING"
    assert review["verdict"] == "PASS"
    assert review["blocking_findings"] == []
    assert review["independent_reproduction"]["all_cases_match"] is True
    assert {row["result"] for row in review["criteria"]} == {"PASS"}


def test_wp4_remains_qualified_history_after_integration() -> None:
    pointer = load(STATE / "CURRENT_STATE_POINTER.json")
    state = load(STATE / pointer["current_state"])
    for field in ("status", "current_packet", "current_gate", "next_packet"):
        assert pointer[field] == state[field]
    assert state["tests"]["wp4_independent_algorithm_review"] == "PASS_ELIGIBLE_INDEPENDENT_REVIEW"
    assert state["tests"]["wp4_integration"] == "PASS_INTEGRATED_PR_987"
    assert state["blockers"] == []
    assert pointer["next_operator_gate"] == "ATLAS-G-OBSERVABILITY-ACTIVATE"


def test_wp4_main_advance_is_non_material_to_reviewed_algorithm() -> None:
    record = load(WP4 / "ATLAS_WP4_PLACEMENT_CURRENTNESS_RECORD.json")
    assert record["material_invalidation"] is False
    assert record["algorithm_review_reopened"] is False
    assert record["dependency_assessment"]["wp4_reviewed_algorithm_blobs"] == "UNCHANGED"
    assert record["action"] == "NORMAL_MERGE_CURRENT_MAIN_RENEW_EXACT_PIP_PLACEMENT_AND_ASSURANCE"
