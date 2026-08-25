#!/usr/bin/env python3
"""Preview the next GRT DebtFloor without mutating an ordinary packet tree.

The active integration-ownership policy makes DebtFloor generation an A2
exact-tree projection. This helper verifies the packet changed no floor control
path and emits a preparation receipt. Final generation/hash are recomputed by
GRT-EXACT after late physical placement.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

from ovc.programme_genesis.grt_v0_2.debt import (
    G4_CANDIDATE_FINDING_ID,
    G4_GRANDFATHERED_FINDING_ID,
    compare_debt_extent,
    validate_g4_current_projection_substitution,
)
from ovc.programme_genesis.grt_v0_2.g3_floor import full_g3_snapshot_at_commit
from scripts.governance.grt_v0_2.integration_floor import (
    POLICY_PATH,
    assert_no_packet_floor_mutation,
    validate_policy,
)

ROOT = Path(__file__).resolve().parents[3]
G4_DECISION_PATH = "docs/programmes/grt-v0-2/g4/GRT2_G4_OPERATOR_DECISION.json"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def _json_at(commit: str, path: str) -> Mapping[str, Any] | None:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{commit}:{path}"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode:
        return None
    value = json.loads(proc.stdout)
    if not isinstance(value, Mapping):
        raise ValueError(f"GRT_FLOOR_PREP_RECORD_NOT_OBJECT:{path}")
    return value


def _findings(snapshot: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows: dict[str, Mapping[str, Any]] = {}
    for row in snapshot.get("findings", []):
        finding_id = str(row.get("finding_id", ""))
        if not finding_id or finding_id in rows:
            raise ValueError("GRT_FLOOR_PREP_FINDING_ID_INVALID_OR_DUPLICATE")
        rows[finding_id] = row
    return rows


def _assert_evaluable(snapshot: Mapping[str, Any], label: str) -> None:
    if snapshot.get("adapter_errors") or snapshot.get("not_evaluable"):
        raise ValueError(f"GRT_FLOOR_PREP_{label}_NOT_EVALUABLE")
    if any(value != "EVALUATED" for value in snapshot.get("family_coverage", {}).values()):
        raise ValueError(f"GRT_FLOOR_PREP_{label}_FAMILY_COVERAGE_GAP")


def _exact_g4_transition(before: Mapping[str, Any], after: Mapping[str, Any]) -> bool:
    return (
        G4_GRANDFATHERED_FINDING_ID in before
        and G4_GRANDFATHERED_FINDING_ID not in after
        and G4_CANDIDATE_FINDING_ID not in before
        and G4_CANDIDATE_FINDING_ID in after
    )


def prepare(base_ref: str, head_ref: str) -> dict[str, Any]:
    base = _git("rev-parse", f"{base_ref}^{{commit}}")
    head = _git("rev-parse", f"{head_ref}^{{commit}}")
    policy = _json_at(head, POLICY_PATH)
    if policy is None:
        raise ValueError("GRT_FLOOR_PREP_INTEGRATION_OWNERSHIP_POLICY_MISSING")
    validate_policy(policy)
    assert_no_packet_floor_mutation(_git("diff", "--name-only", base, head).splitlines())

    before_snapshot = full_g3_snapshot_at_commit(ROOT, commit=base)
    after_snapshot = full_g3_snapshot_at_commit(ROOT, commit=head)
    _assert_evaluable(before_snapshot, "BASE")
    _assert_evaluable(after_snapshot, "HEAD")
    before = _findings(before_snapshot)
    after = _findings(after_snapshot)

    substitutions: dict[str, str] = {}
    if _exact_g4_transition(before, after):
        decision = _json_at(head, G4_DECISION_PATH)
        if decision is None:
            raise ValueError("GRT_FLOOR_PREP_G4_DECISION_MISSING")
        substitutions = validate_g4_current_projection_substitution(decision, before, after)
    new_ids = sorted(set(after) - set(before) - set(substitutions.values()))
    if new_ids:
        raise ValueError(f"GRT_FLOOR_PREP_NEW_OR_RECURRENT_DEBT:{new_ids[:10]}")

    for finding_id in sorted(set(before) & set(after)):
        previous = before[finding_id].get("debt_extent")
        current = after[finding_id].get("debt_extent")
        if not isinstance(previous, Mapping) or not isinstance(current, Mapping):
            raise ValueError(f"GRT_FLOOR_PREP_DEBT_EXTENT_MISSING:{finding_id}")
        disposition = compare_debt_extent(previous, current)
        if disposition in {"EXPANDED", "MATERIAL_CHANGED"}:
            raise ValueError(f"GRT_FLOOR_PREP_{disposition}_DEBT:{finding_id}")

    return {
        "schema": "ovc-grt2-debt-floor-preparation-receipt/v2",
        "base_commit": base,
        "head_commit": head,
        "floor_materialisation_mode": "VIRTUAL_EXACT_TREE_PROJECTION",
        "packet_tree_mutation": False,
        "late_binding_final_projection_required": True,
        "remaining_count": len(after),
        "resolved_count": len(set(before) - set(after) - set(substitutions)),
        "authorized_identity_substitution_count": len(substitutions),
        "status": "NO_PACKET_MUTATION_REQUIRED",
        "authority_effect": "NONE_PACKET_PREPARATION_ONLY",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.base, args.head), indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"::error title=GRT DebtFloor preparation::{type(exc).__name__}:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
