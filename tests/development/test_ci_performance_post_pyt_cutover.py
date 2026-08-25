from __future__ import annotations

import json
from pathlib import Path
import tempfile

import pytest

from tools.ci import pytest_shard_canonical as canonical
from tools.ci import pytest_shard_shadow as shadow

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "registries/implementation/ci_performance/CIPR_POST_PYT_PYTEST_SHARD_CANONICAL_POLICY_v0_1.json"
WORKFLOW = ROOT / ".github/workflows/tests.yml"


def _synthetic_policy() -> dict:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    policy["heavy_path_to_shard"] = {}
    return policy


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
    with pytest.raises(RuntimeError, match="authority mismatch"):
        canonical._load_policy(shadow.DEFAULT_POLICY)


def test_manifest_exact_union_and_order_are_preserved() -> None:
    nodeids = [f"tests/test_x.py::test_{index}" for index in range(12)]
    manifest = canonical.build_manifest(
        nodeids,
        _synthetic_policy(),
        head_sha="a" * 40,
        execution_sha="a" * 40,
    )
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
        with pytest.raises(RuntimeError, match="operator-approved authority"):
            canonical._read_selection_payload(path)


def test_aggregate_requires_byte_identical_manifest_and_all_four_results() -> None:
    nodeids = [f"tests/test_x.py::test_{index}" for index in range(8)]
    manifest = canonical.build_manifest(
        nodeids,
        _synthetic_policy(),
        head_sha="b" * 40,
        execution_sha="b" * 40,
    )
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
    aggregate = workflow.split("\n  pytest-unified:\n", 1)[1].split("\n  pytest-unittest-parity:\n", 1)[0]
    assert "name: tests" in aggregate
    assert "pytest_shard_canonical.py aggregate" in aggregate
    assert "required_check_substitution_active" not in aggregate
    assert "actions/download-artifact@v4" in aggregate
    assert "xdist" not in workflow.lower()
