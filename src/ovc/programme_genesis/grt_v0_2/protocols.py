from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Mapping

from .bootstrap import BootstrapValidationError, validate_instance
from .serialization import canonical_sha256

B0_ID = "B0"
B0_MEMBER_COUNT = 569
B0_SOURCE_COMMIT = "100b3fa342c5dee7c96a7a4e5af9e80dac3ddfe4"
B0_SOURCE_TREE = "91374c54bde0e0b61ac51705f6434d4f2b0d8417"
B0_TOPOLOGY_SHA256 = "4120468ecb1c1f484ab073c851287706f4fb45ad0e99fc355b4624094bb795f2"
B0_MEMBERSHIP_SHA256 = "3587c224c07360751923e5718c5bedb432ce4a5c8cccd4061f73dd53ef07de5d"
SCANNER_IDENTITY = f"GRT.V0.1@{B0_SOURCE_COMMIT}:{B0_SOURCE_TREE}"

_HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_RULE_ID_RE = re.compile(r"^GRT-R[0-9]{3}$")


def _parse_utc(text: str, *, field: str) -> datetime:
    if not isinstance(text, str) or not text.endswith("Z"):
        raise BootstrapValidationError(f"GRT_PROTOCOL_TIME_NOT_UTC:{field}")
    try:
        value = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise BootstrapValidationError(f"GRT_PROTOCOL_TIME_INVALID:{field}") from exc
    if value.tzinfo != timezone.utc:
        raise BootstrapValidationError(f"GRT_PROTOCOL_TIME_NOT_UTC:{field}")
    return value


def _validate_debt_extent(extent: Mapping[str, int]) -> None:
    if not extent:
        raise BootstrapValidationError("GRT_DEBT_EXTENT_INVALID")
    for key, value in extent.items():
        if not isinstance(key, str) or not key:
            raise BootstrapValidationError("GRT_DEBT_EXTENT_KEY_INVALID")
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise BootstrapValidationError(f"GRT_DEBT_EXTENT_VALUE_INVALID:{key}")


