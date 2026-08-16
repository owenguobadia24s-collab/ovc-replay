from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Mapping

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_routing import validate_vit_lineage_record

AA0_BACKGROUND_REUSABLE = "AA0_BACKGROUND_REUSABLE"
AA1_PROSPECTIVE_TREE_BOUND = "AA1_PROSPECTIVE_TREE_BOUND"
AA2_MATERIALISATION_EDGE = "AA2_MATERIALISATION_EDGE"
AA3_POST_WRITE_EQUIVALENCE = "AA3_POST_WRITE_EQUIVALENCE"
AA0_REUSE_SCHEMA = "ovc-vit-aa0-reuse-authorization/v1"

VIT_CONTROLLER = "DSAI_VIT_PHYSICAL_CONTROLLER"
SIQ_GATEWAY = "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY"
REQUIRED_MAIN_CHECK = "OVC merge readiness"

REUSABLE_HEAD_MOVEMENT_CLASSES = frozenset({"IRRELEVANT", "INTEGRATION_RELEVANT"})


class AssuranceDecouplingError(ValueError):
    """Raised when assurance reuse or physical-main exclusivity cannot be proven."""


def _canonical_record_id(payload: Mapping[str, Any]) -> str:
    logical = {key: value for key, value in payload.items() if key != "authorization_id"}
    return canonical_sha256(logical, role="OVC_VIT_AA0_REUSE_AUTHORIZATION")


def _validate_head_movement_receipt(receipt: Mapping[str, Any]) -> None:
    if receipt.get("schema") != "ovc-parallel-development-head-movement-receipt/v1":
        raise AssuranceDecouplingError("AA0_REUSE_HEAD_MOVEMENT_SCHEMA_INVALID")
    recorded = str(receipt.get("receipt_sha256", ""))
    logical = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    expected = canonical_sha256(logical)
    if recorded != expected:
        raise AssuranceDecouplingError("AA0_REUSE_HEAD_MOVEMENT_RECEIPT_ID_INVALID")
    if receipt.get("classification") not in REUSABLE_HEAD_MOVEMENT_CLASSES:
        raise AssuranceDecouplingError("AA0_REUSE_HEAD_MOVEMENT_NOT_REUSABLE")
    if receipt.get("scientific_evidence_reuse") != "PERMITTED_IF_BOUND_IDENTITIES_UNCHANGED":
        raise AssuranceDecouplingError("AA0_REUSE_EVIDENCE_REUSE_NOT_PERMITTED")


