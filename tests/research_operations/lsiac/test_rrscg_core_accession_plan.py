import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PLAN_DIR = ROOT / "docs/programmes/lsiac-v0-1/rrscg-core-accession-plan"
STATE = ROOT / "records/research_operations/lsiac/LSIAC_PROGRAMME_STATE_v0_18.json"
C2_POINTER = ROOT / "registries/opt_b/c2/vnext/CURRENT_OWNER_STRUCTURAL_SNAPSHOT_READ_SURFACE.json"
IROF_POINTER = ROOT / "registries/implementation/irof/CURRENT_STATE_POINTER.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_plan_requires_repository_effective_c2_owner_read_surface_and_reuses_irof():
    state = load(STATE)
    c2 = load(C2_POINTER)
    irof = load(IROF_POINTER)
    assert state["c2_owner_handoff"] == "SATISFIED_REPOSITORY_EFFECTIVE"
    assert c2["read_authority_id"] == "AUTH.OPT-B.C2.vNext.OWNER_STRUCTURAL_SNAPSHOT.READ.v0.1"
    assert c2["source_expansion"] == "NONE"
    assert irof["status"] == "COMPLETED"
    assert irof["programme_disposition"] == "INACTIVE_INFRASTRUCTURE_AVAILABLE"
    assert state["generic_execution_backbone"] == "REUSE_IROF_NO_NEW_GENERIC_RUNNER"


def test_rrscg_core_scope_is_narrow_and_specialist_programmes_are_excluded():
    state = load(STATE)
    scope = set(state["rrscg_core_scope"])
    assert {
        "RRSCG_R2_CONTINUATION_CONSTRAINT_KERNEL",
        "RRSCG_D9_CONSTRAINT_STATE_GEOMETRY_KINEMATICS",
        "RRSCG_D10_REDUCER_SUBCOMPONENT",
        "IROF_STAGE_ADAPTER",
    } <= scope
    excluded = " ".join(state["excluded_from_core"])
    assert "REPRESENTATION_ROBUSTNESS" in excluded
    assert "SPECIALIST_MEMORY_REGION_DRIVER_PRETRANSITION_BOUNDARY_SFF" in excluded
    assert "MULTICLOCK_COORDINATE_UTILITY_UNTIL_AFTER_SINGLE_CLOCK_PARITY" in excluded


def test_source_matrix_fails_closed_before_algorithm_implementation():
    matrix = load(PLAN_DIR / "RRSCG_CORE_SOURCE_BINDING_MATRIX_v0_1.json")
    by_component = {row["component"]: row for row in matrix["sources"]}
    assert set(by_component) == {
        "RRSCG_R2_CONTINUATION_CONSTRAINT_KERNEL",
        "RRSCG_D9_CONSTRAINT_STATE_GEOMETRY_KINEMATICS",
        "RRSCG_D10_REDUCER_SUBCOMPONENT",
    }
    assert all(row["repository_algorithm_bytes"] == "NOT_FOUND" for row in by_component.values())
    assert all(row["binding_state"] == "SOURCE_BYTES_UNAVAILABLE_FOR_IMPLEMENTATION" for row in by_component.values())
    assert by_component["RRSCG_D9_CONSTRAINT_STATE_GEOMETRY_KINEMATICS"]["exact_handover_hashes"]["implementation_wheel_sha256"] == "41aa8e608155e332cf202e9a57b38662c1b4cc9aefa0762eb67c62e50be98cab"
    assert by_component["RRSCG_D10_REDUCER_SUBCOMPONENT"]["supersession_scope"].startswith("REDUCER_LAYER_ONLY")


def test_plan_does_not_grant_reserved_rrscg_accession_or_active_authority():
    authority = load(PLAN_DIR / "RRSCG_CORE_PLAN_AUTHORITY_MANIFEST_v0_1.json")
    state = load(STATE)
    assert authority["authority_delta"] == "NONE_PLAN_AND_SOURCE_BINDING_ROUTE_ONLY"
    assert "EFFECT_RRSCG_CANONICAL_CAPABILITY_OR_OBSERVER_FACULTY_ACCESSION" in authority["denied"]
    assert state["active_discovery_development_validation_authority"] == "NONE"
    assert state["validation"] == "LOCKED_UNCONSUMED"
    assert state["publication"] == "NONE"
    assert state["probability_risk_exposure_e_h_execution_authority"] == "NONE"
    assert state["future_operator_gate"] == "LSIAC-G-RRSCG-CORE-ACCESSION-AUTHORITY_AFTER_WP0_SOURCE_BINDING"
