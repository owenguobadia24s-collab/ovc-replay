"""Source-bound GRT2-G3 generation-0 DebtFloor preparation helpers.

This module is non-enforcing.  It reads an exact Git tree, evaluates the already
qualified full-G3 constitutional adapter across the complete governed tree, and
prepares a candidate floor only when every required fact is evaluable and B0
lineage can be resolved without inference.
"""
from __future__ import annotations

import io
import json
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from . import full_enforcement as fe
from . import full_enforcement_bounded as feb
from .debt import B0_MEMBER_COUNT, B0_MEMBERSHIP_SHA256, baseline_membership_sha256, propose_debt_floor, validate_baseline_members, validate_debt_floor
from .g3_readiness import anomaly_subject_key, anomaly_subject_projection, baseline_topology_from_member_records
from .serialization import canonical_sha256

_TEXT_SUFFIXES = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".cfg", ".ini", ".csv"}


def _archive_texts(root: Path, commit: str, known_paths: set[str]) -> dict[str, str]:
    cp = subprocess.run(["git", "-C", str(root), "archive", "--format=tar", commit], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cp.returncode != 0:
        raise ValueError("GRT2_G3_ARCHIVE_READ_FAILED:" + cp.stderr.decode("utf-8", "replace")[-1000:])
    texts: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(cp.stdout), mode="r:") as archive:
        for member in archive.getmembers():
            path = member.name.rstrip("/")
            if not member.isfile() or path not in known_paths or PurePosixPath(path).suffix.lower() not in _TEXT_SUFFIXES:
                continue
            stream = archive.extractfile(member)
            if stream is None:
                continue
            texts[path] = stream.read().decode("utf-8", "replace")
    return texts


def full_g3_snapshot_at_commit(repository_root: Path | str, *, commit: str) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    commit_id = fe._commit(root, commit)
    tree = fe._tree(root, commit_id)
    inventory = fe._inventory(root, commit_id)
    known = set(inventory)
    texts = _archive_texts(root, commit_id, known)
    referrers: dict[str, set[str]] = {}
    for source_path, text in texts.items():
        for target in fe._path_refs(text, known):
            referrers.setdefault(target, set()).add(source_path)
    current_targets, status_targets, pointer_violations = feb._pointer_catalog(
        inventory=inventory,
        texts=texts,
    )
    programme_status_errors: list[str] = []
    for target in current_targets:
        if target not in texts:
            text = fe._show(root, commit_id, target)
            if text is None:
                programme_status_errors.append(f"CURRENT_STATE_TARGET_UNREADABLE:{target}")
            else:
                texts[target] = text
    b0_valid, b0_errors = fe._b0_valid(root, commit_id)
    rules = fe._json(root, commit_id, fe.RULE_BUNDLE_PATH)
    snapshot = fe.build_source_bound_snapshot(
        commit=commit_id,
        tree=tree,
        inventory=inventory,
        texts=texts,
        impact_paths=sorted(known),
        referrers={key: sorted(value) for key, value in referrers.items()},
        current_targets=current_targets | status_targets,
        pointer_errors=programme_status_errors,
        rule_bundle=rules,
        root_registry=fe._json(root, commit_id, fe.ROOT_REGISTRY_PATH),
        pgn_state=fe._json(root, commit_id, fe.PGN_STATE_PATH),
        workflow_policy=fe._json(root, commit_id, fe.WORKFLOW_POLICY_PATH),
        b0_valid=b0_valid,
        b0_errors=b0_errors,
        exact_diff_new_writes=(),
        rule_bundle_changed=False,
    )
    feb._apply_pointer_violations(snapshot, violations=pointer_violations, rule_bundle=rules)
    snapshot["full_tree_component_count"] = len(inventory)
    snapshot["full_tree_text_component_count"] = len(texts)
    snapshot["snapshot_hash"] = canonical_sha256(snapshot)
    return snapshot


