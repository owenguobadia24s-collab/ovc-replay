"""GRT v0.2 court-record preflight and exact B0 reconciliation helpers.

This module is deliberately read-only with respect to repository authority.  It
replays the accepted GRT v0.1 observer at exact Git commits and emits compact,
source-bound evidence for GRT2-WP0/G1.  It never infers Programme Genesis
adoption and never changes the immutable B0 population.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


B0_SOURCE_COMMIT = "100b3fa342c5dee7c96a7a4e5af9e80dac3ddfe4"
B0_SOURCE_TREE = "91374c54bde0e0b61ac51705f6434d4f2b0d8417"
B0_TOPOLOGY_SHA256 = "4120468ecb1c1f484ab073c851287706f4fb45ad0e99fc355b4624094bb795f2"
B0_WARNING_COUNT = 569
B0_ANOMALY_COUNT = 1364
B0_COMPONENT_COUNT = 4615
B0_PROGRAMME_COUNT = 53
B0_COMPONENT_EDGE_COUNT = 11861


class WP0ReconciliationError(RuntimeError):
    """Fail-closed GRT2-WP0 source/reconciliation error."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _git(repository_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", "-C", str(repository_root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and completed.returncode != 0:
        raise WP0ReconciliationError(
            f"git {' '.join(args)} failed ({completed.returncode}): {completed.stderr.strip()}"
        )
    return completed


def resolve_commit(repository_root: Path, ref: str) -> str:
    value = _git(repository_root, "rev-parse", f"{ref}^{{commit}}").stdout.strip()
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise WP0ReconciliationError(f"invalid commit identity for {ref!r}: {value!r}")
    return value


def resolve_tree(repository_root: Path, commit: str) -> str:
    value = _git(repository_root, "rev-parse", f"{commit}^{{tree}}").stdout.strip()
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise WP0ReconciliationError(f"invalid tree identity for {commit}: {value!r}")
    return value


def ensure_commit(repository_root: Path, commit: str) -> None:
    present = _git(repository_root, "cat-file", "-e", f"{commit}^{{commit}}", check=False)
    if present.returncode == 0:
        return
    fetched = _git(repository_root, "fetch", "--no-tags", "origin", commit, check=False)
    if fetched.returncode != 0:
        raise WP0ReconciliationError(
            f"required source commit {commit} is unavailable and exact fetch failed: {fetched.stderr.strip()}"
        )
    verify = _git(repository_root, "cat-file", "-e", f"{commit}^{{commit}}", check=False)
    if verify.returncode != 0:
        raise WP0ReconciliationError(f"required source commit {commit} remains unavailable after exact fetch")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise WP0ReconciliationError(f"expected JSON object at {path}")
    return value


def _json_file_bytes(paths: Iterable[Path]) -> int:
    total = 0
    for path in paths:
        try:
            total += path.stat().st_size
        except OSError:
            pass
    return total


def build_exact_topology(repository_root: Path, commit: str, *, verify_determinism: bool) -> dict[str, Any]:
    """Execute the observer bytes from *commit* in an isolated detached worktree."""
    repository_root = repository_root.resolve()
    ensure_commit(repository_root, commit)
    expected_tree = resolve_tree(repository_root, commit)
    with tempfile.TemporaryDirectory(prefix="grt2-wp0-") as temp_root_text:
        temp_root = Path(temp_root_text)
        worktree = temp_root / "source"
        output = temp_root / "output"
        added = False
        try:
            _git(repository_root, "worktree", "add", "--detach", str(worktree), commit)
            added = True
            env = os.environ.copy()
            env["PYTHONPATH"] = str(worktree / "src")
            command = [
                sys.executable,
                str(worktree / "scripts/governance/build_genesis_repository_topology.py"),
                "--repository-root",
                str(worktree),
                "--ref",
                commit,
                "--output-dir",
                str(output),
            ]
            if verify_determinism:
                command.append("--verify-determinism")
            started = time.perf_counter()
            completed = subprocess.run(
                command,
                cwd=str(worktree),
                env=env,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            elapsed = time.perf_counter() - started
            if completed.returncode != 0:
                raise WP0ReconciliationError(
                    f"exact GRT v0.1 observer failed for {commit}: {completed.stderr[-4000:]}"
                )
            read_model_path = output / "GENESIS_REPOSITORY_TOPOLOGY_READ_MODEL.json"
            summary_path = output / "GRT_TOPOLOGY_COMPACT_SUMMARY.json"
            manifest_path = output / "GRT_TOPOLOGY_BUILD_MANIFEST.json"
            if not read_model_path.is_file() or not manifest_path.is_file():
                raise WP0ReconciliationError(f"observer did not emit required outputs for {commit}")
            read_model = _load_json(read_model_path)
            manifest = _load_json(manifest_path)
            summary = _load_json(summary_path) if summary_path.is_file() else {}
            source_commit = str(manifest.get("source_commit") or read_model.get("portfolio", {}).get("source_commit") or "")
            if source_commit != commit:
                raise WP0ReconciliationError(
                    f"observer source commit mismatch: requested {commit}, emitted {source_commit}"
                )
            return {
                "commit": commit,
                "tree": expected_tree,
                "read_model": read_model,
                "manifest": manifest,
                "summary": summary,
                "execution": {
                    "elapsed_seconds": round(elapsed, 6),
                    "stdout_tail": completed.stdout[-2000:],
                    "stderr_tail": completed.stderr[-2000:],
                    "emitted_bytes": _json_file_bytes((read_model_path, summary_path, manifest_path)),
                    "python": sys.version.split()[0],
                    "platform": platform.platform(),
                },
            }
        finally:
            if added:
                _git(repository_root, "worktree", "remove", "--force", str(worktree), check=False)
            shutil.rmtree(worktree, ignore_errors=True)


def _anomalies(build: dict[str, Any]) -> list[dict[str, Any]]:
    raw = build["read_model"].get("anomalies", [])
    if not isinstance(raw, list):
        raise WP0ReconciliationError("read model anomalies is not a list")
    result: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise WP0ReconciliationError("read model contains non-object anomaly")
        result.append(item)
    return result


def warning_members(build: dict[str, Any]) -> list[dict[str, Any]]:
    warnings = [item for item in _anomalies(build) if item.get("severity") == "WARNING"]
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in sorted(warnings, key=lambda row: str(row.get("anomaly_id", ""))):
        anomaly_id = str(item.get("anomaly_id", ""))
        if not anomaly_id or anomaly_id in seen:
            raise WP0ReconciliationError(f"missing/duplicate warning anomaly_id: {anomaly_id!r}")
        seen.add(anomaly_id)
        rows.append(
            {
                "anomaly_id": anomaly_id,
                "anomaly_code": str(item.get("anomaly_code", "")),
                "payload_sha256": canonical_sha256(item),
            }
        )
    return rows


def _validate_b0(build: dict[str, Any]) -> list[dict[str, Any]]:
    manifest = build["manifest"]
    topology_sha = str(manifest.get("topology_sha256") or build["read_model"].get("topology_sha256") or "")
    if build["commit"] != B0_SOURCE_COMMIT:
        raise WP0ReconciliationError(f"wrong B0 source commit: {build['commit']}")
    if build["tree"] != B0_SOURCE_TREE:
        raise WP0ReconciliationError(
            f"B0 source tree mismatch: expected {B0_SOURCE_TREE}, got {build['tree']}"
        )
    if topology_sha != B0_TOPOLOGY_SHA256:
        raise WP0ReconciliationError(
            f"B0 topology mismatch: expected {B0_TOPOLOGY_SHA256}, got {topology_sha}"
        )
    anomalies = _anomalies(build)
    if len(anomalies) != B0_ANOMALY_COUNT:
        raise WP0ReconciliationError(
            f"B0 anomaly count mismatch: expected {B0_ANOMALY_COUNT}, got {len(anomalies)}"
        )
    members = warning_members(build)
    if len(members) != B0_WARNING_COUNT:
        raise WP0ReconciliationError(
            f"B0 raw WARNING count mismatch: expected {B0_WARNING_COUNT}, got {len(members)}"
        )
    counts = manifest.get("counts", {})
    expected_counts = {
        "programmes": B0_PROGRAMME_COUNT,
        "components": B0_COMPONENT_COUNT,
        "component_edges": B0_COMPONENT_EDGE_COUNT,
        "anomalies": B0_ANOMALY_COUNT,
    }
    for key, expected in expected_counts.items():
        actual = counts.get(key)
        if actual != expected:
            raise WP0ReconciliationError(f"B0 {key} mismatch: expected {expected}, got {actual}")
    determinism = manifest.get("determinism", {})
    if determinism.get("result") != "PASS":
        raise WP0ReconciliationError("B0 observer determinism did not PASS")
    return members


def reconcile(repository_root: Path, *, baseline_commit: str, verify_b0_determinism: bool = True) -> dict[str, Any]:
    """Reproduce immutable B0 and perform a separate fresh baseline census."""
    repository_root = repository_root.resolve()
    baseline_commit = resolve_commit(repository_root, baseline_commit)
    baseline_tree = resolve_tree(repository_root, baseline_commit)

    b0 = build_exact_topology(repository_root, B0_SOURCE_COMMIT, verify_determinism=verify_b0_determinism)
    b0_members = _validate_b0(b0)
    b0_ids = {row["anomaly_id"] for row in b0_members}

    current = build_exact_topology(repository_root, baseline_commit, verify_determinism=False)
    current_members = warning_members(current)
    current_ids = {row["anomaly_id"] for row in current_members}
    mapped = sorted(current_ids & b0_ids)
    late_preexisting = sorted(current_ids - b0_ids)
    resolved_before_grt2 = sorted(b0_ids - current_ids)
    current_anomalies = _anomalies(current)
    current_codes = Counter(
        str(item.get("anomaly_code", "UNKNOWN"))
        for item in current_anomalies
        if item.get("severity") == "WARNING"
    )
    b0_codes = Counter(row["anomaly_code"] for row in b0_members)

    b0_membership_sha = canonical_sha256([row["payload_sha256"] for row in b0_members])
    current_membership_sha = canonical_sha256([row["payload_sha256"] for row in current_members])
    return {
        "schema": "ovc-grt2-wp0-reconciliation/v1",
        "programme_id": "OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE",
        "baseline": {
            "commit": baseline_commit,
            "tree": baseline_tree,
        },
        "b0": {
            "source_commit": B0_SOURCE_COMMIT,
            "source_tree": B0_SOURCE_TREE,
            "topology_sha256": B0_TOPOLOGY_SHA256,
            "raw_warning_count": len(b0_members),
            "anomaly_count": len(_anomalies(b0)),
            "membership_sha256": b0_membership_sha,
            "warning_category_counts": dict(sorted(b0_codes.items())),
            "members": b0_members,
            "execution": b0["execution"],
            "determinism": b0["manifest"].get("determinism", {}),
        },
        "current_census": {
            "source_commit": baseline_commit,
            "source_tree": baseline_tree,
            "topology_sha256": str(
                current["manifest"].get("topology_sha256")
                or current["read_model"].get("topology_sha256")
                or ""
            ),
            "raw_warning_count": len(current_members),
            "anomaly_count": len(current_anomalies),
            "membership_sha256": current_membership_sha,
            "warning_category_counts": dict(sorted(current_codes.items())),
            "members": current_members,
            "classification": {
                "B0_MAPPED": mapped,
                "LATE_DISCOVERED_PRE_EXISTING": late_preexisting,
                "RESOLVED_BEFORE_GRT2": resolved_before_grt2,
                "TRANSITION_OR_NEW_DEBT": [],
            },
            "execution": current["execution"],
        },
        "invariants": {
            "b0_is_exactly_569": len(b0_members) == B0_WARNING_COUNT,
            "b0_source_reproducible": True,
            "fresh_census_does_not_redefine_b0": True,
            "pre_materialisation_census_has_no_grt2_transition_debt": True,
        },
        "authority_effect": "NONE_READ_ONLY_EVIDENCE",
    }


def write_reconciliation_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    b0 = result["b0"]
    current = result["current_census"]
    compact_b0 = {
        "schema": "ovc-grt2-b0-reproduction/v1",
        "programme_id": result["programme_id"],
        **b0,
        "authority_effect": "NONE_IMMUTABLE_SOURCE_EVIDENCE",
    }
    compact_current = {
        "schema": "ovc-grt2-current-debt-census/v1",
        "programme_id": result["programme_id"],
        "baseline": result["baseline"],
        **current,
        "authority_effect": "NONE_OBSERVATION_ONLY",
    }
    for name, value in (
        ("GRT2_B0_REPRODUCTION.json", compact_b0),
        ("GRT2_CURRENT_DEBT_CENSUS.json", compact_current),
    ):
        (output_dir / name).write_bytes(_canonical_bytes(value) + b"\n")
