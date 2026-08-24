from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Sequence

CI_DIR = Path(__file__).resolve().parent
if str(CI_DIR) not in sys.path:
    sys.path.insert(0, str(CI_DIR))

import pytest_unittest_parity as parity  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = (
    ROOT
    / "registries/implementation/ci_performance/CIPR_POST_PYT_PYTEST_SHARD_POLICY_v0_1.json"
)


@dataclass(frozen=True)
class NodeRecord:
    key: str
    source_path: str
    ordinal: int


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def _pytest_env() -> dict[str, str]:
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    required = (str(ROOT / "src"), str(ROOT))
    env["PYTHONPATH"] = (
        os.pathsep.join((*required, existing))
        if existing
        else os.pathsep.join(required)
    )
    return env


def _load_policy(path: Path) -> dict:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("schema") != "ovc-pytest-shard-policy/v1":
        raise RuntimeError(
            f"unsupported pytest shard policy schema: {policy.get('schema')!r}"
        )
    if policy.get("authority_mode") != "SHADOW_ONLY_NO_REQUIRED_CHECK_SUBSTITUTION":
        raise RuntimeError("pytest shard policy must remain shadow-only")
    shard_count = policy.get("shard_count")
    if not isinstance(shard_count, int) or shard_count < 2:
        raise RuntimeError("shard_count must be an integer >= 2")
    heavy = policy.get("heavy_path_to_shard")
    if not isinstance(heavy, dict):
        raise RuntimeError("heavy_path_to_shard must be an object")
    for path_key, shard in heavy.items():
        if (
            not isinstance(path_key, str)
            or not isinstance(shard, int)
            or not 0 <= shard < shard_count
        ):
            raise RuntimeError(
                f"invalid heavy_path_to_shard entry: {path_key!r} -> {shard!r}"
            )
    required = (
        "policy_id",
        "policy_version",
        "assignment_algorithm",
        "canonical_command",
        "canonical_collection_command",
    )
    missing = [name for name in required if not policy.get(name)]
    if missing:
        raise RuntimeError(f"pytest shard policy missing required fields: {missing}")
    if policy.get("required_check_substitution_active") is not False:
        raise RuntimeError("required-check substitution must remain disabled")
    return policy


def _parse_collection_output(text: str) -> list[str]:
    nodeids = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("tests/") and "::" in line
    ]
    if not nodeids:
        raise RuntimeError("canonical pytest collection produced no node ids")
    counts = Counter(nodeids)
    duplicates = sorted(key for key, count in counts.items() if count != 1)
    if duplicates:
        raise RuntimeError(
            f"canonical pytest collection contains duplicate node ids: {duplicates[:20]}"
        )
    return nodeids


def collect_canonical_nodeids() -> list[str]:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests",
            "--collect-only",
            "-q",
        ],
        cwd=ROOT,
        env=_pytest_env(),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0:
        print(completed.stdout, end="", file=sys.stderr)
        raise RuntimeError(
            f"canonical pytest collection failed with exit code {completed.returncode}"
        )
    return _parse_collection_output(completed.stdout)


def _records(nodeids: Sequence[str]) -> list[NodeRecord]:
    records = [
        NodeRecord(
            key=nodeid,
            source_path=nodeid.split("::", 1)[0],
            ordinal=index,
        )
        for index, nodeid in enumerate(nodeids)
    ]
    counts = Counter(record.key for record in records)
    duplicates = sorted(key for key, count in counts.items() if count != 1)
    if duplicates:
        raise RuntimeError(f"duplicate canonical pytest identities: {duplicates[:20]}")
    return records


def assign_records(
    records: Sequence[NodeRecord],
    *,
    shard_count: int,
    heavy_path_to_shard: dict[str, int],
) -> list[list[NodeRecord]]:
    if shard_count < 2:
        raise RuntimeError("shard_count must be >= 2")
    counts = Counter(record.key for record in records)
    duplicates = sorted(key for key, count in counts.items() if count != 1)
    if duplicates:
        raise RuntimeError(
            f"duplicate canonical pytest identities are not admissible: {duplicates[:20]}"
        )
    discovered_paths = {record.source_path for record in records}
    missing_heavy = sorted(set(heavy_path_to_shard) - discovered_paths)
    if missing_heavy:
        raise RuntimeError(
            f"configured heavy paths missing from canonical pytest population: {missing_heavy}"
        )

    shards: list[list[NodeRecord]] = [[] for _ in range(shard_count)]
    regular_index = 0
    for record in records:
        designated = heavy_path_to_shard.get(record.source_path)
        if designated is not None:
            shards[designated].append(record)
            continue
        shards[regular_index % shard_count].append(record)
        regular_index += 1

    if any(not shard for shard in shards):
        raise RuntimeError("pytest shard policy produced an empty shard")
    for shard in shards:
        ordinals = [record.ordinal for record in shard]
        if ordinals != sorted(ordinals):
            raise RuntimeError(
                "pytest shard execution order does not preserve canonical collection order"
            )
    return shards


