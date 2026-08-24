#!/usr/bin/env python3
"""Emit exact no-authority evidence for the superseding GRT2-G3 census."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from ovc.programme_genesis._topology_engine import build_repository_topology
from ovc.programme_genesis.grt_v0_2.debt import (
    B0_MEMBER_COUNT,
    B0_MEMBERSHIP_SHA256,
    baseline_membership_sha256,
    compare_debt_extent,
    validate_baseline_members,
)
from ovc.programme_genesis.grt_v0_2.g3_floor import (
    full_g3_snapshot_at_commit,
    propose_candidate_floor,
    reconcile_b0_to_current_full_g3,
)
from ovc.programme_genesis.grt_v0_2.g3_readiness import (
    baseline_topology_from_member_records,
    reconcile_observer_transition_candidates,
)
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256

FORMER_GATE_READY_MAIN = "8e53e52537e9756e350b7f8d0c1551db3c581c6a"
FORMER_FLOOR_HASH = "f008cbad6bbb891b18f615aa91f9981fbf71ec874972630d8c6eb38ae1642ba9"
CONSTITUTION_HASH = "cac9fc5f0e31db08c4c37153c92a214fcc482414421f34d74c594faec65a71b0"
OLD_FLOOR = ROOT / "docs/programmes/grt-v0-2/g3/GRT2_G3_PROPOSED_DEBT_FLOOR_GENERATION_0.json"
B0_MEMBERS = ROOT / "registries/governance/grt_v0_2/baseline/GRT_B0_BASELINE_MEMBERS_v0_1.jsonl"
CONSTITUTION = ROOT / "registries/governance/grt_v0_2/GRT_REPOSITORY_CONSTITUTION_v0_2.json"
AUTHORITY = ROOT / "registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_1.json"
PGN = ROOT / "registries/governance/programme_genesis/OVC_PGN_PORTFOLIO_LEDGER_v0_2.json"
OUT = Path(
    os.environ.get(
        "GRT2_G3_SUPERSEDING_CENSUS_OUT",
        "artifacts/grt2-g3-superseding-census.json",
    )
)


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args],
        text=True,
    ).strip()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(snapshot: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(row["finding_id"]): row
        for row in snapshot.get("findings", [])
        if isinstance(row, Mapping) and row.get("finding_id")
    }


def _changed_paths(before: str, after: str) -> list[dict[str, str]]:
    raw = _git("diff", "--name-status", "--no-renames", before, after)
    rows: list[dict[str, str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        status, path = line.split("\t", 1)
        rows.append({"status": status, "path": path})
    return rows


def _replacement_candidates(
    resolved_rows: list[Mapping[str, Any]],
    added_rows: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Produce explicit, non-authoritative same-rule replacement candidates."""
    by_key_old: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    by_key_new: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for row in resolved_rows:
        key = (str(row.get("rule_id", "")), str(row.get("relation_role", "")))
        by_key_old.setdefault(key, []).append(row)
    for row in added_rows:
        key = (str(row.get("rule_id", "")), str(row.get("relation_role", "")))
        by_key_new.setdefault(key, []).append(row)
    candidates: list[dict[str, Any]] = []
    for key in sorted(set(by_key_old) & set(by_key_new)):
        old_group = sorted(
            by_key_old[key],
            key=lambda item: str(item.get("finding_id", "")),
        )
        new_group = sorted(
            by_key_new[key],
            key=lambda item: str(item.get("finding_id", "")),
        )
        candidates.append(
            {
                "rule_id": key[0],
                "relation_role": key[1],
                "resolved_finding_ids": [
                    str(item.get("finding_id", "")) for item in old_group
                ],
                "added_finding_ids": [
                    str(item.get("finding_id", "")) for item in new_group
                ],
                "resolved_subjects": [
                    str(item.get("subject_artifact_id", "")) for item in old_group
                ],
                "added_subjects": [
                    str(item.get("subject_artifact_id", "")) for item in new_group
                ],
                "classification": (
                    "DETERMINISTIC_CURRENT_STATE_REPLACEMENT_CANDIDATE"
                    if len(old_group) == len(new_group)
                    else "SAME_RULE_RECONCILIATION_REQUIRES_REVIEW"
                ),
                "authority_effect": "NONE_DIAGNOSTIC_CLASSIFICATION_ONLY",
            }
        )
    return candidates


