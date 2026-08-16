from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ovc.development.identity import canonical_sha256


ROOT = Path(__file__).resolve().parents[2]
PLAN_IDENTITY = ROOT / "docs/plans/system-atlas/ATLAS_PLAN_IDENTITY_v0_1_R1.json"
WP0 = ROOT / "docs/programmes/system-atlas-v0-1/wp0"
REGISTRY = ROOT / "registries/system_atlas"
STATE_ROOT = ROOT / "registries/implementation/system_atlas_v0_1"
PG_MIGRATION_REGISTRY = ROOT / "registries/governance/programme_genesis/MIGRATION_SOURCE_REGISTRY_v0_1.json"
PGN_CENSUS_BUILDER = ROOT / "scripts/governance/build_pgn_wp2_census.py"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_exact_ratified_plan_and_design_identities() -> None:
    identity = load(PLAN_IDENTITY)
    assert identity["plan_id"] == "OVC-SYSTEM-ATLAS-CONFORMANCE-IMPLEMENTATION-PLAN-0.1-R1-RATIFIED"
    assert identity["sha256"] == "a2b2ed19e1836059c02ccb00aae554194ddb1ea6259279a5a0914c808f467c30"
    assert identity["byte_size"] == 59244
    assert identity["governing_design"]["sha256"] == "7ff61e5a4e488aa6b1a405a43ca49947db4e26175e9c7e3b4bb1aa20b2614e1e"
    assert identity["governing_design"]["byte_size"] == 64158


def test_g0_pass_preserves_reserved_authority_boundary() -> None:
    decision = load(WP0 / "ATLAS_G0_OPERATOR_DECISION.json")
    authority = load(WP0 / "ATLAS_WP0_AUTHORITY_ENVELOPE.json")
    assert decision["decision"] == "PASS"
    assert decision["authority_after_materialisation"]["validation_consumption"] == "LOCKED_UNCONSUMED"
    assert decision["authority_after_materialisation"]["permanent_operational_reliance"] == "DENIED_UNTIL_ATLAS-G-OBSERVABILITY-ACTIVATE"
    assert "INFER_OWNER_OR_AUTHORITY" in authority["denied"]
    assert "NEW_RESEARCH_CONSOLE_SOURCE" in authority["denied"]
    assert "ATLAS-G-OBSERVABILITY-ACTIVATE" in authority["reserved_stops"]


def test_baseline_binds_physical_main_and_qualified_vit_tree() -> None:
    baseline = load(WP0 / "ATLAS_WP0_BASELINE.json")
    assert baseline["physical_main"]["commit"] == "1afae5de5134003b756ae3e077ff628018896491"
    assert baseline["physical_main"]["tree"] == "4c1c6892a4c930b1e252270564c893162e242d9d"
    assert baseline["qualified_vit_predecessor"]["head_commit"] == "074b0b4ae449e79f1864910f8bd9f81b9c59c5a2"
    assert baseline["qualified_vit_predecessor"]["exact_physical_vit_tree_equality"] is True
    assert baseline["external_main_movement"]["payload_rebuild_required"] is False


def test_reuse_and_cross_programme_admission_are_non_transitive() -> None:
    reuse = load(REGISTRY / "ATLAS_REUSE_BINDING_MATRIX_v0_1.json")
    by_dependency = {entry["dependency"]: entry for entry in reuse["entries"]}
    assert by_dependency["GRT_TOPOLOGY_ENGINE"]["classification"] == "REQUIRED_REUSE"
    assert by_dependency["SHARED_SYSTEMS"]["fallback"] == "LOCAL_BOUNDED"
    assert by_dependency["EXTERNAL_ATLAS_ARTIFACT_ROOT"]["status"] == "SATISFIED_BOUND_READ_WRITE_VERIFIED"

    admission = load(REGISTRY / "ATLAS_CROSS_PROGRAMME_ADMISSION_MATRIX_v0_1.json")
    by_source = {entry["source"]: entry for entry in admission["entries"]}
    assert by_source["RESEARCH_CONSOLE_VNEXT"]["existing_admission"] == "NO_REAL_ATLAS_SOURCE_ADMISSION"
    assert by_source["PROGRAMME_GENESIS_GRT"]["interlock"] == "NO_GRT2_G3_ACTIVATION_OR_PROGRAMME_WRITE"
    assert "grants no Console source" in admission["non_transitivity"]


