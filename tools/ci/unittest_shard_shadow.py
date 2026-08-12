from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import subprocess
import sys
import time
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

CI_DIR = Path(__file__).resolve().parent
if str(CI_DIR) not in sys.path:
    sys.path.insert(0, str(CI_DIR))

import pytest_unittest_parity as parity  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / "registries/implementation/ci_performance/CIPR_UNITTEST_SHARD_POLICY_v0_1.json"


@dataclass(frozen=True)
class CaseRecord:
    key: str
    source_path: str
    ordinal: int


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def _load_policy(path: Path) -> dict:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("schema") != "ovc-unittest-shard-policy/v1":
        raise RuntimeError(f"unsupported shard policy schema: {policy.get('schema')!r}")

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
        "authority_mode",
    )
    missing = [name for name in required if not policy.get(name)]
    if missing:
        raise RuntimeError(f"shard policy missing required fields: {missing}")
    return policy


def _case_record(case: unittest.TestCase, ordinal: int) -> CaseRecord:
    source = parity._source_path(case).relative_to(ROOT).as_posix()
    return CaseRecord(
        key=f"{source}::{case.__class__.__name__}::{case._testMethodName}",
        source_path=source,
        ordinal=ordinal,
    )


def _records(cases: Sequence[unittest.TestCase]) -> list[CaseRecord]:
    records = [_case_record(case, index) for index, case in enumerate(cases)]
    counts = Counter(record.key for record in records)
    duplicates = sorted(key for key, count in counts.items() if count != 1)
    if duplicates:
        raise RuntimeError(f"duplicate legacy unittest identities: {duplicates}")
    return records


def assign_records(
    records: Sequence[CaseRecord],
    *,
    shard_count: int,
    heavy_path_to_shard: dict[str, int],
) -> list[list[CaseRecord]]:
    if shard_count < 2:
        raise RuntimeError("shard_count must be >= 2")

    counts = Counter(record.key for record in records)
    duplicates = sorted(key for key, count in counts.items() if count != 1)
    if duplicates:
        raise RuntimeError(f"duplicate case identities are not admissible: {duplicates}")

    discovered_paths = {record.source_path for record in records}
    missing_heavy = sorted(set(heavy_path_to_shard) - discovered_paths)
    if missing_heavy:
        raise RuntimeError(
            f"configured heavy paths missing from legacy population: {missing_heavy}"
        )

    shards: list[list[CaseRecord]] = [[] for _ in range(shard_count)]
    regular_index = 0
    for record in records:
        designated = heavy_path_to_shard.get(record.source_path)
        if designated is not None:
            shards[designated].append(record)
            continue
        shards[regular_index % shard_count].append(record)
        regular_index += 1

    if any(not shard for shard in shards):
        raise RuntimeError("shard policy produced an empty shard")

    for shard in shards:
        ordinals = [record.ordinal for record in shard]
        if ordinals != sorted(ordinals):
            raise RuntimeError("shard execution order does not preserve legacy discovery order")
    return shards


def build_manifest(
    cases: Sequence[unittest.TestCase],
    policy: dict,
    *,
    head_sha: str,
    execution_sha: str,
) -> dict:
    records = _records(cases)
    shard_count = policy["shard_count"]
    heavy = dict(policy["heavy_path_to_shard"])
    shards = assign_records(
        records,
        shard_count=shard_count,
        heavy_path_to_shard=heavy,
    )
    population_keys = [record.key for record in records]
    policy_identity = {
        "schema": policy["schema"],
        "policy_id": policy["policy_id"],
        "policy_version": policy["policy_version"],
        "shard_count": shard_count,
        "assignment_algorithm": policy["assignment_algorithm"],
        "heavy_path_to_shard": heavy,
        "authority_mode": policy["authority_mode"],
    }
    payload = {
        "schema": "ovc-unittest-shard-manifest/v1",
        "programme_id": "OVC-CI-PERFORMANCE-REMEDIATION-v0.1",
        "packet_id": "CIPR-WP4-SHADOW-SHARD-CANDIDATE",
        "authority_mode": "SHADOW_ONLY_NO_REQUIRED_CHECK_SUBSTITUTION",
        "head_sha": head_sha,
        "execution_sha": execution_sha,
        "policy": policy_identity,
        "policy_hash": _sha256_bytes(_canonical_bytes(policy_identity)),
        "population_count": len(population_keys),
        "population_hash": _sha256_bytes(_canonical_bytes(population_keys)),
        "shards": [
            {
                "shard_index": index,
                "case_count": len(shard),
                "cases": [record.key for record in shard],
            }
            for index, shard in enumerate(shards)
        ],
    }
    payload["manifest_hash"] = _sha256_bytes(_canonical_bytes(payload))
    return payload


