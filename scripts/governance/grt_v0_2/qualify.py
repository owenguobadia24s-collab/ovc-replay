#!/usr/bin/env python3
"""GRT2-G2 live qualification evidence harness.

This runner is intentionally fail-closed.  It gathers real CI evidence from the
checked-out candidate, exercises the existing A1-A8 surfaces, performs an exact
post-WP3 classification-coverage census, and freezes no performance budget unless
the candidate is fully evaluable.  It never activates GRT or creates DebtFloor state.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from ovc.programme_genesis._topology_engine import tracked_inventory  # noqa: E402
from ovc.programme_genesis.grt_v0_2.integration import (  # noqa: E402
    build_conformance_proof,
    build_integration_context,
    classify_movement,
    evaluate_readiness,
)
from ovc.programme_genesis.grt_v0_2.qualification import (  # noqa: E402
    ASSURANCE_AXES,
    PERFORMANCE_SURFACES,
    PerformanceBudgetError,
    build_qualification_record,
    build_qualification_target,
    evaluate_g2_readiness,
    freeze_performance_budget,
)
from ovc.programme_genesis.grt_v0_2.reference import (  # noqa: E402
    ReferenceRuntimeError,
    _artifact_type_from_path,
    observe_component,
)
from ovc.programme_genesis.grt_v0_2.rules import (  # noqa: E402
    RuleEvaluationError,
    evaluate_rule,
    reconcile_finding,
)
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256  # noqa: E402

OUT = Path(os.environ.get("GRT2_G2_EVIDENCE_OUT", "artifacts/grt2-g2-qualification-evidence.json"))

AXIS_TESTS: dict[str, list[str]] = {
    "A1": [
        "tests/governance/grt_v0_2/test_grt2_wp1_bootstrap.py",
        "tests/governance/grt_v0_2/test_grt2_wp1_constitution.py",
        "tests/governance/grt_v0_2/test_grt2_wp1_protocols.py",
    ],
    "A2": ["tests/governance/grt_v0_2/test_grt2_wp3c.py"],
    "A3": [
        "tests/governance/grt_v0_2/test_grt2_wp2.py",
        "tests/governance/grt_v0_2/test_grt2_wp3a.py",
    ],
    "A5": [
        "tests/governance/grt_v0_2/test_grt2_wp3d.py",
        "tests/governance/grt_v0_2/test_grt2_g2_incremental_fallback.py",
    ],
    "A6": [
        "tests/governance/grt_v0_2/test_grt2_wp2.py",
        "tests/governance/grt_v0_2/test_grt2_wp3a.py",
        "tests/governance/grt_v0_2/test_grt2_wp3b.py",
    ],
    "A7": [
        "tests/governance/grt_v0_2/test_grt2_wp3d.py",
        "tests/governance/grt_v0_2/test_grt2_wp3e.py",
    ],
}


def run(*args: str, check: bool = True) -> str:
    cp = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and cp.returncode != 0:
        raise RuntimeError(f"command failed ({cp.returncode}): {' '.join(args)}\n{cp.stdout}\n{cp.stderr}")
    return cp.stdout.strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def runtime_hash() -> str:
    rows = []
    root = ROOT / "src/ovc/programme_genesis/grt_v0_2"
    for path in sorted(root.glob("*.py")):
        rows.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)})
    return canonical_sha256(rows)


def axis_pytest(axis: str, paths: list[str]) -> dict[str, Any]:
    started = time.perf_counter()
    cp = subprocess.run(
        [sys.executable, "-m", "pytest", *paths, "-q", "--tb=short"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return {
        "axis": axis,
        "status": "PASS" if cp.returncode == 0 else "FAIL",
        "duration_ms": max(1, round((time.perf_counter() - started) * 1000)),
        "command": [sys.executable, "-m", "pytest", *paths, "-q", "--tb=short"],
        "output_tail": cp.stdout[-8000:],
    }


def mutation_probes() -> dict[str, Any]:
    probes: list[tuple[str, Callable[[], bool]]] = []

    def invalid_path() -> bool:
        try:
            observe_component(tree_hash="1" * 40, path="../escape", content_hash="2" * 40)
        except ReferenceRuntimeError:
            return True
        return False

    def invalid_rule_fact() -> bool:
        rule = {
            "rule_id": "R.TEST",
            "applicability_predicate": "applies",
            "violation_predicate": "violates",
        }
        try:
            evaluate_rule(rule, {"artifact_id": "A"}, {"applies": "MAYBE"})
        except RuleEvaluationError:
            return True
        return False

    def expanded_debt_fails() -> bool:
        result = reconcile_finding(
            predecessor_state="GRANDFATHERED",
            candidate_state="GRANDFATHERED",
            predecessor_extent={"violations": 1},
            candidate_extent={"violations": 2},
        )
        return result["admission"] == "FAIL" and result["classification"] == "BASELINE_EXPANDED"

    def stale_readiness_renews() -> bool:
        context = build_integration_context(
            base_commit="1" * 40,
            base_tree="2" * 40,
            head_commit="3" * 40,
            head_tree="4" * 40,
            integration_tree="5" * 40,
            merge_strategy="SQUASH",
            constitution_hash="6" * 64,
            runtime_hash="7" * 64,
            scanner_hash="8" * 64,
            debt_floor_generation=None,
            debt_floor_hash=None,
        )
        proof = build_conformance_proof(
            context=context,
            result="PASS",
            findings_hash="9" * 64,
            debt_hash="a" * 64,
            evidence_hash="b" * 64,
        )
        movement = classify_movement(
            proof=proof,
            current_main_commit="1" * 40,
            current_head_commit="c" * 40,
            current_integration_tree="5" * 40,
        )
        readiness = evaluate_readiness(
            proof=proof,
            current_main_commit="1" * 40,
            current_head_commit="c" * 40,
            current_integration_tree="5" * 40,
            movement_class=movement,
        )
        return movement == "HEAD_MOVED" and readiness["status"] == "RENEW_REQUIRED"

    def insufficient_budget_fails() -> bool:
        try:
            freeze_performance_budget(
                samples=[],
                environment_hash="d" * 64,
                repository_scale=1,
                cache_storage_ceiling_bytes=1,
                proof_evidence_size_ceiling_bytes=1,
                capacity_failure_threshold=1,
            )
        except PerformanceBudgetError:
            return True
        return False

    probes.extend(
        [
            ("INVALID_OBSERVED_PATH", invalid_path),
            ("INVALID_RULE_FACT", invalid_rule_fact),
            ("BASELINE_EXPANSION", expanded_debt_fails),
            ("STALE_HEAD_READINESS", stale_readiness_renews),
            ("INSUFFICIENT_PERFORMANCE_EVIDENCE", insufficient_budget_fails),
        ]
    )
    results = []
    for name, probe in probes:
        try:
            detected = bool(probe())
            error = None
        except Exception as exc:  # qualification evidence records unexpected probe defects
            detected = False
            error = f"{type(exc).__name__}: {exc}"
        results.append({"probe": name, "detected": detected, "error": error})
    survivors = [row["probe"] for row in results if not row["detected"]]
    return {"results": results, "mandatory_mutation_survivors": len(survivors), "survivors": survivors}


def current_census(commit: str) -> dict[str, Any]:
    inventory = tracked_inventory(ROOT, commit=commit)
    types: Counter[str] = Counter()
    unsupported: list[str] = []
    for row in inventory:
        artifact_type = _artifact_type_from_path(row["path"])
        if artifact_type is None:
            unsupported.append(row["path"])
        else:
            types[artifact_type] += 1
    return {
        "schema": "grt-g2-post-wp3-census/v0.1",
        "source_commit": commit,
        "source_tree": run("git", "rev-parse", f"{commit}^{{tree}}"),
        "tracked_component_count": len(inventory),
        "classified_component_count": len(inventory) - len(unsupported),
        "artifact_type_counts": dict(sorted(types.items())),
        "not_evaluable_component_count": len(unsupported),
        "not_evaluable_paths_sample": unsupported[:100],
        "classification_status": "RESOLVED" if not unsupported else "NOT_EVALUABLE",
        "current_actionable_condition_count": None,
        "transition_debt_count": None,
        "authority_effect": "NONE_CENSUS_EVIDENCE_ONLY",
    }


def changed_paths(base: str, head: str) -> list[str]:
    out = run("git", "diff", "--name-only", f"{base}...{head}")
    return [line for line in out.splitlines() if line]


def a8_shadow(base: str, head: str, census: dict[str, Any], probes: dict[str, Any]) -> dict[str, Any]:
    paths = changed_paths(base, head)
    unsupported = [path for path in paths if _artifact_type_from_path(path) is None]
    status = "PASS" if census["classification_status"] == "RESOLVED" and not unsupported and probes["mandatory_mutation_survivors"] == 0 else "NOT_EVALUABLE"
    return {
        "schema": "grt-g2-a8-real-ci-shadow/v0.1",
        "base_commit": base,
        "head_commit": head,
        "real_ci_candidate": True,
        "changed_path_count": len(paths),
        "changed_paths": paths,
        "not_evaluable_changed_paths": unsupported,
        "active_false_negative_probe_count": len(probes["results"]),
        "unresolved_enforcement_false_negatives": probes["mandatory_mutation_survivors"],
        "blocking_false_positives": 0 if status == "PASS" else None,
        "pilot_escapes": 0 if status == "PASS" else None,
        "review_status": status,
        "authority_effect": "NONE_REAL_CI_SHADOW_ONLY",
    }


def main() -> int:
    head = run("git", "rev-parse", "HEAD")
    base = os.environ.get("GRT2_BASE_COMMIT") or run("git", "merge-base", "HEAD", "origin/main")
    constitution = json.loads((ROOT / "registries/governance/grt_v0_2/GRT_REPOSITORY_CONSTITUTION_v0_2.json").read_text())
    constitution_hash = constitution["canonical_hash"]
    scanner_hash = sha256_file(ROOT / "src/ovc/programme_genesis/_topology_engine.py")
    live_runtime_hash = runtime_hash()

    probes = mutation_probes()
    census = current_census(head)
    shadow = a8_shadow(base, head, census, probes)

    axis_records: dict[str, dict[str, Any]] = {}
    for axis, paths in AXIS_TESTS.items():
        axis_records[axis] = axis_pytest(axis, paths)
    axis_records["A4"] = {
        "axis": "A4",
        "status": "PASS" if probes["mandatory_mutation_survivors"] == 0 else "FAIL",
        "mutation_probe_evidence": probes,
    }
    axis_records["A8"] = {
        "axis": "A8",
        "status": "PASS" if shadow["review_status"] == "PASS" else "NOT_EVALUABLE",
        "shadow_evidence": shadow,
    }

    axis_results = {axis: axis_records[axis]["status"] for axis in ASSURANCE_AXES}
    target = build_qualification_target(
        constitution_hash=constitution_hash,
        runtime_hash=live_runtime_hash,
        scanner_hash=scanner_hash,
        platform_classes=[f"{platform.system()}-{platform.machine()}-python-{platform.python_version()}"],
        mutation_catalogue_hash=canonical_sha256(probes["results"]),
    )
    qualification = build_qualification_record(
        target=target,
        axis_results=axis_results,
        mutation_survivors=probes["mandatory_mutation_survivors"],
        reference_incremental_differences=0 if axis_results["A5"] == "PASS" else 1,
        unresolved_false_negatives=probes["mandatory_mutation_survivors"],
        blocking_false_positives=0,
        capacity_status="PASS" if axis_results["A7"] == "PASS" else "FAIL",
        restart_status="PASS" if axis_results["A7"] == "PASS" else "FAIL",
        platform_status="PASS" if axis_results["A7"] == "PASS" else "FAIL",
        shadow_status="PASS" if axis_results["A8"] == "PASS" else "NOT_EVALUABLE",
        evidence_refs=[f"git:{head}", "ci:GRT2-G2-QUALIFICATION-EVIDENCE"],
    )

    performance_budget = None
    budget_status = "NOT_FROZEN"
    budget_reason = "GRT_PERFORMANCE_MEASUREMENT_NOT_RUN_UNTIL_QUALIFICATION_AND_CENSUS_RESOLVE"
    if qualification["decision"] == "PASS" and census["classification_status"] == "RESOLVED":
        # Deliberately left fail-closed until the exact workload surfaces are all executable.
        budget_reason = "GRT_PERFORMANCE_SURFACE_MEASUREMENT_HARNESS_REQUIRED"

    transition_debt_count = census["transition_debt_count"]
    readiness = None
    if transition_debt_count is not None:
        readiness = evaluate_g2_readiness(
            qualification=qualification,
            performance_budget=performance_budget,
            transition_debt_count=transition_debt_count,
        )

    blockers = []
    if qualification["decision"] != "PASS":
        blockers.append("G2_QUALIFICATION_NOT_PASS")
    if census["classification_status"] != "RESOLVED":
        blockers.append("G2_POST_WP3_CURRENT_CENSUS_NOT_EVALUABLE")
    if performance_budget is None:
        blockers.append("G2_MEASURED_PERFORMANCE_BUDGET_MISSING")
    if shadow["review_status"] != "PASS":
        blockers.append("G2_A8_REAL_CI_SHADOW_NOT_PASS")

    record = {
        "schema": "ovc-grt2-g2-live-qualification-evidence/v0.1",
        "programme_id": "OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE",
        "plan_id": "OVC-GRT-V0.2-RCCC-CONFORMANCE-IMPLEMENTATION-PLAN-0.2-REVISED-RATIFIED",
        "gate_id": "GRT2-G2",
        "packet_id": "GRT2-G2-QUALIFICATION-EVIDENCE",
        "baseline_commit": base,
        "candidate_commit": head,
        "candidate_tree": run("git", "rev-parse", "HEAD^{tree}"),
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_job": os.environ.get("GITHUB_JOB"),
        },
        "qualification_target": target,
        "axis_records": axis_records,
        "qualification_record": qualification,
        "post_wp3_current_census": census,
        "a8_real_ci_shadow": shadow,
        "performance_budget_status": budget_status,
        "performance_budget_reason": budget_reason,
        "performance_budget": performance_budget,
        "g2_readiness": readiness,
        "blockers": blockers,
        "authority_effect": "NONE_G2_EVIDENCE_ONLY",
        "active_enforcement": "NONE",
        "debt_floor_generation": None,
        "decision": "PASS" if not blockers else "BLOCK",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": record["decision"], "blockers": blockers, "output": str(OUT)}, sort_keys=True))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
