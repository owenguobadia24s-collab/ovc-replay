"""GRT2-WP3D exact-context impact, proof, readiness and receipt primitives.

All functions are non-enforcing before G3.  They model exact tree/proof identity
for qualification and shadow assurance only; DSAI/PDC remain the execution and
merge-authority owners.
"""
from __future__ import annotations

import re
from collections import defaultdict, deque
from typing import Any, Mapping, Sequence

from .serialization import SERIALIZATION_ID, canonical_sha256

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
LAYERS = ("L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8")
MOVEMENT_CLASSES = {
    "NON_INTERACTING", "IMPACTING_REUSABLE", "IMPACTING_RECOMPUTE", "CONFLICTING",
    "CONSTITUTION_CHANGED", "HEAD_MOVED",
}


class IntegrationProofError(ValueError):
    pass


def _sha(value: Any, *, kind: str = "commit") -> str:
    if not isinstance(value, str) or not _HEX40.fullmatch(value):
        raise IntegrationProofError(f"GRT_{kind.upper()}_IDENTITY_INVALID")
    return value


def build_cache_key(
    *, layer_id: str, input_hashes: Sequence[str], runtime_release_hash: str,
    scanner_hash: str, constitution_hash: str, registry_hashes: Sequence[str], serializer_version: str = SERIALIZATION_ID,
) -> str:
    if layer_id not in LAYERS:
        raise IntegrationProofError("GRT_CACHE_LAYER_INVALID")
    for digest in [runtime_release_hash, scanner_hash, constitution_hash, *registry_hashes, *input_hashes]:
        if not isinstance(digest, str) or not _HEX64.fullmatch(digest):
            raise IntegrationProofError("GRT_CACHE_HASH_INVALID")
    return canonical_sha256({
        "layer_id": layer_id,
        "input_tree_or_partition_hashes": sorted(input_hashes),
        "runtime_release_hash": runtime_release_hash,
        "scanner_hash": scanner_hash,
        "constitution_hash": constitution_hash,
        "relevant_registry_hashes": sorted(registry_hashes),
        "serializer_version": serializer_version,
    })


