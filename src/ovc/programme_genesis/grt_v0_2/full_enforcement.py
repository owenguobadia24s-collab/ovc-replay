"""Exact source-bound full-G3 shadow replay.

Corrective implementation of the already-ratified GRT2 WP3B/WP3C/WP3E
candidate semantics.  This module is non-enforcing: it cannot activate the
Repository Constitution, create/activate DebtFloor generation 0, promote
inferred ownership/Genesis/dependencies, or change GRT2-D1..D433.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
import tracemalloc
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from .debt import (
    B0_MEMBER_COUNT,
    B0_MEMBERSHIP_SHA256,
    baseline_membership_sha256,
    classify_debt_transition,
    compare_debt_extent,
    finding_id,
    validate_baseline_members,
)
from .rules import evaluate_rule
from .serialization import canonical_sha256

RULE_BUNDLE_PATH = "registries/governance/grt_v0_2/GRT_RULE_BUNDLE_v0_2.json"
ROOT_REGISTRY_PATH = "registries/governance/grt_v0_2/GRT_ROOT_REGISTRY_v0_2.json"
PGN_STATE_PATH = "registries/governance/programme_genesis/OVC_PGN_PORTFOLIO_LEDGER_v0_2.json"
WORKFLOW_POLICY_PATH = "registries/development/OVC_CI_WORKFLOW_GOVERNANCE_POLICY_v0_3.json"
B0_MEMBERS_PATH = "registries/governance/grt_v0_2/baseline/GRT_B0_BASELINE_MEMBERS_v0_1.jsonl"

REQUIRED_FULL_G3_RULE_FAMILIES = (
    "ROOTS_AND_PLACEMENT",
    "ARTIFACT_CLASSIFICATION",
    "OWNERSHIP",
    "GENESIS_BINDINGS",
    "COMPANIONS_AND_ORPHANS",
    "DEPENDENCIES",
    "SUPERSESSION",
    "CURRENT_STATE_AND_DOCUMENTATION",
    "WORKFLOWS_AND_TOOLING",
    "BASELINE_AND_INTEGRITY",
)
REQUIRED_RULE_IDS = (
    "GRT-R001", "GRT-R005", "GRT-R100", "GRT-R200", "GRT-R300",
    "GRT-R421", "GRT-R500", "GRT-R600", "GRT-R700", "GRT-R805",
    "GRT-R900", "GRT-R954",
)
_TEXT_SUFFIXES = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".cfg", ".ini", ".csv"}
_PROGRAMME_RE = re.compile(r'"programme_id"\s*:\s*"([^"\\]+)"')
_PATH_RE = re.compile(r"(?<![A-Za-z0-9_.-])((?:src|apps|contracts|schemas|registries|fixtures|tests|scripts|tools|docs|records|plans|legacy|\.github/workflows)/[A-Za-z0-9_./@+=:-]+)")
_SOURCE_BOUND_OWNER_CLASSES = {"REGISTRY", "CONTRACT", "PLAN", "DECISION_RECORD", "PROGRAMME_STATE", "DOCUMENTATION", "EVIDENCE_POINTER"}
_LIVE_LIFECYCLES = {"CURRENT_AUTHORITATIVE", "CURRENT_IMPLEMENTATION", "CURRENT_SUPPORTING"}


class FullG3ReplayError(ValueError):
    pass


def _git(root: Path, *args: str, check: bool = True) -> str:
    cp = subprocess.run(["git", "-C", str(root), *args], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if check and cp.returncode != 0:
        raise FullG3ReplayError(f"git {' '.join(args)} failed: {cp.stderr.strip()}")
    return cp.stdout


def _commit(root: Path, ref: str) -> str:
    value = _git(root, "rev-parse", ref).strip()
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise FullG3ReplayError("GRT2_G3_COMMIT_IDENTITY_INVALID")
    return value


def _tree(root: Path, commit: str) -> str:
    value = _git(root, "rev-parse", f"{commit}^{{tree}}").strip()
    if len(value) != 40:
        raise FullG3ReplayError("GRT2_G3_TREE_IDENTITY_INVALID")
    return value


def _show(root: Path, commit: str, path: str) -> str | None:
    cp = subprocess.run(["git", "-C", str(root), "show", f"{commit}:{path}"], check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace")
    return cp.stdout if cp.returncode == 0 else None


def _json(root: Path, commit: str, path: str) -> Mapping[str, Any]:
    text = _show(root, commit, path)
    if text is None:
        raise FullG3ReplayError(f"GRT2_G3_REQUIRED_SOURCE_MISSING:{path}")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FullG3ReplayError(f"GRT2_G3_REQUIRED_SOURCE_INVALID_JSON:{path}") from exc
    if not isinstance(value, Mapping):
        raise FullG3ReplayError(f"GRT2_G3_REQUIRED_SOURCE_NOT_OBJECT:{path}")
    return value


def _b0_valid(root: Path, commit: str) -> tuple[bool, list[str]]:
    text = _show(root, commit, B0_MEMBERS_PATH)
    if text is None:
        return False, ["B0_MEMBERS_SOURCE_MISSING"]
    try:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        if not all(isinstance(row, dict) for row in rows):
            return False, ["B0_MEMBER_ROW_INVALID"]
        validate_baseline_members(rows)
        valid = len(rows) == B0_MEMBER_COUNT and baseline_membership_sha256(rows) == B0_MEMBERSHIP_SHA256
    except Exception as exc:
        return False, [f"B0_VALIDATION_FAILED:{type(exc).__name__}"]
    return valid, [] if valid else ["B0_MEMBERSHIP_MISMATCH"]


def _inventory(root: Path, commit: str) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in _git(root, "ls-tree", "-r", "--full-tree", commit).splitlines():
        metadata, path = line.split("\t", 1)
        mode, object_type, blob_hash = metadata.split(" ", 2)
        if object_type == "blob":
            rows[path] = {"path": path, "blob_hash": blob_hash, "mode": mode}
    return rows


def _changed_paths(root: Path, predecessor: str, candidate: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in _git(root, "diff", "--name-status", "--find-renames", predecessor, candidate).splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        status = parts[0]
        if status.startswith("R") and len(parts) == 3:
            rows.append({"status": status, "old_path": parts[1], "path": parts[2]})
        elif len(parts) >= 2:
            rows.append({"status": status, "path": parts[-1]})
    return rows


def _grep_referrers(root: Path, commit: str, literal: str) -> set[str]:
    if not literal:
        return set()
    cp = subprocess.run(["git", "-C", str(root), "grep", "-l", "-F", "-e", literal, commit, "--"], check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace")
    if cp.returncode not in {0, 1}:
        raise FullG3ReplayError("GRT2_G3_GIT_GREP_FAILED")
    prefix = commit + ":"
    out: set[str] = set()
    for raw in cp.stdout.splitlines():
        value = raw.strip()
        if value.startswith(prefix):
            value = value[len(prefix):]
        if value:
            out.add(value)
    return out


def _artifact_type(path: str) -> str | None:
    p = PurePosixPath(path)
    if path.startswith(".github/workflows/") and p.suffix.lower() in {".yml", ".yaml"}:
        return "WORKFLOW"
    if path.startswith(("src/", "apps/")):
        return "IMPLEMENTATION"
    if path.startswith("registries/implementation/") and p.suffix.lower() == ".json" and "STATE" in p.name.upper() and p.name != "CURRENT_STATE_POINTER.json":
        return "PROGRAMME_STATE"
    root = path.split("/", 1)[0]
    mapping = {"contracts": "CONTRACT", "schemas": "SCHEMA", "registries": "REGISTRY", "fixtures": "FIXTURE", "tests": "TEST", "scripts": "TOOLING", "tools": "TOOLING", "plans": "PLAN", "records": "DOCUMENTATION", "legacy": "DOCUMENTATION", "artifacts": "GENERATED_ARTIFACT", "benchmarks": "GENERATED_ARTIFACT", "data": "GENERATED_ARTIFACT", "design": "DOCUMENTATION", "qa": "EVIDENCE_POINTER"}
    if root in mapping:
        return mapping[root]
    if root == "docs":
        upper = p.name.upper()
        if "DECISION" in upper:
            return "DECISION_RECORD"
        if "STATE" in upper and p.suffix.lower() == ".json":
            return "PROGRAMME_STATE"
        if any(token in upper for token in ("MANIFEST", "RECEIPT", "EVIDENCE", "QA_PACKET")):
            return "EVIDENCE_POINTER"
        if "PLAN" in upper:
            return "PLAN"
        return "DOCUMENTATION"
    return None


def _programme_ids(text: str) -> set[str]:
    return {match.group(1).strip() for match in _PROGRAMME_RE.finditer(text) if match.group(1).strip()}


def _path_refs(text: str, known_paths: set[str]) -> set[str]:
    return {token for token in (match.group(1).rstrip(".,;:)]}'\"") for match in _PATH_RE.finditer(text)) if token in known_paths}


def _pointer_targets(*, inventory: Mapping[str, Any], texts: Mapping[str, str]) -> tuple[set[str], list[str]]:
    targets: set[str] = set()
    errors: list[str] = []
    for path in sorted(inventory):
        if not path.endswith("CURRENT_STATE_POINTER.json"):
            continue
        text = texts.get(path)
        if text is None:
            errors.append(f"CURRENT_STATE_POINTER_UNREADABLE:{path}")
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            errors.append(f"CURRENT_STATE_POINTER_INVALID:{path}")
            continue
        if not isinstance(payload, Mapping):
            errors.append(f"CURRENT_STATE_POINTER_INVALID:{path}")
            continue
        values = sorted({str(payload[key]) for key in ("current_state", "current_state_path", "state_path") if isinstance(payload.get(key), str) and payload.get(key)})
        if len(values) != 1:
            errors.append(f"CURRENT_STATE_POINTER_TARGET_AMBIGUOUS:{path}")
        elif values[0] not in inventory:
            errors.append(f"CURRENT_STATE_POINTER_TARGET_MISSING:{path}:{values[0]}")
        else:
            targets.add(values[0])
    return targets, errors


def _lifecycle(path: str, art_type: str, text: str, current_targets: set[str]) -> str:
    upper = text[:65536].upper()
    if path in current_targets:
        return "CURRENT_AUTHORITATIVE"
    if path.startswith("legacy/") or "SUPERSEDED" in upper:
        return "HISTORICAL_IMMUTABLE"
    if art_type == "IMPLEMENTATION":
        return "CURRENT_IMPLEMENTATION"
    if art_type in {"PROGRAMME_STATE", "DECISION_RECORD", "EVIDENCE_POINTER"}:
        return "HISTORICAL_IMMUTABLE"
    return "CURRENT_SUPPORTING"


def _workflow_governed(policy: Mapping[str, Any]) -> set[str]:
    paths = {str(x) for x in policy.get("approved_pull_request_workflows", []) if isinstance(x, str)}
    admitted = policy.get("admitted_new_workflow")
    if isinstance(admitted, Mapping) and isinstance(admitted.get("path"), str):
        paths.add(str(admitted["path"]))
    for row in policy.get("additional_non_pr_diagnostic_workflows", []):
        if isinstance(row, Mapping) and isinstance(row.get("path"), str):
            paths.add(str(row["path"]))
    return paths


def _pgn_native_adoption_active(pgn_state: Mapping[str, Any]) -> bool:
    authority = pgn_state.get("authority")
    if not isinstance(authority, Mapping):
        return False
    value = str(authority.get("native_genesis_adoption", "")).upper()
    return value.startswith(("ACTIVE", "ADOPTED", "APPROVED")) and "DENIED" not in value


def _root_registry(root_registry: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    registered, deprecated = set(), set()
    for row in root_registry.get("roots", []):
        if not isinstance(row, Mapping) or not row.get("path"):
            continue
        path = str(row["path"]).rstrip("/")
        registered.add(path)
        labels = " ".join(str(row.get(key, "")) for key in ("classification_status", "lifecycle_class", "new_write_policy", "status")).upper()
        if "DEPRECATED" in labels or "NO_NEW_WRITES" in labels:
            deprecated.add(path)
    return registered, deprecated


def _rule_index(bundle: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = bundle.get("rules")
    if not isinstance(rows, list):
        raise FullG3ReplayError("GRT2_G3_RULE_BUNDLE_INVALID")
    out = {str(row["rule_id"]): row for row in rows if isinstance(row, Mapping) and isinstance(row.get("rule_id"), str)}
    missing = [rule_id for rule_id in REQUIRED_RULE_IDS if rule_id not in out]
    if missing:
        raise FullG3ReplayError("GRT2_G3_REQUIRED_RULE_MISSING:" + ",".join(missing))
    return out


def _subject(path: str) -> str:
    return "GRT.ARTIFACT.PATH." + canonical_sha256({"path": path})[:24]


def _root_subject(path: str) -> str:
    return "GRT.ARTIFACT.ROOT." + canonical_sha256({"root": path})[:24]


def _dependency_subject(source_path: str, index: int, dep: Mapping[str, Any]) -> str:
    projection = {"source_path": source_path, "index": index, "from": dep.get("from_programme_id", dep.get("from_node")), "to": dep.get("to_programme_id", dep.get("to_node")), "edge_type": dep.get("edge_type")}
    return "GRT.ARTIFACT.DEP." + canonical_sha256(projection)[:24]


def _eval(rule: Mapping[str, Any], subject_id: str, applicable: bool | str, violated: bool | str, *, extent: Mapping[str, int] | None = None, evidence: Iterable[str] = ()) -> dict[str, Any]:
    facts = {str(rule["applicability_predicate"]): applicable, str(rule["violation_predicate"]): violated}
    row = evaluate_rule(rule, {"artifact_id": subject_id}, facts)
    return {**row, "debt_extent": dict(extent or {"violations": 1}), "evidence_refs": sorted({str(value) for value in evidence if str(value)})}


def _dependency_records(value: Any) -> list[Mapping[str, Any]]:
    found: list[Mapping[str, Any]] = []
    if isinstance(value, Mapping):
        keys = set(value)
        if "edge_type" in keys and ({"from_node", "to_node"} <= keys or {"from_programme_id", "to_programme_id"} <= keys):
            found.append(value)
        for child in value.values():
            found.extend(_dependency_records(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_dependency_records(child))
    return found


def _programme_statuses(*, texts: Mapping[str, str], current_targets: set[str]) -> tuple[dict[str, str], list[str]]:
    statuses: dict[str, str] = {}
    errors: list[str] = []
    for path in sorted(current_targets):
        text = texts.get(path)
        if text is None:
            errors.append(f"CURRENT_PROGRAMME_STATE_UNREADABLE:{path}")
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            errors.append(f"CURRENT_PROGRAMME_STATE_INVALID:{path}")
            continue
        if not isinstance(payload, Mapping):
            continue
        pid, status = payload.get("programme_id"), payload.get("status")
        if isinstance(pid, str) and pid and isinstance(status, str) and status:
            if pid in statuses and statuses[pid] != status:
                errors.append(f"CURRENT_PROGRAMME_STATE_CONFLICT:{pid}")
            else:
                statuses[pid] = status
    return statuses, errors


def build_source_bound_snapshot(*, commit: str, tree: str, inventory: Mapping[str, Mapping[str, Any]], texts: Mapping[str, str], impact_paths: Sequence[str], referrers: Mapping[str, Sequence[str]], current_targets: set[str], pointer_errors: Sequence[str], rule_bundle: Mapping[str, Any], root_registry: Mapping[str, Any], pgn_state: Mapping[str, Any], workflow_policy: Mapping[str, Any], b0_valid: bool, b0_errors: Sequence[str] = (), exact_diff_new_writes: Sequence[str] = (), rule_bundle_changed: bool = False) -> dict[str, Any]:
    """Pure fail-closed adapter from exact source evidence to full-G3 facts."""
    rules = _rule_index(rule_bundle)
    registered_roots, deprecated_roots = _root_registry(root_registry)
    native_genesis_active = _pgn_native_adoption_active(pgn_state)
    governed_workflows = _workflow_governed(workflow_policy)
    programme_status, status_errors = _programme_statuses(texts=texts, current_targets=current_targets)
    errors = [*pointer_errors, *status_errors, *b0_errors]
    evaluations: list[dict[str, Any]] = []

    for top in sorted({path.split("/", 1)[0] for path in inventory if path}):
        evaluations.append(_eval(rules["GRT-R001"], _root_subject(top), True, top not in registered_roots, evidence=[ROOT_REGISTRY_PATH, f"git-tree:{tree}:{top}"]))
    writes = [path for path in exact_diff_new_writes if path.split("/", 1)[0] in deprecated_roots]
    evaluations.append(_eval(rules["GRT-R005"], "GRT.ARTIFACT.GLOBAL.DEPRECATED_ROOT_WRITE", bool(writes), bool(writes), extent={"new_write_count": len(writes)}, evidence=writes))

    for path in sorted(set(impact_paths)):
        meta = inventory.get(path)
        if meta is None:
            continue
        art_type = _artifact_type(path)
        sid = _subject(path)
        if art_type is None:
            evaluations.append(_eval(rules["GRT-R100"], sid, True, True, evidence=[f"git:{path}@{meta.get('blob_hash')}"]))
            continue
        text = texts.get(path, "")
        lifecycle = _lifecycle(path, art_type, text, current_targets)
        evaluations.append(_eval(rules["GRT-R100"], sid, True, False, evidence=[f"git:{path}@{meta.get('blob_hash')}"]))

        references = sorted(set(referrers.get(path, ())))
        owners = set(_programme_ids(text))
        owner_sources = [path] if owners else []
        for source_path in references:
            if _artifact_type(source_path) not in _SOURCE_BOUND_OWNER_CLASSES:
                continue
            pids = _programme_ids(texts.get(source_path, ""))
            if pids:
                owners.update(pids)
                owner_sources.append(source_path)

        if art_type == "IMPLEMENTATION" and lifecycle == "CURRENT_IMPLEMENTATION":
            evaluations.append(_eval(rules["GRT-R200"], sid, True, len(owners) != 1, extent={"source_bound_owner_count": len(owners)}, evidence=owner_sources))
        if art_type in {"IMPLEMENTATION", "PLAN", "PROGRAMME_STATE"} and lifecycle in {"CURRENT_IMPLEMENTATION", "CURRENT_AUTHORITATIVE"}:
            accepted = native_genesis_active and len(owners) == 1
            evaluations.append(_eval(rules["GRT-R300"], sid, True, not accepted, extent={"accepted_native_genesis_binding_count": 1 if accepted else 0}, evidence=[PGN_STATE_PATH, *owner_sources]))
        if art_type == "SCHEMA" and lifecycle in {"CURRENT_SUPPORTING", "CURRENT_AUTHORITATIVE"}:
            consumers = [source for source in references if _artifact_type(source) in {"CONTRACT", "REGISTRY", "TEST", "IMPLEMENTATION", "DOCUMENTATION"}]
            evaluations.append(_eval(rules["GRT-R421"], sid, True, not consumers, extent={"lawful_consumer_count": len(consumers)}, evidence=consumers))
        if art_type in {"PROGRAMME_STATE", "DOCUMENTATION", "DECISION_RECORD"}:
            applicable = path in current_targets
            evaluations.append(_eval(rules["GRT-R700"], sid, applicable, False, evidence=[path] if applicable else []))
        if art_type == "WORKFLOW" and lifecycle in _LIVE_LIFECYCLES:
            evaluations.append(_eval(rules["GRT-R805"], sid, True, path not in governed_workflows, extent={"governance_record_count": 1 if path in governed_workflows else 0}, evidence=[WORKFLOW_POLICY_PATH] if path in governed_workflows else [path]))

        # Repository fixtures may contain source-explicit dependency *examples*.
        # They are test inputs, not live dependency declarations of the fixture
        # artifact itself, and must not be promoted into current authority.
        if not path.startswith("fixtures/") and PurePosixPath(path).suffix.lower() == ".json" and text.lstrip().startswith(("{", "[")):
            try:
                structured = json.loads(text)
            except json.JSONDecodeError:
                structured = None
            if structured is not None:
                for index, dep in enumerate(_dependency_records(structured)):
                    hardness = str(dep.get("hardness", ""))
                    source_kind = str(dep.get("source_kind", dep.get("evidence_status", "")))
                    applicable = hardness == "HARD" and source_kind == "SOURCE_EXPLICIT"
                    to_pid = str(dep.get("to_programme_id", dep.get("to_node", "")))
                    target_status = programme_status.get(to_pid)
                    dep_sid = _dependency_subject(path, index, dep)
                    if applicable and not to_pid:
                        target_fact: bool | str = "NOT_EVALUABLE"
                        errors.append(f"REQUIRED_DEPENDENCY_TARGET_ID_MISSING:{path}:{index}")
                    elif applicable and target_status is None:
                        target_fact = "NOT_EVALUABLE"
                        errors.append(f"REQUIRED_DEPENDENCY_TARGET_CURRENT_STATE_NOT_EVALUABLE:{path}:{index}:{to_pid}")
                    else:
                        target_fact = bool(target_status and target_status.upper() in {"BLOCKED", "QUARANTINED", "SUPERSEDED", "RETIRED"})
                    evaluations.append(_eval(rules["GRT-R500"], dep_sid, applicable, target_fact if applicable else False, evidence=[path]))
                    superseded: bool | str = "NOT_EVALUABLE" if applicable and target_status is None else bool(target_status and target_status.upper() in {"SUPERSEDED", "RETIRED"})
                    evaluations.append(_eval(rules["GRT-R600"], dep_sid, applicable, superseded if applicable else False, evidence=[path]))

    evaluations.append(_eval(rules["GRT-R900"], "GRT.ARTIFACT.BASELINE.B0", True, not b0_valid, extent={"baseline_integrity_failure_count": 0 if b0_valid else 1}, evidence=[B0_MEMBERS_PATH]))
    evaluations.append(_eval(rules["GRT-R954"], "GRT.ARTIFACT.CONSTITUTION.RULE_BUNDLE", rule_bundle_changed, rule_bundle_changed, extent={"semantic_change_count": 1 if rule_bundle_changed else 0}, evidence=[RULE_BUNDLE_PATH]))
    if rule_bundle_changed:
        errors.append("RULE_SEMANTIC_CHANGE_REQUIRES_OPERATOR_APPROVED_AMENDMENT")

    # Coverage is defined by adapter phases, not by whether a candidate happened
    # to contain an applicable subject in every family.  Missing required rule
    # identities fail in _rule_index; missing source facts remain NOT_EVALUABLE.
    family_by_rule = {rule_id: str(rule.get("rule_family", "")) for rule_id, rule in rules.items()}
    implemented_families = {family_by_rule[rule_id] for rule_id in REQUIRED_RULE_IDS}
    missing_families = sorted(set(REQUIRED_FULL_G3_RULE_FAMILIES) - implemented_families)
    errors.extend(f"RULE_FAMILY_SKIPPED:{family}" for family in missing_families)

    findings: dict[str, dict[str, Any]] = {}
    not_evaluable: list[dict[str, Any]] = []
    for row in evaluations:
        family = family_by_rule[str(row["rule_id"])]
        if row["evaluation_status"] == "NOT_EVALUABLE":
            not_evaluable.append({"rule_id": row["rule_id"], "subject_artifact_id": row["subject_artifact_id"]})
        if row["evaluation_status"] == "VIOLATION" and rules[str(row["rule_id"])].get("debt_effect") == "ACTIONABLE_DEBT":
            fid = finding_id(str(row["rule_id"]), str(row["subject_artifact_id"]), family)
            findings[fid] = {"finding_id": fid, "rule_id": row["rule_id"], "rule_family": family, "subject_artifact_id": row["subject_artifact_id"], "debt_extent": dict(row["debt_extent"]), "evidence_refs": list(row["evidence_refs"])}

    family_coverage = {family: "EVALUATED" if family in implemented_families and family not in missing_families else "NOT_EVALUABLE" for family in REQUIRED_FULL_G3_RULE_FAMILIES}
    return {"schema": "ovc-grt2-full-g3-source-bound-snapshot/v1", "commit": commit, "tree": tree, "impact_path_count": len(set(impact_paths)), "evaluation_count": len(evaluations), "evaluations": sorted(evaluations, key=lambda row: (str(row["rule_id"]), str(row["subject_artifact_id"]))), "findings": [findings[key] for key in sorted(findings)], "not_evaluable": sorted(not_evaluable, key=canonical_sha256), "adapter_errors": sorted(set(errors)), "family_coverage": family_coverage, "pgn_native_genesis_adoption_active": native_genesis_active, "authority_effect": "NONE_FULL_G3_SHADOW_SNAPSHOT_ONLY"}


def _transition_rows(predecessor: Mapping[str, Any], candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    before = {str(row["finding_id"]): row for row in predecessor.get("findings", [])}
    after = {str(row["finding_id"]): row for row in candidate.get("findings", [])}
    rows: list[dict[str, Any]] = []
    for fid in sorted(set(before) | set(after)):
        previous, current = before.get(fid), after.get(fid)
        if previous is None and current is not None:
            classification, admission = classify_debt_transition(predecessor_state="ABSENT", candidate_state="ACTIONABLE")
            extent_result = None
        elif previous is not None and current is None:
            classification, admission = classify_debt_transition(predecessor_state="GRANDFATHERED", candidate_state="RESOLVED_WITH_PROOF")
            extent_result = None
        else:
            assert previous is not None and current is not None
            extent_result = compare_debt_extent(previous["debt_extent"], current["debt_extent"])
            classification, admission = classify_debt_transition(predecessor_state="GRANDFATHERED", candidate_state="ACTIONABLE", extent_result=extent_result)
        source = current or previous
        assert source is not None
        rows.append({"finding_id": fid, "rule_id": source["rule_id"], "rule_family": source["rule_family"], "classification": classification, "admission": admission, "extent_result": extent_result})
    return rows


def _read_impact_evidence(root: Path, *, commit: str, inventory: Mapping[str, Mapping[str, Any]], seed_paths: Sequence[str]) -> tuple[set[str], dict[str, str], dict[str, list[str]], set[str], list[str]]:
    known = set(inventory)
    impact = {path for path in seed_paths if path in known}
    pointer_paths = {path for path in known if path.endswith("CURRENT_STATE_POINTER.json")}
    impact.update(pointer_paths)
    texts: dict[str, str] = {}
    referrers: dict[str, set[str]] = defaultdict(set)

    def read(path: str) -> str:
        if path not in texts:
            texts[path] = (_show(root, commit, path) or "") if PurePosixPath(path).suffix.lower() in _TEXT_SUFFIXES else ""
        return texts[path]

    frontier = set(impact)
    for _ in range(4):
        additions: set[str] = set()
        for path in sorted(frontier):
            text = read(path)
            for target in _path_refs(text, known):
                referrers[target].add(path)
                additions.add(target)
            for source in _grep_referrers(root, commit, path):
                if source in known and (_artifact_type(source) in _SOURCE_BOUND_OWNER_CLASSES or source.endswith("CURRENT_STATE_POINTER.json")):
                    referrers[path].add(source)
                    additions.add(source)
        new = additions - impact
        impact.update(additions)
        frontier = new
        if len(impact) > 2048:
            return impact, texts, {key: sorted(value) for key, value in referrers.items()}, set(), ["IMPACT_FRONTIER_CAPACITY_EXCEEDED"]
        if not new:
            break
    errors: list[str] = []
    if frontier:
        errors.append("IMPACT_FRONTIER_TRANSITIVE_CLOSURE_NOT_BOUNDED")
    for path in sorted(impact):
        text = read(path)
        for target in _path_refs(text, known):
            if target in impact:
                referrers[target].add(path)
    current_targets, pointer_errors = _pointer_targets(inventory=inventory, texts=texts)
    for target in current_targets:
        impact.add(target)
        read(target)
    return impact, texts, {key: sorted(value) for key, value in referrers.items()}, current_targets, [*errors, *pointer_errors]


def replay_full_g3_candidate(repository_root: Path | str, *, predecessor_commit: str, candidate_commit: str) -> dict[str, Any]:
    """Replay one exact predecessor/candidate pair without enforcement authority."""
    root = Path(repository_root).resolve()
    predecessor, candidate = _commit(root, predecessor_commit), _commit(root, candidate_commit)
    predecessor_tree, candidate_tree = _tree(root, predecessor), _tree(root, candidate)
    diff = _changed_paths(root, predecessor, candidate)
    seed_paths = sorted({row[key] for row in diff for key in ("path", "old_path") if row.get(key)})
    new_writes = sorted({row["path"] for row in diff if not row["status"].startswith("D") and row.get("path")})

    started = time.perf_counter_ns()
    tracemalloc.start()
    p_inventory, c_inventory = _inventory(root, predecessor), _inventory(root, candidate)
    p_impact, p_texts, p_referrers, p_targets, p_errors = _read_impact_evidence(root, commit=predecessor, inventory=p_inventory, seed_paths=seed_paths)
    c_impact, c_texts, c_referrers, c_targets, c_errors = _read_impact_evidence(root, commit=candidate, inventory=c_inventory, seed_paths=seed_paths)
    impact_union = sorted(p_impact | c_impact)
    for path in impact_union:
        if path in p_inventory and path not in p_texts:
            p_texts[path] = _show(root, predecessor, path) or ""
        if path in c_inventory and path not in c_texts:
            c_texts[path] = _show(root, candidate, path) or ""

    p_rules_text, c_rules_text = _show(root, predecessor, RULE_BUNDLE_PATH), _show(root, candidate, RULE_BUNDLE_PATH)
    if p_rules_text is None or c_rules_text is None:
        raise FullG3ReplayError("GRT2_G3_RULE_BUNDLE_MISSING")
    try:
        p_rules, c_rules = json.loads(p_rules_text), json.loads(c_rules_text)
    except json.JSONDecodeError as exc:
        raise FullG3ReplayError("GRT2_G3_RULE_BUNDLE_INVALID_JSON") from exc
    if not isinstance(p_rules, Mapping) or not isinstance(c_rules, Mapping):
        raise FullG3ReplayError("GRT2_G3_RULE_BUNDLE_INVALID")

    p_b0, p_b0_errors = _b0_valid(root, predecessor)
    c_b0, c_b0_errors = _b0_valid(root, candidate)
    p_snapshot = build_source_bound_snapshot(commit=predecessor, tree=predecessor_tree, inventory=p_inventory, texts=p_texts, impact_paths=impact_union, referrers=p_referrers, current_targets=p_targets, pointer_errors=p_errors, rule_bundle=p_rules, root_registry=_json(root, predecessor, ROOT_REGISTRY_PATH), pgn_state=_json(root, predecessor, PGN_STATE_PATH), workflow_policy=_json(root, predecessor, WORKFLOW_POLICY_PATH), b0_valid=p_b0, b0_errors=p_b0_errors)
    c_snapshot = build_source_bound_snapshot(commit=candidate, tree=candidate_tree, inventory=c_inventory, texts=c_texts, impact_paths=impact_union, referrers=c_referrers, current_targets=c_targets, pointer_errors=c_errors, rule_bundle=c_rules, root_registry=_json(root, candidate, ROOT_REGISTRY_PATH), pgn_state=_json(root, candidate, PGN_STATE_PATH), workflow_policy=_json(root, candidate, WORKFLOW_POLICY_PATH), b0_valid=c_b0, b0_errors=c_b0_errors, exact_diff_new_writes=new_writes, rule_bundle_changed=p_rules_text != c_rules_text)

    transitions = _transition_rows(p_snapshot, c_snapshot)
    blockers = [row for row in transitions if row["admission"] != "PASS"]
    adapter_errors = sorted(set([*p_snapshot["adapter_errors"], *c_snapshot["adapter_errors"]]))
    not_evaluable_rows = [*p_snapshot["not_evaluable"], *c_snapshot["not_evaluable"]]
    family_coverage = {family: "PASS" if p_snapshot["family_coverage"].get(family) == "EVALUATED" and c_snapshot["family_coverage"].get(family) == "EVALUATED" else "NOT_EVALUABLE" for family in REQUIRED_FULL_G3_RULE_FAMILIES}
    skipped = [family for family, status in family_coverage.items() if status != "PASS"]
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    duration_ms = max(1, (time.perf_counter_ns() - started + 999_999) // 1_000_000)

    status, reasons = "PASS", []
    if skipped:
        status = "NOT_EVALUABLE"; reasons.append("FULL_G3_RULE_FAMILY_NOT_MATERIALIZED_FOR_REPLAY")
    if adapter_errors or not_evaluable_rows:
        status = "NOT_EVALUABLE"; reasons.append("SOURCE_BOUND_FACT_NOT_EVALUABLE")
    if blockers:
        status = "FAIL"; reasons.append("NEW_EXPANDED_OR_UNRESOLVED_ACTIONABLE_DEBT")
    semantic = {"schema": "ovc-grt2-full-g3-candidate-replay/v1", "predecessor_commit": predecessor, "predecessor_tree": predecessor_tree, "candidate_commit": candidate, "candidate_tree": candidate_tree, "changed_paths": diff, "impact_path_count": len(impact_union), "required_rule_families": list(REQUIRED_FULL_G3_RULE_FAMILIES), "family_coverage": family_coverage, "predecessor_finding_count": len(p_snapshot["findings"]), "candidate_finding_count": len(c_snapshot["findings"]), "transition_count": len(transitions), "new_or_expanded_debt_count": len(blockers), "not_evaluable_count": len(adapter_errors) + len(not_evaluable_rows) + len(skipped), "blocking_transitions": blockers, "transitions": transitions, "adapter_errors": adapter_errors, "status": status, "reason_codes": sorted(set(reasons)), "authority_effect": "NONE_FULL_G3_SHADOW_REPLAY_ONLY", "active_enforcement": "UNCHANGED_LIMITED_G2_5_ONLY", "debt_floor_generation": None}
    return {**semantic, "performance": {"surface": "GRT_EXACT", "duration_ms": int(duration_ms), "peak_memory_bytes": int(peak), "status": "MEASURED_NOT_YET_COMPARED_TO_FROZEN_BUDGET"}, "canonical_hash": canonical_sha256(semantic)}