def test_external_root_and_reviewer_binding_fail_closed() -> None:
    external = load(WP0 / "ATLAS_EXTERNAL_GENERATION_ROOT.json")
    reviewer = load(REGISTRY / "ATLAS_INDEPENDENT_REVIEWER_BINDING_v0_1.json")
    assert external["status"] == "BOUND_READ_WRITE_VERIFIED"
    assert external["repository_disjoint"] is True
    assert external["destructive_retention"].startswith("DENIED")
    assert reviewer["status"] in {"UNBOUND", "ACCEPTED_EXTERNAL_BINDING_PENDING_REPOSITORY_MATERIALISATION"}
    if reviewer["status"] == "UNBOUND":
        assert reviewer["implementation_effect"] == "NONE_WP0_THROUGH_Q6_MAY_PROCEED"
        assert "INELIGIBLE" in reviewer["activation_effect"]
    else:
        assert reviewer["implementation_effect"] == "ATLAS_G4_ALG_REVIEWER_REQUIREMENT_SATISFIED_ON_MATERIALISATION"
        assert "Q6_IND" in reviewer["activation_effect"]
        assert reviewer["scope_status"]["Q6-IND_GOVERNANCE_SECURITY_VISUAL_OPERATIONAL_REVIEW"].startswith("NOT_REVIEWED")


def test_source_census_has_no_required_missing_source() -> None:
    census = load(WP0 / "ATLAS_SOURCE_DEPENDENCY_CENSUS.json")
    assert census["baseline_tree"] == "4c1c6892a4c930b1e252270564c893162e242d9d"
    assert census["mandatory_missing_sources"] == []
    assert census["authority_discrepancy"].startswith("NONE_MATERIAL_TO_ATLAS_ENTRY")
    assert len(census["pre_existing_currentness_findings"]) == 2
    assert len(census["repository_sources"]) >= 13
    for source in census["repository_sources"]:
        assert len(source["blob"]) == 40
        int(source["blob"], 16)


def test_programme_state_preserves_wp0_completion_and_activation_boundary() -> None:
    pointer = load(STATE_ROOT / "CURRENT_STATE_POINTER.json")
    state = load(STATE_ROOT / pointer["current_state"])
    assert pointer["programme_id"] == "OVC-SYSTEM-ATLAS-CONFORMANCE-v0.1"
    assert pointer["next_operator_gate"] == "ATLAS-G-OBSERVABILITY-ACTIVATE"
    assert state["tests"]["wp0_materialisation"] in {"PENDING_EXACT_PACKET_HEAD", "PASS_INTEGRATED_PR_970"}
    if state["current_gate"] == "ATLAS-G4-ALG" and state["gate_status"].startswith("BLOCKED"):
        assert state["blockers"] == ["ATLAS_G4_ALG_ELIGIBLE_INDEPENDENT_REVIEWER_UNBOUND"]
    else:
        assert state["blockers"] == []
    assert state["terminal_pre_activation_target"] == "ATLAS_IMPLEMENTED_QUALIFIED_LIVE_SHADOW"


def test_atlas_state_is_not_a_programme_genesis_legacy_migration_target() -> None:
    atlas_state_path = "registries/implementation/system_atlas_v0_1/ATLAS_PROGRAMME_STATE_v0_1.json"
    migration_registry = load(PG_MIGRATION_REGISTRY)
    assert atlas_state_path in migration_registry["discovery"]["exclude_paths"]
    assert "OVC-SYSTEM-ATLAS-CONFORMANCE-v0.1" in migration_registry["discovery"]["native_programmes_excluded"]
    builder_source = PGN_CENSUS_BUILDER.read_text(encoding="utf-8")
    assert atlas_state_path in builder_source


def test_vit_authority_and_dependency_identities_are_canonical() -> None:
    authority = load(WP0 / "ATLAS_WP0_VIT_AUTHORITY_MANIFEST.json")
    frontier = load(WP0 / "ATLAS_WP0_VIT_DEPENDENCY_FRONTIER.json")
    assert canonical_sha256(authority["payload"]) == authority["logical_id"]
    assert canonical_sha256(frontier["payload"]) == frontier["logical_id"]
    assert authority["payload"]["authority_class"] == "AUTO_EXECUTABLE"
    assert frontier["payload"]["predecessor_requirement"] == "QUALIFIED_VIT_GENERATION_REQUIRED"


def test_all_wp0_json_is_canonicalizable_and_self_consistent() -> None:
    files = sorted(WP0.glob("*.json")) + sorted(REGISTRY.glob("*.json")) + sorted(STATE_ROOT.glob("*.json")) + [PLAN_IDENTITY]
    assert files
    for path in files:
        value = load(path)
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        assert len(hashlib.sha256(canonical).hexdigest()) == 64
