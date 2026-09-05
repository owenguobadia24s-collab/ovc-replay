from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .registers_gen0002 import (
    AUTHORITY_EFFECT as REGISTER_AUTHORITY_EFFECT,
    PASS2_MERGE_COMMIT,
    PASS2_VIRTUAL_VIEW_ID,
    build_register_bundle,
)

PROGRAMME_ID = "OVC-LSIAC-v0.1"
GENERATION_ID = "OVC-LSIAC-ACCESSION-GEN-0002"
PACKET_ID = "LSIAC-GEN0002-ARCHITECTURE-RECONCILIATION"
SOURCE_REGISTER_MERGE_COMMIT = "e7cf3df85b43bcca07ad6120d2fc838269402810"
SOURCE_REGISTER_TREE = "38ed3674bcb79d9fb0fc3852514ea0dfe14148d2"
SOURCE_REGISTER_VIRTUAL_BUNDLE_ID = "54c047d4c97b90aecfedb2eff7830f10d8a632a9c26405863d7db2f8da0ba8b8"
PROJECTION = "GEN0002_ARCHITECTURE_RECONCILIATION_NO_FORWARD_ACCESSION_V1"
AUTHORITY_EFFECT = "NONE_RECONCILIATION_ONLY"
DISPOSITION = "NO_FORWARD_ACCESSION_ARCHITECTURE_CHANGE"


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def build_architecture_reconciliation(root: str) -> dict[str, Any]:
    bundle = build_register_bundle(root)
    _require(bundle.get("bundle_id") == SOURCE_REGISTER_VIRTUAL_BUNDLE_ID, "LSIAC_GEN0002_RECONCILIATION_REGISTER_BUNDLE_MISMATCH")
    _require(bundle.get("source_pass2_virtual_view_id") == PASS2_VIRTUAL_VIEW_ID, "LSIAC_GEN0002_RECONCILIATION_PASS2_VIEW_MISMATCH")
    _require(bundle.get("source_pass2_merge_commit") == PASS2_MERGE_COMMIT, "LSIAC_GEN0002_RECONCILIATION_PASS2_MERGE_MISMATCH")
    _require(bundle.get("authority_effect") == REGISTER_AUTHORITY_EFFECT, "LSIAC_GEN0002_RECONCILIATION_REGISTER_AUTHORITY_MISMATCH")

    registers: Mapping[str, Mapping[str, Any]] = bundle["registers"]
    lsir = registers["lsir"]
    negative = registers["negative_knowledge"]
    supersession = registers["supersession"]
    destination = registers["destination_binding"]
    effects = registers["architecture_effect"]
    gaps = registers["architecture_gap"]

    _require(lsir["decision_index_count"] == 431, "LSIAC_GEN0002_RECONCILIATION_DECISION_TRACEABILITY_INCOMPLETE")
    _require(lsir["entry_count"] == 0, "LSIAC_GEN0002_RECONCILIATION_FORWARD_LSIR_NOT_EMPTY")
    _require(negative["entry_count"] == 0, "LSIAC_GEN0002_RECONCILIATION_NEGATIVE_REGISTER_NOT_EMPTY")
    _require(supersession["edge_count"] == 0, "LSIAC_GEN0002_RECONCILIATION_SUPERSESSION_NOT_EMPTY")
    _require(destination["binding_count"] == 0, "LSIAC_GEN0002_RECONCILIATION_DESTINATION_BINDINGS_NOT_EMPTY")
    _require(effects["record_count"] == 431, "LSIAC_GEN0002_RECONCILIATION_EFFECT_ACCOUNTING_INCOMPLETE")
    _require(effects["primary_effect_counts"] == {"NO_FORWARD_IMPLEMENTATION": 431}, "LSIAC_GEN0002_RECONCILIATION_EFFECT_SET_NOT_NO_FORWARD")
    _require(effects["actionable_effect_count"] == 0, "LSIAC_GEN0002_RECONCILIATION_ACTIONABLE_EFFECT_PRESENT")
    _require(effects["execution_count"] == 0, "LSIAC_GEN0002_RECONCILIATION_EXECUTION_PRESENT")

    gap_count = int(gaps["gap_count"])
    gap_subject_ids = sorted(str(item["subject_id"]) for item in gaps["gaps"])
    _require(all(item["severity"] == "REPRODUCIBILITY_BLOCKER" for item in gaps["gaps"]), "LSIAC_GEN0002_RECONCILIATION_GAP_SEVERITY_DRIFT")
    _require(all(item["downstream_effect"] == "NO_FORWARD_IMPLEMENTATION" for item in gaps["gaps"]), "LSIAC_GEN0002_RECONCILIATION_GAP_EFFECT_DRIFT")

    reconciliation = {
        "schema": "ovc-lsiac-gen0002-architecture-reconciliation/v0.1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "generation_id": GENERATION_ID,
        "source_register_merge_commit": SOURCE_REGISTER_MERGE_COMMIT,
        "source_register_tree": SOURCE_REGISTER_TREE,
        "source_register_virtual_bundle_id": SOURCE_REGISTER_VIRTUAL_BUNDLE_ID,
        "source_pass2_virtual_view_id": PASS2_VIRTUAL_VIEW_ID,
        "source_register_ids": dict(sorted(bundle["register_identities"].items())),
        "decision_traceability_count": int(lsir["decision_index_count"]),
        "forward_inheritance_entry_count": int(lsir["entry_count"]),
        "admitted_negative_knowledge_entry_count": int(negative["entry_count"]),
        "deferred_negative_subject_count": int(negative["deferred_negative_subject_count"]),
        "supersession_edge_count": int(supersession["edge_count"]),
        "non_empty_destination_binding_count": int(destination["binding_count"]),
        "architecture_effect_record_count": int(effects["record_count"]),
        "actionable_architecture_effect_count": int(effects["actionable_effect_count"]),
        "architecture_execution_count": int(effects["execution_count"]),
        "reproducibility_gap_count": gap_count,
        "reproducibility_gap_subject_ids": gap_subject_ids,
        "architecture_reconciliation_disposition": DISPOSITION,
        "required_repository_changes": {
            "owner_change": False,
            "owner_contract_change": False,
            "runtime_change": False,
            "data_migration": False,
            "semantic_or_ontology_change": False,
            "selector_model_family_theory_change": False,
            "validation_consumption_change": False,
            "publication_change": False,
            "deferred_capability_activation": False,
        },
        "preservation_requirements": [
            "PRESERVE_EFFECTIVE_GEN0002_PASS2_DECISIONS",
            "PRESERVE_EMPTY_FORWARD_LSIR_AND_EMPTY_DESTINATION_SUPERSESSION_SURFACES",
            "PRESERVE_431_NO_FORWARD_IMPLEMENTATION_ARCHITECTURE_EFFECT_RECORDS",
            "PRESERVE_EXPLICIT_REPRODUCIBILITY_SOURCE_BINDING_GAPS_FOR_SUCCESSOR_REENTRY",
            "PRESERVE_SECTION_23_DEVELOPMENT_FREEZE_UNTIL_SEPARATE_SCIENCE_RESUME_OPERATOR_DECISION",
        ],
        "conformance_plan_mode": "PRESERVATION_ONLY_NO_FORWARD_ACCESSION_IMPLEMENTATION",
        "next_packet": "LSIAC-GEN0002-LABORATORY-CANON-ACCESSION-CONFORMANCE-IMPLEMENTATION-PLAN",
        "next_operator_gate": "LSIAC-SCIENCE-RESUME",
        "projection": PROJECTION,
        "authority_effect": AUTHORITY_EFFECT,
    }
    return {**reconciliation, "reconciliation_id": _canonical_sha256(reconciliation)}


def build_reconciliation_identity(*, algorithm_git_blob_sha: str) -> str:
    payload = {
        "schema": "ovc-lsiac-gen0002-architecture-reconciliation-identity/v0.1",
        "programme_id": PROGRAMME_ID,
        "generation_id": GENERATION_ID,
        "packet_id": PACKET_ID,
        "source_register_merge_commit": SOURCE_REGISTER_MERGE_COMMIT,
        "source_register_tree": SOURCE_REGISTER_TREE,
        "source_register_virtual_bundle_id": SOURCE_REGISTER_VIRTUAL_BUNDLE_ID,
        "source_pass2_virtual_view_id": PASS2_VIRTUAL_VIEW_ID,
        "algorithm_git_blob_sha": algorithm_git_blob_sha,
        "projection": PROJECTION,
        "authority_effect": AUTHORITY_EFFECT,
    }
    return _canonical_sha256(payload)
