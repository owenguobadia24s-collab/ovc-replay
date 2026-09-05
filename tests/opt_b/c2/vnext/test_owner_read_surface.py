import copy
import json
from pathlib import Path
import subprocess

import pytest

from ovc.opt_b.c2_vnext import owner_read_surface as ors


ROOT = Path(__file__).resolve().parents[4]
GENERATION = ROOT / "registries/opt_b/c2/vnext/C2_OWNER_STRUCTURAL_SNAPSHOT_GENERATION_v0_1.json"
AUTHORITY = ROOT / "registries/opt_b/c2/vnext/C2_OWNER_STRUCTURAL_SNAPSHOT_READ_AUTHORITY_v0_1.json"
POINTER = ROOT / "registries/opt_b/c2/vnext/CURRENT_OWNER_STRUCTURAL_SNAPSHOT_READ_SURFACE.json"
FIELD_CATALOG = ROOT / "registries/opt_b/c2/vnext/C2_OWNER_STRUCTURAL_SNAPSHOT_FIELD_CATALOG_v0_1.json"
SCHEMA = ROOT / "schemas/opt_b/c2/vnext/C2_OWNER_STRUCTURAL_SNAPSHOT_READ_v0_1.schema.json"
DECISION = ROOT / "docs/releases/active-stack-reclassification-v0-1/c2-owner-read-handoff/C2_OWNER_READ_HANDOFF_OPERATOR_DECISION_v0_1.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def binding(**overrides):
    value = {
        "schema": ors.SOURCE_BINDING_SCHEMA,
        "source_binding_id": "TEST.SOURCE.BINDING.v1",
        "source_authority_ref": "TEST_ALREADY_AUTHORISED_SOURCE",
        "provider": "TEST_PROVIDER_PROVENANCE_ONLY",
        "instrument": "GBPUSD",
        "side": "BID",
        "local_clock": "15M",
        "parent_clock": "2H_A_L",
        "partition_id": "TEST.PARTITION.v1",
        "context_start_utc": "2026-01-01T00:00:00Z",
        "context_end_exclusive_utc": "2026-01-03T00:00:00Z",
        "target_start_utc": "2026-01-01T00:00:00Z",
        "target_end_exclusive_utc": "2026-01-02T00:00:00Z",
        "source_slice_id": "TEST.SOURCE.SLICE.v1",
        "source_manifest_sha256": "a" * 64,
        "opt_a_release_id": "TEST.OPT-A.v1",
        "opt_a_manifest_id": "TEST.OPT-A.MANIFEST.v1",
        "opt_a_manifest_sha256": "b" * 64,
        "c1_release_id": "TEST.C1.v1",
        "c1_manifest_id": "TEST.C1.MANIFEST.v1",
        "source_object_ids": ["SOURCE.OBJECT.1"],
    }
    value.update(overrides)
    return value


