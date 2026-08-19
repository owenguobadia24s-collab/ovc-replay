#!/usr/bin/env python3
"""Execute the complete non-authoritative GRT2-G3 readiness evidence programme."""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from ovc.programme_genesis._topology_engine import build_repository_topology
from ovc.programme_genesis.grt_v0_2.debt import B0_MEMBER_COUNT, B0_MEMBERSHIP_SHA256, baseline_membership_sha256, validate_baseline_members
from ovc.programme_genesis.grt_v0_2.full_enforcement import REQUIRED_FULL_G3_RULE_FAMILIES, replay_full_g3_candidate
from ovc.programme_genesis.grt_v0_2.g3_floor import full_g3_snapshot_at_commit, propose_candidate_floor, reconcile_b0_to_current_full_g3
from ovc.programme_genesis.grt_v0_2.g3_readiness import baseline_topology_from_member_records, reconcile_observer_transition_candidates, summarize_g3_readiness
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256

OUT = Path(os.environ.get("GRT2_G3_READINESS_OUT", "artifacts/grt2-g3-readiness-evidence.json"))
PILOT = ROOT / "docs/programmes/grt-v0-2/gates/GRT2_G2_5_PILOT_LEDGER.json"
HISTORICAL = ROOT / "docs/programmes/grt-v0-2/g3/GRT2_G3_HISTORICAL_CANDIDATE_MANIFEST.json"
PERFORMANCE = ROOT / "docs/programmes/grt-v0-2/g2/GRT2_G2_PERFORMANCE_RECEIPT.json"
B0_MEMBERS = ROOT / "registries/governance/grt_v0_2/baseline/GRT_B0_BASELINE_MEMBERS_v0_1.jsonl"
CONSTITUTION = ROOT / "registries/governance/grt_v0_2/GRT_REPOSITORY_CONSTITUTION_v0_2.json"
AUTHORITY = ROOT / "registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_1.json"
POINTER = ROOT / "registries/implementation/grt_v0_2/CURRENT_STATE_POINTER.json"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def _candidate_record(candidate_id: str, replay: Mapping[str, Any], *, budget: Mapping[str, Any], inherited: Mapping[str, Any] | None = None) -> dict[str, Any]:
    inherited = dict(inherited or {})
    max_ms = int(budget["runtime_budgets"]["GRT_EXACT"]["max_ms"])
    memory_ceiling = int(budget["peak_memory_ceiling_bytes"])
    perf = replay["performance"]
    performance_status = "PASS" if int(perf["duration_ms"]) <= max_ms and int(perf["peak_memory_bytes"]) <= memory_ceiling else "FAIL"
    family_ok = len(replay.get("family_coverage", {})) == len(REQUIRED_FULL_G3_RULE_FAMILIES) and all(value == "PASS" for value in replay.get("family_coverage", {}).values())
    shadow_ok = replay.get("status") == "PASS" and family_ok and replay.get("new_or_expanded_debt_count") == 0 and replay.get("not_evaluable_count") == 0 and not replay.get("adapter_errors") and not replay.get("blocking_transitions")
    return {
        "candidate_id": candidate_id,
        "predecessor_commit": replay["predecessor_commit"],
        "candidate_commit": replay["candidate_commit"],
        "predecessor_tree": replay["predecessor_tree"],
        "candidate_tree": replay["candidate_tree"],
        "full_g3_shadow_status": "PASS" if shadow_ok else str(replay.get("status", "INCOMPLETE")),
        "full_g3_canonical_hash": replay["canonical_hash"],
        "family_coverage": dict(replay.get("family_coverage", {})),
        "new_or_expanded_debt_count": replay.get("new_or_expanded_debt_count"),
        "not_evaluable_count": replay.get("not_evaluable_count"),
        "unresolved_escape_count": int(inherited.get("unresolved_escape_count", 0)),
        "blocking_false_positive_count": int(inherited.get("blocking_false_positive_count", 0)),
        "unresolved_false_negative_count": int(inherited.get("unresolved_false_negative_count", 0)),
        "scope_leakage_count": int(inherited.get("scope_leakage_count", 0)),
        "performance": dict(perf),
        "performance_status": performance_status,
        "qa_disposition": "PASS" if shadow_ok and performance_status == "PASS" else "FAIL",
        "reason_codes": list(replay.get("reason_codes", [])),
        "authority_effect": "NONE_G3_READINESS_EVIDENCE_ONLY",
    }