def _legacy_keys() -> set[str]:
    cases, _ = parity._discover()
    return parity._expected_keys(cases)


def build_manifest(
    nodeids: Sequence[str],
    policy: dict,
    *,
    head_sha: str,
    execution_sha: str,
) -> dict:
    records = _records(nodeids)
    shards = assign_records(
        records,
        shard_count=policy["shard_count"],
        heavy_path_to_shard=dict(policy["heavy_path_to_shard"]),
    )
    population_keys = [record.key for record in records]
    legacy = _legacy_keys()
    canonical = set(population_keys)
    missing_legacy = sorted(legacy - canonical)
    if missing_legacy:
        raise RuntimeError(
            f"canonical pytest population is missing legacy parity items: {missing_legacy[:20]}"
        )
    pytest_native = sorted(canonical - legacy)
    if policy.get("require_pytest_native_items") is True and not pytest_native:
        raise RuntimeError("post-PYT shard policy requires pytest-native canonical items")

    policy_identity = {
        "schema": policy["schema"],
        "policy_id": policy["policy_id"],
        "policy_version": policy["policy_version"],
        "shard_count": policy["shard_count"],
        "assignment_algorithm": policy["assignment_algorithm"],
        "heavy_path_to_shard": dict(policy["heavy_path_to_shard"]),
        "authority_mode": policy["authority_mode"],
        "canonical_command": policy["canonical_command"],
        "canonical_collection_command": policy["canonical_collection_command"],
        "require_pytest_native_items": policy.get("require_pytest_native_items", False),
        "required_check_substitution_active": False,
    }
    payload = {
        "schema": "ovc-pytest-shard-manifest/v1",
        "programme_id": "OVC-CI-PERFORMANCE-REMEDIATION-v0.1",
        "packet_id": "CIPR-WP5R-POST-PYT-CANONICAL-CENSUS-SHADOW",
        "authority_mode": "SHADOW_ONLY_NO_REQUIRED_CHECK_SUBSTITUTION",
        "head_sha": head_sha,
        "execution_sha": execution_sha,
        "policy": policy_identity,
        "policy_hash": _sha256_bytes(_canonical_bytes(policy_identity)),
        "population_count": len(population_keys),
        "population_hash": _sha256_bytes(_canonical_bytes(population_keys)),
        "legacy_unittest_item_count": len(legacy),
        "pytest_native_item_count": len(pytest_native),
        "pytest_native_population_hash": _sha256_bytes(_canonical_bytes(pytest_native)),
        "shards": [
            {
                "shard_index": index,
                "item_count": len(shard),
                "items": [record.key for record in shard],
            }
            for index, shard in enumerate(shards)
        ],
    }
    payload["manifest_hash"] = _sha256_bytes(_canonical_bytes(payload))
    return payload


def prove_manifest(manifest: dict, nodeids: Sequence[str]) -> None:
    expected = list(nodeids)
    actual = [
        key
        for shard in manifest["shards"]
        for key in shard["items"]
    ]
    if len(actual) != len(set(actual)):
        raise RuntimeError("pytest shard manifest contains duplicate item identities")
    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        unexpected = sorted(set(actual) - set(expected))
        raise RuntimeError(
            f"pytest shard manifest union mismatch: missing={missing[:20]} unexpected={unexpected[:20]}"
        )
    if len(actual) != len(expected):
        raise RuntimeError(
            "pytest shard manifest cardinality does not equal canonical collection"
        )
    if any(
        shard["item_count"] != len(shard["items"])
        for shard in manifest["shards"]
    ):
        raise RuntimeError("pytest shard manifest item_count mismatch")


