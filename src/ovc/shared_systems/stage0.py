"""Shared Systems Stage-0 bootstrap proof.

This module is intentionally restricted to Python standard-library primitives.
It must not import the steady-state Shared Systems registry/resolution/runtime,
GRT runtime, or DSAI execution/security runtime.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence

PROGRAMME_ID = "OVC-SHARED-SYSTEMS-v0.1"
PLAN_ID = "OVC-SHARED-SYSTEMS-CONFORMANCE-IMPLEMENTATION-PLAN-0.2-R1"
DESIGN_ID = "OVC-SHARED-SYSTEMS-DESIGN-SPEC-0.1-R1"
G0A_DECISION_ID = "SHSI-G0A-RATIFICATION-v0.2-R1"
BINDING_ID = "GRT.SHARED_SERVICE_BINDING.OVC_SHARED_SYSTEMS.v0.1"
EXPECTED_OWNER = PROGRAMME_ID
EXPECTED_SERVICE = PROGRAMME_ID
EXPECTED_BINDING_HASH = "46e4d03f56c1dd27fbdc0828c30b1910fc4b7510ec56bdb7b089edc1e2780945"

BOOTSTRAP_NODES = (
    "B0_IMMUTABLE_PRIMITIVES",
    "B1_BOOTSTRAP_VALIDATION_MANIFEST",
    "B2_DESIGN_CONTRACT_BUNDLE_VALIDATION",
    "B3_GRT_REPOSITORY_CLASSIFICATION_BINDING",
    "B4_EXACT_SHARED_SERVICE_BINDING",
    "B5_SHARED_REGISTRY_RESOLUTION_RUNTIME",
    "B6_CONSUMER_MIGRATION_RUNTIME_ADOPTION",
)

NORMATIVE_EDGES = tuple(zip(BOOTSTRAP_NODES, BOOTSTRAP_NODES[1:]))

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class SharedSystemsStage0Error(ValueError):
    """Fail-closed Stage-0 proof error."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def logical_hash(value: Any) -> str:
    return sha256_hex(canonical_json_bytes(value))


def _require_hex(value: str, *, length: int, field: str) -> None:
    pattern = _HEX40 if length == 40 else _HEX64
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise SharedSystemsStage0Error(f"{field}_INVALID")


def canonical_hash_without(value: Mapping[str, Any], field: str) -> str:
    payload = deepcopy(dict(value))
    payload.pop(field, None)
    return logical_hash(payload)


def topological_order(
    nodes: Sequence[str], edges: Iterable[tuple[str, str]]
) -> tuple[str, ...]:
    node_set = set(nodes)
    indegree = {node: 0 for node in nodes}
    outgoing = {node: [] for node in nodes}
    for source, target in edges:
        if source not in node_set or target not in node_set:
            raise SharedSystemsStage0Error("BOOTSTRAP_UNKNOWN_NODE")
        outgoing[source].append(target)
        indegree[target] += 1

    ready = [node for node in nodes if indegree[node] == 0]
    order: list[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for target in outgoing[node]:
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)

    if len(order) != len(nodes):
        raise SharedSystemsStage0Error("BOOTSTRAP_CYCLE")
    return tuple(order)


def validate_bootstrap_graph(
    edges: Iterable[tuple[str, str]],
) -> tuple[str, ...]:
    edges_tuple = tuple(edges)
    allowed = set(NORMATIVE_EDGES)
    observed = set(edges_tuple)
    if observed != allowed:
        unexpected = sorted(observed - allowed)
        missing = sorted(allowed - observed)
        if unexpected:
            raise SharedSystemsStage0Error(
                "BOOTSTRAP_FORBIDDEN_OR_UNDECLARED_EDGE:" + repr(unexpected)
            )
        raise SharedSystemsStage0Error(
            "BOOTSTRAP_MANDATORY_EDGE_MISSING:" + repr(missing)
        )
    order = topological_order(BOOTSTRAP_NODES, edges_tuple)
    if order != BOOTSTRAP_NODES:
        raise SharedSystemsStage0Error("BOOTSTRAP_TOPOLOGY_MISMATCH")
    return order


