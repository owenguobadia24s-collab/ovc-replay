import ast
import copy
import hashlib
import json
from pathlib import Path

import pytest

from ovc.opt_b.c2_vnext import owner_read_surface as owner
from ovc.research_operations.spto import source_binding as spto


ROOT = Path(__file__).resolve().parents[3]


def source_binding():
    return {
        "schema": owner.SOURCE_BINDING_SCHEMA,
        "source_binding_id": "SPTO.WP4.SYNTHETIC.v1",
        "source_authority_ref": "C2S-SPTOI-WP4-SYNTHETIC-QUALIFICATION-ONLY",
        "provider": "SYNTHETIC_QUALIFICATION_FIXTURE",
        "instrument": "GBPUSD",
        "side": "BID",
        "local_clock": "15M",
        "parent_clock": "2H_A_L",
        "partition_id": "SPTO.WP4.PARTITION.v1",
        "context_start_utc": "2026-01-01T00:00:00Z",
        "context_end_exclusive_utc": "2026-01-03T00:00:00Z",
        "target_start_utc": "2026-01-01T00:00:00Z",
        "target_end_exclusive_utc": "2026-01-02T00:00:00Z",
        "source_slice_id": "SPTO.WP4.SLICE.v1",
        "source_manifest_sha256": "a" * 64,
        "opt_a_release_id": "SYNTHETIC.OPT-A.v1",
        "opt_a_manifest_id": "SYNTHETIC.OPT-A.MANIFEST.v1",
        "opt_a_manifest_sha256": "b" * 64,
        "c1_release_id": "SYNTHETIC.C1.v1",
        "c1_manifest_id": "SYNTHETIC.C1.MANIFEST.v1",
        "source_object_ids": ["SYNTHETIC.OBJECT.1"],
    }


def owner_snapshot(*, fvt="2026-01-01T00:15:00Z", continuity="SEGMENT_START", eligible=True):
    observation = {
        "observation_id": f"OBS.{fvt}",
        "interval_start": "2026-01-01T00:00:00Z",
        "interval_end": fvt,
        "first_valid_time": fvt,
        "continuity": {"status": continuity, "segment_id": "SEG.1"},
        "projection_eligibility": {"eligible": eligible},
    }
    side = {
        "side": "BID",
        "complete15": [observation],
        "memberships": [],
        "levels": [],
        "containers": [],
        "relations": [],
        "relation_sets": [],
        "profiles": [],
        "contexts": [],
        "bundles": [{
            "observation_id": observation["observation_id"],
            "first_valid_time": fvt,
            "target_eligible": eligible,
            "horizon_membership_ids": [],
            "level_ids": [],
            "container_ids": [],
            "relation_set_ids": [],
            "profile_output_ids": {},
            "context_bundle_id": None,
            "fixed_parent_observation_id": None,
        }],
    }
    return owner.build_snapshot_stream(side, source_binding())[0]


def test_current_owner_surface_resolves_exact_generation_and_blobs():
    resolved = spto.resolve_owner_read_surface(ROOT)
    assert resolved["owner_generation_id"] == owner.OWNER_GENERATION_ID
    assert resolved["read_authority_id"] == spto.READ_AUTHORITY_ID
    assert len(resolved["component_bindings"]) == 9
    assert resolved["validation"] == "LOCKED_UNCONSUMED"
    assert resolved["protected_source_access"] == "NONE"


def test_snapshot_adapter_preserves_owner_records_and_content_identity():
    snapshot = owner_snapshot()
    adapted = spto.adapt_owner_snapshot(snapshot)
    assert adapted == snapshot
    assert adapted is not snapshot
    assert adapted["owner_records"] == snapshot["owner_records"]


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("owner_generation_id", "DRIFT", "OWNER_SNAPSHOT_BINDING_MISMATCH"),
        ("effective_time", "2026-01-01T00:14:59Z", "OWNER_EFFECTIVE_TIME_MISMATCH"),
        ("first_valid_time", "2026-01-01T00:14:59Z", "OWNER_FIRST_VALID_TIME_MISMATCH"),
        ("probability", 0.5, "FORBIDDEN_FLATTENED_FIELD_REACHABLE"),
    ],
)
def test_snapshot_adapter_fails_closed_on_drift_or_forbidden_fields(field, value, reason):
    snapshot = owner_snapshot()
    snapshot[field] = value
    if field != "probability":
        body = {key: item for key, item in snapshot.items() if key != "snapshot_id"}
        snapshot["snapshot_id"] = owner.canonical_sha256(body)
    with pytest.raises(spto.SPTOBindingError, match=reason):
        spto.adapt_owner_snapshot(snapshot)