def main() -> int:
    current_main = os.environ.get("GRT2_G3_CURRENT_MAIN", "").strip()
    if not current_main:
        current_main = _git("rev-parse", "origin/main")
    current_tree = _git("rev-parse", f"{current_main}^{{tree}}")

    old_floor = _load(OLD_FLOOR)
    constitution = _load(CONSTITUTION)
    authority = _load(AUTHORITY)
    pgn = _load(PGN)
    if old_floor.get("floor_hash") != FORMER_FLOOR_HASH:
        raise RuntimeError("FORMER_G3_FLOOR_IDENTITY_MISMATCH")
    if constitution.get("canonical_hash") != CONSTITUTION_HASH:
        raise RuntimeError("CONSTITUTION_IDENTITY_MISMATCH")

    b0_rows = [
        json.loads(line)
        for line in B0_MEMBERS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    validate_baseline_members(b0_rows)
    b0_hash = baseline_membership_sha256(b0_rows)
    b0_exact = len(b0_rows) == B0_MEMBER_COUNT and b0_hash == B0_MEMBERSHIP_SHA256

    former = full_g3_snapshot_at_commit(ROOT, commit=FORMER_GATE_READY_MAIN)
    current = full_g3_snapshot_at_commit(ROOT, commit=current_main)
    former_rows = _rows(former)
    current_rows = _rows(current)
    old_ids = set(str(value) for value in old_floor["open_grandfathered_findings"])
    current_ids = set(current_rows)

    resolved_ids = sorted(old_ids - current_ids)
    added_ids = sorted(current_ids - old_ids)
    common_ids = sorted(old_ids & current_ids)
    resolved_rows = [former_rows[fid] for fid in resolved_ids if fid in former_rows]
    added_rows = [current_rows[fid] for fid in added_ids]

    extent_counts = {
        "UNCHANGED": 0,
        "REDUCED": 0,
        "EXPANDED": 0,
        "MATERIAL_CHANGED": 0,
        "NOT_COMPARABLE": 0,
    }
    extent_rows: list[dict[str, Any]] = []
    for finding_id in common_ids:
        prior = former_rows.get(finding_id, {}).get("debt_extent")
        now = current_rows.get(finding_id, {}).get("debt_extent")
        if isinstance(prior, Mapping) and isinstance(now, Mapping):
            disposition = compare_debt_extent(prior, now)
        else:
            disposition = "NOT_COMPARABLE"
        extent_counts[disposition] += 1
        if disposition != "UNCHANGED":
            extent_rows.append(
                {
                    "finding_id": finding_id,
                    "disposition": disposition,
                    "former_extent": prior,
                    "current_extent": now,
                }
            )

    baseline_topology = baseline_topology_from_member_records(b0_rows)
    current_topology = build_repository_topology(ROOT, ref=current_main)
    transition = reconcile_observer_transition_candidates(
        baseline_topology=baseline_topology,
        current_topology=current_topology,
        full_snapshot=current,
        constitution_status=str(constitution.get("status", "")),
    )
    lineage = reconcile_b0_to_current_full_g3(
        b0_rows=b0_rows,
        current_topology=current_topology,
        full_snapshot=current,
        transition_reconciliation=transition,
    )
    candidate_floor = propose_candidate_floor(
        predecessor_commit=current_main,
        predecessor_tree=current_tree,
        constitution_hash=str(constitution["canonical_hash"]),
        full_snapshot=current,
        lineage_reconciliation=lineage,
        transition_zero=transition.get("transition_debt_zero_proven") is True,
        baseline_expansion_zero=transition.get("baseline_expansion_zero_proven") is True,
    )

    family_coverage = dict(current.get("family_coverage", {}))
    all_families_evaluated = bool(family_coverage) and all(
        value == "EVALUATED" for value in family_coverage.values()
    )
    not_evaluable = list(current.get("not_evaluable", []))
    adapter_errors = list(current.get("adapter_errors", []))
    unresolved_lineage = int(lineage.get("unresolved_lineage_count", -1))
    floor_constructed = isinstance(candidate_floor, Mapping)

    conditions = {
        "b0_exact": b0_exact,
        "constitution_identity_exact": constitution.get("canonical_hash") == CONSTITUTION_HASH,
        "constitution_remains_unactivated": constitution.get("status") == "PROPOSED_UNADMITTED",
        "limited_enforcement_remains_active": authority.get("enforcement_mode") == "LIMITED_NEW_ARTIFACT_ENFORCEMENT",
        "g3_authority_unconsumed": authority.get("g3_status") == "NOT_AUTHORISED",
        "all_rule_families_evaluated": all_families_evaluated,
        "not_evaluable_count_zero": len(not_evaluable) == 0,
        "adapter_error_count_zero": len(adapter_errors) == 0,
        "unresolved_lineage_zero": unresolved_lineage == 0,
        "transition_debt_zero_proven": transition.get("transition_debt_zero_proven") is True,
        "baseline_expansion_zero_proven": transition.get("baseline_expansion_zero_proven") is True,
        "candidate_floor_constructed": floor_constructed,
    }

    record: dict[str, Any] = {
        "schema": "ovc-grt2-g3-superseding-census-evidence/v1",
        "programme_id": "OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE",
        "packet_id": "GRT2-G3-SUPERSEDING-READINESS-RECONCILIATION",
        "gate_id": "GRT2-G3",
        "authority_effect": "NONE_SUPERSEDING_READINESS_EVIDENCE_ONLY",
        "current_main_commit": current_main,
        "current_main_tree": current_tree,
        "former_gate_ready_main_commit": FORMER_GATE_READY_MAIN,
        "former_floor": {
            "path": str(OLD_FLOOR.relative_to(ROOT)),
            "generation": old_floor.get("generation"),
            "count": len(old_ids),
            "floor_hash": old_floor.get("floor_hash"),
            "predecessor_commit": old_floor.get("predecessor_commit"),
            "predecessor_tree": old_floor.get("predecessor_tree"),
            "status": "HISTORICAL_APPROVED_BUT_UNCONSUMED",
        },
        "current_census": {
            "finding_count": len(current_ids),
            "evaluation_count": current.get("evaluation_count"),
            "full_tree_component_count": current.get("full_tree_component_count"),
            "snapshot_hash": current.get("snapshot_hash"),
            "family_coverage": family_coverage,
            "not_evaluable": not_evaluable,
            "adapter_errors": adapter_errors,
        },
        "old_to_current_reconciliation": {
            "unchanged_finding_count": len(common_ids),
            "resolved_finding_count": len(resolved_ids),
            "added_finding_count": len(added_ids),
            "resolved_finding_ids": resolved_ids,
            "added_finding_ids": added_ids,
            "resolved_rows": resolved_rows,
            "added_rows": added_rows,
            "extent_dispositions": extent_counts,
            "non_unchanged_extent_rows": extent_rows,
            "same_rule_replacement_candidates": _replacement_candidates(
                resolved_rows,
                added_rows,
            ),
            "changed_paths_since_former_gate_ready": _changed_paths(
                FORMER_GATE_READY_MAIN,
                current_main,
            ),
        },
        "b0_integrity": {
            "member_count": len(b0_rows),
            "membership_sha256": b0_hash,
            "expected_member_count": B0_MEMBER_COUNT,
            "expected_membership_sha256": B0_MEMBERSHIP_SHA256,
            "exact": b0_exact,
        },
        "observer_transition": transition,
        "b0_to_current_lineage": lineage,
        "candidate_replacement_debt_floor_generation_0": candidate_floor,
        "candidate_replacement_floor_count": (
            len(candidate_floor.get("open_grandfathered_findings", []))
            if isinstance(candidate_floor, Mapping)
            else None
        ),
        "candidate_replacement_floor_hash": (
            candidate_floor.get("floor_hash")
            if isinstance(candidate_floor, Mapping)
            else None
        ),
        "authority_frontier": {
            "constitution_status": constitution.get("status"),
            "active_enforcement": authority.get("enforcement_mode"),
            "g3_status": authority.get("g3_status"),
            "pgn_native_genesis_adoption": (
                pgn.get("authority", {}).get("native_genesis_adoption")
                if isinstance(pgn, Mapping)
                else None
            ),
            "previous_operator_pass": "RECEIVED_UNCONSUMED_EXACT_APPROVED_FLOOR_STALE",
        },
        "readiness_conditions": conditions,
        "mechanically_eligible_for_superseding_gate_preparation": all(conditions.values()),
        "warnings": [],
        "unresolved_issues": [],
    }
    record["logical_sha256"] = canonical_sha256(record)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": (
                    "MECHANICALLY_ELIGIBLE"
                    if record["mechanically_eligible_for_superseding_gate_preparation"]
                    else "REQUIRES_RECONCILIATION_REVIEW"
                ),
                "current_main": current_main,
                "current_tree": current_tree,
                "former_count": len(old_ids),
                "current_count": len(current_ids),
                "resolved_count": len(resolved_ids),
                "added_count": len(added_ids),
                "replacement_floor_count": record["candidate_replacement_floor_count"],
                "replacement_floor_hash": record["candidate_replacement_floor_hash"],
                "logical_sha256": record["logical_sha256"],
                "output": str(OUT),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
