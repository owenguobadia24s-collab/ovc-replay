from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools.ci import pytest_shard_canonical as canonical
from tools.ci import pytest_shard_shadow as shadow

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "registries/implementation/ci_performance/CIPR_POST_PYT_PYTEST_SHARD_CANONICAL_POLICY_v0_1.json"
WORKFLOW = ROOT / ".github/workflows/tests.yml"
CURRENT_STATE_POINTER = ROOT / "registries/implementation/ci_performance/CURRENT_STATE_POINTER.json"
MATERIALISED_STATE = ROOT / (
    "registries/implementation/ci_performance/"
    "OVC_CIPR_STATE_v0_13_PHYSICAL_MATERIALISATION_COMPLETED.json"
)
MATERIALISATION_ROOT = ROOT / (
    "docs/releases/ci-performance-remediation-v0-1/"
    "cipr-wp5c-physical-materialisation"
)
MERGE_RECEIPT = ROOT / (
    "docs/releases/ci-performance-remediation-v0-1/cipr-wp5c/"
    "CIPR_WP5C_MERGE_RECEIPT.json"
)


def _synthetic_policy() -> dict:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    policy["heavy_path_to_shard"] = {}
    return policy


def _synthetic_manifest(nodeids: list[str], sha: str) -> dict:
    # These tests exercise deterministic manifest/aggregate mechanics only. Keep the
    # production fail-closed legacy-parity census intact by replacing its repository
    # census input solely inside this bounded synthetic fixture.
    with mock.patch.object(canonical.shadow, "_legacy_keys", return_value={nodeids[0]}):
        return canonical.build_manifest(
            nodeids,
            _synthetic_policy(),
            head_sha=sha,
            execution_sha=sha,
        )


def test_canonical_policy_is_exact_operator_approved_g5_surface() -> None:
    policy = canonical._load_policy(POLICY)
    assert policy["authority_mode"] == canonical.AUTHORITY_MODE
    assert policy["operator_gate_id"] == canonical.GATE_ID
    assert policy["operator_decision"] == "PASS"
    assert policy["authority_manifest_id"] == canonical.AUTHORITY_MANIFEST_ID
    assert policy["required_check_context"] == "tests"
    assert policy["required_check_substitution_active"] is False
    assert policy["runner_cutover_active"] is True
    assert policy["xdist_active"] is False
    assert policy["shard_count"] == 4


def test_shadow_policy_cannot_be_loaded_as_canonical_authority() -> None:
    with unittest.TestCase().assertRaisesRegex(RuntimeError, "authority mismatch"):
        canonical._load_policy(shadow.DEFAULT_POLICY)


def test_manifest_exact_union_and_order_are_preserved() -> None:
    nodeids = [f"tests/test_x.py::test_{index}" for index in range(12)]
    manifest = _synthetic_manifest(nodeids, "a" * 40)
    shadow.prove_manifest(manifest, nodeids)
    flattened = [item for shard in manifest["shards"] for item in shard["items"]]
    assert set(flattened) == set(nodeids)
    assert len(flattened) == len(nodeids)
    assert len(flattened) == len(set(flattened))
    for shard in manifest["shards"]:
        positions = [nodeids.index(item) for item in shard["items"]]
        assert positions == sorted(positions)


def test_selection_transport_is_file_based_and_one_pytest_session() -> None:
    command = canonical._pytest_shard_command()
    assert command[:3] == [canonical.sys.executable, "-m", "pytest"]
    assert "tests" in command
    assert command.count("pytest_shard_canonical") == 1
    assert "-p" in command
    assert "-n" not in command
    assert "xdist" not in " ".join(command).lower()
    assert not any("::" in token for token in command)


def test_selection_fails_closed_on_authority_mismatch() -> None:
    payload = {
        "schema": "ovc-pytest-shard-selection/v1",
        "authority_mode": "SHADOW_ONLY_NO_REQUIRED_CHECK_SUBSTITUTION",
        "required_check_context": "tests",
        "manifest_hash": "m",
        "population_hash": "p",
        "shard_index": 0,
        "selected_item_count": 1,
        "items": ["tests/test_x.py::test_a"],
    }
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "selection.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with unittest.TestCase().assertRaisesRegex(
            RuntimeError, "operator-approved authority"
        ):
            canonical._read_selection_payload(path)


