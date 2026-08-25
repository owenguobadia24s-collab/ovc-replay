#!/usr/bin/env python3
"""Exact active GRT v0.2 integration admission.

The activation transaction is fail-closed: the exact activation predecessor and
candidate must both reproduce the operator-approved generation-0 finding set.
After G3, every candidate must carry the next immutable DebtFloor generation and
advance the current-floor pointer. GRT-EXACT validates that generation against
the exact base/candidate snapshots before SIQ/PDC may admit the integration.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Mapping

from ovc.programme_genesis.grt_v0_2.debt import compare_debt_extent, validate_debt_floor
from ovc.programme_genesis.grt_v0_2.g3_floor import full_g3_snapshot_at_commit
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256

ROOT = Path(__file__).resolve().parents[3]
APPROVED_FLOOR_PATH = "docs/programmes/grt-v0-2/g3/GRT2_G3_TERMINAL_SUPERSESSION_DECISION.json"
FLOOR_POINTER_PATH = "registries/governance/grt_v0_2/GRT_DEBT_FLOOR_CURRENT.json"
FLOOR_DIR = "registries/governance/grt_v0_2/debt_floors"
ACTIVE_AUTHORITY_PATH = "registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_2.json"
EXPECTED_FLOOR_HASH = "2c2152397e1ac5ace98b3363ca39c84f5d5a5dadbc6243e73cbd1fba15413c8b"
EXPECTED_CONSTITUTION_HASH = "cac9fc5f0e31db08c4c37153c92a214fcc482414421f34d74c594faec65a71b0"


def _run(*args: str, env: Mapping[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=None if env is None else {**os.environ, **env},
    )


def _commit(ref: str) -> str:
    cp = _run("rev-parse", f"{ref}^{{commit}}")
    if cp.returncode:
        raise ValueError("GRT_EXACT_COMMIT_UNRESOLVED:" + ref)
    value = cp.stdout.strip()
    if len(value) != 40:
        raise ValueError("GRT_EXACT_COMMIT_INVALID:" + ref)
    return value


def _tree(ref: str) -> str:
    cp = _run("rev-parse", f"{ref}^{{tree}}")
    if cp.returncode:
        raise ValueError("GRT_EXACT_TREE_UNRESOLVED:" + ref)
    value = cp.stdout.strip()
    if len(value) != 40:
        raise ValueError("GRT_EXACT_TREE_INVALID:" + ref)
    return value


def _text_at(commit: str, path: str) -> str | None:
    cp = _run("show", f"{commit}:{path}")
    return cp.stdout if cp.returncode == 0 else None


def _json_at(commit: str, path: str) -> Mapping[str, Any]:
    text = _text_at(commit, path)
    if text is None:
        raise ValueError("GRT_EXACT_REQUIRED_RECORD_MISSING:" + path)
    value = json.loads(text)
    if not isinstance(value, Mapping):
        raise ValueError("GRT_EXACT_REQUIRED_RECORD_NOT_OBJECT:" + path)
    return value


def _path_exists(commit: str, path: str) -> bool:
    return _run("cat-file", "-e", f"{commit}:{path}").returncode == 0


def _prospective_commit(base: str, head: str) -> tuple[str, str, str]:
    base = _commit(base)
    head = _commit(head)
    if _run("merge-base", "--is-ancestor", base, head).returncode == 0:
        return head, _tree(head), "HEAD_DESCENDS_FROM_BASE"
    merge = _run("merge-tree", "--write-tree", base, head)
    if merge.returncode != 0:
        detail = (merge.stdout + "\n" + merge.stderr)[-4000:]
        raise ValueError("GRT_EXACT_PROSPECTIVE_TREE_CONFLICT:" + detail)
    tree = merge.stdout.splitlines()[0].strip()
    if len(tree) != 40:
        raise ValueError("GRT_EXACT_PROSPECTIVE_TREE_INVALID")
    env = {
        "GIT_AUTHOR_NAME": "OVC GRT-EXACT",
        "GIT_AUTHOR_EMAIL": "grt-exact@invalid.local",
        "GIT_COMMITTER_NAME": "OVC GRT-EXACT",
        "GIT_COMMITTER_EMAIL": "grt-exact@invalid.local",
        "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
        "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
    }
    commit = _run(
        "commit-tree",
        tree,
        "-p",
        base,
        "-p",
        head,
        "-m",
        "GRT-EXACT prospective integration tree",
        env=env,
    )
    if commit.returncode != 0:
        raise ValueError("GRT_EXACT_PROSPECTIVE_COMMIT_FAILED:" + commit.stderr[-2000:])
    return commit.stdout.strip(), tree, "MERGE_TREE_PROSPECTIVE"


def _evaluability_errors(snapshot: Mapping[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    for item in snapshot.get("adapter_errors", []):
        errors.append(f"{label}:ADAPTER_ERROR:{item}")
    for item in snapshot.get("not_evaluable", []):
        errors.append(f"{label}:NOT_EVALUABLE:{item}")
    for family, status in sorted(snapshot.get("family_coverage", {}).items()):
        if status != "EVALUATED":
            errors.append(f"{label}:FAMILY_NOT_EVALUATED:{family}:{status}")
    return errors


def _findings(snapshot: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows: dict[str, Mapping[str, Any]] = {}
    for row in snapshot.get("findings", []):
        finding_id = str(row.get("finding_id", ""))
        if not finding_id or finding_id in rows:
            raise ValueError("GRT_EXACT_FINDING_ID_INVALID_OR_DUPLICATE:" + finding_id)
        rows[finding_id] = row
    return rows


def _floor_state(commit: str) -> Mapping[str, Any]:
    pointer = _json_at(commit, FLOOR_POINTER_PATH)
    generation = int(pointer.get("generation", -1))
    if generation < 0:
        raise ValueError("GRT_EXACT_FLOOR_POINTER_GENERATION_INVALID")
    if str(pointer.get("constitution_hash", "")) != EXPECTED_CONSTITUTION_HASH:
        raise ValueError("GRT_EXACT_FLOOR_POINTER_CONSTITUTION_MISMATCH")
    definition = str(pointer.get("definition", ""))
    expected = f"{FLOOR_DIR}/GRT_DEBT_FLOOR_G{generation}.json"
    if definition != expected:
        raise ValueError("GRT_EXACT_FLOOR_POINTER_PATH_INVALID")
    floor = _json_at(commit, definition)
    validate_debt_floor(floor)
    if floor.get("floor_hash") != pointer.get("floor_hash"):
        raise ValueError("GRT_EXACT_FLOOR_POINTER_HASH_MISMATCH")
    if int(floor.get("generation", -1)) != generation:
        raise ValueError("GRT_EXACT_FLOOR_POINTER_GENERATION_MISMATCH")
    if floor.get("constitution_hash") != EXPECTED_CONSTITUTION_HASH:
        raise ValueError("GRT_EXACT_FLOOR_CONSTITUTION_MISMATCH")
    return {"pointer": pointer, "floor": floor, "definition": definition}


def _activation_floor(candidate: str) -> Mapping[str, Any]:
    decision = _json_at(candidate, APPROVED_FLOOR_PATH)
    approved = dict(decision.get("proposed_replacement_generation_0_floor", {}))
    approved.pop("member_count", None)
    approved.pop("status", None)
    validate_debt_floor(approved)
    if approved.get("floor_hash") != EXPECTED_FLOOR_HASH:
        raise ValueError("GRT_EXACT_APPROVED_FLOOR_HASH_MISMATCH")
    current = _floor_state(candidate)
    if int(current["floor"]["generation"]) != 0:
        raise ValueError("GRT_EXACT_ACTIVATION_FLOOR_GENERATION_INVALID")
    if current["floor"] != approved:
        raise ValueError("GRT_EXACT_ACTIVATION_FLOOR_BYTES_NOT_APPROVED_GENERATION_0")
    return current


def evaluate(base_ref: str, head_ref: str) -> dict[str, Any]:
    base = _commit(base_ref)
    base_tree = _tree(base)
    candidate, candidate_tree, composition_mode = _prospective_commit(base, head_ref)

    base_snapshot = full_g3_snapshot_at_commit(ROOT, commit=base)
    candidate_snapshot = full_g3_snapshot_at_commit(ROOT, commit=candidate)
    errors = _evaluability_errors(base_snapshot, "BASE") + _evaluability_errors(candidate_snapshot, "CANDIDATE")
    base_findings = _findings(base_snapshot)
    candidate_findings = _findings(candidate_snapshot)
    base_ids = set(base_findings)
    candidate_ids = set(candidate_findings)

    activation_mode = not _path_exists(base, ACTIVE_AUTHORITY_PATH)
    if activation_mode:
        if not _path_exists(candidate, ACTIVE_AUTHORITY_PATH):
            errors.append("GRT_EXACT_ACTIVATION_AUTHORITY_RECORD_MISSING")
        try:
            floor_state = _activation_floor(candidate)
            floor = floor_state["floor"]
            approved_ids = set(floor["open_grandfathered_findings"])
            if base_ids != approved_ids:
                missing = sorted(approved_ids - base_ids)
                added = sorted(base_ids - approved_ids)
                errors.append(
                    "GRT_EXACT_ACTIVATION_PREDECESSOR_FLOOR_MISMATCH:"
                    f"missing={len(missing)}:added={len(added)}:"
                    f"missing_sample={missing[:10]}:added_sample={added[:10]}"
                )
            if candidate_ids != approved_ids:
                missing = sorted(approved_ids - candidate_ids)
                added = sorted(candidate_ids - approved_ids)
                errors.append(
                    "GRT_EXACT_ACTIVATION_CANDIDATE_FLOOR_MISMATCH:"
                    f"missing={len(missing)}:added={len(added)}:"
                    f"missing_sample={missing[:10]}:added_sample={added[:10]}"
                )
        except Exception as exc:
            errors.append(f"GRT_EXACT_ACTIVATION_FLOOR_INVALID:{type(exc).__name__}:{exc}")
        current_floor_generation = None
        candidate_floor_generation = 0
        floor_hash = EXPECTED_FLOOR_HASH
    else:
        try:
            base_floor_state = _floor_state(base)
            candidate_floor_state = _floor_state(candidate)
            base_floor = base_floor_state["floor"]
            candidate_floor = candidate_floor_state["floor"]
            current_floor_generation = int(base_floor["generation"])
            candidate_floor_generation = int(candidate_floor["generation"])
            floor_hash = str(base_floor["floor_hash"])
            if set(base_floor["open_grandfathered_findings"]) != base_ids:
                errors.append("GRT_EXACT_BASE_DEBT_FLOOR_DOES_NOT_EQUAL_BASE_FINDINGS")
            if candidate_floor_generation != current_floor_generation + 1:
                errors.append("GRT_EXACT_CANDIDATE_FLOOR_GENERATION_NOT_NEXT")
            if candidate_floor.get("predecessor_commit") != base or candidate_floor.get("predecessor_tree") != base_tree:
                errors.append("GRT_EXACT_CANDIDATE_FLOOR_PREDECESSOR_MISMATCH")
            if set(candidate_floor["open_grandfathered_findings"]) != candidate_ids:
                errors.append("GRT_EXACT_CANDIDATE_FLOOR_DOES_NOT_EQUAL_CANDIDATE_FINDINGS")
            if not candidate_ids.issubset(set(base_floor["open_grandfathered_findings"])):
                errors.append("GRT_EXACT_CANDIDATE_FLOOR_GRANDFATHERED_SET_GREW")
        except Exception as exc:
            errors.append(f"GRT_EXACT_FLOOR_CHAIN_INVALID:{type(exc).__name__}:{exc}")
            current_floor_generation = None
            candidate_floor_generation = None
            floor_hash = None

    new_or_recurrent = sorted(candidate_ids - base_ids)
    if new_or_recurrent:
        errors.append(
            f"GRT_EXACT_NEW_OR_RECURRENT_ACTIONABLE:count={len(new_or_recurrent)}:"
            f"sample={new_or_recurrent[:10]}"
        )

    extent_dispositions = {"UNCHANGED": 0, "REDUCED": 0, "EXPANDED": 0, "MATERIAL_CHANGED": 0}
    expansion_ids: list[str] = []
    material_ids: list[str] = []
    for finding_id in sorted(base_ids & candidate_ids):
        previous = base_findings[finding_id].get("debt_extent")
        current = candidate_findings[finding_id].get("debt_extent")
        if not isinstance(previous, Mapping) or not isinstance(current, Mapping):
            errors.append(f"GRT_EXACT_DEBT_EXTENT_MISSING:{finding_id}")
            continue
        disposition = compare_debt_extent(previous, current)
        extent_dispositions[disposition] += 1
        if disposition == "EXPANDED":
            expansion_ids.append(finding_id)
        elif disposition == "MATERIAL_CHANGED":
            material_ids.append(finding_id)
    if expansion_ids:
        errors.append(f"GRT_EXACT_BASELINE_EXPANDED:count={len(expansion_ids)}:sample={expansion_ids[:10]}")
    if material_ids:
        errors.append(f"GRT_EXACT_BASELINE_MATERIAL_CHANGED:count={len(material_ids)}:sample={material_ids[:10]}")

    result = {
        "schema": "ovc-grt-exact-proof/v1",
        "profile": "GRT-EXACT",
        "constitution_hash": EXPECTED_CONSTITUTION_HASH,
        "activation_mode": activation_mode,
        "base_commit": base,
        "base_tree": base_tree,
        "head_commit": _commit(head_ref),
        "candidate_commit": candidate,
        "candidate_tree": candidate_tree,
        "composition_mode": composition_mode,
        "floor_hash": floor_hash,
        "current_floor_generation": current_floor_generation,
        "candidate_floor_generation": candidate_floor_generation,
        "base_actionable_count": len(base_ids),
        "candidate_actionable_count": len(candidate_ids),
        "resolved_count": len(base_ids - candidate_ids),
        "new_or_recurrent_count": len(new_or_recurrent),
        "extent_dispositions": extent_dispositions,
        "base_snapshot_hash": base_snapshot.get("snapshot_hash"),
        "candidate_snapshot_hash": candidate_snapshot.get("snapshot_hash"),
        "errors": errors,
        "result": "PASS" if not errors else "FAIL",
        "authority_effect": "INTEGRATION_ADMISSION_PROOF_ONLY",
    }
    result["logical_sha256"] = canonical_sha256(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", default="artifacts/grt2-g3/grt-exact.json")
    args = parser.parse_args()
    try:
        result = evaluate(args.base, args.head)
    except Exception as exc:
        result = {
            "schema": "ovc-grt-exact-proof/v1",
            "profile": "GRT-EXACT",
            "base_ref": args.base,
            "head_ref": args.head,
            "result": "FAIL",
            "errors": [f"{type(exc).__name__}:{exc}"],
            "authority_effect": "INTEGRATION_ADMISSION_PROOF_ONLY",
        }
        result["logical_sha256"] = canonical_sha256(result)
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
