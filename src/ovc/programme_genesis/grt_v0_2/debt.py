"""GRT2-WP2 finding, immutable-baseline, lineage and DebtFloor mechanics.

This module is deterministic and non-enforcing. It materialises record identity,
validation and debt-reconciliation semantics required for G2 readiness. It does
not activate the Repository Constitution, create DebtFloor generation 0, or
classify the current tree ahead of the WP3A scanner/artifact graph.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

from .bootstrap import BootstrapValidationError, validate_instance
from .serialization import canonical_json_v1_text, canonical_sha256

B0_ID = "B0"
B0_MEMBER_COUNT = 569
B0_SOURCE_COMMIT = "100b3fa342c5dee7c96a7a4e5af9e80dac3ddfe4"
B0_SOURCE_TREE = "91374c54bde0e0b61ac51705f6434d4f2b0d8417"
B0_TOPOLOGY_SHA256 = "4120468ecb1c1f484ab073c851287706f4fb45ad0e99fc355b4624094bb795f2"
B0_MEMBERSHIP_SHA256 = "3587c224c07360751923e5718c5bedb432ce4a5c8cccd4061f73dd53ef07de5d"
SCANNER_IDENTITY = f"GRT.V0.1@{B0_SOURCE_COMMIT}:{B0_SOURCE_TREE}"
G4_GATE_PACKET_LOGICAL_SHA256 = "028257fd9e7c19e5e03031fc09e932ec71411a08bdabc8b203ebfc25d6e62354"
G4_GRANDFATHERED_FINDING_ID = "GRT.FIND.8995c2197e0d50326967b31f"
G4_CANDIDATE_FINDING_ID = "GRT.FIND.f9c53308623fa597c63c5f47"

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_RULE_ID = re.compile(r"^GRT-R[0-9]{3}$")
_FINDING_ID = re.compile(r"^GRT\.FIND\.[0-9a-f]{24}$")


class DebtValidationError(BootstrapValidationError):
    """Fail-closed GRT2-WP2 debt or lineage record error."""


def subject_locator_from_anomaly(anomaly: Mapping[str, Any]) -> str:
    """Return a lossless canonical locator projection from the original anomaly.

    The locator contains only source-emitted subject-bearing fields and never
    invents a native v0.2 artifact identity. WP3A may later resolve this locator
    to a native RepositoryArtifact or a LegacyArtifactLocator.
    """
    projection = {
        "affected_component_ids": list(anomaly.get("affected_component_ids", [])),
        "affected_programme_ids": list(anomaly.get("affected_programme_ids", [])),
        "source_evidence": list(anomaly.get("source_evidence", [])),
    }
    if not any(projection.values()):
        raise DebtValidationError("GRT_B0_SUBJECT_LOCATOR_SOURCE_EMPTY")
    return canonical_json_v1_text(projection)


def baseline_member_id(anomaly_id: str, payload_hash: str) -> str:
    if not isinstance(anomaly_id, str) or not anomaly_id.startswith("GRT.ANOM."):
        raise DebtValidationError("GRT_B0_MEMBER_SOURCE_IDENTITY_INVALID")
    if not isinstance(payload_hash, str) or not _HEX64.fullmatch(payload_hash):
        raise DebtValidationError("GRT_B0_MEMBER_SOURCE_IDENTITY_INVALID")
    digest = canonical_sha256(
        {
            "baseline_id": B0_ID,
            "original_anomaly_id": anomaly_id,
            "payload_hash": payload_hash,
        }
    )
    return f"GRT.B0.MEMBER.{digest[:24]}"


def validate_baseline_member_record(
    record: Mapping[str, Any], schema: Mapping[str, Any] | None = None
) -> None:
    if schema is not None:
        validate_instance(record, schema)
    anomaly_id = str(record.get("original_GRT_anomaly", ""))
    payload_hash = str(record.get("payload_hash", ""))
    if record.get("baseline_member_id") != baseline_member_id(anomaly_id, payload_hash):
        raise DebtValidationError("GRT_B0_MEMBER_ID_MISMATCH")
    if record.get("original_scanner_identity") != SCANNER_IDENTITY:
        raise DebtValidationError("GRT_B0_SCANNER_IDENTITY_MISMATCH")
    locator = record.get("original_subject_locator")
    if not isinstance(locator, str) or not locator:
        raise DebtValidationError("GRT_B0_SUBJECT_LOCATOR_MISSING")
    try:
        parsed = json.loads(locator)
    except json.JSONDecodeError as exc:
        raise DebtValidationError("GRT_B0_SUBJECT_LOCATOR_NOT_CANONICAL_JSON") from exc
    if canonical_json_v1_text(parsed) != locator:
        raise DebtValidationError("GRT_B0_SUBJECT_LOCATOR_NOT_CANONICAL_JSON")
    if not any(parsed.get(key) for key in ("affected_component_ids", "affected_programme_ids", "source_evidence")):
        raise DebtValidationError("GRT_B0_SUBJECT_LOCATOR_SOURCE_EMPTY")
    if record.get("mapping_status") == "MAPPED" and not record.get("mapped_finding_id"):
        raise DebtValidationError("GRT_B0_MAPPED_FINDING_REQUIRED")
    if record.get("mapping_status") != "MAPPED" and record.get("mapped_finding_id") is not None:
        raise DebtValidationError("GRT_B0_UNMAPPED_FINDING_ID_PRESENT")


def validate_baseline_members(
    rows: Sequence[Mapping[str, Any]], schema: Mapping[str, Any] | None = None
) -> None:
    if len(rows) != B0_MEMBER_COUNT:
        raise DebtValidationError(f"GRT_B0_MEMBER_COUNT_MISMATCH:{len(rows)}")
    ids: set[str] = set()
    anomaly_ids: set[str] = set()
    payload_hashes: set[str] = set()
    ordinals: list[int] = []
    for row in rows:
        validate_baseline_member_record(row, schema)
        ordinal = row.get("ordinal")
        if isinstance(ordinal, bool) or not isinstance(ordinal, int):
            raise DebtValidationError("GRT_B0_ORDINAL_INVALID")
        ids.add(str(row["baseline_member_id"]))
        anomaly_ids.add(str(row["original_GRT_anomaly"]))
        payload_hashes.add(str(row["payload_hash"]))
        ordinals.append(ordinal)
    if len(ids) != B0_MEMBER_COUNT or len(anomaly_ids) != B0_MEMBER_COUNT:
        raise DebtValidationError("GRT_B0_MEMBER_UNIQUENESS_VIOLATION")
    if len(payload_hashes) != B0_MEMBER_COUNT:
        raise DebtValidationError("GRT_B0_EXACT_SOURCE_PAYLOAD_HASH_COLLISION")
    if sorted(ordinals) != list(range(1, B0_MEMBER_COUNT + 1)):
        raise DebtValidationError("GRT_B0_ORDINAL_SEQUENCE_INVALID")


def baseline_membership_sha256(rows: Sequence[Mapping[str, Any]]) -> str:
    validate_baseline_members(rows)
    ordered = sorted(rows, key=lambda row: int(row["ordinal"]))
    return canonical_sha256([str(row["payload_hash"]) for row in ordered])


def validate_debt_baseline(
    baseline: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    schema: Mapping[str, Any] | None = None,
) -> None:
    if schema is not None:
        validate_instance(baseline, schema)
    validate_baseline_members(rows)
    if baseline.get("baseline_id") != B0_ID or baseline.get("raw_warning_count") != B0_MEMBER_COUNT:
        raise DebtValidationError("GRT_B0_BASELINE_ID_OR_COUNT_MISMATCH")
    if baseline.get("source_commit") != B0_SOURCE_COMMIT or baseline.get("source_tree_hash") != B0_SOURCE_TREE:
        raise DebtValidationError("GRT_B0_SOURCE_IDENTITY_MISMATCH")
    if baseline.get("source_topology_sha256") != B0_TOPOLOGY_SHA256:
        raise DebtValidationError("GRT_B0_TOPOLOGY_HASH_MISMATCH")
    if baseline_membership_sha256(rows) != B0_MEMBERSHIP_SHA256:
        raise DebtValidationError("GRT_B0_MEMBERSHIP_HASH_MISMATCH")
    expected = [
        str(row["baseline_member_id"])
        for row in sorted(rows, key=lambda row: int(row["ordinal"]))
    ]
    if baseline.get("baseline_member_ids") != expected:
        raise DebtValidationError("GRT_B0_MEMBER_INDEX_SUBSTITUTION")
    if baseline.get("constitution_mapping_status") == "MAPPED_COMPLETE":
        if any(row.get("mapping_status") != "MAPPED" for row in rows):
            raise DebtValidationError("GRT_B0_MAPPING_COMPLETION_OVERSTATED")


def finding_id(
    rule_id: str,
    subject_artifact_id: str,
    relation_role: str,
    counterparty_identity: str | None = None,
) -> str:
    if not _RULE_ID.fullmatch(rule_id) or not subject_artifact_id or not relation_role:
        raise DebtValidationError("GRT_FINDING_IDENTITY_INPUT_INVALID")
    projection = {
        "constitution_rule_id": rule_id,
        "subject_artifact_id": subject_artifact_id,
        "relation_role": relation_role,
        "relevant_counterparty_identity": counterparty_identity,
    }
    return "GRT.FIND." + canonical_sha256(projection)[:24]


def _validate_extent(extent: Mapping[str, int]) -> None:
    if not extent:
        raise DebtValidationError("GRT_DEBT_EXTENT_INVALID")
    for key, value in extent.items():
        if not isinstance(key, str) or not key:
            raise DebtValidationError("GRT_DEBT_EXTENT_KEY_INVALID")
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise DebtValidationError(f"GRT_DEBT_EXTENT_VALUE_INVALID:{key}")


def compare_debt_extent(previous: Mapping[str, int], current: Mapping[str, int]) -> str:
    """Return the ratified four-way debt extent comparator result."""
    _validate_extent(previous)
    _validate_extent(current)
    if set(previous) != set(current):
        return "MATERIAL_CHANGED"
    deltas = [current[key] - previous[key] for key in sorted(previous)]
    if all(delta == 0 for delta in deltas):
        return "UNCHANGED"
    if all(delta <= 0 for delta in deltas):
        return "REDUCED"
    if all(delta >= 0 for delta in deltas):
        return "EXPANDED"
    return "MATERIAL_CHANGED"


def validate_g4_current_projection_substitution(
    decision: Mapping[str, Any],
    before_findings: Mapping[str, Mapping[str, Any]],
    after_findings: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    """Validate the exact operator-approved G4 current-state identity substitution.

    This is deliberately not a generic debt waiver. It recognizes only the one
    path-identity replacement ratified by the merged GRT2-G4 gate packet and
    requires the rule and debt extent to remain byte-semantically unchanged.
    """
    payload = dict(decision)
    logical_sha256 = str(payload.pop("logical_sha256", ""))
    if not _HEX64.fullmatch(logical_sha256) or canonical_sha256(payload) != logical_sha256:
        raise DebtValidationError("GRT_G4_DECISION_LOGICAL_HASH_MISMATCH")
    if decision.get("schema") != "ovc-grt2-g4-operator-decision/v1":
        raise DebtValidationError("GRT_G4_DECISION_SCHEMA_INVALID")
    if decision.get("gate_id") != "GRT2-G4" or decision.get("decision") != "PASS":
        raise DebtValidationError("GRT_G4_DECISION_NOT_PASS")
    if decision.get("operator_instruction") != "OVC APPROVE GRT2-G4 PASS":
        raise DebtValidationError("GRT_G4_OPERATOR_INSTRUCTION_MISMATCH")
    gate = decision.get("approved_gate_packet")
    if not isinstance(gate, Mapping) or gate.get("logical_sha256") != G4_GATE_PACKET_LOGICAL_SHA256:
        raise DebtValidationError("GRT_G4_GATE_PACKET_BINDING_MISMATCH")
    delta = decision.get("approved_authority_delta")
    substitution = delta.get("exact_current_projection_substitution") if isinstance(delta, Mapping) else None
    expected = {
        "admit_finding_id": G4_CANDIDATE_FINDING_ID,
        "remove_grandfathered_finding_id": G4_GRANDFATHERED_FINDING_ID,
        "rule_id": "GRT-R300",
        "scope": "ONE_FOR_ONE_CURRENT_STATE_TARGET_PATH_IDENTITY_ONLY",
        "debt_extent_change": "UNCHANGED",
    }
    if substitution != expected:
        raise DebtValidationError("GRT_G4_SUBSTITUTION_NOT_EXACT")
    before = before_findings.get(G4_GRANDFATHERED_FINDING_ID)
    after = after_findings.get(G4_CANDIDATE_FINDING_ID)
    if before is None or after is None:
        raise DebtValidationError("GRT_G4_SUBSTITUTION_FINDING_MISSING")
    if G4_CANDIDATE_FINDING_ID in before_findings or G4_GRANDFATHERED_FINDING_ID in after_findings:
        raise DebtValidationError("GRT_G4_SUBSTITUTION_NOT_ONE_FOR_ONE")
    if before.get("rule_id") != "GRT-R300" or after.get("rule_id") != "GRT-R300":
        raise DebtValidationError("GRT_G4_SUBSTITUTION_RULE_MISMATCH")
    before_extent = before.get("debt_extent")
    after_extent = after.get("debt_extent")
    if not isinstance(before_extent, Mapping) or not isinstance(after_extent, Mapping):
        raise DebtValidationError("GRT_G4_SUBSTITUTION_EXTENT_MISSING")
    if compare_debt_extent(before_extent, after_extent) != "UNCHANGED":
        raise DebtValidationError("GRT_G4_SUBSTITUTION_EXTENT_CHANGED")
    return {G4_GRANDFATHERED_FINDING_ID: G4_CANDIDATE_FINDING_ID}


def make_finding(
    *,
    rule_id: str,
    subject_artifact_id: str,
    relation_role: str,
    debt_extent: Mapping[str, int],
    first_seen_tree: str,
    applicability_evidence: Sequence[str] = (),
    violation_evidence: Sequence[str] = (),
    counterparty_identity: str | None = None,
    lifecycle: str = "OPEN",
) -> dict[str, Any]:
    _validate_extent(debt_extent)
    if not _HEX40.fullmatch(first_seen_tree):
        raise DebtValidationError("GRT_FINDING_FIRST_SEEN_TREE_INVALID")
    if lifecycle not in {
        "OPEN", "RESOLVED", "HISTORICAL_NON_DEBT", "QUARANTINED", "TEMPORARILY_ADMITTED_ACTIONABLE"
    }:
        raise DebtValidationError("GRT_FINDING_LIFECYCLE_INVALID")
    return {
        "schema": "grt-finding-record/v0.2",
        "finding_id": finding_id(rule_id, subject_artifact_id, relation_role, counterparty_identity),
        "rule_id": rule_id,
        "subject_artifact_id": subject_artifact_id,
        "relation_role": relation_role,
        "counterparty_identity": counterparty_identity,
        "applicability_evidence": sorted(set(applicability_evidence)),
        "violation_evidence": sorted(set(violation_evidence)),
        "debt_extent": dict(sorted(debt_extent.items())),
        "lifecycle": lifecycle,
        "first_seen_tree": first_seen_tree,
    }


def make_lineage(
    predecessor_finding_ids: Sequence[str],
    successor_finding_ids: Sequence[str],
    kind: str,
    evidence_refs: Sequence[str],
) -> dict[str, Any]:
    if kind not in {"MOVE", "RENAME", "SPLIT", "MERGE", "SCANNER_MIGRATION", "CONSTITUTION_MIGRATION"}:
        raise DebtValidationError("GRT_DEBT_LINEAGE_KIND_INVALID")
    predecessor = sorted(set(predecessor_finding_ids))
    successor = sorted(set(successor_finding_ids))
    if not predecessor and not successor:
        raise DebtValidationError("GRT_DEBT_LINEAGE_EMPTY")
    if any(not _FINDING_ID.fullmatch(value) for value in predecessor + successor):
        raise DebtValidationError("GRT_DEBT_LINEAGE_FINDING_ID_INVALID")
    payload = {
        "schema": "grt-debt-lineage-record/v0.2",
        "predecessor_finding_ids": predecessor,
        "successor_finding_ids": successor,
        "kind": kind,
        "evidence_refs": sorted(set(evidence_refs)),
        "authority_effect": "NONE_LINEAGE_ONLY",
    }
    canonical_hash = canonical_sha256(payload)
    return {
        **payload,
        "canonical_hash": canonical_hash,
        "lineage_id": "GRT.DEBT.LINEAGE." + canonical_hash[:24],
    }


def validate_lineage(record: Mapping[str, Any]) -> None:
    payload = {
        key: record[key]
        for key in (
            "schema", "predecessor_finding_ids", "successor_finding_ids", "kind", "evidence_refs", "authority_effect"
        )
    }
    expected_hash = canonical_sha256(payload)
    if record.get("canonical_hash") != expected_hash:
        raise DebtValidationError("GRT_DEBT_LINEAGE_HASH_MISMATCH")
    if record.get("lineage_id") != "GRT.DEBT.LINEAGE." + expected_hash[:24]:
        raise DebtValidationError("GRT_DEBT_LINEAGE_ID_MISMATCH")


def classify_debt_transition(
    *,
    predecessor_state: str,
    candidate_state: str,
    extent_result: str | None = None,
    related_identity: bool = True,
) -> tuple[str, str]:
    """Implement the ratified predecessor/floor admission table."""
    if predecessor_state == "ABSENT" and candidate_state == "ABSENT":
        return "NONE", "PASS"
    if predecessor_state == "ABSENT" and candidate_state == "ACTIONABLE":
        return "NEW_ACTIONABLE", "FAIL"
    if predecessor_state == "GRANDFATHERED":
        if candidate_state == "RESOLVED_WITH_PROOF":
            return "BASELINE_RESOLVED", "PASS"
        if candidate_state != "ACTIONABLE":
            return "UNRESOLVED", "FAIL"
        if extent_result == "UNCHANGED":
            return "BASELINE_UNCHANGED", "PASS"
        if extent_result == "REDUCED":
            return "BASELINE_REDUCED", "PASS"
        if extent_result == "EXPANDED":
            return "BASELINE_EXPANDED", "FAIL"
        return "UNRESOLVED", "FAIL"
    if predecessor_state == "HISTORICAL_NON_DEBT":
        return ("HISTORICAL_NON_DEBT", "PASS") if candidate_state == "UNCHANGED_NON_DEBT" else ("NEW_ACTIONABLE", "FAIL")
    if predecessor_state == "RESOLVED_HISTORICAL" and candidate_state == "ACTIONABLE":
        return "NEW_ACTIONABLE_RECURRENCE", "FAIL"
    if predecessor_state == "REMOVED_A" and candidate_state == "ADDED_B" and not related_identity:
        return "RESOLVED_PLUS_NEW_ACTIONABLE", "FAIL"
    return "UNRESOLVED", "FAIL"


def propose_debt_floor(
    *,
    generation: int,
    predecessor_commit: str,
    predecessor_tree: str,
    constitution_hash: str,
    open_grandfathered_findings: Sequence[str],
    previous_floor: Mapping[str, Any] | None = None,
    permanently_resolved_finding_ids: Sequence[str] = (),
    historical_non_debt: Sequence[str] = (),
    quarantined_findings: Sequence[str] = (),
    temporarily_admitted_actionable: Sequence[str] = (),
    authorized_identity_substitutions: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
        raise DebtValidationError("GRT_DEBT_FLOOR_GENERATION_INVALID")
    if not _HEX40.fullmatch(predecessor_commit) or not _HEX40.fullmatch(predecessor_tree):
        raise DebtValidationError("GRT_DEBT_FLOOR_GIT_IDENTITY_INVALID")
    if not _HEX64.fullmatch(constitution_hash):
        raise DebtValidationError("GRT_DEBT_FLOOR_CONSTITUTION_HASH_INVALID")
    current = set(open_grandfathered_findings)
    resolved = set(permanently_resolved_finding_ids)
    if current & resolved:
        raise DebtValidationError("GRT_DEBT_RECURRENCE_REQUIRES_NEW_FINDING_ID")
    if previous_floor is not None:
        if generation != int(previous_floor.get("generation", -1)) + 1:
            raise DebtValidationError("GRT_DEBT_FLOOR_GENERATION_NOT_MONOTONIC")
        previous_open = set(previous_floor.get("open_grandfathered_findings", []))
        substitutions = dict(authorized_identity_substitutions or {})
        removed = set(substitutions)
        added = set(substitutions.values())
        if len(added) != len(substitutions):
            raise DebtValidationError("GRT_DEBT_FLOOR_SUBSTITUTION_NOT_ONE_FOR_ONE")
        if not removed.issubset(previous_open) or not added.issubset(current):
            raise DebtValidationError("GRT_DEBT_FLOOR_SUBSTITUTION_MEMBERSHIP_INVALID")
        if removed & current or added & previous_open:
            raise DebtValidationError("GRT_DEBT_FLOOR_SUBSTITUTION_NOT_EXACT_REPLACEMENT")
        if current - previous_open - added:
            raise DebtValidationError("GRT_DEBT_FLOOR_GRANDFATHERED_SET_GREW")
    floor = {
        "schema": "grt-debt-floor/v0.2",
        "generation": generation,
        "predecessor_commit": predecessor_commit,
        "predecessor_tree": predecessor_tree,
        "constitution_hash": constitution_hash,
        "open_grandfathered_findings": sorted(current),
        "historical_non_debt": sorted(set(historical_non_debt)),
        "quarantined_findings": sorted(set(quarantined_findings)),
        "temporarily_admitted_actionable": sorted(set(temporarily_admitted_actionable)),
    }
    floor["floor_hash"] = canonical_sha256(floor)
    return floor


def validate_debt_floor(floor: Mapping[str, Any]) -> None:
    payload = dict(floor)
    actual = str(payload.pop("floor_hash", ""))
    if not _HEX64.fullmatch(actual) or canonical_sha256(payload) != actual:
        raise DebtValidationError("GRT_DEBT_FLOOR_HASH_MISMATCH")
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
        raise DebtValidationError("GRT_DEBT_FLOOR_STATE_OVERLAP")


__all__ = [
    "B0_ID", "B0_MEMBER_COUNT", "B0_SOURCE_COMMIT", "B0_SOURCE_TREE",
    "B0_TOPOLOGY_SHA256", "B0_MEMBERSHIP_SHA256", "SCANNER_IDENTITY",
    "DebtValidationError", "subject_locator_from_anomaly", "baseline_member_id",
    "validate_baseline_member_record", "validate_baseline_members",
    "baseline_membership_sha256", "validate_debt_baseline", "finding_id",
    "make_finding", "compare_debt_extent", "validate_g4_current_projection_substitution",
    "make_lineage", "validate_lineage",
    "classify_debt_transition", "propose_debt_floor", "validate_debt_floor",
]