def verify_binding_registry(registry: Mapping[str, Any]) -> dict[str, Any]:
    if registry.get("schema") != "grt-governance-binding-registry/v0.2":
        raise SharedSystemsStage0Error("BINDING_SCHEMA_MISMATCH")
    if registry.get("conflicts") not in ([], ()):
        raise SharedSystemsStage0Error("OWNER_BINDING_CONFLICT")
    stored_hash = registry.get("canonical_hash")
    if stored_hash != EXPECTED_BINDING_HASH:
        raise SharedSystemsStage0Error("BINDING_HASH_GENERATION_MISMATCH")
    if canonical_hash_without(registry, "canonical_hash") != stored_hash:
        raise SharedSystemsStage0Error("BINDING_CANONICAL_HASH_MISMATCH")

    matches = [
        item
        for item in registry.get("shared_service_bindings", [])
        if item.get("service_id") == EXPECTED_SERVICE
    ]
    if len(matches) != 1:
        raise SharedSystemsStage0Error("OWNER_BINDING_CARDINALITY_INVALID")
    binding = matches[0]
    expected = {
        "binding_id": BINDING_ID,
        "service_id": EXPECTED_SERVICE,
        "owner_programme_id": EXPECTED_OWNER,
        "binding_status": "RESOLVED",
        "service_state": "INACTIVE_NOT_IMPLEMENTED",
        "authority_effect": "NONE_GOVERNANCE_PROJECTION",
    }
    for key, value in expected.items():
        if binding.get(key) != value:
            raise SharedSystemsStage0Error(f"BINDING_{key.upper()}_MISMATCH")
    if binding.get("consumer_programmes") not in ([], ()):
        raise SharedSystemsStage0Error("STAGE0_ACTIVE_CONSUMER_UNEXPECTED")
    return deepcopy(binding)


def verify_operator_decision(decision: Mapping[str, Any]) -> None:
    if decision.get("decision_id") != G0A_DECISION_ID:
        raise SharedSystemsStage0Error("G0A_DECISION_ID_MISMATCH")
    if decision.get("decision") != "PASS":
        raise SharedSystemsStage0Error("G0A_NOT_PASS")
    if decision.get("programme_id") != PROGRAMME_ID:
        raise SharedSystemsStage0Error("G0A_PROGRAMME_MISMATCH")
    envelope = decision.get("effective_authority_envelope") or {}
    if envelope.get("envelope_id") != "SHSI-AE-v0.2-R1":
        raise SharedSystemsStage0Error("G0A_AUTHORITY_ENVELOPE_MISMATCH")
    if "SHSI-WP0" not in envelope.get("authorized_sequence", []):
        raise SharedSystemsStage0Error("G0A_WP0_NOT_AUTHORIZED")


def build_stage0_proof(
    *,
    design_sha256: str,
    plan_sha256: str,
    operator_decision: Mapping[str, Any],
    binding_registry: Mapping[str, Any],
    baseline_commit: str,
    baseline_tree: str,
    edges: Iterable[tuple[str, str]] = NORMATIVE_EDGES,
) -> dict[str, Any]:
    _require_hex(design_sha256, length=64, field="DESIGN_SHA256")
    _require_hex(plan_sha256, length=64, field="PLAN_SHA256")
    _require_hex(baseline_commit, length=40, field="BASELINE_COMMIT")
    _require_hex(baseline_tree, length=40, field="BASELINE_TREE")
    verify_operator_decision(operator_decision)
    binding = verify_binding_registry(binding_registry)
    order = validate_bootstrap_graph(edges)

    payload = {
        "schema": "ovc-shared-systems-stage0-proof/v1",
        "programme_id": PROGRAMME_ID,
        "plan_id": PLAN_ID,
        "design_id": DESIGN_ID,
        "design_sha256": design_sha256,
        "plan_sha256": plan_sha256,
        "operator_decision_id": G0A_DECISION_ID,
        "authority_envelope_id": "SHSI-AE-v0.2-R1",
        "baseline_commit": baseline_commit,
        "baseline_tree": baseline_tree,
        "binding": {
            "binding_id": binding["binding_id"],
            "owner_programme_id": binding["owner_programme_id"],
            "service_state": binding["service_state"],
            "canonical_registry_hash": binding_registry["canonical_hash"],
        },
        "bootstrap": {
            "nodes": list(BOOTSTRAP_NODES),
            "edges": [list(edge) for edge in NORMATIVE_EDGES],
            "topological_order": list(order),
            "cycle_count": 0,
            "forbidden_edge_count": 0,
        },
        "runtime_state": "INACTIVE_BOOTSTRAP",
        "authority_effect": "NONE",
    }
    first = canonical_json_bytes(payload)
    second = canonical_json_bytes(json.loads(first.decode("utf-8")))
    if first != second:
        raise SharedSystemsStage0Error("BOOTSTRAP_ROUNDTRIP_MISMATCH")
    payload["proof_hash"] = sha256_hex(first)
    return payload


def stage1_ready(*, current_gate: str, g0b_status: str) -> bool:
    return current_gate == "SHSI-G1" and g0b_status == "COMPLETED"
