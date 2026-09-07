import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ovc.research_operations.spto.factorised_diagnostics import SPECIFICATIONS
from ovc.research_operations.spto.factorised_mechanics import DECLARED_REPRESENTATIONS, content_id
from ovc.research_operations.spto.factorised_nulls import NULL_SPECS, REPLICAS_PER_NULL, build_null_qualification_pack
from ovc.research_operations.spto.integrated_assurance import (
    IntegratedAssuranceError,
    build_artifact_reuse_snapshot,
    build_integrated_assurance_receipt,
    build_reference_snapshot,
    build_sharded_null_pack,
    verify_content_addressed_artifact,
)


ROOT = Path(__file__).resolve().parents[3]
RECEIPT = "docs/programmes/c2s-sptoi-v0-1/wp10/C2S_SPTOI_WP10_INTEGRATED_ASSURANCE_RECEIPT_v0_1.json"
RUNNER = ROOT / "tools/research_operations/spto/build_wp10_integrated_assurance.py"


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def run_fresh(mode):
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join((str(ROOT / "src"), str(ROOT)))
    return subprocess.check_output(
        [sys.executable, str(RUNNER), "--root", str(ROOT), "--mode", mode],
        cwd=ROOT,
        env=env,
        text=True,
    ).strip()


def test_reference_and_artifact_reuse_are_byte_identical():
    assert build_reference_snapshot() == build_artifact_reuse_snapshot(ROOT)


def test_three_way_null_sharding_rebuilds_exact_full_pack():
    sharded = build_sharded_null_pack(
        (("FG-NC", "FG-NO"), ("FG-NORD", "FG-NCORE"), ("FG-NFO", "FG-NBROAD"))
    )
    assert sharded == build_null_qualification_pack()


@pytest.mark.parametrize("mode", ("reference", "artifact-reuse", "sharded"))
def test_fresh_process_restart_is_byte_identical(mode):
    assert run_fresh(mode) == run_fresh(mode)


def test_reference_and_artifact_reuse_fresh_process_ids_match():
    reference = json.loads(run_fresh("reference"))
    artifact = json.loads(run_fresh("artifact-reuse"))
    assert reference["snapshot_id"] == artifact["snapshot_id"]


def test_corrupt_json_fails_closed(tmp_path):
    path = tmp_path / "docs/programmes/c2s-sptoi-v0-1/wp6"
    path.mkdir(parents=True)
    (path / "C2S_SPTOI_WP6_SYNTHETIC_QUALIFICATION_FIXTURE_v0_1.json").write_text("{broken")
    with pytest.raises(IntegratedAssuranceError, match="CORRUPT_ARTIFACT"):
        build_artifact_reuse_snapshot(tmp_path)


def test_incomplete_and_identity_corrupt_artifacts_fail_closed():
    with pytest.raises(IntegratedAssuranceError, match="INCOMPLETE_ARTIFACT"):
        verify_content_addressed_artifact({}, identity_key="pack_id", contract="X", required=("rows", "pack_id"))
    value = {"rows": [], "pack_id": "0" * 64}
    with pytest.raises(IntegratedAssuranceError, match="CORRUPT_ARTIFACT"):
        verify_content_addressed_artifact(value, identity_key="pack_id", contract="X", required=("rows", "pack_id"))


def test_incomplete_or_duplicate_shards_fail_closed():
    with pytest.raises(IntegratedAssuranceError, match="INCOMPLETE_NULL_SHARDS"):
        build_sharded_null_pack((("FG-NC",),))
    with pytest.raises(IntegratedAssuranceError, match="DUPLICATE_NULL_SHARD"):
        build_sharded_null_pack((("FG-NC",), ("FG-NC",)))


