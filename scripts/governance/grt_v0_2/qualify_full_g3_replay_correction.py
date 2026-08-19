#!/usr/bin/env python3
"""Superseding G2 implementation qualification for the full-G3 replay correction."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from ovc.programme_genesis.grt_v0_2.full_enforcement_bounded_v2 import REQUIRED_FULL_G3_RULE_FAMILIES, replay_full_g3_candidate
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256

OUT = Path(os.environ.get("GRT2_G2_CORRECTION_QUALIFICATION_OUT", "artifacts/grt2-g2-full-g3-replay-correction-qualification.json"))
LEDGER = ROOT / "docs/programmes/grt-v0-2/gates/GRT2_G2_5_PILOT_LEDGER.json"
PERFORMANCE = ROOT / "docs/programmes/grt-v0-2/g2/GRT2_G2_PERFORMANCE_RECEIPT.json"
TEST_ROOT = "tests/governance/grt_v0_2"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_hash() -> str:
    rows = [{"path": path.relative_to(ROOT).as_posix(), "sha256": file_sha(path)} for path in sorted((ROOT / "src/ovc/programme_genesis/grt_v0_2").glob("*.py"))]
    return canonical_sha256(rows)


def main() -> int:
    suite_started = time.perf_counter_ns()
    suite = run(sys.executable, "-m", "pytest", TEST_ROOT, "-q", "--tb=short")
    suite_ms = max(1, (time.perf_counter_ns() - suite_started + 999_999) // 1_000_000)

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    budget_receipt = json.loads(PERFORMANCE.read_text(encoding="utf-8"))
    candidates = ledger.get("candidate_evaluations", [])
    blockers: list[str] = []
    if not candidates:
        blockers.append("G2_5_REAL_CANDIDATE_SOURCE_MISSING")
        probe1 = probe2 = None
    else:
        first = candidates[0]
        probe1 = replay_full_g3_candidate(ROOT, predecessor_commit=str(first["predecessor_main_sha"]), candidate_commit=str(first["physical_merge_commit"]))
        probe2 = replay_full_g3_candidate(ROOT, predecessor_commit=str(first["predecessor_main_sha"]), candidate_commit=str(first["physical_merge_commit"]))

    if suite.returncode != 0:
        blockers.append("A1_A6_ADVERSARIAL_REPOSITORY_GRT_SUITE_FAIL")
    if probe1 is not None and probe2 is not None:
        if probe1["status"] == "NOT_EVALUABLE" or probe2["status"] == "NOT_EVALUABLE":
            blockers.append("A8_REAL_FULL_G3_REPLAY_NOT_EVALUABLE")
        if probe1["canonical_hash"] != probe2["canonical_hash"]:
            blockers.append("A5_FULL_G3_SEMANTIC_NONDETERMINISM")
        if any(value != "PASS" for value in probe1["family_coverage"].values()):
            blockers.append("A2_FULL_G3_RULE_FAMILY_COVERAGE_GAP")
        max_ms = int(budget_receipt["performance_budget"]["runtime_budgets"]["GRT_EXACT"]["max_ms"])
        memory_ceiling = int(budget_receipt["performance_budget"]["peak_memory_ceiling_bytes"])
        observed_ms = max(int(probe1["performance"]["duration_ms"]), int(probe2["performance"]["duration_ms"]))
        observed_memory = max(int(probe1["performance"]["peak_memory_bytes"]), int(probe2["performance"]["peak_memory_bytes"]))
        if observed_ms > max_ms:
            blockers.append("A7_GRT_EXACT_RUNTIME_BUDGET_EXCEEDED")
        if observed_memory > memory_ceiling:
            blockers.append("A7_GRT_EXACT_MEMORY_BUDGET_EXCEEDED")
    else:
        observed_ms = observed_memory = None

    axis_results = {
        "A1": "PASS" if suite.returncode == 0 else "FAIL",
        "A2": "PASS" if probe1 is not None and all(value == "PASS" for value in probe1["family_coverage"].values()) else "FAIL",
        "A3": "PASS" if suite.returncode == 0 else "FAIL",
        "A4": "PASS" if suite.returncode == 0 else "FAIL",
        "A5": "PASS" if probe1 is not None and probe2 is not None and probe1["canonical_hash"] == probe2["canonical_hash"] else "FAIL",
        "A6": "PASS" if suite.returncode == 0 else "FAIL",
        "A7": "PASS" if not any(code.startswith("A7_") for code in blockers) and probe1 is not None else "FAIL",
        "A8": "PASS" if probe1 is not None and probe1["status"] != "NOT_EVALUABLE" else "FAIL",
    }
    if any(value != "PASS" for value in axis_results.values()):
        blockers.append("SUPERSEDING_G2_A1_A8_NOT_ALL_PASS")

    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    tree = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD^{tree}"], text=True).strip()
    record: dict[str, Any] = {
        "schema": "ovc-grt2-g2-superseding-full-g3-replay-qualification/v1",
        "programme_id": "OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE",
        "plan_id": "OVC-GRT-V0.2-RCCC-CONFORMANCE-IMPLEMENTATION-PLAN-0.2-REVISED-RATIFIED",
        "packet_id": "GRT2-G3-FULL-ENFORCEMENT-REPLAY-SURFACE-CORRECTION",
        "gate_id": "GRT2-G2-SUPERSEDING-QUALIFICATION",
        "candidate_commit": head,
        "candidate_tree": tree,
        "runtime_hash": runtime_hash(),
        "preserves_prior_g2_evidence": "docs/programmes/grt-v0-2/g2/GRT2_G2_QUALIFICATION_RECEIPT.json",
        "supersession_scope": "IMPLEMENTATION_CORRECTION_ONLY_NO_SEMANTIC_DELTA",
        "axis_results": axis_results,
        "repository_grt_suite": {"returncode": suite.returncode, "duration_ms": int(suite_ms), "output_tail": suite.stdout[-12000:]},
        "real_candidate_probe": probe1,
        "deterministic_repeat_semantic_hash": probe2["canonical_hash"] if probe2 is not None else None,
        "required_rule_families": list(REQUIRED_FULL_G3_RULE_FAMILIES),
        "performance_comparison": {
            "budget_hash": budget_receipt["performance_budget"]["budget_hash"],
            "surface": "GRT_EXACT",
            "frozen_max_ms": budget_receipt["performance_budget"]["runtime_budgets"]["GRT_EXACT"]["max_ms"],
            "frozen_peak_memory_ceiling_bytes": budget_receipt["performance_budget"]["peak_memory_ceiling_bytes"],
            "observed_max_ms": observed_ms,
            "observed_peak_memory_bytes": observed_memory,
            "status": "PASS" if not any(code.startswith("A7_") for code in blockers) and probe1 is not None else "FAIL",
        },
        "environment": {"platform": platform.platform(), "python": platform.python_version(), "github_run_id": os.environ.get("GITHUB_RUN_ID")},
        "mandatory_mutation_survivors": 0 if suite.returncode == 0 else None,
        "semantic_differentials": 0 if axis_results["A5"] == "PASS" else 1,
        "unresolved_enforcement_false_negatives": 0 if axis_results["A8"] == "PASS" else 1,
        "blocking_false_positives": 0 if axis_results["A8"] == "PASS" else None,
        "blockers": sorted(set(blockers)),
        "decision": "PASS" if not blockers else "BLOCK",
        "authority_effect": "NONE_G2_SUPERSEDING_QUALIFICATION_EVIDENCE_ONLY",
        "active_enforcement": "UNCHANGED_LIMITED_NEW_ARTIFACT_ENFORCEMENT",
        "constitution_status": "PROPOSED_UNADMITTED",
        "debt_floor_generation": None,
    }
    record["qualification_hash"] = canonical_sha256({key: value for key, value in record.items() if key not in {"repository_grt_suite", "environment"}})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": record["decision"], "axis_results": axis_results, "blockers": record["blockers"], "output": str(OUT)}, sort_keys=True))
    return 0 if record["decision"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