def validate_amendment_record(record: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    validate_instance(record, schema)
    status = record["status"]
    if record["source_constitution_hash"] == record["candidate_constitution_hash"]:
        raise BootstrapValidationError("GRT_AMENDMENT_NO_SEMANTIC_GENERATION_CHANGE")
    if status in {"SHADOW_EVALUATION", "GATE_READY", "APPROVED"} and not record["shadow_evidence_refs"]:
        raise BootstrapValidationError("GRT_AMENDMENT_SHADOW_EVIDENCE_REQUIRED")
    if status in {"GATE_READY", "APPROVED"}:
        if not record["finding_migration_ref"]:
            raise BootstrapValidationError("GRT_AMENDMENT_FINDING_MIGRATION_REQUIRED")
        if not record["debt_floor_migration_ref"]:
            raise BootstrapValidationError("GRT_AMENDMENT_DEBT_FLOOR_MIGRATION_REQUIRED")
    if status == "APPROVED" and not record["operator_decision_ref"]:
        raise BootstrapValidationError("GRT_AMENDMENT_OPERATOR_DECISION_REQUIRED")
    if record["activation_gate"] != "OPERATOR_REQUIRED":
        raise BootstrapValidationError("GRT_AMENDMENT_OPERATOR_GATE_REQUIRED")


def validate_override_record(record: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    validate_instance(record, schema)
    issued_at = _parse_utc(record["issued_at"], field="issued_at")
    expires_at = _parse_utc(record["expires_at"], field="expires_at")
    remediation_due = _parse_utc(record["remediation_due"], field="remediation_due")
    if expires_at <= issued_at:
        raise BootstrapValidationError("GRT_OVERRIDE_EXPIRY_NOT_AFTER_ISSUE")
    if remediation_due < issued_at:
        raise BootstrapValidationError("GRT_OVERRIDE_REMEDIATION_PRECEDES_ISSUE")
    if record["max_uses"] != 1:
        raise BootstrapValidationError("GRT_OVERRIDE_MAX_USES_NOT_ONE")
    if record["uses"] > record["max_uses"]:
        raise BootstrapValidationError("GRT_OVERRIDE_ALREADY_OVERUSED")
    if record["base_commit"] == record["candidate_commit"]:
        raise BootstrapValidationError("GRT_OVERRIDE_CANDIDATE_EQUALS_BASE")
    if record["underlying_finding_status"] != "TEMPORARILY_ADMITTED_ACTIONABLE":
        raise BootstrapValidationError("GRT_OVERRIDE_FINDING_STATUS_WEAKENED")


def validate_historical_disposition_record(record: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    validate_instance(record, schema)
    open_count = record["batch_open_b0_count"]
    member_count = record["batch_member_count"]
    if open_count == 0 and member_count > 0:
        raise BootstrapValidationError("GRT_DISPOSITION_OPEN_DENOMINATOR_ZERO")
    enhanced_required = member_count * 20 > open_count
    if enhanced_required and not record["enhanced_independent_qa_required"]:
        raise BootstrapValidationError("GRT_DISPOSITION_ENHANCED_QA_REQUIRED")
    if enhanced_required and len(record["qa_refs"]) < 2:
        raise BootstrapValidationError("GRT_DISPOSITION_INDEPENDENT_QA_EVIDENCE_REQUIRED")


def baseline_member_id(anomaly_id: str, payload_hash: str) -> str:
    if not anomaly_id.startswith("GRT.ANOM.") or not _HEX64_RE.fullmatch(payload_hash):
        raise BootstrapValidationError("GRT_B0_MEMBER_SOURCE_IDENTITY_INVALID")
    digest = canonical_sha256(
        {
            "baseline_id": B0_ID,
            "original_anomaly_id": anomaly_id,
            "payload_hash": payload_hash,
        }
    )
    return f"GRT.B0.MEMBER.{digest[:24]}"


def validate_baseline_members(rows: list[Mapping[str, Any]]) -> None:
    if len(rows) != B0_MEMBER_COUNT:
        raise BootstrapValidationError(f"GRT_B0_MEMBER_COUNT_MISMATCH:{len(rows)}")
    ids: set[str] = set()
    anomaly_ids: set[str] = set()
    payload_hashes: set[str] = set()
    ordinals: list[int] = []
    for row in rows:
        anomaly_id = str(row.get("original_GRT_anomaly", ""))
        payload_hash = str(row.get("payload_hash", ""))
        if row.get("baseline_member_id") != baseline_member_id(anomaly_id, payload_hash):
            raise BootstrapValidationError("GRT_B0_MEMBER_ID_MISMATCH")
        if row.get("original_scanner_identity") != SCANNER_IDENTITY:
            raise BootstrapValidationError("GRT_B0_SCANNER_IDENTITY_MISMATCH")
        if not row.get("original_subject_locator"):
            raise BootstrapValidationError("GRT_B0_SUBJECT_LOCATOR_MISSING")
        ordinal = row.get("ordinal")
        if isinstance(ordinal, bool) or not isinstance(ordinal, int):
            raise BootstrapValidationError("GRT_B0_ORDINAL_INVALID")
        ids.add(str(row["baseline_member_id"]))
        anomaly_ids.add(anomaly_id)
        payload_hashes.add(payload_hash)
        ordinals.append(ordinal)
    if len(ids) != B0_MEMBER_COUNT or len(anomaly_ids) != B0_MEMBER_COUNT:
        raise BootstrapValidationError("GRT_B0_MEMBER_UNIQUENESS_VIOLATION")
    if len(payload_hashes) != B0_MEMBER_COUNT:
        raise BootstrapValidationError("GRT_B0_EXACT_SOURCE_PAYLOAD_HASH_COLLISION")
    if sorted(ordinals) != list(range(1, B0_MEMBER_COUNT + 1)):
        raise BootstrapValidationError("GRT_B0_ORDINAL_SEQUENCE_INVALID")


def baseline_membership_sha256(rows: list[Mapping[str, Any]]) -> str:
    validate_baseline_members(rows)
    ordered = sorted(rows, key=lambda row: int(row["ordinal"]))
    return canonical_sha256([str(row["payload_hash"]) for row in ordered])


def validate_debt_baseline(baseline: Mapping[str, Any], rows: list[Mapping[str, Any]]) -> None:
    validate_baseline_members(rows)
    if baseline.get("baseline_id") != B0_ID or baseline.get("raw_warning_count") != B0_MEMBER_COUNT:
        raise BootstrapValidationError("GRT_B0_BASELINE_ID_OR_COUNT_MISMATCH")
    if baseline.get("source_commit") != B0_SOURCE_COMMIT or baseline.get("source_tree_hash") != B0_SOURCE_TREE:
        raise BootstrapValidationError("GRT_B0_SOURCE_IDENTITY_MISMATCH")
    if baseline.get("source_topology_sha256") != B0_TOPOLOGY_SHA256:
        raise BootstrapValidationError("GRT_B0_TOPOLOGY_HASH_MISMATCH")
    if baseline_membership_sha256(rows) != B0_MEMBERSHIP_SHA256:
        raise BootstrapValidationError("GRT_B0_MEMBERSHIP_HASH_MISMATCH")
    expected_ids = [
        str(row["baseline_member_id"])
        for row in sorted(rows, key=lambda row: int(row["ordinal"]))
    ]
    if baseline.get("baseline_member_ids") != expected_ids:
        raise BootstrapValidationError("GRT_B0_MEMBER_INDEX_SUBSTITUTION")


def finding_id(
    rule_id: str,
    subject_artifact_id: str,
    relation_role: str,
    counterparty_identity: str | None = None,
) -> str:
    if not _RULE_ID_RE.fullmatch(rule_id) or not subject_artifact_id or not relation_role:
        raise BootstrapValidationError("GRT_FINDING_IDENTITY_INPUT_INVALID")
    projection = {
        "rule_id": rule_id,
        "subject_artifact_id": subject_artifact_id,
        "relation_role": relation_role,
        "counterparty_identity": counterparty_identity,
    }
    return "GRT.FIND." + canonical_sha256(projection)[:24]


def make_finding(
    *,
    rule_id: str,
    subject_artifact_id: str,
    relation_role: str,
    debt_extent: Mapping[str, int],
    first_seen_tree: str,
    applicability_evidence: list[str] | None = None,
    violation_evidence: list[str] | None = None,
    counterparty_identity: str | None = None,
    lifecycle: str = "OPEN",
) -> dict[str, Any]:
    _validate_debt_extent(debt_extent)
    if not _HEX40_RE.fullmatch(first_seen_tree):
        raise BootstrapValidationError("GRT_FINDING_FIRST_SEEN_TREE_INVALID")
    return {
        "schema": "grt-finding-record/v0.2",
        "finding_id": finding_id(
            rule_id,
            subject_artifact_id,
            relation_role,
            counterparty_identity,
        ),
        "rule_id": rule_id,
        "subject_artifact_id": subject_artifact_id,
        "relation_role": relation_role,
        "counterparty_identity": counterparty_identity,
        "applicability_evidence": sorted(set(applicability_evidence or [])),
        "violation_evidence": sorted(set(violation_evidence or [])),
        "debt_extent": dict(sorted(debt_extent.items())),
        "lifecycle": lifecycle,
        "first_seen_tree": first_seen_tree,
    }


def compare_debt_extent(previous: Mapping[str, int], current: Mapping[str, int]) -> str:
    _validate_debt_extent(previous)
    _validate_debt_extent(current)
    if set(previous) != set(current):
        return "INCOMPARABLE"
    if any(current[key] > previous[key] for key in previous):
        return "EXPANDED"
    if any(current[key] < previous[key] for key in previous):
        return "SHRUNK"
    return "UNCHANGED"


def make_lineage(
    predecessor_finding_ids: list[str],
    successor_finding_ids: list[str],
    kind: str,
    evidence_refs: list[str],
) -> dict[str, Any]:
    if kind not in {
        "MOVE",
        "RENAME",
        "SPLIT",
        "MERGE",
        "SCANNER_MIGRATION",
        "CONSTITUTION_MIGRATION",
    }:
        raise BootstrapValidationError("GRT_DEBT_LINEAGE_KIND_INVALID")
    payload = {
        "schema": "grt-debt-lineage-record/v0.2",
        "predecessor_finding_ids": sorted(set(predecessor_finding_ids)),
        "successor_finding_ids": sorted(set(successor_finding_ids)),
        "kind": kind,
        "evidence_refs": sorted(set(evidence_refs)),
        "authority_effect": "NONE_LINEAGE_ONLY",
    }
    if not payload["predecessor_finding_ids"] and not payload["successor_finding_ids"]:
        raise BootstrapValidationError("GRT_DEBT_LINEAGE_EMPTY")
    payload["canonical_hash"] = canonical_sha256(payload)
    payload["lineage_id"] = "GRT.DEBT.LINEAGE." + payload["canonical_hash"][:24]
    return payload


def propose_debt_floor(
    *,
    generation: int,
    predecessor_commit: str,
    predecessor_tree: str,
    constitution_hash: str,
    open_grandfathered_findings: list[str],
    previous_floor: Mapping[str, Any] | None = None,
    permanently_resolved_finding_ids: list[str] | None = None,
    historical_non_debt: list[str] | None = None,
    quarantined_findings: list[str] | None = None,
    temporarily_admitted_actionable: list[str] | None = None,
) -> dict[str, Any]:
    if generation < 0:
        raise BootstrapValidationError("GRT_DEBT_FLOOR_GENERATION_INVALID")
    if not _HEX40_RE.fullmatch(predecessor_commit) or not _HEX40_RE.fullmatch(predecessor_tree):
        raise BootstrapValidationError("GRT_DEBT_FLOOR_GIT_IDENTITY_INVALID")
    if not _HEX64_RE.fullmatch(constitution_hash):
        raise BootstrapValidationError("GRT_DEBT_FLOOR_CONSTITUTION_HASH_INVALID")
    current = set(open_grandfathered_findings)
    resolved = set(permanently_resolved_finding_ids or [])
    if current & resolved:
        raise BootstrapValidationError("GRT_DEBT_RECURRENCE_REQUIRES_NEW_FINDING_ID")
    if previous_floor is not None:
        if generation != int(previous_floor.get("generation", -1)) + 1:
            raise BootstrapValidationError("GRT_DEBT_FLOOR_GENERATION_NOT_MONOTONIC")
        previous_open = set(previous_floor.get("open_grandfathered_findings", []))
        if current - previous_open:
            raise BootstrapValidationError("GRT_DEBT_FLOOR_GRANDFATHERED_SET_GREW")
    floor = {
        "schema": "grt-debt-floor/v0.2",
        "generation": generation,
        "predecessor_commit": predecessor_commit,
        "predecessor_tree": predecessor_tree,
        "constitution_hash": constitution_hash,
        "open_grandfathered_findings": sorted(current),
        "historical_non_debt": sorted(set(historical_non_debt or [])),
        "quarantined_findings": sorted(set(quarantined_findings or [])),
        "temporarily_admitted_actionable": sorted(set(temporarily_admitted_actionable or [])),
    }
    floor["floor_hash"] = canonical_sha256(floor)
    return floor


def validate_debt_floor(floor: Mapping[str, Any]) -> None:
    payload = dict(floor)
    actual_hash = str(payload.pop("floor_hash", ""))
    if not _HEX64_RE.fullmatch(actual_hash) or canonical_sha256(payload) != actual_hash:
        raise BootstrapValidationError("GRT_DEBT_FLOOR_HASH_MISMATCH")
    groups = [
        set(floor.get(key, []))
        for key in (
            "open_grandfathered_findings",
            "historical_non_debt",
            "quarantined_findings",
            "temporarily_admitted_actionable",
        )
    ]
    if any(groups[i] & groups[j] for i in range(len(groups)) for j in range(i + 1, len(groups))):
        raise BootstrapValidationError("GRT_DEBT_FLOOR_STATE_OVERLAP")


__all__ = [
    "validate_amendment_record",
    "validate_override_record",
    "validate_historical_disposition_record",
    "B0_ID",
    "B0_MEMBER_COUNT",
    "B0_MEMBERSHIP_SHA256",
    "SCANNER_IDENTITY",
    "baseline_member_id",
    "validate_baseline_members",
    "baseline_membership_sha256",
    "validate_debt_baseline",
    "finding_id",
    "make_finding",
    "compare_debt_extent",
    "make_lineage",
    "propose_debt_floor",
    "validate_debt_floor",
]
