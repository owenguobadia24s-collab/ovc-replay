from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Sequence

CI_DIR = Path(__file__).resolve().parent
if str(CI_DIR) not in sys.path:
    sys.path.insert(0, str(CI_DIR))

import pytest_shard_shadow as shadow  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = (
    ROOT
    / "registries/implementation/ci_performance/CIPR_POST_PYT_PYTEST_SHARD_CANONICAL_POLICY_v0_1.json"
)
SELECTION_ENV = "OVC_PYTEST_CANONICAL_SHARD_SELECTION_FILE"
AUTHORITY_MODE = "OPERATOR_APPROVED_CANONICAL_REQUIRED_TEST_TOPOLOGY"
GATE_ID = "CIPR-G5-POST-PYT-CONSOLIDATED-CUTOVER"
AUTHORITY_MANIFEST_ID = "b61020089792388be5e7ce78b3a28c2db6c436ac667bb48edf451cc5b071f4b8"
REQUIRED_CONTEXT = "tests"


def _load_policy(path: Path) -> dict:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("schema") != "ovc-pytest-shard-policy/v1":
        raise RuntimeError(f"unsupported pytest shard policy schema: {policy.get('schema')!r}")
    expected = {
        "authority_mode": AUTHORITY_MODE,
        "operator_gate_id": GATE_ID,
        "operator_decision": "PASS",
        "authority_manifest_id": AUTHORITY_MANIFEST_ID,
        "required_check_context": REQUIRED_CONTEXT,
        "required_check_substitution_active": False,
        "runner_cutover_active": True,
        "xdist_active": False,
    }
    for key, value in expected.items():
        if policy.get(key) != value:
            raise RuntimeError(f"canonical shard policy authority mismatch: {key}={policy.get(key)!r}")
    shard_count = policy.get("shard_count")
    if not isinstance(shard_count, int) or shard_count < 2:
        raise RuntimeError("shard_count must be an integer >= 2")
    heavy = policy.get("heavy_path_to_shard")
    if not isinstance(heavy, dict):
        raise RuntimeError("heavy_path_to_shard must be an object")
    for path_key, shard_index in heavy.items():
        if not isinstance(path_key, str) or not isinstance(shard_index, int) or not 0 <= shard_index < shard_count:
            raise RuntimeError(f"invalid heavy_path_to_shard entry: {path_key!r} -> {shard_index!r}")
    for key in (
        "policy_id",
        "policy_version",
        "assignment_algorithm",
        "canonical_reference_command",
        "canonical_collection_command",
    ):
        if not policy.get(key):
            raise RuntimeError(f"canonical shard policy missing required field: {key}")
    return policy


def build_manifest(nodeids: Sequence[str], policy: dict, *, head_sha: str, execution_sha: str) -> dict:
    records = shadow._records(nodeids)
    shards = shadow.assign_records(
        records,
        shard_count=policy["shard_count"],
        heavy_path_to_shard=dict(policy["heavy_path_to_shard"]),
    )
    population = [record.key for record in records]
    legacy = shadow._legacy_keys()
    canonical = set(population)
    missing_legacy = sorted(legacy - canonical)
    if missing_legacy:
        raise RuntimeError(f"canonical pytest population is missing legacy parity items: {missing_legacy[:20]}")
    pytest_native = sorted(canonical - legacy)
    if policy.get("require_pytest_native_items") is True and not pytest_native:
        raise RuntimeError("canonical shard policy requires pytest-native canonical items")
    policy_identity = {
        "schema": policy["schema"],
        "policy_id": policy["policy_id"],
        "policy_version": policy["policy_version"],
        "shard_count": policy["shard_count"],
        "assignment_algorithm": policy["assignment_algorithm"],
        "heavy_path_to_shard": dict(policy["heavy_path_to_shard"]),
        "authority_mode": AUTHORITY_MODE,
        "operator_gate_id": GATE_ID,
        "operator_decision": "PASS",
        "authority_manifest_id": AUTHORITY_MANIFEST_ID,
        "required_check_context": REQUIRED_CONTEXT,
        "canonical_reference_command": policy["canonical_reference_command"],
        "canonical_collection_command": policy["canonical_collection_command"],
        "require_pytest_native_items": policy.get("require_pytest_native_items", False),
        "required_check_substitution_active": False,
        "runner_cutover_active": True,
        "xdist_active": False,
    }
    payload = {
        "schema": "ovc-pytest-shard-manifest/v1",
        "programme_id": "OVC-CI-PERFORMANCE-REMEDIATION-v0.1",
        "packet_id": "CIPR-WP5C-POST-PYT-CANONICAL-SHARD-CUTOVER",
        "authority_mode": AUTHORITY_MODE,
        "required_check_context": REQUIRED_CONTEXT,
        "head_sha": head_sha,
        "execution_sha": execution_sha,
        "policy": policy_identity,
        "policy_hash": shadow._sha256_bytes(shadow._canonical_bytes(policy_identity)),
        "population_count": len(population),
        "population_hash": shadow._sha256_bytes(shadow._canonical_bytes(population)),
        "legacy_unittest_item_count": len(legacy),
        "pytest_native_item_count": len(pytest_native),
        "pytest_native_population_hash": shadow._sha256_bytes(shadow._canonical_bytes(pytest_native)),
        "shards": [
            {
                "shard_index": index,
                "item_count": len(shard),
                "items": [record.key for record in shard],
            }
            for index, shard in enumerate(shards)
        ],
    }
    payload["manifest_hash"] = shadow._sha256_bytes(shadow._canonical_bytes(payload))
    return payload


