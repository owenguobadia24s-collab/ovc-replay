#!/usr/bin/env python3
"""Active GRT-EXACT adapter for VIT-owned DebtFloor materialisation.

This wrapper preserves the qualified legacy GRT-EXACT comparison engine while
supplying its floor states as deterministic exact-tree projections. Ordinary
packet trees never carry the mutable GRT floor pointer or next-generation file.

The physical base floor is reconstructed from the immutable G2 anchor through
every first-parent main generation carrying the exact pinned policy. This makes
an unexplained or bypassed physical commit fail closed rather than silently
turning its findings into newly grandfathered debt.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from ovc.programme_genesis.grt_v0_2.debt import (
    G4_CANDIDATE_FINDING_ID,
    G4_GRANDFATHERED_FINDING_ID,
    compare_debt_extent,
)
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256
from scripts.governance.grt_v0_2 import grt_exact as legacy
from scripts.governance.grt_v0_2.integration_floor import (
    POLICY_ID,
    POLICY_PATH,
    assert_no_packet_floor_mutation,
    build_floor,
    policy_anchor,
    validate_policy,
)

ROOT = Path(__file__).resolve().parents[3]


def _policy_at(commit: str) -> Mapping[str, Any] | None:
    if not legacy._path_exists(commit, POLICY_PATH):
        return None
    policy = legacy._json_at(commit, POLICY_PATH)
    validate_policy(policy)
    return policy


def _first_parent(commit: str) -> str:
    cp = legacy._run("rev-list", "--parents", "-n", "1", commit)
    if cp.returncode:
        raise ValueError("GRT_EXACT_VIRTUAL_FIRST_PARENT_UNRESOLVED")
    parts = cp.stdout.strip().split()
    if len(parts) < 2:
        raise ValueError("GRT_EXACT_VIRTUAL_FIRST_PARENT_MISSING")
    return legacy._commit(parts[1])


def _assert_legacy_anchor(
    commit: str,
    policy: Mapping[str, Any],
    floor_state_loader=legacy._floor_state,
) -> Mapping[str, Any]:
    # Bind the original legacy loader as a default argument. During evaluation
    # legacy._floor_state is temporarily replaced by virtual_floor_state; using
    # a dynamic lookup here would recurse instead of reading the immutable G2
    # migration anchor.
    state = floor_state_loader(commit)
    anchor = policy_anchor(policy)
    floor = state["floor"]
    if int(floor.get("generation", -1)) != int(anchor["generation"]):
        raise ValueError("GRT_EXACT_VIRTUAL_ANCHOR_GENERATION_MISMATCH")
    if floor.get("floor_hash") != anchor.get("floor_hash"):
        raise ValueError("GRT_EXACT_VIRTUAL_ANCHOR_HASH_MISMATCH")
    if state.get("definition") != anchor.get("definition"):
        raise ValueError("GRT_EXACT_VIRTUAL_ANCHOR_DEFINITION_MISMATCH")
    if floor.get("constitution_hash") != anchor.get("constitution_hash"):
        raise ValueError("GRT_EXACT_VIRTUAL_ANCHOR_CONSTITUTION_MISMATCH")
    return state


def _findings_at(commit: str, label: str) -> dict[str, Mapping[str, Any]]:
    snapshot = legacy.full_g3_snapshot_at_commit(ROOT, commit=commit)
    errors = legacy._evaluability_errors(snapshot, label)
    if errors:
        raise ValueError("GRT_EXACT_VIRTUAL_HISTORY_NOT_EVALUABLE:" + "|".join(errors[:20]))
    return legacy._findings(snapshot)


def _assert_nonexpanding_transition(
    before: Mapping[str, Mapping[str, Any]],
    after: Mapping[str, Mapping[str, Any]],
    *,
    label: str,
) -> None:
    new_ids = sorted(set(after) - set(before))
    if new_ids:
        raise ValueError(
            f"GRT_EXACT_VIRTUAL_HISTORY_NEW_OR_RECURRENT:{label}:"
            f"count={len(new_ids)}:sample={new_ids[:10]}"
        )
    expanded: list[str] = []
    material: list[str] = []
    for finding_id in sorted(set(before) & set(after)):
        previous = before[finding_id].get("debt_extent")
        current = after[finding_id].get("debt_extent")
        if not isinstance(previous, Mapping) or not isinstance(current, Mapping):
            raise ValueError(
                f"GRT_EXACT_VIRTUAL_HISTORY_DEBT_EXTENT_MISSING:{label}:{finding_id}"
            )
        disposition = compare_debt_extent(previous, current)
        if disposition == "EXPANDED":
            expanded.append(finding_id)
        elif disposition == "MATERIAL_CHANGED":
            material.append(finding_id)
    if expanded:
        raise ValueError(
            f"GRT_EXACT_VIRTUAL_HISTORY_EXPANDED:{label}:"
            f"count={len(expanded)}:sample={expanded[:10]}"
        )
    if material:
        raise ValueError(
            f"GRT_EXACT_VIRTUAL_HISTORY_MATERIAL_CHANGED:{label}:"
            f"count={len(material)}:sample={material[:10]}"
        )


def _reconstruct_physical_floor(
    commit: str,
    policy: Mapping[str, Any],
) -> tuple[Mapping[str, Any], int]:
    """Reproduce the exact virtual floor chain from G2 to one physical commit."""
    current = legacy._commit(commit)
    reverse_commits: list[str] = []
    while True:
        current_policy = _policy_at(current)
        if current_policy is None:
            raise ValueError("GRT_EXACT_VIRTUAL_POLICY_HISTORY_GAP")
        if current_policy.get("logical_sha256") != policy.get("logical_sha256"):
            raise ValueError("GRT_EXACT_VIRTUAL_POLICY_HISTORY_CHANGED")
        reverse_commits.append(current)
        parent = _first_parent(current)
        parent_policy = _policy_at(parent)
        if parent_policy is None:
            anchor_commit = parent
            break
        current = parent

    anchor_state = _assert_legacy_anchor(anchor_commit, policy)
    anchor_floor = anchor_state["floor"]
    previous_findings = _findings_at(anchor_commit, "VIRTUAL_ANCHOR")
    if set(anchor_floor.get("open_grandfathered_findings", [])) != set(previous_findings):
        raise ValueError("GRT_EXACT_VIRTUAL_ANCHOR_FINDING_SET_MISMATCH")

    previous_commit = anchor_commit
    generation = int(anchor_floor["generation"])
    floor: Mapping[str, Any] = anchor_floor
    ordered_commits = list(reversed(reverse_commits))
    for current_commit in ordered_commits:
        current_findings = _findings_at(
            current_commit,
            f"VIRTUAL_PHYSICAL_GENERATION_{generation + 1}",
        )
        _assert_nonexpanding_transition(
            previous_findings,
            current_findings,
            label=f"{previous_commit}->{current_commit}",
        )
        generation += 1
        floor = build_floor(
            policy=policy,
            generation=generation,
            predecessor_commit=previous_commit,
            predecessor_tree=legacy._tree(previous_commit),
            result_tree=legacy._tree(current_commit),
            open_grandfathered_findings=current_findings,
        )
        previous_commit = current_commit
        previous_findings = current_findings

    return {
        "pointer": {
            "generation": generation,
            "floor_hash": floor["floor_hash"],
            "constitution_hash": floor["constitution_hash"],
            "definition": "VIRTUAL_EXACT_TREE_PROJECTION",
        },
        "floor": floor,
        "definition": "VIRTUAL_EXACT_TREE_PROJECTION",
    }, len(ordered_commits)


def _exact_g4_transition(
    before: Mapping[str, Mapping[str, Any]],
    after: Mapping[str, Mapping[str, Any]],
) -> bool:
    return (
        G4_GRANDFATHERED_FINDING_ID in before
        and G4_GRANDFATHERED_FINDING_ID not in after
        and G4_CANDIDATE_FINDING_ID not in before
        and G4_CANDIDATE_FINDING_ID in after
    )


def evaluate(base_ref: str, head_ref: str) -> dict[str, Any]:
    base = legacy._commit(base_ref)
    base_tree = legacy._tree(base)
    candidate, candidate_tree, _ = legacy._prospective_commit(base, head_ref)
    policy = _policy_at(candidate)
    if policy is None:
        return legacy.evaluate(base_ref, head_ref)

    changed_paths = legacy._run("diff", "--name-only", base, candidate)
    if changed_paths.returncode:
        raise ValueError("GRT_EXACT_VIRTUAL_CHANGED_PATHS_UNRESOLVED")
    assert_no_packet_floor_mutation(changed_paths.stdout.splitlines())

    base_policy = _policy_at(base)
    if base_policy is not None and base_policy.get("logical_sha256") != policy.get("logical_sha256"):
        raise ValueError("GRT_EXACT_VIRTUAL_POLICY_CHANGED")

    if base_policy is None:
        base_floor_state = _assert_legacy_anchor(base, policy)
        anchor_findings = _findings_at(base, "VIRTUAL_MIGRATION_ANCHOR")
        if set(base_floor_state["floor"].get("open_grandfathered_findings", [])) != set(anchor_findings):
            raise ValueError("GRT_EXACT_VIRTUAL_MIGRATION_ANCHOR_FINDING_SET_MISMATCH")
        history_replay_count = 0
    else:
        base_floor_state, history_replay_count = _reconstruct_physical_floor(base, base_policy)

    real_floor_state = legacy._floor_state
    real_findings = legacy._findings
    real_g4_validator = legacy.validate_g4_current_projection_substitution
    captured: dict[str, dict[str, Mapping[str, Any]]] = {}
    projected: dict[str, Mapping[str, Any]] = {"base": base_floor_state["floor"]}

    def capture_findings(snapshot: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
        rows = real_findings(snapshot)
        commit = str(snapshot.get("commit", ""))
        if commit:
            captured[commit] = rows
        return rows

    def guarded_g4(
        decision: Mapping[str, Any],
        before: Mapping[str, Mapping[str, Any]],
        after: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, str]:
        if _exact_g4_transition(before, after):
            return real_g4_validator(decision, before, after)
        return {}

    def virtual_floor_state(commit: str) -> Mapping[str, Any]:
        commit = legacy._commit(commit)
        if commit == base:
            return base_floor_state
        if commit == candidate:
            generation = int(projected["base"]["generation"]) + 1
            floor = build_floor(
                policy=policy,
                generation=generation,
                predecessor_commit=base,
                predecessor_tree=base_tree,
                result_tree=candidate_tree,
                open_grandfathered_findings=captured[candidate],
            )
            projected["candidate"] = floor
            return {
                "pointer": {
                    "generation": generation,
                    "floor_hash": floor["floor_hash"],
                    "constitution_hash": floor["constitution_hash"],
                    "definition": "VIRTUAL_EXACT_TREE_PROJECTION",
                },
                "floor": floor,
                "definition": "VIRTUAL_EXACT_TREE_PROJECTION",
            }
        return real_floor_state(commit)

    legacy._findings = capture_findings
    legacy._floor_state = virtual_floor_state
    legacy.validate_g4_current_projection_substitution = guarded_g4
    try:
        result = legacy.evaluate(base_ref, head_ref)
    finally:
        legacy._findings = real_findings
        legacy._floor_state = real_floor_state
        legacy.validate_g4_current_projection_substitution = real_g4_validator

    result["floor_materialisation_mode"] = "VIRTUAL_EXACT_TREE_PROJECTION"
    result["floor_policy_id"] = POLICY_ID
    result["base_floor_hash"] = projected["base"].get("floor_hash")
    result["candidate_floor"] = dict(projected.get("candidate", {}))
    result["candidate_floor_hash"] = projected.get("candidate", {}).get("floor_hash")
    result["physical_floor_history_replay_count"] = history_replay_count
    result["packet_floor_control_mutation_count"] = 0
    result["packet_floor_control_mutations"] = []
    result["logical_sha256"] = canonical_sha256(
        {key: value for key, value in result.items() if key != "logical_sha256"}
    )
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
