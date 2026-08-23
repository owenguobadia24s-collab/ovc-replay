"""Bounded exact source-bound full-G3 shadow replay.

Corrects the first replay-surface implementation without changing GRT2-D1..D433.
The adapter remains non-enforcing. It narrows impact discovery to typed, source-bound
relationship closure and resolves historical current-state pointers relative to their
own registry directory before treating a pointer as stale debt.
"""
from __future__ import annotations

import json
import subprocess
import time
import tracemalloc
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from . import full_enforcement as base
from .debt import finding_id
from .serialization import canonical_sha256

_POINTER_KEYS = (
    "authoritative_state",
    "state_record",
    "current_state_path",
    "state_path",
    "current_state",
)
_MAX_IMPACT_PATHS = 512
_MAX_CLOSURE_ROUNDS = 6


def _read_text(root: Path, commit: str, path: str) -> str:
    if PurePosixPath(path).suffix.lower() not in base._TEXT_SUFFIXES:
        return ""
    return base._show(root, commit, path) or ""


def _resolve_pointer_value(path: str, raw: str, known: set[str]) -> str:
    value = raw.strip().replace("\\", "/")
    if value in known:
        return value
    if "/" not in value:
        relative = (PurePosixPath(path).parent / value).as_posix()
        if relative in known:
            return relative
        return relative
    return value


def _pointer_catalog(
    *,
    inventory: Mapping[str, Any],
    texts: Mapping[str, str],
) -> tuple[set[str], set[str], list[dict[str, str]]]:
    """Resolve exact current-state targets and classify provable stale pointers as debt.

    A pointer whose target is absent is not an adapter blind spot: the Git tree proves
    the pointer and proves the target absence. Such a case is therefore evaluated by
    GRT-R700 as current-state/documentation debt. The pointer itself remains usable as
    a source-bound programme/status fallback for dependency evaluation.
    """
    known = set(inventory)
    current_targets: set[str] = set()
    status_targets: set[str] = set()
    violations: list[dict[str, str]] = []
    for path in sorted(known):
        if not path.endswith("CURRENT_STATE_POINTER.json"):
            continue
        text = texts.get(path)
        if text is None:
            violations.append({"path": path, "reason": "CURRENT_STATE_POINTER_UNREADABLE"})
            status_targets.add(path)
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            violations.append({"path": path, "reason": "CURRENT_STATE_POINTER_INVALID_JSON"})
            status_targets.add(path)
            continue
        if not isinstance(payload, Mapping):
            violations.append({"path": path, "reason": "CURRENT_STATE_POINTER_INVALID_OBJECT"})
            status_targets.add(path)
            continue
        raw_values = [str(payload[key]) for key in _POINTER_KEYS if isinstance(payload.get(key), str) and str(payload.get(key)).strip()]
        resolved = sorted({_resolve_pointer_value(path, value, known) for value in raw_values})
        if not resolved:
            violations.append({"path": path, "reason": "CURRENT_STATE_POINTER_TARGET_UNDECLARED"})
            status_targets.add(path)
            continue
        existing = [target for target in resolved if target in known]
        if len(set(resolved)) > 1:
            violations.append({"path": path, "reason": "CURRENT_STATE_POINTER_TARGET_CONFLICT:" + "|".join(resolved)})
        if len(existing) == 1:
            current_targets.add(existing[0])
            status_targets.add(existing[0])
        elif len(existing) > 1:
            violations.append({"path": path, "reason": "CURRENT_STATE_POINTER_MULTIPLE_EXISTING_TARGETS:" + "|".join(existing)})
            status_targets.add(path)
        else:
            violations.append({"path": path, "reason": "CURRENT_STATE_POINTER_TARGET_MISSING:" + resolved[0]})
            status_targets.add(path)
    return current_targets, status_targets, violations


