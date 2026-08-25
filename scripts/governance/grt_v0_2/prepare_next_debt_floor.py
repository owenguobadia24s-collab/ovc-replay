#!/usr/bin/env python3
"""Prepare the next immutable DebtFloor generation for an active-GRT packet.

This helper is deterministic and non-authoritative. It reads the exact base and
candidate trees, proves the candidate contains no new/recurrent/expanded debt,
then writes the next floor generation and current-floor pointer into the working
tree. It never commits, pushes, merges or grants authority.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

from ovc.programme_genesis.grt_v0_2.debt import (
    compare_debt_extent,
    propose_debt_floor,
    validate_debt_floor,
    validate_g4_current_projection_substitution,
)
from ovc.programme_genesis.grt_v0_2.g3_floor import full_g3_snapshot_at_commit
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256

ROOT = Path(__file__).resolve().parents[3]
POINTER = ROOT / "registries/governance/grt_v0_2/GRT_DEBT_FLOOR_CURRENT.json"
FLOOR_DIR = ROOT / "registries/governance/grt_v0_2/debt_floors"
G4_DECISION_PATH = "docs/programmes/grt-v0-2/g4/GRT2_G4_OPERATOR_DECISION.json"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"GRT_FLOOR_PREP_RECORD_NOT_OBJECT:{path}")
    return value


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
    out: dict[str, Mapping[str, Any]] = {}
    for row in snapshot.get("findings", []):
        finding_id = str(row.get("finding_id", ""))
        if not finding_id or finding_id in out:
            raise ValueError("GRT_FLOOR_PREP_FINDING_ID_INVALID_OR_DUPLICATE")
        out[finding_id] = row
    return out


def _assert_evaluable(snapshot: Mapping[str, Any], label: str) -> None:
    if snapshot.get("adapter_errors") or snapshot.get("not_evaluable"):
        raise ValueError(f"GRT_FLOOR_PREP_{label}_NOT_EVALUABLE")
    if any(value != "EVALUATED" for value in snapshot.get("family_coverage", {}).values()):
        raise ValueError(f"GRT_FLOOR_PREP_{label}_FAMILY_COVERAGE_GAP")


def prepare(base_ref: str, head_ref: str) -> dict[str, Any]:
    base = _git("rev-parse", f"{base_ref}^{{commit}}")
    head = _git("rev-parse", f"{head_ref}^{{commit}}")
    base_tree = _git("rev-parse", f"{base}^{{tree}}")

    pointer = _load(POINTER)
    generation = int(pointer.get("generation", -1))
    if generation < 0:
        raise ValueError("GRT_FLOOR_PREP_CURRENT_GENERATION_INVALID")
    current_path = ROOT / str(pointer.get("definition", ""))
    current_floor = _load(current_path)
    validate_debt_floor(current_floor)
    if int(current_floor.get("generation", -1)) != generation:
        raise ValueError("GRT_FLOOR_PREP_POINTER_GENERATION_MISMATCH")
    if current_floor.get("floor_hash") != pointer.get("floor_hash"):
        raise ValueError("GRT_FLOOR_PREP_POINTER_HASH_MISMATCH")

    before_snapshot = full_g3_snapshot_at_commit(ROOT, commit=base)
    after_snapshot = full_g3_snapshot_at_commit(ROOT, commit=head)
    _assert_evaluable(before_snapshot, "BASE")
    _assert_evaluable(after_snapshot, "HEAD")
    before = _findings(before_snapshot)
    after = _findings(after_snapshot)
    before_ids = set(before)
    after_ids = set(after)
    floor_ids = set(current_floor.get("open_grandfathered_findings", []))
    if before_ids != floor_ids:
        raise ValueError("GRT_FLOOR_PREP_BASE_FINDINGS_DO_NOT_MATCH_CURRENT_FLOOR")
    authorized_substitutions: dict[str, str] = {}
    decision = _json_at(head, G4_DECISION_PATH)
    if decision is not None:
        authorized_substitutions = validate_g4_current_projection_substitution(
            decision,
            before,
            after,
        )
    authorized_removed = set(authorized_substitutions)
    authorized_added = set(authorized_substitutions.values())
    new_ids = sorted(after_ids - before_ids - authorized_added)
    if new_ids:
        raise ValueError(f"GRT_FLOOR_PREP_NEW_OR_RECURRENT_DEBT:{new_ids[:10]}")

    expanded: list[str] = []
    material: list[str] = []
    for finding_id in sorted(before_ids & after_ids):
        previous = before[finding_id].get("debt_extent")
        current = after[finding_id].get("debt_extent")
        if not isinstance(previous, Mapping) or not isinstance(current, Mapping):
            raise ValueError(f"GRT_FLOOR_PREP_DEBT_EXTENT_MISSING:{finding_id}")
        disposition = compare_debt_extent(previous, current)
        if disposition == "EXPANDED":
            expanded.append(finding_id)
        elif disposition == "MATERIAL_CHANGED":
            material.append(finding_id)
    if expanded:
        raise ValueError(f"GRT_FLOOR_PREP_EXPANDED_DEBT:{expanded[:10]}")
    if material:
        raise ValueError(f"GRT_FLOOR_PREP_MATERIAL_CHANGED_DEBT:{material[:10]}")

    next_generation = generation + 1
    next_floor = propose_debt_floor(
        generation=next_generation,
        predecessor_commit=base,
        predecessor_tree=base_tree,
        constitution_hash=str(current_floor["constitution_hash"]),
        open_grandfathered_findings=sorted(after_ids),
        previous_floor=current_floor,
        authorized_identity_substitutions=authorized_substitutions,
    )
    validate_debt_floor(next_floor)
    FLOOR_DIR.mkdir(parents=True, exist_ok=True)
    floor_rel = f"registries/governance/grt_v0_2/debt_floors/GRT_DEBT_FLOOR_G{next_generation}.json"
    floor_path = ROOT / floor_rel
    floor_path.write_text(json.dumps(next_floor, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    pointer_payload = {
        "schema": "ovc-grt2-debt-floor-current-pointer/v1",
        "programme_id": "OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE",
        "status": "CANDIDATE_NEXT_GENERATION",
        "generation": next_generation,
        "floor_hash": next_floor["floor_hash"],
        "definition": floor_rel,
        "constitution_hash": next_floor["constitution_hash"],
        "predecessor_generation": generation,
        "predecessor_floor_hash": current_floor["floor_hash"],
        "authority_effect": "NONE_PACKET_PREPARATION_ONLY",
    }
    pointer_payload["logical_sha256"] = canonical_sha256(pointer_payload)
    POINTER.write_text(json.dumps(pointer_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "schema": "ovc-grt2-debt-floor-preparation-receipt/v1",
        "base_commit": base,
        "head_commit": head,
        "predecessor_generation": generation,
        "next_generation": next_generation,
        "next_floor_hash": next_floor["floor_hash"],
        "next_floor_path": floor_rel,
        "resolved_count": len(before_ids - after_ids - authorized_removed),
        "remaining_count": len(after_ids),
        "authorized_identity_substitution_count": len(authorized_substitutions),
        "authority_effect": "NONE_PACKET_PREPARATION_ONLY",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    try:
        receipt = prepare(args.base, args.head)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"::error title=GRT DebtFloor preparation::{type(exc).__name__}:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