def git_blob(path: str) -> str:
    return subprocess.run(
        ["git", "hash-object", path],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_operator_pass_and_current_pointer_are_bounded_read_only():
    decision = load(DECISION)
    authority = load(AUTHORITY)
    pointer = load(POINTER)
    assert decision["operator_instruction"] == "OVC APPROVE read-only C2 owner handoff"
    assert decision["decision"] == "PASS"
    assert decision["authority_delta"] == "READ_ONLY_CURRENT_OWNER_STRUCTURAL_SNAPSHOT_HANDOFF_ONLY"
    assert authority["operator_instruction"] == decision["operator_instruction"]
    assert authority["source_scope"]["instrument"] == "GBPUSD"
    assert set(authority["source_scope"]["sides"]) == {"BID", "ASK"}
    assert set(authority["source_scope"]["clocks"]) == {"15M", "2H_A_L"}
    assert authority["source_scope"]["validation"] == "LOCKED_UNCONSUMED"
    assert "OWNER_STATE_WRITE_OR_MUTATION" in authority["denied"]
    assert "NEW_PROVIDER_INSTRUMENT_MARKET_SIDE_OR_CLOCK" in authority["denied"]
    assert pointer["read_authority_id"] == authority["authority_id"]
    assert pointer["source_expansion"] == "NONE"


def test_owner_generation_binds_nine_exact_components_and_public_surface_blobs():
    generation = load(GENERATION)
    components = generation["active_component_bindings"]
    assert len(components) == 9
    assert {row["component"] for row in components} == {
        "OBSERVATION", "HORIZON", "LEVEL", "CONTAINER", "RELATION",
        "FORMULA", "TRANSITION", "PARENT_CONTEXT", "COMPUTABILITY",
    }
    for row in components:
        assert git_blob(row["implementation_path"]) == row["implementation_git_blob_sha"]
        assert git_blob(row["schema_path"]) == row["schema_git_blob_sha"]
    public = generation["public_read_surface"]
    assert git_blob(public["contract_path"]) == public["contract_git_blob_sha"]
    assert git_blob(public["schema_path"]) == public["schema_git_blob_sha"]
    assert git_blob(public["reader_code_path"]) == public["reader_code_git_blob_sha"]
    assert generation["owner"]["package_sha256"] == ors.OWNER_PACKAGE_SHA256


def test_public_field_catalog_is_schema_bound_and_fail_closed():
    catalog = load(FIELD_CATALOG)
    schema = load(SCHEMA)
    classes = {row["component"] for row in catalog["embedded_owner_record_classes"]}
    assert classes == {
        "OBSERVATION", "HORIZON", "LEVEL", "CONTAINER", "RELATION",
        "FORMULA", "TRANSITION", "PARENT_CONTEXT", "COMPUTABILITY",
    }
    assert "target_eligible" in schema["required"]
    assert "relations" in schema["properties"]["owner_records"]["required"]
    prohibited = set(catalog["prohibited_flattened_fields"])
    assert {"future_outcome", "probability", "risk", "exposure", "execution_action"} <= prohibited


@pytest.mark.parametrize(
    "mutation,marker",
    [
        ({"instrument": "EURUSD"}, "NEW_INSTRUMENT_AUTHORITY_DENIED"),
        ({"side": "MID"}, "NEW_SIDE_AUTHORITY_DENIED"),
        ({"local_clock": "5M"}, "NEW_LOCAL_CLOCK_AUTHORITY_DENIED"),
        ({"parent_clock": "4H"}, "NEW_PARENT_CLOCK_AUTHORITY_DENIED"),
        ({"source_authority_ref": ""}, "SOURCE_AUTHORITY_REF_REQUIRED"),
        ({"provider": ""}, "PROVIDER_PROVENANCE_REQUIRED"),
    ],
)
def test_source_binding_rejects_scope_or_authority_inference(mutation, marker):
    with pytest.raises(ors.OwnerReadSurfaceError, match=marker):
        ors.validate_source_binding(binding(**mutation))


def test_owner_scope_calls_existing_owner_builder_and_restores_globals(monkeypatch):
    source = binding()
    local = [{
        "side": "BID", "clock": "15M", "c1_release_id": source["c1_release_id"],
        "opt_a_release_id": source["opt_a_release_id"],
        "source_manifest_sha256": source["source_manifest_sha256"],
        "source_slice_id": source["source_slice_id"],
    }]
    parent = [{
        "side": "BID", "clock": "2H_A_L", "c1_release_id": source["c1_release_id"],
        "opt_a_release_id": source["opt_a_release_id"],
        "source_manifest_sha256": source["source_manifest_sha256"],
        "source_slice_id": source["source_slice_id"],
    }]
    original = {
        key: getattr(ors.c2rm, key)
        for key in ("CONTEXT_START", "CONTEXT_END", "TARGET_START", "TARGET_END", "PARTITION_ID", "MATERIALISATION_ID")
    }
    observed = {}

    def fake_build_side(side, rows15, rows2h):
        observed.update({
            "side": side,
            "context_start": ors.c2rm.CONTEXT_START,
            "target_end": ors.c2rm.TARGET_END,
            "partition": ors.c2rm.PARTITION_ID,
            "materialisation": ors.c2rm.MATERIALISATION_ID,
            "local_rows": copy.deepcopy(rows15),
            "parent_rows": copy.deepcopy(rows2h),
        })
        return {"side": side}

    monkeypatch.setattr(ors.c2rm, "build_side", fake_build_side)
    assert ors.build_owner_side_result(source, local, parent) == {"side": "BID"}
    assert observed["context_start"] == source["context_start_utc"]
    assert observed["target_end"] == source["target_end_exclusive_utc"]
    assert observed["partition"] == source["partition_id"]
    assert observed["materialisation"].startswith(ors.HANDOFF_ID)
    for key, value in original.items():
        assert getattr(ors.c2rm, key) == value


def manual_side_result():
    fvt = "2026-01-01T00:15:00Z"
    observation = {
        "observation_id": "OBS.1",
        "interval_start": "2026-01-01T00:00:00Z",
        "interval_end": fvt,
        "first_valid_time": fvt,
        "continuity": {"status": "SEGMENT_START", "segment_id": "SEG.1"},
        "projection_eligibility": {"eligible": True},
    }
    membership = {"membership_id": "HOR.1", "first_valid_time": fvt, "status": "COMPUTABLE"}
    level = {"level_id": "LEVEL.1", "first_valid_time": fvt}
    container = {"container_id": "CONT.1", "first_valid_time": fvt}
    relation = {"relation_id": "REL.1", "object_id": "LEVEL.1", "first_valid_time": fvt, "topology": "ABOVE"}
    relation_set = {"relation_set_id": "RELSET.1", "relation_ids": ["REL.1"], "first_valid_time": fvt}
    profiles = [
        {"profile_output_id": f"PROFILE.{axis}", "axis": axis, "as_of_time": fvt, "computability": "COMPUTABLE"}
        for axis in ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION")
    ]
    context = {"bundle_id": "CTX.1", "local_first_valid_time": fvt, "first_valid_time": fvt}
    bundle = {
        "observation_id": "OBS.1",
        "first_valid_time": fvt,
        "target_eligible": True,
        "horizon_membership_ids": ["HOR.1"],
        "level_ids": ["LEVEL.1"],
        "container_ids": ["CONT.1"],
        "relation_set_ids": ["RELSET.1"],
        "profile_output_ids": {axis: [f"PROFILE.{axis}"] for axis in ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION")},
        "context_bundle_id": "CTX.1",
        "fixed_parent_observation_id": None,
    }
    return {
        "side": "BID",
        "complete15": [observation],
        "memberships": [membership],
        "levels": [level],
        "containers": [container],
        "relations": [relation],
        "relation_sets": [relation_set],
        "profiles": profiles,
        "contexts": [context],
        "bundles": [bundle],
    }


def test_snapshot_is_deterministic_exact_owner_read_with_typed_absence():
    source = binding()
    side = manual_side_result()
    first = ors.build_snapshot_stream(side, source)
    second = ors.build_snapshot_stream(copy.deepcopy(side), copy.deepcopy(source))
    assert first == second
    assert len(first) == 1
    snapshot = first[0]
    assert snapshot["snapshot_id"] == ors.canonical_sha256({key: value for key, value in snapshot.items() if key != "snapshot_id"})
    assert snapshot["effective_time"] == snapshot["interval_end"] == snapshot["first_valid_time"]
    assert snapshot["target_eligible"] is True
    assert snapshot["owner_records"]["relations"][0]["relation_id"] == "REL.1"
    assert snapshot["component_availability"]["transition"] == "NOT_EMITTED_BY_BOUND_OWNER_MATERIALISATION"
    assert snapshot["component_availability"]["computability"] == "NOT_EMITTED_BY_BOUND_OWNER_MATERIALISATION"
    assert snapshot["authority"]["read_only"] is True
    assert snapshot["authority"]["new_source_authority"] == "DENIED"


def test_snapshot_fails_closed_on_unresolved_owner_relation_reference():
    side = manual_side_result()
    side["relation_sets"][0]["relation_ids"] = ["REL.MISSING"]
    with pytest.raises(ors.OwnerReadSurfaceError, match="RELATION_REF_UNRESOLVED"):
        ors.build_snapshot_stream(side, binding())
