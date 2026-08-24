from __future__ import annotations

import json
from pathlib import Path

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

ROOT = Path(__file__).resolve().parents[3]
CURRENT_MAIN = "d25236e6550b073d3a220326b764b15441182bec"
FORMER_GATE_READY_MAIN = "8e53e52537e9756e350b7f8d0c1551db3c581c6a"
OLD_FLOOR_PATH = ROOT / "docs/programmes/grt-v0-2/g3/GRT2_G3_PROPOSED_DEBT_FLOOR_GENERATION_0.json"
B0_MEMBERS_PATH = ROOT / "registries/governance/grt_v0_2/baseline/GRT_B0_BASELINE_MEMBERS_v0_1.jsonl"
CONSTITUTION_PATH = ROOT / "registries/governance/grt_v0_2/GRT_REPOSITORY_CONSTITUTION_v0_2.json"


def _rows(snapshot):
    return {str(row["finding_id"]): row for row in snapshot.get("findings", [])}


def test_emit_exact_superseding_g3_reconciliation_probe() -> None:
    old_floor = json.loads(OLD_FLOOR_PATH.read_text(encoding="utf-8"))
    constitution = json.loads(CONSTITUTION_PATH.read_text(encoding="utf-8"))
    b0_rows = [
        json.loads(line)
        for line in B0_MEMBERS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    validate_baseline_members(b0_rows)
    b0_membership = baseline_membership_sha256(b0_rows)

    former = full_g3_snapshot_at_commit(ROOT, commit=FORMER_GATE_READY_MAIN)
    current = full_g3_snapshot_at_commit(ROOT, commit=CURRENT_MAIN)
    former_rows = _rows(former)
    current_rows = _rows(current)
    old_ids = set(str(x) for x in old_floor["open_grandfathered_findings"])
    current_ids = set(current_rows)

    resolved = sorted(old_ids - current_ids)
    added = sorted(current_ids - old_ids)
    common = sorted(old_ids & current_ids)

    extent = {"UNCHANGED": 0, "REDUCED": 0, "EXPANDED": 0, "MATERIAL_CHANGED": 0}
    expanded = []
    material_changed = []
    for finding_id in common:
        prior = former_rows.get(finding_id, {}).get("debt_extent")
        now = current_rows.get(finding_id, {}).get("debt_extent")
        if isinstance(prior, dict) and isinstance(now, dict):
            disposition = compare_debt_extent(prior, now)
            extent[disposition] += 1
            if disposition == "EXPANDED":
                expanded.append(finding_id)
            elif disposition == "MATERIAL_CHANGED":
                material_changed.append(finding_id)

    baseline_topology = baseline_topology_from_member_records(b0_rows)
    current_topology = build_repository_topology(ROOT, ref=CURRENT_MAIN)
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
    floor = propose_candidate_floor(
        predecessor_commit=CURRENT_MAIN,
        predecessor_tree=str(current["tree"]),
        constitution_hash=str(constitution["canonical_hash"]),
        full_snapshot=current,
        lineage_reconciliation=lineage,
        transition_zero=transition.get("transition_debt_zero_proven") is True,
        baseline_expansion_zero=transition.get("baseline_expansion_zero_proven") is True,
    )

    payload = {
        "schema": "ovc-grt2-g3-superseding-readiness-probe/v1",
        "current_main": CURRENT_MAIN,
        "current_tree": current.get("tree"),
        "former_gate_ready_main": FORMER_GATE_READY_MAIN,
        "former_floor_hash": old_floor.get("floor_hash"),
        "former_floor_count": len(old_ids),
        "current_finding_count": len(current_ids),
        "resolved_ids": resolved,
        "added_ids": added,
        "resolved_rows": [former_rows.get(x) for x in resolved],
        "added_rows": [current_rows[x] for x in added],
        "extent_dispositions": extent,
        "expanded_ids": expanded,
        "material_changed_ids": material_changed,
        "b0_member_count": len(b0_rows),
        "b0_membership_sha256": b0_membership,
        "b0_exact": len(b0_rows) == B0_MEMBER_COUNT and b0_membership == B0_MEMBERSHIP_SHA256,
        "current_snapshot_hash": current.get("snapshot_hash"),
        "current_evaluation_count": current.get("evaluation_count"),
        "current_not_evaluable": current.get("not_evaluable", []),
        "current_adapter_errors": current.get("adapter_errors", []),
        "current_family_coverage": current.get("family_coverage", {}),
        "transition": transition,
        "lineage_status": lineage.get("status"),
        "unresolved_lineage_count": lineage.get("unresolved_lineage_count"),
        "candidate_floor": floor,
    }
    raise AssertionError(
        "GRT2_G3_SUPERSEDING_RECONCILIATION_PROBE="
        + json.dumps(payload, sort_keys=True, separators=(",", ":"))
    )