def _write_manifest(path: Path | None, manifest: dict) -> None:
    data = _canonical_bytes(manifest)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(data.decode("utf-8"), end="")


def prove(policy_path: Path, head_sha: str, output: Path | None) -> int:
    policy = _load_policy(policy_path)
    execution_sha = _git_head()
    if head_sha != execution_sha:
        raise RuntimeError(
            f"requested head {head_sha} does not equal execution head {execution_sha}"
        )

    first_collection = collect_canonical_nodeids()
    second_collection = collect_canonical_nodeids()
    if first_collection != second_collection:
        raise RuntimeError("canonical pytest collection order is nondeterministic")

    first = build_manifest(
        first_collection,
        policy,
        head_sha=head_sha,
        execution_sha=execution_sha,
    )
    second = build_manifest(
        second_collection,
        policy,
        head_sha=head_sha,
        execution_sha=execution_sha,
    )
    if _canonical_bytes(first) != _canonical_bytes(second):
        raise RuntimeError("post-PYT pytest shard manifest is nondeterministic")

    prove_manifest(first, first_collection)
    _write_manifest(output, first)
    print(
        json.dumps(
            {
                "status": "PASS",
                "proof": "BYTE_IDENTICAL_EXACT_ONE_CURRENT_PYTEST_UNION",
                "population_count": first["population_count"],
                "legacy_unittest_item_count": first["legacy_unittest_item_count"],
                "pytest_native_item_count": first["pytest_native_item_count"],
                "shard_count": len(first["shards"]),
                "manifest_hash": first["manifest_hash"],
                "population_hash": first["population_hash"],
                "head_sha": head_sha,
                "execution_sha": execution_sha,
            },
            sort_keys=True,
        )
    )
    return 0


def run_shard(
    policy_path: Path,
    head_sha: str,
    shard_index: int,
    output: Path | None,
) -> int:
    policy = _load_policy(policy_path)
    execution_sha = _git_head()
    if head_sha != execution_sha:
        raise RuntimeError(
            f"requested head {head_sha} does not equal execution head {execution_sha}"
        )

    nodeids = collect_canonical_nodeids()
    manifest = build_manifest(
        nodeids,
        policy,
        head_sha=head_sha,
        execution_sha=execution_sha,
    )
    prove_manifest(manifest, nodeids)
    if not 0 <= shard_index < len(manifest["shards"]):
        raise RuntimeError(
            f"shard_index must be in [0, {len(manifest['shards']) - 1}]"
        )

    selected = list(manifest["shards"][shard_index]["items"])
    started = time.perf_counter()
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *selected,
            "-q",
            "--tb=short",
            "--durations=20",
        ],
        cwd=ROOT,
        env=_pytest_env(),
        check=False,
    )
    elapsed = time.perf_counter() - started

    _write_manifest(output, manifest)
    payload = {
        "schema": "ovc-pytest-shard-result/v1",
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "head_sha": head_sha,
        "execution_sha": execution_sha,
        "manifest_hash": manifest["manifest_hash"],
        "population_hash": manifest["population_hash"],
        "shard_index": shard_index,
        "shard_count": len(manifest["shards"]),
        "selected_item_count": len(selected),
        "exit_code": completed.returncode,
        "elapsed_seconds": round(elapsed, 6),
        "authority_mode": "SHADOW_ONLY_NO_REQUIRED_CHECK_SUBSTITUTION",
    }
    print(f"OVC_PYTEST_SHARD_RESULT {json.dumps(payload, sort_keys=True)}")
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministic shadow sharding for the exact current post-PYT canonical "
            "pytest item population. This tool cannot substitute required CI."
        )
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    prove_parser = subparsers.add_parser("prove")
    prove_parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    prove_parser.add_argument("--head-sha", default=None)
    prove_parser.add_argument("--output", type=Path, default=None)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    run_parser.add_argument("--head-sha", default=None)
    run_parser.add_argument("--output", type=Path, default=None)
    run_parser.add_argument("--shard-index", type=int, required=True)

    args = parser.parse_args()
    head_sha = args.head_sha or _git_head()
    try:
        if args.mode == "prove":
            return prove(args.policy, head_sha, args.output)
        return run_shard(
            args.policy,
            head_sha,
            args.shard_index,
            args.output,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "reason": type(exc).__name__,
                    "detail": str(exc),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