def build_aa0_reuse_authorization(
    *,
    previous_lineage: Mapping[str, Any],
    current_lineage: Mapping[str, Any],
    head_movement_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Authorize reuse of expensive AA0 assurance across a placement-only generation refresh."""
    previous = validate_vit_lineage_record(previous_lineage)
    current = validate_vit_lineage_record(current_lineage)
    _validate_head_movement_receipt(head_movement_receipt)

    if previous.programme_id != current.programme_id or previous.packet_id != current.packet_id:
        raise AssuranceDecouplingError("AA0_REUSE_PACKET_IDENTITY_CHANGED")
    if previous.pip_id != current.pip_id:
        raise AssuranceDecouplingError("AA0_REUSE_PIP_CHANGED")

    previous_pip = previous_lineage["pip"]
    current_pip = current_lineage["pip"]
    for field in ("dependency_frontier_id", "authority_manifest_id"):
        if previous_pip.get(field) != current_pip.get(field):
            raise AssuranceDecouplingError(f"AA0_REUSE_{field.upper()}_CHANGED")

    previous_generation = previous_lineage["generation"]
    current_generation = current_lineage["generation"]
    previous_result = previous_generation["result_tree"]["tree_sha"]
    current_predecessor = current_generation["predecessor_tree"]["tree_sha"]
    if head_movement_receipt.get("baseline_main_sha") == head_movement_receipt.get("current_main_sha"):
        raise AssuranceDecouplingError("AA0_REUSE_REQUIRES_REAL_PREDECESSOR_MOVEMENT")

    record: dict[str, Any] = {
        "schema": AA0_REUSE_SCHEMA,
        "programme_id": current.programme_id,
        "packet_id": current.packet_id,
        "payload_id": current.pip_id,
        "dependency_frontier_id": current_pip["dependency_frontier_id"],
        "authority_manifest_id": current_pip["authority_manifest_id"],
        "previous_generation_id": previous.generation_id,
        "current_generation_id": current.generation_id,
        "previous_placement_id": previous.placement_id,
        "current_placement_id": current.placement_id,
        "previous_result_tree": previous_result,
        "current_predecessor_tree": current_predecessor,
        "head_movement_receipt": dict(head_movement_receipt),
        "reuse_scope": AA0_BACKGROUND_REUSABLE,
        "reuse_disposition": "PLACEMENT_ONLY_PIP_REUSE",
        "payload_rebuild_required": False,
        "renewal_required": [
            AA1_PROSPECTIVE_TREE_BOUND,
            AA2_MATERIALISATION_EDGE,
            AA3_POST_WRITE_EQUIVALENCE,
        ],
        "authority_effect": "NONE",
    }
    record["authorization_id"] = _canonical_record_id(record)
    return record


def validate_aa0_reuse_authorization(
    record: Mapping[str, Any],
    *,
    current_lineage: Mapping[str, Any],
) -> str:
    if record.get("schema") != AA0_REUSE_SCHEMA:
        raise AssuranceDecouplingError("AA0_REUSE_SCHEMA_INVALID")
    current = validate_vit_lineage_record(current_lineage)
    current_pip = current_lineage["pip"]

    if record.get("programme_id") != current.programme_id or record.get("packet_id") != current.packet_id:
        raise AssuranceDecouplingError("AA0_REUSE_PACKET_MISMATCH")
    if record.get("payload_id") != current.pip_id:
        raise AssuranceDecouplingError("AA0_REUSE_CURRENT_PIP_MISMATCH")
    if record.get("current_generation_id") != current.generation_id:
        raise AssuranceDecouplingError("AA0_REUSE_CURRENT_GENERATION_MISMATCH")
    if record.get("current_placement_id") != current.placement_id:
        raise AssuranceDecouplingError("AA0_REUSE_CURRENT_PLACEMENT_MISMATCH")
    if record.get("dependency_frontier_id") != current_pip.get("dependency_frontier_id"):
        raise AssuranceDecouplingError("AA0_REUSE_DEPENDENCY_FRONTIER_MISMATCH")
    if record.get("authority_manifest_id") != current_pip.get("authority_manifest_id"):
        raise AssuranceDecouplingError("AA0_REUSE_AUTHORITY_MANIFEST_MISMATCH")
    if record.get("reuse_scope") != AA0_BACKGROUND_REUSABLE:
        raise AssuranceDecouplingError("AA0_REUSE_SCOPE_INVALID")
    if record.get("reuse_disposition") != "PLACEMENT_ONLY_PIP_REUSE":
        raise AssuranceDecouplingError("AA0_REUSE_DISPOSITION_INVALID")
    if record.get("payload_rebuild_required") is not False:
        raise AssuranceDecouplingError("AA0_REUSE_CANNOT_COVER_PAYLOAD_REBUILD")
    _validate_head_movement_receipt(record.get("head_movement_receipt", {}))

    expected = _canonical_record_id(record)
    if record.get("authorization_id") != expected:
        raise AssuranceDecouplingError("AA0_REUSE_AUTHORIZATION_ID_INVALID")
    return expected


def encode_reuse_authorization(record: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


@dataclass(frozen=True)
class PhysicalMainProtectionSnapshot:
    enforcement: str
    required_status_checks: tuple[str, ...]
    allowed_merge_methods: tuple[str, ...]
    bypass_actor_count: int
    pull_request_required: bool
    non_fast_forward_prohibited: bool
    deletion_prohibited: bool

    def validate(self) -> None:
        if self.enforcement != "active":
            raise AssuranceDecouplingError("PHYSICAL_MAIN_RULESET_NOT_ACTIVE")
        if REQUIRED_MAIN_CHECK not in self.required_status_checks:
            raise AssuranceDecouplingError("PHYSICAL_MAIN_VIT_READINESS_CHECK_NOT_REQUIRED")
        if set(self.allowed_merge_methods) != {"squash"}:
            raise AssuranceDecouplingError("PHYSICAL_MAIN_MERGE_METHOD_NOT_EXCLUSIVE")
        if self.bypass_actor_count != 0:
            raise AssuranceDecouplingError("PHYSICAL_MAIN_BYPASS_ACTOR_PRESENT")
        if not self.pull_request_required:
            raise AssuranceDecouplingError("PHYSICAL_MAIN_PULL_REQUEST_NOT_REQUIRED")
        if not self.non_fast_forward_prohibited:
            raise AssuranceDecouplingError("PHYSICAL_MAIN_NON_FAST_FORWARD_NOT_PROHIBITED")
        if not self.deletion_prohibited:
            raise AssuranceDecouplingError("PHYSICAL_MAIN_DELETION_NOT_PROHIBITED")


def physical_main_writer_decision(
    *,
    writer_identity: str,
    physical_gateway: str,
    vit_lineage_valid: bool,
    merge_readiness_pass: bool,
    protection: PhysicalMainProtectionSnapshot,
) -> str:
    """Fail closed unless the existing VIT controller reaches main through SIQ and protected readiness."""
    protection.validate()
    if writer_identity != VIT_CONTROLLER:
        return "DENY_NON_VIT_MAIN_WRITER"
    if physical_gateway != SIQ_GATEWAY:
        return "DENY_NON_SIQ_PHYSICAL_GATEWAY"
    if not vit_lineage_valid:
        return "DENY_MISSING_VIT_LINEAGE"
    if not merge_readiness_pass:
        return "DENY_MERGE_READINESS"
    return "ALLOW_EXISTING_VIT_SIQ_MATERIALISATION_PATH"