def prove_manifest(manifest: dict, cases: Sequence[unittest.TestCase]) -> None:
    expected_records = _records(cases)
    expected = [record.key for record in expected_records]
    actual = [key for shard in manifest["shards"] for key in shard["cases"]]

    if len(actual) != len(set(actual)):
        raise RuntimeError("manifest contains duplicate case identities")
    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        unexpected = sorted(set(actual) - set(expected))
        raise RuntimeError(
            f"manifest union mismatch: missing={missing} unexpected={unexpected}"
        )
    if len(actual) != len(expected):
        raise RuntimeError("manifest cardinality does not equal legacy unittest population")
    if any(
        shard["case_count"] != len(shard["cases"])
        for shard in manifest["shards"]
    ):
        raise RuntimeError("manifest shard case_count mismatch")


def _write_manifest(path: Path | None, manifest: dict) -> None:
    data = _canonical_bytes(manifest)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(data.decode("utf-8"), end="")


def prove(policy_path: Path, head_sha: str, output: Path | None) -> int:
    policy = _load_policy(policy_path)
    cases, _ = parity._discover()
    execution_sha = _git_head()
    first = build_manifest(
        cases,
        policy,
        head_sha=head_sha,
        execution_sha=execution_sha,
    )
    second = build_manifest(
        cases,
        policy,
        head_sha=head_sha,
        execution_sha=execution_sha,
    )
    if _canonical_bytes(first) != _canonical_bytes(second):
        print(
            json.dumps(
                {"status": "FAIL", "reason": "NONDETERMINISTIC_MANIFEST"},
                sort_keys=True,
            )
        )
        return 1

    prove_manifest(first, cases)
    _write_manifest(output, first)
    print(
        json.dumps(
            {
                "status": "PASS",
                "proof": "BYTE_IDENTICAL_EXACT_ONE_COMPLETE_UNION",
                "population_count": first["population_count"],
                "shard_count": len(first["shards"]),
                "manifest_hash": first["manifest_hash"],
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
    cases, _ = parity._discover()
    execution_sha = _git_head()
    manifest = build_manifest(
        cases,
        policy,
        head_sha=head_sha,
        execution_sha=execution_sha,
    )
    prove_manifest(manifest, cases)

    if not 0 <= shard_index < len(manifest["shards"]):
        raise RuntimeError(
            f"shard_index must be in [0, {len(manifest['shards']) - 1}]"
        )

    records = _records(cases)
    case_by_key = {
        record.key: case
        for record, case in zip(records, cases, strict=True)
    }
    selected_keys = manifest["shards"][shard_index]["cases"]
    selected = [case_by_key[key] for key in selected_keys]

    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(selected))
    elapsed = time.perf_counter() - started

    _write_manifest(output, manifest)
    payload = {
        "schema": "ovc-unittest-shard-result/v1",
        "status": "PASS" if result.wasSuccessful() else "FAIL",
        "head_sha": head_sha,
        "execution_sha": execution_sha,
        "manifest_hash": manifest["manifest_hash"],
        "shard_index": shard_index,
        "shard_count": len(manifest["shards"]),
        "test_count": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "elapsed_seconds": round(elapsed, 6),
        "authority_mode": "SHADOW_ONLY_NO_REQUIRED_CHECK_SUBSTITUTION",
    }
    print(f"OVC_SHARD_RESULT {json.dumps(payload, sort_keys=True)}")
    return 0 if result.wasSuccessful() else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministic runner-neutral shadow sharding for the exact "
            "legacy unittest population."
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