def _stable_ref(value: Any) -> str:
    text = str(value)
    if text.startswith("git:"):
        body = text[4:]
        if "@" in body:
            body = body.rsplit("@", 1)[0]
        return "git:" + body
    if text.startswith("git-tree:"):
        return text
    return text


def _member_refs(row: Mapping[str, Any]) -> set[str]:
    try:
        locator = json.loads(str(row["original_subject_locator"]))
    except Exception:
        return set()
    return {_stable_ref(value) for value in locator.get("source_evidence", [])}


def _evidence_refs(row: Mapping[str, Any]) -> set[str]:
    return {_stable_ref(value) for value in row.get("evidence_refs", [])}


def reconcile_b0_to_current_full_g3(
    *,
    b0_rows: Sequence[Mapping[str, Any]],
    current_topology: Mapping[str, Any],
    full_snapshot: Mapping[str, Any],
    transition_reconciliation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    validate_baseline_members(b0_rows)
    if len(b0_rows) != B0_MEMBER_COUNT or baseline_membership_sha256(b0_rows) != B0_MEMBERSHIP_SHA256:
        raise ValueError("GRT2_G3_B0_INTEGRITY_MISMATCH")
    baseline_topology = baseline_topology_from_member_records(b0_rows)
    current_by_key = {
        anomaly_subject_key(row, current_topology): row
        for row in current_topology.get("anomalies", [])
    }
    finding_rows = list(full_snapshot.get("findings", []))
    condition_rows = list((transition_reconciliation or {}).get("current_condition_classifications", []))
    conditions_by_key = {str(row["subject_key"]): row for row in condition_rows}
    entries: list[dict[str, Any]] = []
    unresolved: list[str] = []
    mapped_findings: set[str] = set()
    for row in sorted(b0_rows, key=lambda item: int(item["ordinal"])):
        member_id = str(row["baseline_member_id"])
        baseline_anomaly = next((item for item in baseline_topology["anomalies"] if item.get("baseline_member_id") == member_id), None)
        if baseline_anomaly is None:
            unresolved.append(member_id)
            entries.append({"baseline_member_id": member_id, "status": "UNRESOLVED", "reason": "BASELINE_ANOMALY_PROJECTION_MISSING"})
            continue
        subject_key = anomaly_subject_key(baseline_anomaly, baseline_topology)
        if subject_key not in current_by_key:
            entries.append({"baseline_member_id": member_id, "status": "RESOLVED_OBSERVER_CONDITION", "mapped_finding_ids": []})
            continue
        classification = conditions_by_key.get(subject_key)
        if classification is None:
            unresolved.append(member_id)
            entries.append({"baseline_member_id": member_id, "status": "UNRESOLVED", "mapped_finding_ids": [], "reason": "CURRENT_CONDITION_CLASSIFICATION_MISSING"})
            continue
        status = str(classification.get("classification", ""))
        matches = sorted(str(value) for value in classification.get("mapped_finding_ids", []))
        if status == "B0_MAPPED_CURRENT_ACTIONABLE" and matches:
            mapped_findings.update(matches)
            entries.append({"baseline_member_id": member_id, "status": "MAPPED_CURRENT_ACTIONABLE", "mapped_finding_ids": matches, "evaluated_rule_ids": list(classification.get("evaluated_rule_ids", []))})
        elif status == "B0_MAPPED_LAWFUL_NON_DEBT":
            entries.append({"baseline_member_id": member_id, "status": "HISTORICAL_NON_DEBT_UNDER_CURRENT_CONSTITUTION", "mapped_finding_ids": [], "evaluated_rule_ids": list(classification.get("evaluated_rule_ids", [])), "constitutional_basis": classification.get("constitutional_basis")})
        else:
            unresolved.append(member_id)
            entries.append({"baseline_member_id": member_id, "status": "UNRESOLVED", "mapped_finding_ids": matches, "reason": status or "NO_SOURCE_BOUND_V0_2_EVALUATION"})
    current_finding_ids = {str(row["finding_id"]) for row in finding_rows}
    late_discovered = sorted(current_finding_ids - mapped_findings)
    finding_by_id = {str(row["finding_id"]): row for row in finding_rows}
    condition_by_finding: dict[str, list[Mapping[str, Any]]] = {}
    for row in condition_rows:
        for finding in row.get("mapped_finding_ids", []):
            condition_by_finding.setdefault(str(finding), []).append(row)
    path_subjects = {
        fe._subject(str(row["path"])): str(row["path"])
        for row in current_topology.get("components", [])
        if row.get("path")
    }
    late_records: list[dict[str, Any]] = []
    unresolved_findings: list[str] = []
    for finding_id in late_discovered:
        finding = finding_by_id[finding_id]
        observer_rows = condition_by_finding.get(finding_id, [])
        evidence = sorted(_evidence_refs(finding))
        subject_path = path_subjects.get(str(finding.get("subject_artifact_id", "")))
        if observer_rows:
            basis = "SOURCE_BOUND_NON_B0_OBSERVER_TO_V0_2_FINDING"
        elif evidence or subject_path:
            basis = "SOURCE_BOUND_FULL_G3_FINDING_WITHOUT_V0_1_OBSERVER_EQUIVALENT"
        else:
            basis = "UNRESOLVED_FINDING_SOURCE_LINEAGE"
            unresolved_findings.append(finding_id)
        late_records.append({
            "finding_id": finding_id,
            "status": "LATE_DISCOVERED_PREEXISTING_CURRENT_ACTIONABLE" if basis != "UNRESOLVED_FINDING_SOURCE_LINEAGE" else "UNRESOLVED",
            "constitutional_rule_id": finding.get("rule_id"),
            "subject_artifact_id": finding.get("subject_artifact_id"),
            "subject_path": subject_path,
            "evidence_refs": evidence,
            "observer_subject_keys": sorted(str(row["subject_key"]) for row in observer_rows),
            "classification_basis": basis,
        })
    unresolved_count = len(unresolved) + len(unresolved_findings)
    return {
        "schema": "ovc-grt2-g3-b0-full-g3-lineage-reconciliation/v1",
        "b0_member_count": len(b0_rows),
        "b0_membership_sha256": baseline_membership_sha256(b0_rows),
        "current_full_g3_finding_count": len(current_finding_ids),
        "mapped_current_finding_count": len(mapped_findings),
        "late_discovered_preexisting_candidate_finding_ids": late_discovered,
        "late_discovered_preexisting_findings": late_records,
        "unresolved_baseline_member_ids": unresolved,
        "unresolved_current_finding_ids": unresolved_findings,
        "entries": entries,
        "unresolved_lineage_count": unresolved_count,
        "status": "PASS" if unresolved_count == 0 else "INCOMPLETE",
        "authority_effect": "NONE_LINEAGE_RECONCILIATION_ONLY",
    }


def propose_candidate_floor(*, predecessor_commit: str, predecessor_tree: str, constitution_hash: str, full_snapshot: Mapping[str, Any], lineage_reconciliation: Mapping[str, Any], transition_zero: bool, baseline_expansion_zero: bool) -> dict[str, Any] | None:
    if full_snapshot.get("adapter_errors") or full_snapshot.get("not_evaluable"):
        return None
    if any(value != "EVALUATED" for value in full_snapshot.get("family_coverage", {}).values()):
        return None
    if lineage_reconciliation.get("status") != "PASS" or not transition_zero or not baseline_expansion_zero:
        return None
    floor = propose_debt_floor(
        generation=0,
        predecessor_commit=predecessor_commit,
        predecessor_tree=predecessor_tree,
        constitution_hash=constitution_hash,
        open_grandfathered_findings=sorted(str(row["finding_id"]) for row in full_snapshot.get("findings", [])),
        historical_non_debt=(),
        quarantined_findings=(),
        temporarily_admitted_actionable=(),
    )
    validate_debt_floor(floor)
    return floor
