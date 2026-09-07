import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ovc.research_operations.spto.factorised_assurance import (
    AssuranceFailure,
    build_algorithmic_assurance_receipt,
)
from ovc.research_operations.spto.factorised_mechanics import (
    MechanicsError,
    content_id,
    project_frontier_to_comparison_target,
    select_antecedent_backoff,
    select_target_resolution,
)


ROOT = Path(__file__).resolve().parents[3]
RECEIPT = "docs/programmes/c2s-sptoi-v0-1/wp7/C2S_SPTOI_WP7_RICH_ALGORITHMIC_ASSURANCE_RECEIPT_v0_1.json"


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_filed_receipt_rebuilds_exactly_and_validates_schema():
    filed = load(RECEIPT)
    rebuilt = build_algorithmic_assurance_receipt(ROOT)
    assert rebuilt == filed
    jsonschema = pytest.importorskip("jsonschema")
    schema = load("schemas/research_operations/spto/RICH_ALGORITHMIC_ASSURANCE_RECEIPT_v0_1.schema.json")
    jsonschema.Draft202012Validator(schema).validate(filed)
    body = copy.deepcopy(filed)
    identity = body.pop("receipt_id")
    assert identity == content_id("RichAlgorithmicAssuranceReceipt/v1", body)
    assert filed["check_count"] == 14
    assert all(check["result"] == "PASS" for check in filed["checks"])


def test_fresh_process_runner_is_byte_identical_across_restarts():
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src") + os.pathsep + str(ROOT))
    command = [sys.executable, str(ROOT / "tools/research_operations/run_c2s_sptoi_wp7_assurance.py")]
    first = subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True).stdout
    second = subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True).stdout
    assert first == second
    assert json.loads(first) == load(RECEIPT)


def test_antecedent_hierarchy_primary_and_sensitivities_are_exact():
    supports = {"EXACT": 2, "HI": 3, "MID": 5, "PATH": 8, "OP": 13}
    assert select_antecedent_backoff("BASE", supports, 2) == ("EXACT", 2)
    assert select_antecedent_backoff("BASE", supports, 3) == ("HI", 3)
    assert select_antecedent_backoff("BASE", supports, 5) == ("MID", 5)
    assert select_antecedent_backoff("NO_HI", supports, 3) == ("MID", 5)
    with pytest.raises(MechanicsError, match="UNDECLARED_SUPPORT_POLICY"):
        select_antecedent_backoff("BASE", supports, 4)


def test_target_reducer_selects_richest_supported_pack_or_unresolved():
    supports = {"T0_v1": 1, "T1_v1": 1, "R18_MID_v1": 2, "ETR_v1": 9}
    assert select_target_resolution("BASE", supports) == ("R18_MID_v1", 2)
    assert select_target_resolution("NO_MID", supports) == ("ETR_v1", 9)
    assert select_target_resolution("COMPACT", {}) == (None, 0)


def test_common_target_projection_aggregates_and_missing_map_fails_closed():
    assert project_frontier_to_comparison_target(
        "T1_v1", {"a": 2, "b": 3}, {"a": "x", "b": "x"}
    ) == (("x", 5),)
    assert project_frontier_to_comparison_target("R18_MID_v1", {"x": 2}) == (("x", 2),)
    with pytest.raises(MechanicsError, match="COMPARISON_TARGET_PACK_MISSING"):
        project_frontier_to_comparison_target("T1_v1", {"a": 2})


def test_source_and_cross_export_assurance_fails_on_promoted_c0c_join(tmp_path):
    # Copy only the bounded records the independent runner reads.
    for relative in [
        "docs/programmes/c2s-sptoi-v0-1/wp4/C2S_SPTOI_WP4_C2_OWNER_STREAM_BINDING_v0_1.json",
        "docs/programmes/c2s-sptoi-v0-1/wp4/C2S_SPTOI_WP4_FACTORISED_SOURCE_BINDING_MANIFEST_v0_1.json",
        "docs/programmes/c2s-sptoi-v0-1/wp5/C2S_SPTOI_WP5_C0C_SOURCE_CROSS_EXPORT_CONCORDANCE_RECEIPT_v0_1.json",
        "docs/programmes/c2s-sptoi-v0-1/wp6/C2S_SPTOI_WP6_FACTORISED_DENSE_MICRO_SOURCE_SCOPE_BINDING_v0_1.json",
        "docs/programmes/c2s-sptoi-v0-1/wp6/C2S_SPTOI_WP6_FACTORISED_MECHANICS_REGISTRY_v0_1.json",
        "docs/programmes/c2s-sptoi-v0-1/wp6/C2S_SPTOI_WP6_SYNTHETIC_QUALIFICATION_FIXTURE_v0_1.json",
    ]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    c0c_path = tmp_path / "docs/programmes/c2s-sptoi-v0-1/wp5/C2S_SPTOI_WP5_C0C_SOURCE_CROSS_EXPORT_CONCORDANCE_RECEIPT_v0_1.json"
    c0c = json.loads(c0c_path.read_text())
    c0c["join_eligibility"] = True
    c0c_path.write_text(json.dumps(c0c))
    with pytest.raises(AssuranceFailure, match="WP7-ALG-04"):
        build_algorithmic_assurance_receipt(tmp_path)


def test_pointer_advances_only_to_null_algorithm_packet():
    pointer = load("registries/implementation/c2s_sptoi_v0_1/CURRENT_STATE_POINTER.json")
    state = load(pointer["current_state"])
    gate = load("docs/programmes/c2s-sptoi-v0-1/wp7/C2S_SPTOI_G7_RICH_ALG_DELEGATED_DECISION_v0_1.json")
    assert pointer["current_packet"] == "C2S-SPTOI-WP7"
    assert pointer["next_packet"] == "C2S-SPTOI-WP8"
    assert state["protected_source_access"] == "NONE"
    assert state["factorised_evidence_execution"] == "DENIED"
    assert gate["decision"] == "PASS_SOURCE_FREE_ALGORITHMIC_ASSURANCE"


def test_wp7_authority_and_dependency_frontier_identities_are_exact():
    authority = load("docs/programmes/c2s-sptoi-v0-1/wp7/C2S_SPTOI_WP7_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load("docs/programmes/c2s-sptoi-v0-1/wp7/C2S_SPTOI_WP7_DEPENDENCY_FRONTIER_v0_1.json")
    canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical(authority["authority_manifest"])).hexdigest() == authority["authority_manifest_id"]
    body = copy.deepcopy(frontier)
    identity = body.pop("dependency_frontier_id")
    assert hashlib.sha256(canonical(body)).hexdigest() == identity
