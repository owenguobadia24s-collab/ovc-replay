from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.debt import (
    B0_MEMBER_COUNT,
    B0_MEMBERSHIP_SHA256,
    compare_debt_extent,
)
from ovc.programme_genesis.grt_v0_2.g3_floor import full_g3_snapshot_at_commit


ROOT = Path(__file__).resolve().parents[3]
OLD_FLOOR = ROOT / "docs/programmes/grt-v0-2/g3/GRT2_G3_PROPOSED_DEBT_FLOOR_GENERATION_0.json"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def _finding_map(snapshot: dict) -> dict[str, dict]:
    return {str(row["finding_id"]): row for row in snapshot.get("findings", [])}


def _evaluation_index(snapshot: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in snapshot.get("evaluations", []):
        value = row.get("canonical_hash")
        if isinstance(value, str):
            out[value] = row
    return out


def _detail(finding: dict, eval_index: dict[str, dict]) -> dict:
    hashes = [
        str(value)
        for key in ("applicability_evidence", "violation_evidence")
        for value in finding.get(key, [])
    ]
    evaluations = [eval_index[value] for value in hashes if value in eval_index]
    evidence_refs = sorted({
        str(ref)
        for row in evaluations
        for ref in row.get("evidence_refs", [])
        if str(ref)
    })
    return {
        "finding_id": finding.get("finding_id"),
        "rule_id": finding.get("rule_id"),
        "subject_artifact_id": finding.get("subject_artifact_id"),
        "relation_role": finding.get("relation_role"),
        "debt_extent": finding.get("debt_extent"),
        "evidence_refs": evidence_refs,
    }


def test_emit_superseding_g3_current_main_delta() -> None:
    current_main = _git("rev-parse", "origin/main^{commit}")
    current_tree = _git("rev-parse", f"{current_main}^{{tree}}")
    floor = json.loads(OLD_FLOOR.read_text(encoding="utf-8"))
    old_commit = str(floor["predecessor_commit"])
    old_tree = str(floor["predecessor_tree"])

    old_snapshot = full_g3_snapshot_at_commit(ROOT, commit=old_commit)
    current_snapshot = full_g3_snapshot_at_commit(ROOT, commit=current_main)
    old_findings = _finding_map(old_snapshot)
    current_findings = _finding_map(current_snapshot)
    old_ids = set(old_findings)
    current_ids = set(current_findings)
    old_evals = _evaluation_index(old_snapshot)
    current_evals = _evaluation_index(current_snapshot)

    resolved = sorted(old_ids - current_ids)
    added = sorted(current_ids - old_ids)
    expanded: list[dict] = []
    material_changed: list[dict] = []
    reduced: list[str] = []
    for finding_id in sorted(old_ids & current_ids):
        disposition = compare_debt_extent(
            old_findings[finding_id]["debt_extent"],
            current_findings[finding_id]["debt_extent"],
        )
        if disposition == "EXPANDED":
            expanded.append({
                "finding_id": finding_id,
                "old": old_findings[finding_id]["debt_extent"],
                "current": current_findings[finding_id]["debt_extent"],
            })
        elif disposition == "MATERIAL_CHANGED":
            material_changed.append({
                "finding_id": finding_id,
                "old": old_findings[finding_id]["debt_extent"],
                "current": current_findings[finding_id]["debt_extent"],
            })
        elif disposition == "REDUCED":
            reduced.append(finding_id)

    payload = {
        "schema": "ovc-grt2-g3-superseding-readiness-diagnostic/v1",
        "authority_effect": "NONE_DIAGNOSTIC_ONLY",
        "old_floor": {
            "generation": floor["generation"],
            "count": len(floor["open_grandfathered_findings"]),
            "floor_hash": floor["floor_hash"],
            "predecessor_commit": old_commit,
            "predecessor_tree": old_tree,
        },
        "current_main": current_main,
        "current_tree": current_tree,
        "old_snapshot": {
            "finding_count": len(old_ids),
            "snapshot_hash": old_snapshot.get("snapshot_hash"),
            "adapter_errors": old_snapshot.get("adapter_errors", []),
            "not_evaluable": old_snapshot.get("not_evaluable", []),
            "family_coverage": old_snapshot.get("family_coverage", {}),
        },
        "current_snapshot": {
            "finding_count": len(current_ids),
            "snapshot_hash": current_snapshot.get("snapshot_hash"),
            "adapter_errors": current_snapshot.get("adapter_errors", []),
            "not_evaluable": current_snapshot.get("not_evaluable", []),
            "family_coverage": current_snapshot.get("family_coverage", {}),
            "full_tree_component_count": current_snapshot.get("full_tree_component_count"),
            "full_tree_text_component_count": current_snapshot.get("full_tree_text_component_count"),
        },
        "b0_expected": {
            "member_count": B0_MEMBER_COUNT,
            "membership_sha256": B0_MEMBERSHIP_SHA256,
        },
        "delta": {
            "resolved_count": len(resolved),
            "added_count": len(added),
            "reduced_count": len(reduced),
            "expanded_count": len(expanded),
            "material_changed_count": len(material_changed),
            "resolved": [_detail(old_findings[value], old_evals) for value in resolved],
            "added": [_detail(current_findings[value], current_evals) for value in added],
            "reduced_ids": reduced,
            "expanded": expanded,
            "material_changed": material_changed,
        },
    }
    raise AssertionError(
        "GRT2_G3_SUPERSEDING_DIAGNOSTIC_JSON="
        + json.dumps(payload, sort_keys=True, separators=(",", ":"))
    )