def test_owner_stream_binding_has_complete_denominator_and_typed_break_accounting():
    resolved = spto.resolve_owner_read_surface(ROOT)
    first = owner_snapshot(eligible=False)
    second = owner_snapshot(fvt="2026-01-01T00:30:00Z", continuity="GAP_RESET")
    binding = spto.build_c2_owner_stream_binding(
        owner_resolution=resolved,
        snapshots=[first, second],
    )
    value = binding.to_dict()
    assert value["population_accounting"]["raw_snapshot_count"] == 2
    assert value["population_accounting"]["target_eligible_count"] == 1
    assert value["population_accounting"]["warmup_or_non_target_count"] == 1
    assert value["population_accounting"]["continuity_counts"]["GAP_RESET"] == 1
    assert value["candidate_generation"] == "DENIED"
    assert value["validation"] == "LOCKED_UNCONSUMED"


def test_owner_stream_rejects_reordering_and_real_source_mode():
    resolved = spto.resolve_owner_read_surface(ROOT)
    first = owner_snapshot()
    second = owner_snapshot(fvt="2026-01-01T00:30:00Z", continuity="CONTIGUOUS")
    with pytest.raises(spto.SPTOBindingError, match="OWNER_SNAPSHOT_STREAM_NOT_CANONICALLY_ORDERED"):
        spto.build_c2_owner_stream_binding(owner_resolution=resolved, snapshots=[second, first])
    with pytest.raises(spto.SPTOBindingError, match="REAL_SOURCE_AUTHORITY_REQUIRED"):
        spto.build_c2_owner_stream_binding(
            owner_resolution=resolved,
            snapshots=[first],
            population_mode="PROTECTED_2021_2023",
        )


def test_factorised_manifest_preserves_owner_spine_and_secondary_limit():
    resolved = spto.resolve_owner_read_surface(ROOT)
    owner_binding = spto.build_c2_owner_stream_binding(
        owner_resolution=resolved,
        snapshots=[owner_snapshot()],
    )
    partial = spto.build_factorised_source_binding_manifest(owner_stream_binding=owner_binding).to_dict()
    assert partial["primary_source"]["may_be_repaired_by_secondary"] is False
    assert partial["secondary_source"]["status"] == "REQUIRED_NOT_YET_BOUND_WP6"
    assert partial["factorised_rich_execution_eligible"] is False
    dense = {
        "dense_evidence_binding_id": "DENSE.SYNTHETIC.v1",
        "owner_authority_ref": spto.READ_AUTHORITY_ID,
        "owner_generation_id": owner.OWNER_GENERATION_ID,
        "source_release_id": "SYNTHETIC.DENSE.v1",
        "source_object_ids": ["SYNTHETIC.DENSE.OBJECT.1"],
        "admitted_outputs": ["MicroCarrierContextView", "MicroOperationView", "MicroFactorisedPath"],
    }
    complete = spto.build_factorised_source_binding_manifest(
        owner_stream_binding=owner_binding,
        dense_interstitial_binding=dense,
    ).to_dict()
    assert complete["factorised_rich_execution_eligible"] is True
    assert complete["secondary_source"]["may_create_replace_or_repair_owner_state_or_target"] is False