def test_aggregate_requires_byte_identical_manifest_and_all_four_results() -> None:
    nodeids = [f"tests/test_x.py::test_{index}" for index in range(8)]
    manifest = _synthetic_manifest(nodeids, "b" * 40)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for index in range(5):
            target = root / f"artifact-{index}" / "manifest.json"
            target.parent.mkdir(parents=True)
            target.write_bytes(shadow._canonical_bytes(manifest))
        for shard in manifest["shards"]:
            result = {
                "schema": "ovc-pytest-shard-result/v1",
                "status": "PASS",
                "head_sha": manifest["head_sha"],
                "execution_sha": manifest["execution_sha"],
                "manifest_hash": manifest["manifest_hash"],
                "population_hash": manifest["population_hash"],
                "population_count": manifest["population_count"],
                "shard_index": shard["shard_index"],
                "shard_count": 4,
                "selected_item_count": shard["item_count"],
                "exit_code": 0,
                "elapsed_seconds": float(shard["shard_index"] + 1),
                "authority_mode": canonical.AUTHORITY_MODE,
                "required_check_context": canonical.REQUIRED_CONTEXT,
                "selection_transport": "PYTEST_COLLECTION_FILTER_FILE",
                "xdist_active": False,
            }
            target = root / f"result-{shard['shard_index']}" / "result.json"
            target.parent.mkdir(parents=True)
            target.write_bytes(shadow._canonical_bytes(result))
        output = root / "aggregate.json"
        assert canonical.aggregate(root, output) == 0
        aggregate = json.loads(output.read_text(encoding="utf-8"))
        assert aggregate["status"] == "PASS"
        assert aggregate["selected_item_count_sum"] == manifest["population_count"]
        assert aggregate["required_check_context"] == "tests"
        assert aggregate["required_check_substitution_active"] is False
        assert aggregate["runner_cutover_active"] is True
        assert aggregate["xdist_active"] is False


def test_required_workflow_context_is_aggregate_and_no_new_listener_is_added() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "pytest-shard-manifest:" in workflow
    assert "pytest-shard:" in workflow
    assert "pytest-unified:" in workflow
    shard_job = workflow.split("\n  pytest-shard:\n", 1)[1].split("\n  pytest-unified:\n", 1)[0]
    assert "shard: [0, 1, 2, 3]" in shard_job
    assert shard_job.count("pytest_shard_canonical.py run") == 1
    aggregate = workflow.split("\n  pytest-unified:\n", 1)[1].split("\n  pytest-unittest-parity:\n", 1)[0]
    assert "name: tests" in aggregate
    assert "pytest-shard-manifest" in aggregate
    assert "pytest-shard" in aggregate
    assert "pytest_shard_canonical.py aggregate" in aggregate
    assert "required_check_substitution_active" not in aggregate
    assert "actions/download-artifact@v4" in aggregate
    assert "xdist" not in workflow.lower()


def test_physical_materialisation_state_is_repository_effective_and_consistent() -> None:
    pointer = json.loads(CURRENT_STATE_POINTER.read_text(encoding="utf-8"))
    state = json.loads(MATERIALISED_STATE.read_text(encoding="utf-8"))
    receipt = json.loads(MERGE_RECEIPT.read_text(encoding="utf-8"))
    qa = json.loads(
        (MATERIALISATION_ROOT / "CIPR_WP5C_PHYSICAL_MATERIALISATION_QA_PACKET.json")
        .read_text(encoding="utf-8")
    )
    decision = json.loads(
        (MATERIALISATION_ROOT / "CIPR_WP5C_PHYSICAL_MATERIALISATION_DECISION.json")
        .read_text(encoding="utf-8")
    )

    assert pointer["current_state"] == str(MATERIALISED_STATE.relative_to(ROOT)).replace("\\", "/")
    assert pointer["status"] == state["status"] == "PHYSICALLY_MATERIALISED"
    assert pointer["packet_id"] == state["packet_id"] == "CIPR-WP5C-PHYSICAL-MATERIALISATION"
    assert pointer["next_packet"] == state["next_packet"] == "CIPR-WP5C-TERMINAL-COMPLETION-RECEIPT"
    assert pointer["operator_stop_gate"] == state["operator_stop_gate"] == "CIPR-G5-POST-PYT-CONSOLIDATED-CUTOVER"
    assert pointer["operator_stop_gate_decision"] == state["operator_stop_gate_decision"] == "PASS"
    assert pointer["outstanding_operator_gate"] is state["outstanding_operator_gate"] is None
    assert pointer["physical_cutover_complete"] is state["physical_cutover_complete"] is True
    assert pointer["runner_cutover_repository_effective"] is state["runner_cutover_repository_effective"] is True
    assert state["merge_commit"] == receipt["squash_merge_commit"]
    assert state["merge_tree"] == receipt["squash_merge_tree"]
    assert state["merge_commit"]
    invariants = receipt["terminal_invariants"]
    assert state["required_check_context_identity"] == invariants["required_check_context_identity"] == "tests"
    assert state["canonical_shard_count"] == invariants["canonical_shard_count"] == 4
    assert state["pytest_sessions_per_shard"] == invariants["pytest_sessions_per_shard"] == 1
    assert state["aggregate_fail_closed"] is invariants["aggregate_fail_closed"] is True
    assert state["xdist_active"] is invariants["xdist_active"] is False
    assert state["ruleset_context_mutation_active"] is invariants["ruleset_context_mutation_active"] is False
    assert state["required_check_substitution_active"] is invariants["required_check_substitution_active"] is False
    assert state["blockers"] == receipt["blockers"] == qa["blockers"] == decision["blockers"] == []
    assert qa["qa_status"] == qa["qa_recommendation"] == decision["qa"] == decision["decision"] == "PASS"
    assert decision["authority_delta"] == "NONE_ADMINISTRATIVE_MATERIALISATION_AND_CLOSEOUT_ONLY"
    assert decision["authority_expansion"] == "NONE"
    assert decision["reserved_authority_actions"] == []
