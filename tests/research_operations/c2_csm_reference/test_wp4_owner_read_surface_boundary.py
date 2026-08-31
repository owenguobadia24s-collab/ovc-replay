from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WP4 = ROOT / "docs/programmes/c2s-sptoi-v0-1/wp4"
SPTO = ROOT / "records/research_operations/spto"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def test_current_owner_is_exactly_bound_but_exposes_no_qualified_stream_contract() -> None:
    census = _json(WP4 / "C2S_SPTOI_WP4_OWNER_READ_SURFACE_CENSUS_v0_1.json")
    authority = _json(ROOT / "registries/opt_b/c2/vnext/C2_VNEXT_ACTIVE_RUNTIME_AUTHORITY_v0_1.json")
    assert authority["authority_id"] == census["current_owner"]["authority_id"]
    assert authority["state"] == "ACTIVE_STRUCTURAL_DESCRIPTION_DISCOVERY_DEVELOPMENT"
    assert authority["semantic_authority"] == "EXACT_NINE_COMPONENT_C2_VNEXT_CORE_ONLY"
    assert census["qualified_surfaces"] == []
    assert census["repository_search"]["qualified_contract_matches"] == 0
    assert census["result"] == "OWNER_READ_SURFACE_REQUIRED"
    assert census["source_evaluability"] == "SOURCE_NOT_EVALUABLE"


def test_every_census_candidate_is_hash_bound_and_disqualified() -> None:
    census = _json(WP4 / "C2S_SPTOI_WP4_OWNER_READ_SURFACE_CENSUS_v0_1.json")
    for candidate in census["candidate_surfaces"]:
        assert candidate["qualified"] is False
        assert candidate["disqualifying_evidence"]
        for key, value in candidate.items():
            if key == "sha256":
                assert _sha256(candidate["path"]) == value
            elif key.endswith("_sha256") and key != "sha256":
                path_key = key.removesuffix("_sha256") + "_path"
                assert _sha256(candidate[path_key]) == value


def test_current_authority_record_hash_and_legacy_denial_are_stable() -> None:
    census = _json(WP4 / "C2S_SPTOI_WP4_OWNER_READ_SURFACE_CENSUS_v0_1.json")
    owner = census["current_owner"]
    assert _sha256(owner["authority_record"]) == owner["authority_record_sha256"]
    legacy = (ROOT / "src/ovc/opt_b/c2/__init__.py").read_text(encoding="utf-8")
    assert 'CURRENT_AUTHORITY_STATE = "LEGACY_INACTIVE_NEW_EVIDENCE_DENIED"' in legacy


def test_no_candidate_or_historical_reference_is_substituted() -> None:
    census = _json(WP4 / "C2S_SPTOI_WP4_OWNER_READ_SURFACE_CENSUS_v0_1.json")
    assert census["adapter_implementation"] == "NONE"
    assert census["private_engine_introspection"] == "NOT_PERFORMED"
    assert census["downstream_reconstruction"] == "NOT_PERFORMED"
    assert census["historical_reference_substitution"] == "NOT_PERFORMED"
    state = _json(SPTO / "C2S_SPTOI_PROGRAMME_STATE_v0_4.json")
    assert state["adapter_implementation"] == "NONE"
    assert state["historical_reference_as_current_owner_truth"] == "PROHIBITED_AND_NOT_USED"
    assert state["active_c2_authority"] == "NONE_FOR_C2S_SPTOI"


def test_blocked_state_and_source_matrix_preserve_exact_reentry_boundary() -> None:
    state = _json(SPTO / "C2S_SPTOI_PROGRAMME_STATE_v0_4.json")
    matrix = _json(SPTO / "C2S_SPTOI_SOURCE_COMPLETENESS_MATRIX_v0_4.json")
    assert state["status"] == "BLOCKED_OWNER_READ_SURFACE_REQUIRED_SOURCE_NOT_EVALUABLE"
    assert state["blockers"] == ["OWNER_READ_SURFACE_REQUIRED", "SOURCE_NOT_EVALUABLE"]
    assert state["next_packet"] == "C2S-SPTOI-WP4_REENTRY"
    prospective = next(item for item in matrix["families"] if item["family_id"] == "K_PROSPECTIVE_SPTO_ESL_MACHINERY")
    assert prospective["load_bearing_now"] is True
    assert prospective["status"] == state["status"]
    assert matrix["policy"]["later_sequential_packets_may_bypass_wp4"] is False


def test_historical_partial_source_limited_disposition_remains_unchanged() -> None:
    matrix = _json(SPTO / "C2S_SPTOI_SOURCE_COMPLETENESS_MATRIX_v0_4.json")
    historical = next(item for item in matrix["families"] if item["family_id"] == "A_HISTORICAL_C2_REFERENCE")
    assert historical["status"] == "PARTIAL_SOURCE_LIMITED_ACCEPTED_G3_ALG"
    assert historical["candidate"] == "QUARANTINED_CORROBORATING_ONLY_20_OF_25_CASES_794_OF_800_FIELDS"
    assert historical["owner_truth"] == "PROHIBITED"
    assert matrix["policy"]["parity_criteria_may_be_weakened"] is False


def test_owner_handoff_request_requires_public_materialisation_not_spTO_invention() -> None:
    requirement = _json(WP4 / "C2S_SPTOI_WP4_OWNER_READ_SURFACE_REQUIRED_v0_1.json")
    assert requirement["status"] == "OWNER_READ_SURFACE_REQUIRED"
    assert requirement["source_evaluability"] == "SOURCE_NOT_EVALUABLE"
    assert requirement["adapter_written"] is False
    assert requirement["protected_source_accessed"] is False
    assert len(requirement["required_owner_handoff"]["required_contents"]) == 13
    assert "DO_NOT_AUTHORISE_SPTO_TO_INVENT_THE_MISSING_OWNER_SURFACE" in requirement["operator_action"]


def test_authority_and_dependency_manifests_fail_closed() -> None:
    authority = _json(WP4 / "C2S_SPTOI_WP4_AUTHORITY_MANIFEST_v0_1.json")
    frontier = _json(WP4 / "C2S_SPTOI_WP4_DEPENDENCY_FRONTIER_v0_1.json")
    assert authority["status"] == "BLOCKED_OWNER_READ_SURFACE_REQUIRED"
    assert "PRIVATE_ENGINE_FIELD_INTROSPECTION" in authority["denied"]
    assert "HISTORICAL_C2_REFERENCE_AS_CURRENT_OWNER_TRUTH" in authority["denied"]
    assert frontier["blockers"] == ["OWNER_READ_SURFACE_REQUIRED", "SOURCE_NOT_EVALUABLE"]
    assert frontier["next_packet"] == "C2S-SPTOI-WP4_REENTRY"