def test_filed_receipt_rebuilds_from_its_measured_capacity_and_validates_schema():
    filed = load(RECEIPT)
    assert filed == build_integrated_assurance_receipt(ROOT, filed["measured_capacity"])
    body = copy.deepcopy(filed)
    identity = body.pop("receipt_id")
    assert identity == content_id("IntegratedAssuranceReceipt/v1", body)
    jsonschema = pytest.importorskip("jsonschema")
    schema = load("schemas/research_operations/spto/INTEGRATED_ASSURANCE_RECEIPT_v0_1.schema.json")
    jsonschema.Draft202012Validator(schema).validate(filed)


def test_support_maps_trace_set_and_joint_null_worlds_are_retained():
    receipt = load(RECEIPT)
    retention = receipt["retention"]
    assert retention["expected"] == retention["observed"]
    assert retention["support_maps_retained"] is True
    assert retention["trace_set_retained"] is True
    assert retention["joint_null_worlds_retained"] is True


def test_no_representation_null_replica_or_control_is_removed_for_capacity():
    retained = load(RECEIPT)["retention"]["observed"]
    assert retained == {
        "representations": len(DECLARED_REPRESENTATIONS),
        "null_families": len(NULL_SPECS),
        "null_replicas": len(NULL_SPECS) * REPLICAS_PER_NULL,
        "diagnostic_controls": len(SPECIFICATIONS),
        "support_maps": len(DECLARED_REPRESENTATIONS),
        "traces": len(DECLARED_REPRESENTATIONS),
    }


def test_derivation_dependency_mutation_changes_manifest_identity():
    change = load(RECEIPT)["derivation_dependency_change"]
    assert change["changed"] is True
    assert change["original_manifest_id"] != change["mutated_manifest_id"]


def test_measured_capacity_is_positive_within_frozen_budgets():
    capacity = load(RECEIPT)["measured_capacity"]
    assert 0 < capacity["wall_time_ms"] <= capacity["wall_budget_ms"]
    assert 0 < capacity["peak_traced_memory_bytes"] <= capacity["peak_memory_budget_bytes"]
    assert load(RECEIPT)["capacity_result"] == "PASS_MEASURED_WITHOUT_FEATURE_REMOVAL"


def test_authority_remains_source_free_and_scientifically_inactive():
    receipt = load(RECEIPT)
    assert receipt["protected_source_access"] == "NONE"
    assert receipt["factorised_evidence_execution"] == "DENIED"
    assert receipt["validation"] == "LOCKED_UNCONSUMED"
    assert receipt["scientific_claims"] == "NONE"


def test_pointer_advances_to_pre_greal_packet_only():
    pointer = load("registries/implementation/c2s_sptoi_v0_1/CURRENT_STATE_POINTER.json")
    state = load(pointer["current_state"])
    gate = load("docs/programmes/c2s-sptoi-v0-1/wp10/C2S_SPTOI_G10_INTEGRATED_ASSURANCE_DELEGATED_DECISION_v0_1.json")
    assert pointer["current_packet"] in {"C2S-SPTOI-WP10", "C2S-SPTOI-WP11"}
    assert pointer["next_packet"] in {"C2S-SPTOI-WP11", None}
    assert pointer["next_operator_gate"] == "C2S-SPTOI-GREAL-SCI-PREREG"
    assert state["protected_source_access"] == "NONE"
    assert gate["decision"] == "PASS_INTEGRATED_SOURCE_FREE_ASSURANCE"


def test_wp10_authority_and_dependency_frontier_identities_are_exact():
    authority = load("docs/programmes/c2s-sptoi-v0-1/wp10/C2S_SPTOI_WP10_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load("docs/programmes/c2s-sptoi-v0-1/wp10/C2S_SPTOI_WP10_DEPENDENCY_FRONTIER_v0_1.json")
    canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical(authority["authority_manifest"])).hexdigest() == authority["authority_manifest_id"]
    body = copy.deepcopy(frontier)
    identity = body.pop("dependency_frontier_id")
    assert hashlib.sha256(canonical(body)).hexdigest() == identity