def compute_impact_closure(changed_artifact_ids: Sequence[str], edges: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    graph: dict[str, set[str]] = defaultdict(set)
    ambiguous = False
    for edge in edges:
        source, target = edge.get("source_artifact_id"), edge.get("target_artifact_id")
        if not isinstance(source, str) or not source or not isinstance(target, str) or not target:
            ambiguous = True
            continue
        if edge.get("status", "RESOLVED") != "RESOLVED":
            ambiguous = True
            continue
        graph[source].add(target)
        if edge.get("bidirectional") is True:
            graph[target].add(source)
    seen = set(changed_artifact_ids)
    queue = deque(sorted(seen))
    while queue:
        current = queue.popleft()
        for nxt in sorted(graph.get(current, ())):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return {
        "changed_artifact_ids": sorted(set(changed_artifact_ids)),
        "affected_artifact_ids": sorted(seen),
        "escalation": "FULL_REFERENCE" if ambiguous else "BOUNDED_CLOSURE",
        "reason_codes": ["AMBIGUOUS_IMPACT_BOUNDARY"] if ambiguous else [],
        "authority_effect": "NONE_IMPACT_ONLY",
    }


def build_integration_context(
    *, base_commit: str, base_tree: str, head_commit: str, head_tree: str, integration_tree: str,
    merge_strategy: str, constitution_hash: str, runtime_hash: str, scanner_hash: str,
    debt_floor_generation: int | None, debt_floor_hash: str | None,
) -> dict[str, Any]:
    for value, kind in ((base_commit, "base_commit"), (base_tree, "base_tree"), (head_commit, "head_commit"), (head_tree, "head_tree"), (integration_tree, "integration_tree")):
        _sha(value, kind=kind)
    if merge_strategy not in {"SQUASH", "MERGE", "REBASE"}:
        raise IntegrationProofError("GRT_MERGE_STRATEGY_INVALID")
    for value in (constitution_hash, runtime_hash, scanner_hash):
        if not _HEX64.fullmatch(str(value)):
            raise IntegrationProofError("GRT_RUNTIME_CONSTITUTION_HASH_INVALID")
    if debt_floor_generation is None:
        if debt_floor_hash is not None:
            raise IntegrationProofError("GRT_DEBT_FLOOR_PRE_G3_INCONSISTENT")
    elif isinstance(debt_floor_generation, bool) or not isinstance(debt_floor_generation, int) or debt_floor_generation < 0 or not _HEX64.fullmatch(str(debt_floor_hash)):
        raise IntegrationProofError("GRT_DEBT_FLOOR_IDENTITY_INVALID")
    body = {
        "schema": "grt-integration-context/v0.2",
        "base_commit": base_commit, "base_tree": base_tree,
        "head_commit": head_commit, "head_tree": head_tree,
        "merge_strategy": merge_strategy, "prospective_integration_tree": integration_tree,
        "constitution_hash": constitution_hash, "runtime_hash": runtime_hash, "scanner_hash": scanner_hash,
        "debt_floor_generation": debt_floor_generation, "debt_floor_hash": debt_floor_hash,
        "authority_effect": "NONE_SHADOW_INTEGRATION_CONTEXT",
    }
    return {**body, "context_hash": canonical_sha256(body)}


def build_conformance_proof(
    *, context: Mapping[str, Any], result: str, findings_hash: str, debt_hash: str,
    evidence_hash: str, qualification_status: str = "SHADOW_CANDIDATE",
) -> dict[str, Any]:
    if result not in {"PASS", "FAIL", "OPERATOR_REQUIRED", "INVALID", "NOT_EVALUABLE"}:
        raise IntegrationProofError("GRT_PROOF_RESULT_INVALID")
    for value in (findings_hash, debt_hash, evidence_hash):
        if not _HEX64.fullmatch(str(value)):
            raise IntegrationProofError("GRT_PROOF_EVIDENCE_HASH_INVALID")
    body = {
        "schema": "grt-conformance-proof/v0.2",
        "context_hash": context.get("context_hash"),
        "base_commit": context.get("base_commit"), "base_tree": context.get("base_tree"),
        "head_commit": context.get("head_commit"), "head_tree": context.get("head_tree"),
        "integration_tree": context.get("prospective_integration_tree"),
        "constitution_hash": context.get("constitution_hash"), "runtime_hash": context.get("runtime_hash"),
        "scanner_hash": context.get("scanner_hash"), "debt_floor_generation": context.get("debt_floor_generation"),
        "debt_floor_hash": context.get("debt_floor_hash"), "findings_hash": findings_hash,
        "debt_hash": debt_hash, "evidence_hash": evidence_hash,
        "result": result, "qualification_status": qualification_status,
        "authority_effect": "NONE_SHADOW_PROOF_PRE_G3",
    }
    return {**body, "proof_hash": canonical_sha256(body)}


def classify_movement(
    *, proof: Mapping[str, Any], current_main_commit: str, current_head_commit: str,
    current_integration_tree: str, changed_artifact_ids: Sequence[str] = (), impact_artifact_ids: Sequence[str] = (),
    semantic_partition_hash_equal: bool = False, constitution_hash: str | None = None, merge_conflict: bool = False,
) -> str:
    _sha(current_main_commit, kind="current_main")
    _sha(current_head_commit, kind="current_head")
    _sha(current_integration_tree, kind="current_integration_tree")
    if merge_conflict:
        return "CONFLICTING"
    if constitution_hash is not None and constitution_hash != proof.get("constitution_hash"):
        return "CONSTITUTION_CHANGED"
    if current_head_commit != proof.get("head_commit"):
        return "HEAD_MOVED"
    if current_main_commit == proof.get("base_commit") and current_integration_tree == proof.get("integration_tree"):
        return "NON_INTERACTING"
    impact = set(impact_artifact_ids)
    if set(changed_artifact_ids).isdisjoint(impact):
        return "NON_INTERACTING"
    if semantic_partition_hash_equal:
        return "IMPACTING_REUSABLE"
    return "IMPACTING_RECOMPUTE"


def evaluate_readiness(
    *, proof: Mapping[str, Any], current_main_commit: str, current_head_commit: str,
    current_integration_tree: str, movement_class: str,
) -> dict[str, Any]:
    if movement_class not in MOVEMENT_CLASSES:
        raise IntegrationProofError("GRT_MOVEMENT_CLASS_INVALID")
    exact_match = (
        proof.get("result") == "PASS"
        and current_main_commit == proof.get("base_commit")
        and current_head_commit == proof.get("head_commit")
        and current_integration_tree == proof.get("integration_tree")
    )
    ready = exact_match and movement_class == "NON_INTERACTING"
    return {
        "schema": "grt-integration-readiness/v0.2",
        "proof_hash": proof.get("proof_hash"),
        "current_main_commit": current_main_commit,
        "current_head_commit": current_head_commit,
        "current_integration_tree": current_integration_tree,
        "movement_class": movement_class,
        "status": "READY" if ready else "RENEW_REQUIRED",
        "reason_codes": [] if ready else ["EXACT_CONTEXT_MOVED_OR_PROOF_NOT_PASS"],
        "authority_effect": "NONE_READINESS_ONLY_PRE_G3",
    }


def build_post_merge_receipt(
    *, proof: Mapping[str, Any], actual_merge_commit: str, actual_merge_tree: str,
    new_debt_floor_generation: int | None = None, new_debt_floor_hash: str | None = None,
) -> dict[str, Any]:
    _sha(actual_merge_commit, kind="actual_merge_commit")
    _sha(actual_merge_tree, kind="actual_merge_tree")
    tree_equal = actual_merge_tree == proof.get("integration_tree")
    if not tree_equal:
        status, reason_codes = "INCIDENT", ["POST_MERGE_TREE_MISMATCH"]
    else:
        status, reason_codes = "VERIFIED", []
    if proof.get("debt_floor_generation") is None and new_debt_floor_generation is not None:
        raise IntegrationProofError("GRT_PRE_G3_RECEIPT_CANNOT_CREATE_DEBT_FLOOR")
    body = {
        "schema": "grt-conformance-receipt/v0.2",
        "proof_hash": proof.get("proof_hash"), "actual_merge_commit": actual_merge_commit,
        "actual_merge_tree": actual_merge_tree, "proved_integration_tree": proof.get("integration_tree"),
        "post_merge_tree_equal": tree_equal, "status": status, "reason_codes": reason_codes,
        "new_debt_floor_generation": new_debt_floor_generation, "new_debt_floor_hash": new_debt_floor_hash,
        "authority_effect": "NONE_RECEIPT_ONLY_PRE_G3",
    }
    return {**body, "receipt_hash": canonical_sha256(body)}