def _write_json(path: Path | None, payload: dict) -> None:
    data = shadow._canonical_bytes(payload)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(data.decode("utf-8"), end="")


def _selection_payload(manifest: dict, shard_index: int) -> dict:
    shard = manifest["shards"][shard_index]
    selected = list(shard["items"])
    if shard["item_count"] != len(selected) or not selected:
        raise RuntimeError("canonical shard selection item_count mismatch")
    if len(selected) != len(set(selected)):
        raise RuntimeError("canonical shard selection contains duplicate node ids")
    return {
        "schema": "ovc-pytest-shard-selection/v1",
        "authority_mode": AUTHORITY_MODE,
        "required_check_context": REQUIRED_CONTEXT,
        "manifest_hash": manifest["manifest_hash"],
        "population_hash": manifest["population_hash"],
        "shard_index": shard_index,
        "selected_item_count": len(selected),
        "items": selected,
    }


def _read_selection_payload(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "ovc-pytest-shard-selection/v1":
        raise RuntimeError("unsupported canonical pytest shard selection schema")
    if payload.get("authority_mode") != AUTHORITY_MODE:
        raise RuntimeError("canonical pytest shard selection lacks operator-approved authority")
    if payload.get("required_check_context") != REQUIRED_CONTEXT:
        raise RuntimeError("canonical pytest shard selection required-context mismatch")
    selected = payload.get("items")
    if not isinstance(selected, list) or not selected or not all(isinstance(item, str) and item for item in selected):
        raise RuntimeError("canonical pytest shard selection items must be a non-empty string list")
    if payload.get("selected_item_count") != len(selected):
        raise RuntimeError("canonical pytest shard selection selected_item_count mismatch")
    counts = Counter(selected)
    duplicates = sorted(key for key, count in counts.items() if count != 1)
    if duplicates:
        raise RuntimeError(f"canonical pytest shard selection contains duplicate node ids: {duplicates[:20]}")
    return selected


def pytest_collection_modifyitems(config, items) -> None:  # pragma: no cover - canonical CI plugin
    selection_file = os.environ.get(SELECTION_ENV)
    if not selection_file:
        return
    selected = _read_selection_payload(Path(selection_file))
    retained, deselected = shadow._select_collected_items(items, selected)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
    items[:] = retained


def _pytest_shard_command() -> list[str]:
    return [
        sys.executable,
        "-m",
        "pytest",
        "tests",
        "-p",
        "pytest_shard_canonical",
        "-q",
        "--tb=short",
        "--durations=20",
    ]


def _current_manifest(policy: dict, head_sha: str) -> tuple[str, dict]:
    execution_sha = shadow._git_head()
    if head_sha != execution_sha:
        raise RuntimeError(f"requested head {head_sha} does not equal execution head {execution_sha}")
    nodeids = shadow.collect_canonical_nodeids()
    manifest = build_manifest(nodeids, policy, head_sha=head_sha, execution_sha=execution_sha)
    shadow.prove_manifest(manifest, nodeids)
    return execution_sha, manifest


def prove(policy_path: Path, head_sha: str, output: Path | None) -> int:
    policy = _load_policy(policy_path)
    execution_sha = shadow._git_head()
    if head_sha != execution_sha:
        raise RuntimeError(f"requested head {head_sha} does not equal execution head {execution_sha}")
    first_collection = shadow.collect_canonical_nodeids()
    second_collection = shadow.collect_canonical_nodeids()
    if first_collection != second_collection:
        raise RuntimeError("canonical pytest collection order is nondeterministic")
    first = build_manifest(first_collection, policy, head_sha=head_sha, execution_sha=execution_sha)
    second = build_manifest(second_collection, policy, head_sha=head_sha, execution_sha=execution_sha)
    if shadow._canonical_bytes(first) != shadow._canonical_bytes(second):
        raise RuntimeError("operator-approved canonical pytest shard manifest is nondeterministic")
    shadow.prove_manifest(first, first_collection)
    _write_json(output, first)
    print(
        "OVC_CANONICAL_PYTEST_SHARD_PROOF "
        + json.dumps(
            {
                "status": "PASS",
                "proof": "BYTE_IDENTICAL_EXACT_ONE_CURRENT_PYTEST_UNION",
                "population_count": first["population_count"],
                "legacy_unittest_item_count": first["legacy_unittest_item_count"],
                "pytest_native_item_count": first["pytest_native_item_count"],
                "shard_counts": [row["item_count"] for row in first["shards"]],
                "manifest_hash": first["manifest_hash"],
                "population_hash": first["population_hash"],
                "head_sha": head_sha,
                "authority_mode": AUTHORITY_MODE,
                "required_check_context": REQUIRED_CONTEXT,
            },
            sort_keys=True,
        )
    )
    return 0


def run_shard(
    policy_path: Path,
    head_sha: str,
    shard_index: int,
    manifest_output: Path | None,
    result_output: Path | None,
) -> int:
    policy = _load_policy(policy_path)
    execution_sha, manifest = _current_manifest(policy, head_sha)
    if not 0 <= shard_index < len(manifest["shards"]):
        raise RuntimeError(f"shard_index must be in [0, {len(manifest['shards']) - 1}]")
    selection = _selection_payload(manifest, shard_index)
    with tempfile.TemporaryDirectory(prefix="ovc-canonical-pytest-shard-") as temp_dir:
        selection_path = Path(temp_dir) / "selection.json"
        selection_path.write_bytes(shadow._canonical_bytes(selection))
        env = shadow._pytest_env()
        env[SELECTION_ENV] = str(selection_path)
        started = time.perf_counter()
        completed = subprocess.run(
            _pytest_shard_command(),
            cwd=ROOT,
            env=env,
            check=False,
        )
        elapsed = time.perf_counter() - started
    if manifest_output is not None:
        manifest_output.parent.mkdir(parents=True, exist_ok=True)
        manifest_output.write_bytes(shadow._canonical_bytes(manifest))
    result = {
        "schema": "ovc-pytest-shard-result/v1",
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "head_sha": head_sha,
        "execution_sha": execution_sha,
        "manifest_hash": manifest["manifest_hash"],
        "population_hash": manifest["population_hash"],
        "population_count": manifest["population_count"],
        "shard_index": shard_index,
        "shard_count": len(manifest["shards"]),
        "selected_item_count": selection["selected_item_count"],
        "exit_code": completed.returncode,
        "elapsed_seconds": round(elapsed, 6),
        "authority_mode": AUTHORITY_MODE,
        "required_check_context": REQUIRED_CONTEXT,
        "selection_transport": "PYTEST_COLLECTION_FILTER_FILE",
        "xdist_active": False,
    }
    if result_output is not None:
        result_output.parent.mkdir(parents=True, exist_ok=True)
        result_output.write_bytes(shadow._canonical_bytes(result))
    print(f"OVC_CANONICAL_PYTEST_SHARD_RESULT {json.dumps(result, sort_keys=True)}")
    return completed.returncode


def aggregate(root: Path, output: Path | None) -> int:
    manifest_paths = sorted(root.rglob("manifest.json"))
    result_paths = sorted(root.rglob("result.json"))
    if len(manifest_paths) != 5:
        raise RuntimeError(f"canonical shard aggregate requires 5 manifest copies, found {len(manifest_paths)}")
    if len(result_paths) != 4:
        raise RuntimeError(f"canonical shard aggregate requires 4 shard results, found {len(result_paths)}")
    manifest_bytes = [path.read_bytes() for path in manifest_paths]
    if any(data != manifest_bytes[0] for data in manifest_bytes[1:]):
        raise RuntimeError("canonical shard manifest copies are not byte-identical")
    manifest = json.loads(manifest_bytes[0].decode("utf-8"))
    if manifest.get("authority_mode") != AUTHORITY_MODE or manifest.get("required_check_context") != REQUIRED_CONTEXT:
        raise RuntimeError("canonical shard aggregate manifest authority mismatch")
    results = [json.loads(path.read_text(encoding="utf-8")) for path in result_paths]
    expected_indices = set(range(len(manifest["shards"])))
    actual_indices = {row.get("shard_index") for row in results}
    if actual_indices != expected_indices:
        raise RuntimeError(f"canonical shard aggregate indices mismatch: {sorted(actual_indices)}")
    for row in results:
        if row.get("status") != "PASS" or row.get("exit_code") != 0:
            raise RuntimeError(f"canonical pytest shard failed: {row}")
        if row.get("authority_mode") != AUTHORITY_MODE or row.get("required_check_context") != REQUIRED_CONTEXT:
            raise RuntimeError("canonical shard result authority mismatch")
        for key in ("head_sha", "execution_sha", "manifest_hash", "population_hash", "population_count"):
            if row.get(key) != manifest.get(key):
                raise RuntimeError(f"canonical shard result {key} mismatch")
    selected_sum = sum(int(row["selected_item_count"]) for row in results)
    if selected_sum != manifest["population_count"]:
        raise RuntimeError("canonical shard aggregate selected cardinality mismatch")
    payload = {
        "schema": "ovc-canonical-pytest-shard-aggregate/v1",
        "status": "PASS",
        "head_sha": manifest["head_sha"],
        "execution_sha": manifest["execution_sha"],
        "manifest_hash": manifest["manifest_hash"],
        "population_hash": manifest["population_hash"],
        "population_count": manifest["population_count"],
        "legacy_unittest_item_count": manifest["legacy_unittest_item_count"],
        "pytest_native_item_count": manifest["pytest_native_item_count"],
        "shard_counts": [row["item_count"] for row in manifest["shards"]],
        "selected_item_count_sum": selected_sum,
        "critical_pytest_seconds": max(float(row["elapsed_seconds"]) for row in results),
        "authority_mode": AUTHORITY_MODE,
        "required_check_context": REQUIRED_CONTEXT,
        "required_check_substitution_active": False,
        "runner_cutover_active": True,
        "xdist_active": False,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(shadow._canonical_bytes(payload))
    print(f"OVC_CANONICAL_PYTEST_SHARD_AGGREGATE {json.dumps(payload, sort_keys=True)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Operator-approved deterministic canonical pytest shard runner for CIPR-G5.")
    subparsers = parser.add_subparsers(dest="mode", required=True)
    prove_parser = subparsers.add_parser("prove")
    prove_parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    prove_parser.add_argument("--head-sha", default=None)
    prove_parser.add_argument("--output", type=Path, default=None)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    run_parser.add_argument("--head-sha", default=None)
    run_parser.add_argument("--shard-index", type=int, required=True)
    run_parser.add_argument("--manifest-output", type=Path, default=None)
    run_parser.add_argument("--result-output", type=Path, default=None)
    aggregate_parser = subparsers.add_parser("aggregate")
    aggregate_parser.add_argument("--root", type=Path, required=True)
    aggregate_parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    head_sha = getattr(args, "head_sha", None) or shadow._git_head()
    try:
        if args.mode == "prove":
            return prove(args.policy, head_sha, args.output)
        if args.mode == "run":
            return run_shard(args.policy, head_sha, args.shard_index, args.manifest_output, args.result_output)
        return aggregate(args.root, args.output)
    except Exception as exc:
        print(
            "OVC_CANONICAL_PYTEST_SHARD_FAILURE "
            + json.dumps(
                {
                    "status": "FAIL",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "authority_mode": AUTHORITY_MODE,
                    "required_check_context": REQUIRED_CONTEXT,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
