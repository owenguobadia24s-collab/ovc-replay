"""ATLAS-WP10 qualification, capacity, and retention controls.

The helpers in this module are deliberately read-only with respect to the
repository and source programmes. Publication proofs target an isolated
shadow root, and retention evaluation can report candidates but never delete
them.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import tracemalloc
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .canonical import canonical_sha256
from .core import build_system_graph
from .generation import (
    GenerationBundle,
    build_incremental_generation,
    build_reference_generation,
    publish_current_generation,
    verify_generation_bundle,
)
from .query import AtlasQueryIndex, execute_optimized_query
from .store import GraphStore


class AtlasQualificationError(ValueError):
    """Raised when qualification input crosses a frozen WP10 boundary."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise AtlasQualificationError(code)


def _file_sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _elapsed_ms(start_ns: int) -> int:
    return max(1, (time.perf_counter_ns() - start_ns + 999_999) // 1_000_000)


def validate_live_shadow_binding(binding: Mapping[str, Any], repository_root: Path | str) -> dict[str, Any]:
    """Verify that every declared workbench source is in one exact Git tree."""

    root = Path(repository_root)
    _require(binding.get("schema") == "ovc-atlas-live-shadow-binding/v1", "ATLAS_LIVE_SHADOW_SCHEMA_INVALID")
    _require(binding.get("qualification_class") == "ACTUAL_REPOSITORY_LIVE_SHADOW", "ATLAS_LIVE_SHADOW_CLASS_INVALID")
    _require(binding.get("reality_class") == "CURRENT", "ATLAS_LIVE_SHADOW_REALITY_INVALID")
    _require(binding.get("authority_effect") == "NONE_PRESENTATION_ONLY", "ATLAS_LIVE_SHADOW_AUTHORITY_INVALID")
    _require(binding.get("current_pointer_published") is False, "ATLAS_LIVE_SHADOW_PUBLICATION_FORBIDDEN")
    _require(binding.get("research_console_binding_created") is False, "ATLAS_LIVE_SHADOW_CONSOLE_BINDING_FORBIDDEN")
    commit = str(binding.get("source_commit", ""))
    tree = str(binding.get("source_tree", ""))

    def git(*arguments: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        _require(completed.returncode == 0, f"ATLAS_LIVE_SHADOW_GIT_FAILURE:{arguments[0]}")
        return completed.stdout.strip()

    _require(git("rev-parse", f"{commit}^{{tree}}") == tree, "ATLAS_LIVE_SHADOW_TREE_MISMATCH")
    contract = binding.get("projection_contract", {})
    contract_path = str(contract.get("path", ""))
    _require(git("rev-parse", f"{commit}:{contract_path}") == contract.get("blob"), "ATLAS_LIVE_SHADOW_CONTRACT_MISMATCH")
    rows = list(binding.get("source_bindings", []))
    _require(bool(rows), "ATLAS_LIVE_SHADOW_SOURCES_REQUIRED")
    _require(len({row.get("node_id") for row in rows}) == len(rows), "ATLAS_LIVE_SHADOW_NODE_DUPLICATE")
    for row in rows:
        path = str(row.get("path", ""))
        _require(git("rev-parse", f"{commit}:{path}") == row.get("blob"), f"ATLAS_LIVE_SHADOW_SOURCE_MISMATCH:{path}")
    body = {
        "schema": "ovc-atlas-live-shadow-validation-receipt/v1",
        "source_commit": commit,
        "source_tree": tree,
        "source_binding_count": len(rows),
        "result": "PASS_EXACT_GIT_TREE_LIVE_SHADOW",
        "authority_effect": "NONE_VALIDATION_ONLY",
    }
    return {**body, "receipt_hash": canonical_sha256(body)}


def build_exact_git_shadow_graph(
    source_graph: Mapping[str, Any],
    registries: Mapping[str, Any],
    *,
    repository_root: Path | str,
    repository_commit: str,
    repository_tree: str,
    graph_id: str,
    generation_id: str,
    completeness_profile: str,
) -> dict[str, Any]:
    """Rebind an existing semantic fixture to exact Git evidence for shadow use."""

    root = Path(repository_root)

    def git(specification: str, failure: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", specification],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        _require(completed.returncode == 0, failure)
        return completed.stdout.strip()

    _require(git(f"{repository_commit}^{{tree}}", "ATLAS_SHADOW_COMMIT_UNRESOLVED") == repository_tree, "ATLAS_SHADOW_TREE_MISMATCH")
    generation = deepcopy(source_graph["generation"])
    generation.update(
        generation_id=generation_id,
        repository_commit=repository_commit,
        repository_tree=repository_tree,
        generation_class="REFERENCE",
        authority_effect="NONE",
    )
    evidence = deepcopy(source_graph["evidence_references"])
    for row in evidence:
        path = row["source_path"]
        row["repository_commit"] = repository_commit
        row["repository_tree"] = repository_tree
        row["source_blob_sha"] = git(f"{repository_commit}:{path}", f"ATLAS_SHADOW_SOURCE_UNRESOLVED:{path}")
    return build_system_graph(
        graph_id=graph_id,
        generation=generation,
        entities=source_graph["entities"],
        relationships=source_graph["relationships"],
        assertions=source_graph["assertions"],
        evidence_references=evidence,
        conflicts=source_graph["conflicts"],
        registry_versions=source_graph["registry_versions"],
        completeness_profile=completeness_profile,
        court_record_status="EXACT_GIT_TREE",
        registries=registries,
    )


def evaluate_operational_budget(budget: Mapping[str, Any], observations: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate all frozen dimensions without sampling or dropping evidence."""

    _require(budget.get("schema") == "ovc-atlas-operational-budget/v1", "ATLAS_OPERATIONAL_BUDGET_SCHEMA_INVALID")
    _require(budget.get("status") == "FROZEN_ATLAS_G10", "ATLAS_OPERATIONAL_BUDGET_NOT_FROZEN")
    required = list(budget.get("required_dimensions", []))
    limits = budget.get("limits", {})
    _require(required and set(required) == set(limits), "ATLAS_OPERATIONAL_BUDGET_DIMENSIONS_INVALID")
    _require(set(observations.get("measurements", {})) == set(required), "ATLAS_OPERATIONAL_OBSERVATIONS_INCOMPLETE")
    environment_pass = observations.get("environment") == budget.get("required_environment")
    dimensions = []
    for name in required:
        specification = limits[name]
        observed = observations["measurements"][name]
        _require(isinstance(observed, int) and not isinstance(observed, bool) and observed >= 0, f"ATLAS_OPERATIONAL_MEASUREMENT_INVALID:{name}")
        maximum = specification.get("maximum")
        _require(isinstance(maximum, int) and maximum >= 0, f"ATLAS_OPERATIONAL_LIMIT_INVALID:{name}")
        dimensions.append({
            "dimension": name,
            "unit": specification.get("unit"),
            "observed": observed,
            "maximum": maximum,
            "result": "PASS" if observed <= maximum else "CAPACITY_EXCEEDED",
        })
    passed = environment_pass and all(row["result"] == "PASS" for row in dimensions)
    body = {
        "schema": "ovc-atlas-operational-budget-receipt/v1",
        "budget_id": budget.get("budget_id"),
        "environment": observations.get("environment"),
        "environment_result": "PASS" if environment_pass else "CAPACITY_EXCEEDED",
        "dimensions": dimensions,
        "result": "PASS" if passed else "CAPACITY_EXCEEDED",
        "completeness": "COMPLETE" if passed else "INCOMPLETE_DEGRADED",
        "sampling": "FORBIDDEN_NOT_USED",
        "protected_security_evidence": "PRESERVED_NOT_DROPPED",
        "authority_effect": "NONE_QUALIFICATION_ONLY",
    }
    return {**body, "receipt_hash": canonical_sha256(body)}


def measure_operational_profile(
    graph: Mapping[str, Any],
    registries: Mapping[str, Any],
    *,
    predecessor_bundle: GenerationBundle,
    working_directory: Path | str,
    ordinary_queries: Sequence[Mapping[str, Any]],
    analytical_queries: Sequence[Mapping[str, Any]],
    browser_render_layout_ms: int,
    browser_bundle_growth_bytes: int,
    repository_root: Path | str | None = None,
) -> tuple[dict[str, Any], GenerationBundle]:
    """Measure the frozen operational dimensions on the current Windows runner."""

    _require(ordinary_queries and analytical_queries, "ATLAS_OPERATIONAL_QUERY_PROFILES_REQUIRED")
    _require(browser_render_layout_ms >= 0 and browser_bundle_growth_bytes >= 0, "ATLAS_BROWSER_MEASUREMENT_INVALID")
    working = Path(working_directory)
    working.mkdir(parents=True, exist_ok=True)
    tracemalloc.start()
    try:
        started = time.perf_counter_ns()
        reference = build_reference_generation(graph, registries, repository_root=repository_root, predecessor_root_hash=predecessor_bundle.root_hash)
        full_build_ms = _elapsed_ms(started)

        started = time.perf_counter_ns()
        incremental = build_incremental_generation(graph, registries, previous_bundle=predecessor_bundle, repository_root=repository_root)
        incremental_build_ms = _elapsed_ms(started)
        _require(reference.files == incremental.files, "ATLAS_OPERATIONAL_INCREMENTAL_DIVERGENCE")

        started = time.perf_counter_ns()
        store = GraphStore(working / "atlas-wp10.sqlite3")
        store.rebuild(reference)
        _require(store.root_hash() == reference.root_hash, "ATLAS_OPERATIONAL_INDEX_ROOT_MISMATCH")
        index_load_ms = _elapsed_ms(started)

        index = AtlasQueryIndex(reference)
        partitions = ["ATLAS_PUBLIC_METADATA", "ATLAS_INTERNAL", "ATLAS_RESTRICTED"]
        started = time.perf_counter_ns()
        for query in ordinary_queries:
            result = execute_optimized_query(index, query, allowed_partitions=partitions)
            _require(result["status"] == "PASS", "ATLAS_OPERATIONAL_ORDINARY_QUERY_INCOMPLETE")
        ordinary_ms = _elapsed_ms(started)

        started = time.perf_counter_ns()
        for query in analytical_queries:
            result = execute_optimized_query(index, query, allowed_partitions=partitions)
            _require(result["status"] == "PASS", "ATLAS_OPERATIONAL_ANALYTICAL_QUERY_INCOMPLETE")
        analytical_ms = _elapsed_ms(started)

        started = time.perf_counter_ns()
        verify_generation_bundle(reference)
        manifest_ms = _elapsed_ms(started)
        _, peak_memory = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    previous_bytes = sum(len(value) for value in predecessor_bundle.files.values())
    current_bytes = sum(len(value) for value in reference.files.values())
    measurements = {
        "FULL_BUILD_MS": full_build_ms,
        "INCREMENTAL_BUILD_MS": incremental_build_ms,
        "INDEX_LOAD_MS": index_load_ms,
        "SEARCH_INSPECT_ORDINARY_TRACE_MS": ordinary_ms,
        "IMPACT_DEEP_TRAVERSAL_MS": analytical_ms,
        "PEAK_MEMORY_BYTES": peak_memory,
        "BROWSER_RENDER_LAYOUT_MS": browser_render_layout_ms,
        "BROWSER_BUNDLE_GROWTH_BYTES": browser_bundle_growth_bytes,
        "MANIFEST_MAINTENANCE_MS": manifest_ms,
    }
    return {
        "schema": "ovc-atlas-operational-observations/v1",
        "environment": "windows" if os.name == "nt" else os.name,
        "measurements": measurements,
        "reference_root_hash": reference.root_hash,
        "incremental_root_hash": incremental.root_hash,
        "reference_incremental_equivalence": "PASS_EXACT_BYTES",
        "authority_effect": "NONE_MEASUREMENT_ONLY",
    }, reference


def scan_retention_inventory(
    external_atlas_root: Path | str,
    *,
    current_root_hash: str,
    predecessor_root_hash: str,
    milestone_root_hashes: Iterable[str] = (),
) -> dict[str, Any]:
    """Inventory Atlas-owned storage without changing any retained object."""

    root = Path(external_atlas_root)
    generation_root = root / "generations"
    generation_directories = sorted(
        path for path in generation_root.iterdir() if path.is_dir() and len(path.name) == 64
    ) if generation_root.is_dir() else []
    sizes = {
        path.name: sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
        for path in generation_directories
    }
    milestones = sorted(set(milestone_root_hashes))
    protected = sorted({current_root_hash, predecessor_root_hash, *milestones})
    ordinary = sorted(set(sizes) - set(protected))
    incident_files = [item for name in ("incidents", "quarantine") for item in (root / name).rglob("*") if item.is_file()] if root.exists() else []
    body = {
        "schema": "ovc-atlas-retention-inventory/v1",
        "content_addressed_generation_roots": sorted(sizes),
        "generation_sizes_bytes": sizes,
        "total_generation_bytes": sum(sizes.values()),
        "current_recovery_root_hash": current_root_hash,
        "predecessor_recovery_root_hash": predecessor_root_hash,
        "milestone_root_hashes": milestones,
        "ordinary_generation_roots": ordinary,
        "incident_quarantine_file_count": len(incident_files),
        "incident_quarantine_bytes": sum(item.stat().st_size for item in incident_files),
        "destructive_action_count": 0,
        "authority_effect": "NONE_INVENTORY_ONLY",
    }
    return {**body, "inventory_hash": canonical_sha256(body)}


def evaluate_retention_budget(budget: Mapping[str, Any], inventory: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate retention capacity and emit only a non-destructive disposition."""

    _require(budget.get("schema") == "ovc-atlas-retention-budget/v1", "ATLAS_RETENTION_BUDGET_SCHEMA_INVALID")
    _require(budget.get("status") == "FROZEN_ATLAS_G10", "ATLAS_RETENTION_BUDGET_NOT_FROZEN")
    _require(budget.get("compaction_mode") == "REPORT_ONLY_NO_DELETE", "ATLAS_RETENTION_DESTRUCTIVE_MODE_FORBIDDEN")
    _require(inventory.get("destructive_action_count") == 0, "ATLAS_RETENTION_DESTRUCTIVE_ACTION_FORBIDDEN")
    roots = set(inventory.get("content_addressed_generation_roots", []))
    current = inventory.get("current_recovery_root_hash")
    predecessor = inventory.get("predecessor_recovery_root_hash")
    milestones = set(inventory.get("milestone_root_hashes", []))
    protected = {current, predecessor, *milestones}
    recovery_pass = current in roots and predecessor in roots and current != predecessor
    milestone_pass = milestones.issubset(roots)
    total_pass = inventory.get("total_generation_bytes", -1) <= budget.get("maximum_total_generation_bytes", -2)
    ordinary = list(inventory.get("ordinary_generation_roots", []))
    ordinary_pass = len(ordinary) <= budget.get("maximum_ordinary_generation_count", -1)
    incident_pass = budget.get("incident_quarantine_retention") == "RETAIN_ALL_IMMUTABLE"
    passed = recovery_pass and milestone_pass and total_pass and ordinary_pass and incident_pass
    compaction_candidates = [] if ordinary_pass else ordinary[: max(0, len(ordinary) - budget["maximum_ordinary_generation_count"])]
    _require(not set(compaction_candidates) & protected, "ATLAS_RETENTION_PROTECTED_COMPACTION_FORBIDDEN")
    body = {
        "schema": "ovc-atlas-retention-budget-receipt/v1",
        "budget_id": budget.get("budget_id"),
        "inventory_hash": inventory.get("inventory_hash"),
        "dimensions": {
            "current_predecessor_recovery": "PASS" if recovery_pass else "CAPACITY_EXCEEDED",
            "milestone_retention": "PASS" if milestone_pass else "CAPACITY_EXCEEDED",
            "total_storage": "PASS" if total_pass else "CAPACITY_EXCEEDED",
            "ordinary_generation_count": "PASS" if ordinary_pass else "CAPACITY_EXCEEDED",
            "incident_quarantine_retention": "PASS" if incident_pass else "CAPACITY_EXCEEDED",
            "external_maintenance": "PASS_ATLAS_OWNED_REPORT_ONLY",
        },
        "result": "PASS" if passed else "CAPACITY_EXCEEDED_REPORT_ONLY",
        "protected_root_hashes": sorted(protected),
        "report_only_compaction_candidates": compaction_candidates,
        "destructive_action_count": 0,
        "authority_effect": "NONE_RETENTION_QUALIFICATION_ONLY",
    }
    return {**body, "receipt_hash": canonical_sha256(body)}


def prove_exact_current_publication_shadow(
    bundle: GenerationBundle,
    shadow_root: Path | str,
    *,
    current_main: Mapping[str, str],
    canonical_external_root: Path | str,
) -> dict[str, Any]:
    """Exercise the two-point publication path without touching canonical state."""

    shadow = Path(shadow_root).resolve()
    canonical = Path(canonical_external_root).resolve()
    _require(shadow != canonical, "ATLAS_PUBLICATION_SHADOW_MUST_BE_ISOLATED")
    canonical_pointer = canonical / "generations" / "CURRENT.json"
    before = _file_sha256(canonical_pointer)
    receipt = publish_current_generation(
        bundle,
        shadow,
        pre_publish_main=current_main,
        rechecked_main=current_main,
    )
    pointer_path = shadow / "generations" / "CURRENT.json"
    _require(receipt["result"] == "PASS_CURRENT_POINTER_SWITCHED", "ATLAS_EXACT_CURRENT_PUBLICATION_PROOF_FAILED")
    _require(pointer_path.is_file(), "ATLAS_PUBLICATION_SHADOW_POINTER_MISSING")
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    _require(pointer.get("root_hash") == bundle.root_hash, "ATLAS_PUBLICATION_SHADOW_ROOT_MISMATCH")
    after = _file_sha256(canonical_pointer)
    _require(before == after, "ATLAS_CANONICAL_POINTER_CHANGED_DURING_SHADOW_PROOF")
    body = {
        "schema": "ovc-atlas-exact-current-publication-shadow-receipt/v1",
        "source_commit": current_main["commit"],
        "source_tree": current_main["tree"],
        "root_hash": bundle.root_hash,
        "publication_receipt_hash": receipt["receipt_hash"],
        "result": "PASS_EXACT_CURRENT_SHADOW_ONLY",
        "canonical_pointer_before_sha256": before,
        "canonical_pointer_after_sha256": after,
        "canonical_pointer_unchanged": True,
        "canonical_publication": False,
        "authority_effect": "NONE_QUALIFICATION_ONLY",
    }
    return {**body, "receipt_hash": canonical_sha256(body)}


def build_qualification_report(
    stage_results: Mapping[str, str],
    *,
    live_shadow_receipt_hash: str,
    publication_receipt_hash: str,
    operational_receipt: Mapping[str, Any],
    retention_receipt: Mapping[str, Any],
    q6_ind_status: str,
) -> dict[str, Any]:
    """Aggregate Q0-Q6 while preserving the independent-review boundary."""

    required = [f"Q{number}" for number in range(7)]
    _require(set(stage_results) == set(required), "ATLAS_QUALIFICATION_STAGES_INCOMPLETE")
    stages_pass = all(stage_results[stage] == "PASS" for stage in required)
    budgets_pass = operational_receipt.get("result") == "PASS" and retention_receipt.get("result") == "PASS"
    _require(q6_ind_status in {"PENDING_ELIGIBLE_INDEPENDENT_REVIEW", "PASS_ELIGIBLE_INDEPENDENT_REVIEW"}, "ATLAS_Q6_IND_STATUS_INVALID")
    q6_ind_pass = q6_ind_status == "PASS_ELIGIBLE_INDEPENDENT_REVIEW"
    mechanically_complete = stages_pass and budgets_pass
    if mechanically_complete and q6_ind_pass:
        status = "ATLAS_IMPLEMENTED_QUALIFIED_LIVE_SHADOW"
        activation_eligibility = "ELIGIBLE_FOR_OPERATOR_DECISION_NOT_ACTIVATED"
    elif mechanically_complete:
        status = "ATLAS_Q0_Q6_PASS_Q6_IND_PENDING"
        activation_eligibility = "INELIGIBLE_PENDING_Q6_IND"
    else:
        status = "ATLAS_QUALIFICATION_BLOCKED"
        activation_eligibility = "INELIGIBLE_QUALIFICATION_INCOMPLETE"
    body = {
        "schema": "ovc-atlas-qualification-report/v1",
        "programme_id": "OVC-SYSTEM-ATLAS-CONFORMANCE-v0.1",
        "stage_results": dict(stage_results),
        "live_shadow_receipt_hash": live_shadow_receipt_hash,
        "exact_current_publication_shadow_receipt_hash": publication_receipt_hash,
        "operational_budget_receipt_hash": operational_receipt.get("receipt_hash"),
        "retention_budget_receipt_hash": retention_receipt.get("receipt_hash"),
        "q6_ind_status": q6_ind_status,
        "status": status,
        "activation_eligibility": activation_eligibility,
        "activation_status": "NOT_ACTIVATED_OPERATOR_GATE_REQUIRED",
        "research_console_source_binding": "ABSENT",
        "canonical_publication": False,
        "write_authority": "ABSENT",
        "validation": "LOCKED_UNCONSUMED",
        "authority_effect": "NONE_QUALIFICATION_ONLY",
    }
    return {**body, "report_hash": canonical_sha256(body)}