def _grep_referrer_sources(root: Path, commit: str, literals: Sequence[str]) -> set[str]:
    values = sorted({value for value in literals if value})
    if not values:
        return set()
    args = ["git", "-C", str(root), "grep", "-l", "-F"]
    for value in values:
        args.extend(["-e", value])
    args.extend([commit, "--"])
    cp = subprocess.run(
        args,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if cp.returncode not in {0, 1}:
        raise base.FullG3ReplayError("GRT2_G3_GIT_GREP_FAILED")
    prefix = commit + ":"
    out: set[str] = set()
    for raw in cp.stdout.splitlines():
        value = raw.strip()
        if value.startswith(prefix):
            value = value[len(prefix):]
        if value:
            out.add(value)
    return out


def _read_impact_evidence_bounded(
    root: Path,
    *,
    commit: str,
    inventory: Mapping[str, Mapping[str, Any]],
    seed_paths: Sequence[str],
) -> tuple[set[str], dict[str, str], dict[str, list[str]], set[str], list[dict[str, str]], list[str]]:
    known = set(inventory)
    impact = {path for path in seed_paths if path in known}
    texts: dict[str, str] = {}
    referrers: dict[str, set[str]] = defaultdict(set)
    adapter_errors: list[str] = []

    def read(path: str) -> str:
        if path not in texts:
            texts[path] = _read_text(root, commit, path)
        return texts[path]

    # Current-state pointers are a status index, not an automatic impact expansion.
    pointer_paths = sorted(path for path in known if path.endswith("CURRENT_STATE_POINTER.json"))
    for path in pointer_paths:
        read(path)
    current_targets, status_targets, pointer_violations = _pointer_catalog(inventory=inventory, texts=texts)
    for path in sorted(status_targets | current_targets):
        if path in known:
            read(path)

    frontier = set(impact)
    for round_index in range(_MAX_CLOSURE_ROUNDS):
        if not frontier:
            break
        additions: set[str] = set()

        # Forward closure is exact declared repository-path evidence.
        for path in sorted(frontier):
            text = read(path)
            for target in base._path_refs(text, known):
                if base._artifact_type(target) is not None:
                    referrers[target].add(path)
                    additions.add(target)

        # Reverse closure is one batched source lookup per round, filtered to
        # source-bound owner/relationship classes before it can enter impact.
        for source in sorted(_grep_referrer_sources(root, commit, sorted(frontier))):
            if source not in known or base._artifact_type(source) not in base._SOURCE_BOUND_OWNER_CLASSES:
                continue
            source_text = read(source)
            referenced = base._path_refs(source_text, known) & (frontier | impact | additions)
            if not referenced:
                continue
            additions.add(source)
            for target in referenced:
                referrers[target].add(source)

        new = additions - impact
        impact.update(additions)
        if len(impact) > _MAX_IMPACT_PATHS:
            adapter_errors.append("IMPACT_FRONTIER_CAPACITY_EXCEEDED")
            break
        frontier = new
    else:
        if frontier:
            adapter_errors.append("IMPACT_FRONTIER_TYPED_CLOSURE_NOT_BOUNDED")

    for path in sorted(impact):
        text = read(path)
        for target in base._path_refs(text, known):
            if target in impact:
                referrers[target].add(path)

    return (
        impact,
        texts,
        {key: sorted(value) for key, value in referrers.items()},
        status_targets | current_targets,
        pointer_violations,
        adapter_errors,
    )


def _apply_pointer_violations(
    snapshot: dict[str, Any],
    *,
    violations: Sequence[Mapping[str, str]],
    rule_bundle: Mapping[str, Any],
) -> None:
    if not violations:
        return
    rules = base._rule_index(rule_bundle)
    rule = rules["GRT-R700"]
    family = str(rule.get("rule_family", "CURRENT_STATE_AND_DOCUMENTATION"))
    findings = {str(row["finding_id"]): row for row in snapshot.get("findings", [])}
    evaluations = list(snapshot.get("evaluations", []))
    for violation in violations:
        path = str(violation["path"])
        reason = str(violation["reason"])
        row = base._eval(
            rule,
            base._subject(path),
            True,
            True,
            extent={"current_state_pointer_violation_count": 1},
            evidence=[path, reason],
        )
        evaluations.append(row)
        if row["evaluation_status"] == "VIOLATION" and rule.get("debt_effect") == "ACTIONABLE_DEBT":
            fid = finding_id(str(row["rule_id"]), str(row["subject_artifact_id"]), family)
            findings[fid] = {
                "finding_id": fid,
                "rule_id": row["rule_id"],
                "rule_family": family,
                "subject_artifact_id": row["subject_artifact_id"],
                "debt_extent": dict(row["debt_extent"]),
                "evidence_refs": list(row["evidence_refs"]),
            }
    snapshot["evaluations"] = sorted(evaluations, key=lambda row: (str(row["rule_id"]), str(row["subject_artifact_id"]), canonical_sha256(row)))
    snapshot["findings"] = [findings[key] for key in sorted(findings)]


def replay_full_g3_candidate(
    repository_root: Path | str,
    *,
    predecessor_commit: str,
    candidate_commit: str,
) -> dict[str, Any]:
    """Replay one exact predecessor/candidate pair without enforcement authority."""
    root = Path(repository_root).resolve()
    predecessor = base._commit(root, predecessor_commit)
    candidate = base._commit(root, candidate_commit)
    predecessor_tree, candidate_tree = base._tree(root, predecessor), base._tree(root, candidate)
    diff = base._changed_paths(root, predecessor, candidate)
    seed_paths = sorted({row[key] for row in diff for key in ("path", "old_path") if row.get(key)})
    new_writes = sorted({row["path"] for row in diff if not row["status"].startswith("D") and row.get("path")})

    started = time.perf_counter_ns()
    tracemalloc.start()
    p_inventory, c_inventory = base._inventory(root, predecessor), base._inventory(root, candidate)
    p_impact, p_texts, p_referrers, p_targets, p_pointer_violations, p_errors = _read_impact_evidence_bounded(
        root, commit=predecessor, inventory=p_inventory, seed_paths=seed_paths
    )
    c_impact, c_texts, c_referrers, c_targets, c_pointer_violations, c_errors = _read_impact_evidence_bounded(
        root, commit=candidate, inventory=c_inventory, seed_paths=seed_paths
    )
    impact_union = sorted(p_impact | c_impact)
    for path in impact_union:
        if path in p_inventory and path not in p_texts:
            p_texts[path] = _read_text(root, predecessor, path)
        if path in c_inventory and path not in c_texts:
            c_texts[path] = _read_text(root, candidate, path)

    p_rules_text, c_rules_text = base._show(root, predecessor, base.RULE_BUNDLE_PATH), base._show(root, candidate, base.RULE_BUNDLE_PATH)
    if p_rules_text is None or c_rules_text is None:
        raise base.FullG3ReplayError("GRT2_G3_RULE_BUNDLE_MISSING")
    try:
        p_rules, c_rules = json.loads(p_rules_text), json.loads(c_rules_text)
    except json.JSONDecodeError as exc:
        raise base.FullG3ReplayError("GRT2_G3_RULE_BUNDLE_INVALID_JSON") from exc
    if not isinstance(p_rules, Mapping) or not isinstance(c_rules, Mapping):
        raise base.FullG3ReplayError("GRT2_G3_RULE_BUNDLE_INVALID")

    p_b0, p_b0_errors = base._b0_valid(root, predecessor)
    c_b0, c_b0_errors = base._b0_valid(root, candidate)
    p_snapshot = base.build_source_bound_snapshot(
        commit=predecessor,
        tree=predecessor_tree,
        inventory=p_inventory,
        texts=p_texts,
        impact_paths=impact_union,
        referrers=p_referrers,
        current_targets=p_targets,
        pointer_errors=p_errors,
        rule_bundle=p_rules,
        root_registry=base._json(root, predecessor, base.ROOT_REGISTRY_PATH),
        pgn_state=base._json(root, predecessor, base.PGN_STATE_PATH),
        workflow_policy=base._json(root, predecessor, base.WORKFLOW_POLICY_PATH),
        b0_valid=p_b0,
        b0_errors=p_b0_errors,
    )
    c_snapshot = base.build_source_bound_snapshot(
        commit=candidate,
        tree=candidate_tree,
        inventory=c_inventory,
        texts=c_texts,
        impact_paths=impact_union,
        referrers=c_referrers,
        current_targets=c_targets,
        pointer_errors=c_errors,
        rule_bundle=c_rules,
        root_registry=base._json(root, candidate, base.ROOT_REGISTRY_PATH),
        pgn_state=base._json(root, candidate, base.PGN_STATE_PATH),
        workflow_policy=base._json(root, candidate, base.WORKFLOW_POLICY_PATH),
        b0_valid=c_b0,
        b0_errors=c_b0_errors,
        exact_diff_new_writes=new_writes,
        rule_bundle_changed=p_rules_text != c_rules_text,
    )
    _apply_pointer_violations(p_snapshot, violations=p_pointer_violations, rule_bundle=p_rules)
    _apply_pointer_violations(c_snapshot, violations=c_pointer_violations, rule_bundle=c_rules)

    transitions = base._transition_rows(p_snapshot, c_snapshot)
    blockers = [row for row in transitions if row["admission"] != "PASS"]
    adapter_errors = sorted(set([*p_snapshot["adapter_errors"], *c_snapshot["adapter_errors"]]))
    not_evaluable_rows = [*p_snapshot["not_evaluable"], *c_snapshot["not_evaluable"]]
    family_coverage = {
        family: "PASS"
        if p_snapshot["family_coverage"].get(family) == "EVALUATED" and c_snapshot["family_coverage"].get(family) == "EVALUATED"
        else "NOT_EVALUABLE"
        for family in base.REQUIRED_FULL_G3_RULE_FAMILIES
    }
    skipped = [family for family, status in family_coverage.items() if status != "PASS"]
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    duration_ms = max(1, (time.perf_counter_ns() - started + 999_999) // 1_000_000)

    status, reasons = "PASS", []
    if skipped:
        status = "NOT_EVALUABLE"
        reasons.append("FULL_G3_RULE_FAMILY_NOT_MATERIALIZED_FOR_REPLAY")
    if adapter_errors or not_evaluable_rows:
        status = "NOT_EVALUABLE"
        reasons.append("SOURCE_BOUND_FACT_NOT_EVALUABLE")
    if blockers:
        status = "FAIL"
        reasons.append("NEW_EXPANDED_OR_UNRESOLVED_ACTIONABLE_DEBT")
    semantic = {
        "schema": "ovc-grt2-full-g3-candidate-replay/v1",
        "predecessor_commit": predecessor,
        "predecessor_tree": predecessor_tree,
        "candidate_commit": candidate,
        "candidate_tree": candidate_tree,
        "changed_paths": diff,
        "impact_path_count": len(impact_union),
        "required_rule_families": list(base.REQUIRED_FULL_G3_RULE_FAMILIES),
        "family_coverage": family_coverage,
        "predecessor_finding_count": len(p_snapshot["findings"]),
        "candidate_finding_count": len(c_snapshot["findings"]),
        "transition_count": len(transitions),
        "new_or_expanded_debt_count": len(blockers),
        "not_evaluable_count": len(adapter_errors) + len(not_evaluable_rows) + len(skipped),
        "blocking_transitions": blockers,
        "transitions": transitions,
        "adapter_errors": adapter_errors,
        "pointer_violation_count": len(p_pointer_violations) + len(c_pointer_violations),
        "status": status,
        "reason_codes": sorted(set(reasons)),
        "authority_effect": "NONE_FULL_G3_SHADOW_REPLAY_ONLY",
        "active_enforcement": "UNCHANGED_LIMITED_G2_5_ONLY",
        "debt_floor_generation": None,
    }
    return {
        **semantic,
        "performance": {
            "surface": "GRT_EXACT",
            "duration_ms": int(duration_ms),
            "peak_memory_bytes": int(peak),
            "status": "MEASURED_NOT_YET_COMPARED_TO_FROZEN_BUDGET",
        },
        "canonical_hash": canonical_sha256(semantic),
    }


REQUIRED_FULL_G3_RULE_FAMILIES = base.REQUIRED_FULL_G3_RULE_FAMILIES
FullG3ReplayError = base.FullG3ReplayError