def main() -> int:
    started = time.perf_counter_ns()
    head = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    pilot = _load(PILOT)
    historical = _load(HISTORICAL)
    perf_receipt = _load(PERFORMANCE)
    budget = perf_receipt["performance_budget"]
    constitution = _load(CONSTITUTION)
    authority = _load(AUTHORITY)
    pointer = _load(POINTER)
    blockers: list[str] = []

    if constitution.get("canonical_hash") != "cac9fc5f0e31db08c4c37153c92a214fcc482414421f34d74c594faec65a71b0" or constitution.get("status") != "PROPOSED_UNADMITTED":
        blockers.append("CONSTITUTION_IDENTITY_OR_PREACTIVATION_STATE_MISMATCH")
    if authority.get("enforcement_mode") != "LIMITED_NEW_ARTIFACT_ENFORCEMENT" or authority.get("g3_status") != "NOT_AUTHORISED":
        blockers.append("G2_5_ACTIVE_AUTHORITY_FRONTIER_MISMATCH")
    if pointer.get("next_packet") != "GRT2-G3-READINESS-EVIDENCE":
        blockers.append("GRT2_NEXT_PACKET_NOT_G3_READINESS")
    if budget.get("budget_hash") != "88fadf691be87f0c55d98c994d29f54f6112e6c6e43f8d4bbbb328dc7fdb0b58":
        blockers.append("G2_PERFORMANCE_BUDGET_IDENTITY_MISMATCH")

    pilot_records: list[dict[str, Any]] = []
    for row in pilot.get("candidate_evaluations", []):
        replay = replay_full_g3_candidate(ROOT, predecessor_commit=str(row["predecessor_main_sha"]), candidate_commit=str(row["physical_merge_commit"]))
        pilot_records.append(_candidate_record(str(row["candidate_id"]), replay, budget=budget, inherited=row))

    historical_records: list[dict[str, Any]] = []
    for row in historical.get("candidates", []):
        candidate_id = f"GRT2.G3.HIST.{int(row['ordinal']):02d}"
        replay = replay_full_g3_candidate(ROOT, predecessor_commit=str(row["predecessor_commit"]), candidate_commit=str(row["integration_commit"]))
        historical_records.append(_candidate_record(candidate_id, replay, budget=budget))

    deterministic_repeat = None
    if pilot.get("candidate_evaluations"):
        row = pilot["candidate_evaluations"][0]
        first = replay_full_g3_candidate(ROOT, predecessor_commit=str(row["predecessor_main_sha"]), candidate_commit=str(row["physical_merge_commit"]))
        second = replay_full_g3_candidate(ROOT, predecessor_commit=str(row["predecessor_main_sha"]), candidate_commit=str(row["physical_merge_commit"]))
        deterministic_repeat = {"first": first["canonical_hash"], "second": second["canonical_hash"], "status": "PASS" if first["canonical_hash"] == second["canonical_hash"] else "FAIL"}
        if deterministic_repeat["status"] != "PASS":
            blockers.append("FULL_G3_REPLAY_NONDETERMINISTIC")

    b0_rows = [json.loads(line) for line in B0_MEMBERS.read_text(encoding="utf-8").splitlines() if line.strip()]
    validate_baseline_members(b0_rows)
    b0_membership = baseline_membership_sha256(b0_rows)
    if len(b0_rows) != B0_MEMBER_COUNT or b0_membership != B0_MEMBERSHIP_SHA256:
        blockers.append("B0_569_MEMBER_INTEGRITY_FAIL")
    baseline_topology = baseline_topology_from_member_records(b0_rows)
    current_topology = build_repository_topology(ROOT, ref=head)
    transition = reconcile_observer_transition_candidates(baseline_topology=baseline_topology, current_topology=current_topology)
    transition["baseline_membership_sha256"] = b0_membership
    transition["current_topology_sha256"] = current_topology.get("topology_sha256")
    transition["evidence_hash"] = canonical_sha256(transition)

    full_snapshot = full_g3_snapshot_at_commit(ROOT, commit=head)
    lineage = reconcile_b0_to_current_full_g3(b0_rows=b0_rows, current_topology=current_topology, full_snapshot=full_snapshot)
    floor = propose_candidate_floor(
        predecessor_commit=head,
        predecessor_tree=tree,
        constitution_hash=str(constitution["canonical_hash"]),
        full_snapshot=full_snapshot,
        lineage_reconciliation=lineage,
        transition_zero=transition.get("transition_debt_zero_proven") is True,
        baseline_expansion_zero=transition.get("baseline_expansion_zero_proven") is True,
    )
    floor_ready = floor is not None

    summary = summarize_g3_readiness(
        pilot_records=pilot_records,
        historical_records=historical_records,
        transition_reconciliation=transition,
        candidate_floor_ready=floor_ready,
        required_historical_count=10,
    )
    if lineage.get("unresolved_lineage_count") != 0:
        blockers.append("B0_TO_CURRENT_V0_2_LINEAGE_UNRESOLVED")
    if full_snapshot.get("adapter_errors") or full_snapshot.get("not_evaluable"):
        blockers.append("FULL_CURRENT_G3_SNAPSHOT_NOT_EVALUABLE")
    if any(value != "EVALUATED" for value in full_snapshot.get("family_coverage", {}).values()):
        blockers.append("FULL_CURRENT_G3_RULE_FAMILY_COVERAGE_GAP")
    if summary.get("status") != "GATE_READY":
        blockers.extend(str(x) for x in summary.get("reason_codes", []))

    targeted = _run(sys.executable, "-m", "pytest", "tests/governance/grt_v0_2", "-q", "--tb=short")
    if targeted.returncode != 0:
        blockers.append("GRT2_REPOSITORY_TEST_SUITE_FAIL")

    elapsed_ms = max(1, (time.perf_counter_ns() - started + 999_999) // 1_000_000)
    record: dict[str, Any] = {
        "schema": "ovc-grt2-g3-readiness-evidence/v1",
        "programme_id": "OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE",
        "plan_id": "OVC-GRT-V0.2-RCCC-CONFORMANCE-IMPLEMENTATION-PLAN-0.2-REVISED-RATIFIED",
        "packet_id": "GRT2-G3-READINESS-EVIDENCE",
        "gate_id": "GRT2-G3",
        "candidate_commit": head,
        "candidate_tree": tree,
        "constitution_hash": constitution["canonical_hash"],
        "performance_budget_hash": budget["budget_hash"],
        "b0_member_count": len(b0_rows),
        "b0_membership_sha256": b0_membership,
        "pilot_records": pilot_records,
        "historical_records": historical_records,
        "deterministic_repeat": deterministic_repeat,
        "transition_reconciliation": transition,
        "full_current_snapshot": {
            "commit": full_snapshot.get("commit"), "tree": full_snapshot.get("tree"),
            "full_tree_component_count": full_snapshot.get("full_tree_component_count"),
            "evaluation_count": full_snapshot.get("evaluation_count"),
            "finding_count": len(full_snapshot.get("findings", [])),
            "not_evaluable_count": len(full_snapshot.get("not_evaluable", [])),
            "adapter_errors": full_snapshot.get("adapter_errors", []),
            "family_coverage": full_snapshot.get("family_coverage", {}),
            "snapshot_hash": full_snapshot.get("snapshot_hash"),
        },
        "b0_lineage_reconciliation": lineage,
        "candidate_debt_floor_generation_0": floor,
        "readiness_summary": summary,
        "tests": {"returncode": targeted.returncode, "output_tail": targeted.stdout[-12000:]},
        "environment": {"platform": platform.platform(), "python": platform.python_version(), "github_run_id": os.environ.get("GITHUB_RUN_ID")},
        "elapsed_ms": int(elapsed_ms),
        "blockers": sorted(set(blockers)),
        "qa_disposition": "PASS" if not blockers else "BLOCK",
        "recommended_decision": "PASS" if not blockers else "BLOCK",
        "status": "GATE_READY" if not blockers else "BLOCKED",
        "authority_effect": "NONE_G3_READINESS_AND_GATE_PREPARATION_ONLY",
        "active_enforcement": "UNCHANGED_LIMITED_NEW_ARTIFACT_ENFORCEMENT",
        "g3_authority": "NOT_CONSUMED",
    }
    record["evidence_hash"] = canonical_sha256({key: value for key, value in record.items() if key not in {"environment", "tests"}})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "qa": record["qa_disposition"], "recommended_decision": record["recommended_decision"], "blockers": record["blockers"], "evidence_hash": record["evidence_hash"], "output": str(OUT)}, sort_keys=True))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