def test_forbidden_dependency_negative_reachability_is_static_and_exact():
    path = ROOT / "src/ovc/research_operations/spto/source_binding.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert imports == {
        "__future__",
        "copy",
        "json",
        "subprocess",
        "dataclasses",
        "pathlib",
        "typing",
        "ovc.opt_b.c2_vnext.owner_read_surface",
    }
    lowered = path.read_text(encoding="utf-8").lower()
    for dependency in spto.FORBIDDEN_GENERATING_DEPENDENCIES:
        assert f"import {dependency}" not in lowered
        assert f"from {dependency}" not in lowered


def test_output_schemas_validate_qualification_objects():
    jsonschema = pytest.importorskip("jsonschema")
    resolved = spto.resolve_owner_read_surface(ROOT)
    owner_binding = spto.build_c2_owner_stream_binding(
        owner_resolution=resolved,
        snapshots=[owner_snapshot()],
    )
    factorised = spto.build_factorised_source_binding_manifest(owner_stream_binding=owner_binding)
    owner_schema = json.loads((ROOT / "schemas/research_operations/spto/C2_OWNER_STREAM_BINDING_v0_1.schema.json").read_text())
    factorised_schema = json.loads((ROOT / "schemas/research_operations/spto/FACTORISED_SOURCE_BINDING_MANIFEST_v0_1.schema.json").read_text())
    jsonschema.Draft202012Validator(owner_schema).validate(owner_binding.to_dict())
    jsonschema.Draft202012Validator(factorised_schema).validate(factorised.to_dict())


def test_wp4_reentry_court_record_closes_blocker_forward_without_real_source():
    pointer = json.loads(
        (ROOT / "registries/implementation/c2s_sptoi_v0_1/CURRENT_STATE_POINTER.json").read_text()
    )
    state = json.loads((ROOT / pointer["current_state"]).read_text())
    gate = json.loads(
        (ROOT / "docs/programmes/c2s-sptoi-v0-1/wp4/C2S_SPTOI_G4_DELEGATED_DECISION_v0_1.json").read_text()
    )
    owner_binding = json.loads(
        (ROOT / "docs/programmes/c2s-sptoi-v0-1/wp4/C2S_SPTOI_WP4_C2_OWNER_STREAM_BINDING_v0_1.json").read_text()
    )
    factorised = json.loads(
        (ROOT / "docs/programmes/c2s-sptoi-v0-1/wp4/C2S_SPTOI_WP4_FACTORISED_SOURCE_BINDING_MANIFEST_v0_1.json").read_text()
    )
    authority_manifest = json.loads(
        (ROOT / "docs/programmes/c2s-sptoi-v0-1/wp4/C2S_SPTOI_WP4_REENTRY_AUTHORITY_MANIFEST_v0_1.json").read_text()
    )
    frontier = json.loads(
        (ROOT / "docs/programmes/c2s-sptoi-v0-1/wp4/C2S_SPTOI_WP4_REENTRY_DEPENDENCY_FRONTIER_v0_1.json").read_text()
    )
    canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    assert pointer["current_packet"] == "C2S-SPTOI-WP4-REENTRY"
    assert pointer["next_packet"] == "C2S-SPTOI-WP5"
    assert state["supersedes_state"].endswith("C2S_SPTOI_PROGRAMME_STATE_v0_4.json")
    assert state["protected_source_access"] == "NONE"
    assert gate["decision"] == "PASS"
    assert gate["effective_on_main_merge"] is True
    assert owner_binding["c2_owner_stream_binding_id"] == "6250c7ae301b1d3bfda320e64f1d294ea4a88ae691cca900b2c5191d9112c23a"
    assert owner_binding["population_mode"] == "SYNTHETIC_QUALIFICATION_FIXTURE"
    assert factorised["status"] == "PARTIAL_SECONDARY_SOURCE_PENDING"
    assert factorised["factorised_rich_execution_eligible"] is False
    assert hashlib.sha256(canonical(authority_manifest["authority_manifest"])).hexdigest() == authority_manifest["authority_manifest_id"]
    frontier_identity = frontier.pop("dependency_frontier_id")
    assert hashlib.sha256(canonical(frontier)).hexdigest() == frontier_identity
