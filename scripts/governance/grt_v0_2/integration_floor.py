"""Deterministic GRT DebtFloor projection owned by VIT materialisation.

The active GRT constitution still ratchets actionable inherited debt on every
physical-main generation.  This module changes only who materialises the next
floor: ordinary packet payloads never write GRT's singleton pointer or floor
registry.  GRT-EXACT derives the next immutable floor from the exact physical
predecessor and qualified prospective Git tree, and the serialized VIT/SIQ
materialisation transaction makes that projection effective.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256

POLICY_PATH = (
    "registries/governance/grt_v0_2/"
    "GRT_DEBTFLOOR_INTEGRATION_OWNERSHIP_v0_1.json"
)
POLICY_SCHEMA = "ovc-grt2-debt-floor-integration-ownership/v1"
POLICY_ID = "GRT2-VIT-DEBTFLOOR-INTEGRATION-OWNERSHIP-v0.1"
FLOOR_SCHEMA = "grt-integration-debt-floor/v0.2"
FLOOR_POINTER_PATH = "registries/governance/grt_v0_2/GRT_DEBT_FLOOR_CURRENT.json"
FLOOR_DIR = "registries/governance/grt_v0_2/debt_floors"
FLOOR_PATH_RE = re.compile(
    r"^registries/governance/grt_v0_2/debt_floors/GRT_DEBT_FLOOR_G[0-9]+\.json$"
)
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_FINDING_ID = re.compile(r"^GRT\.FIND\.[0-9a-f]{24}$")

# Filled from the exact canonical policy bytes.  Any future meaning-bearing
# amendment must update this code under the policy's operator-required
# amendment protocol; a candidate cannot self-amend the policy by recomputing
# its embedded hash alone.
EXPECTED_POLICY_LOGICAL_SHA256 = "779b815523b11710ad62b9295a0912db701bb27cb5e6ded9e2a0be900c4de7ec"


class IntegrationFloorError(ValueError):
    """Fail-closed policy or virtual-floor validation error."""


def _require_hex(value: Any, pattern: re.Pattern[str], reason: str) -> str:
    text = str(value)
    if not pattern.fullmatch(text):
        raise IntegrationFloorError(reason)
    return text


def _exact_string(value: Any, expected: str, reason: str) -> None:
    if value != expected:
        raise IntegrationFloorError(reason)


def validate_policy(policy: Mapping[str, Any]) -> None:
    payload = dict(policy)
    actual = str(payload.pop("logical_sha256", ""))
    _require_hex(actual, _HEX64, "GRT_INTEGRATION_FLOOR_POLICY_HASH_INVALID")
    if canonical_sha256(payload) != actual:
        raise IntegrationFloorError("GRT_INTEGRATION_FLOOR_POLICY_HASH_MISMATCH")
    if actual != EXPECTED_POLICY_LOGICAL_SHA256:
        raise IntegrationFloorError("GRT_INTEGRATION_FLOOR_POLICY_IDENTITY_NOT_PINNED")
    _exact_string(policy.get("schema"), POLICY_SCHEMA, "GRT_INTEGRATION_FLOOR_POLICY_SCHEMA_INVALID")
    _exact_string(policy.get("policy_id"), POLICY_ID, "GRT_INTEGRATION_FLOOR_POLICY_ID_INVALID")
    _exact_string(policy.get("status"), "ACTIVE", "GRT_INTEGRATION_FLOOR_POLICY_NOT_ACTIVE")
    _exact_string(
        policy.get("programme_id"),
        "OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE",
        "GRT_INTEGRATION_FLOOR_POLICY_PROGRAMME_INVALID",
    )
    _exact_string(
        policy.get("floor_materialisation_mode"),
        "VIRTUAL_EXACT_TREE_PROJECTION",
        "GRT_INTEGRATION_FLOOR_POLICY_MODE_INVALID",
    )
    _exact_string(
        policy.get("materialisation_controller"),
        "DSAI_VIT_PHYSICAL_CONTROLLER",
        "GRT_INTEGRATION_FLOOR_POLICY_CONTROLLER_INVALID",
    )
    _exact_string(
        policy.get("physical_gateway"),
        "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY",
        "GRT_INTEGRATION_FLOOR_POLICY_GATEWAY_INVALID",
    )
    anchor = policy.get("legacy_anchor")
    if not isinstance(anchor, Mapping):
        raise IntegrationFloorError("GRT_INTEGRATION_FLOOR_POLICY_ANCHOR_MISSING")
    generation = anchor.get("generation")
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
        raise IntegrationFloorError("GRT_INTEGRATION_FLOOR_POLICY_ANCHOR_GENERATION_INVALID")
    _require_hex(anchor.get("floor_hash"), _HEX64, "GRT_INTEGRATION_FLOOR_POLICY_ANCHOR_HASH_INVALID")
    _require_hex(
        anchor.get("constitution_hash"),
        _HEX64,
        "GRT_INTEGRATION_FLOOR_POLICY_CONSTITUTION_HASH_INVALID",
    )
    expected_definition = f"{FLOOR_DIR}/GRT_DEBT_FLOOR_G{generation}.json"
    _exact_string(
        anchor.get("definition"),
        expected_definition,
        "GRT_INTEGRATION_FLOOR_POLICY_ANCHOR_DEFINITION_INVALID",
    )
    _exact_string(
        anchor.get("pointer"),
        FLOOR_POINTER_PATH,
        "GRT_INTEGRATION_FLOOR_POLICY_POINTER_INVALID",
    )
    packet_contract = policy.get("ordinary_packet_contract")
    if not isinstance(packet_contract, Mapping):
        raise IntegrationFloorError("GRT_INTEGRATION_FLOOR_POLICY_PACKET_CONTRACT_MISSING")
    _exact_string(
        packet_contract.get("floor_registry_mutation"),
        "FORBIDDEN",
        "GRT_INTEGRATION_FLOOR_POLICY_PACKET_MUTATION_NOT_FORBIDDEN",
    )
    _exact_string(
        packet_contract.get("payload_rebuild_for_floor_placement"),
        "FORBIDDEN",
        "GRT_INTEGRATION_FLOOR_POLICY_PAYLOAD_REBUILD_NOT_FORBIDDEN",
    )
    _exact_string(
        packet_contract.get("placement_only_main_movement"),
        "RECOMPUTE_A1_A2_ONLY",
        "GRT_INTEGRATION_FLOOR_POLICY_PLACEMENT_RULE_INVALID",
    )


def policy_anchor(policy: Mapping[str, Any]) -> Mapping[str, Any]:
    validate_policy(policy)
    anchor = policy["legacy_anchor"]
    assert isinstance(anchor, Mapping)
    return anchor


def is_floor_control_path(path: str) -> bool:
    return path == FLOOR_POINTER_PATH or bool(FLOOR_PATH_RE.fullmatch(path))


def assert_no_packet_floor_mutation(paths: Iterable[str]) -> None:
    violations = sorted({path for path in paths if is_floor_control_path(str(path))})
    if violations:
        raise IntegrationFloorError(
            "GRT_INTEGRATION_FLOOR_PACKET_MUTATION_FORBIDDEN:" + ",".join(violations)
        )


def build_floor(
    *,
    policy: Mapping[str, Any],
    generation: int,
    predecessor_commit: str,
    predecessor_tree: str,
    result_tree: str,
    open_grandfathered_findings: Iterable[str],
) -> dict[str, Any]:
    validate_policy(policy)
    anchor = policy_anchor(policy)
    if isinstance(generation, bool) or not isinstance(generation, int):
        raise IntegrationFloorError("GRT_INTEGRATION_FLOOR_GENERATION_INVALID")
    if generation <= int(anchor["generation"]):
        raise IntegrationFloorError("GRT_INTEGRATION_FLOOR_GENERATION_NOT_AFTER_ANCHOR")
    predecessor_commit = _require_hex(
        predecessor_commit, _HEX40, "GRT_INTEGRATION_FLOOR_PREDECESSOR_COMMIT_INVALID"
    )
    predecessor_tree = _require_hex(
        predecessor_tree, _HEX40, "GRT_INTEGRATION_FLOOR_PREDECESSOR_TREE_INVALID"
    )
    result_tree = _require_hex(result_tree, _HEX40, "GRT_INTEGRATION_FLOOR_RESULT_TREE_INVALID")
    finding_ids = sorted(set(str(value) for value in open_grandfathered_findings))
    if any(not _FINDING_ID.fullmatch(value) for value in finding_ids):
        raise IntegrationFloorError("GRT_INTEGRATION_FLOOR_FINDING_ID_INVALID")
    floor = {
        "schema": FLOOR_SCHEMA,
        "policy_id": POLICY_ID,
        "generation": generation,
        "predecessor_commit": predecessor_commit,
        "predecessor_tree": predecessor_tree,
        "result_tree": result_tree,
        "constitution_hash": str(anchor["constitution_hash"]),
        "legacy_anchor_floor_hash": str(anchor["floor_hash"]),
        "open_grandfathered_findings": finding_ids,
        "historical_non_debt": [],
        "quarantined_findings": [],
        "temporarily_admitted_actionable": [],
        "materialisation_controller": str(policy["materialisation_controller"]),
        "physical_gateway": str(policy["physical_gateway"]),
        "authority_effect": "NONE_EXACT_TREE_INTEGRATION_PROJECTION",
    }
    floor["floor_hash"] = canonical_sha256(floor)
    validate_floor(floor, policy=policy)
    return floor


def validate_floor(floor: Mapping[str, Any], *, policy: Mapping[str, Any]) -> None:
    validate_policy(policy)
    payload = dict(floor)
    actual = str(payload.pop("floor_hash", ""))
    _require_hex(actual, _HEX64, "GRT_INTEGRATION_FLOOR_HASH_INVALID")
    if canonical_sha256(payload) != actual:
        raise IntegrationFloorError("GRT_INTEGRATION_FLOOR_HASH_MISMATCH")
    _exact_string(floor.get("schema"), FLOOR_SCHEMA, "GRT_INTEGRATION_FLOOR_SCHEMA_INVALID")
    _exact_string(floor.get("policy_id"), POLICY_ID, "GRT_INTEGRATION_FLOOR_POLICY_BINDING_INVALID")
    anchor = policy_anchor(policy)
    generation = floor.get("generation")
    if isinstance(generation, bool) or not isinstance(generation, int) or generation <= int(anchor["generation"]):
        raise IntegrationFloorError("GRT_INTEGRATION_FLOOR_GENERATION_INVALID")
    for field, reason in (
        ("predecessor_commit", "GRT_INTEGRATION_FLOOR_PREDECESSOR_COMMIT_INVALID"),
        ("predecessor_tree", "GRT_INTEGRATION_FLOOR_PREDECESSOR_TREE_INVALID"),
        ("result_tree", "GRT_INTEGRATION_FLOOR_RESULT_TREE_INVALID"),
    ):
        _require_hex(floor.get(field), _HEX40, reason)
    _exact_string(
        floor.get("constitution_hash"),
        anchor["constitution_hash"],
        "GRT_INTEGRATION_FLOOR_CONSTITUTION_MISMATCH",
    )
    _exact_string(
        floor.get("legacy_anchor_floor_hash"),
        anchor["floor_hash"],
        "GRT_INTEGRATION_FLOOR_ANCHOR_HASH_MISMATCH",
    )
    _exact_string(
        floor.get("materialisation_controller"),
        policy["materialisation_controller"],
        "GRT_INTEGRATION_FLOOR_CONTROLLER_MISMATCH",
    )
    _exact_string(
        floor.get("physical_gateway"),
        policy["physical_gateway"],
        "GRT_INTEGRATION_FLOOR_GATEWAY_MISMATCH",
    )
    groups = []
    for key in (
        "open_grandfathered_findings",
        "historical_non_debt",
        "quarantined_findings",
        "temporarily_admitted_actionable",
    ):
        value = floor.get(key)
        if not isinstance(value, list) or value != sorted(set(str(item) for item in value)):
            raise IntegrationFloorError(f"GRT_INTEGRATION_FLOOR_STATE_SET_INVALID:{key}")
        groups.append(set(value))
    if any(groups[i] & groups[j] for i in range(len(groups)) for j in range(i + 1, len(groups))):
        raise IntegrationFloorError("GRT_INTEGRATION_FLOOR_STATE_OVERLAP")
    if any(not _FINDING_ID.fullmatch(value) for value in groups[0]):
        raise IntegrationFloorError("GRT_INTEGRATION_FLOOR_FINDING_ID_INVALID")


__all__ = [
    "EXPECTED_POLICY_LOGICAL_SHA256",
    "FLOOR_DIR",
    "FLOOR_POINTER_PATH",
    "FLOOR_SCHEMA",
    "IntegrationFloorError",
    "POLICY_ID",
    "POLICY_PATH",
    "POLICY_SCHEMA",
    "assert_no_packet_floor_mutation",
    "build_floor",
    "is_floor_control_path",
    "policy_anchor",
    "validate_floor",
    "validate_policy",
]
