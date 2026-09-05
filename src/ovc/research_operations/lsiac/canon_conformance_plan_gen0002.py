from __future__ import annotations

import hashlib
import json
from typing import Any

from .architecture_reconciliation_gen0002 import (
    DISPOSITION as RECONCILIATION_DISPOSITION,
    SOURCE_REGISTER_VIRTUAL_BUNDLE_ID,
    build_architecture_reconciliation,
    build_reconciliation_identity,
)

PROGRAMME_ID = "OVC-LSIAC-v0.1"
PACKET_ID = "LSIAC-GEN0002-LABORATORY-CANON-ACCESSION-CONFORMANCE-IMPLEMENTATION-PLAN"
PLAN_DOCUMENT_ID = "OVC-LSIAC-GEN0002-LABORATORY-CANON-ACCESSION-CONFORMANCE-IMPLEMENTATION-PLAN-0.1"
PLAN_IDENTITY = "13f1229a2882b62e4c71a3a8ef7cdb16ae54e3cfb7db6dac0afe3fa0bd1d7387"
BASELINE_MAIN = "ad8cbe18125710160ef7bfb456649d9d8b9fc18c"
BASELINE_TREE = "5f0ce302134a0f7b8878e056c32cf3945ca80d5a"
CONSTITUTION_SHA256 = "ec5a28b8edfa572d229b7e1f1694a5439da621aa640229ad23dcfbeb71f5a8c2"
SOURCE_PASS2_VIRTUAL_VIEW_ID = "58b364fbf7b8ce160877fb8bba641cb853ea1b29b5af9c4a4b1a5294648749d8"
SOURCE_ARCHITECTURE_RECONCILIATION_ID = "c0f2c41f27a392fd0417b73db5449ceae2f768750e61536565309b1dd5eb96c6"
SOURCE_RECONCILIATION_ALGORITHM_BLOB_SHA = "9559ccd584fd71d791aca154e854a6fd228fd54c"
PLAN_MODE = "PRESERVATION_ONLY_NO_FORWARD_ACCESSION_IMPLEMENTATION"
AUTHORITY_EFFECT = "NONE_PRESERVATION_PLAN_ONLY"

WORK_PACKET_IDS = ["LSIAC-CANON-WP0", "LSIAC-CANON-WP1", "LSIAC-CANON-WP2"]


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def build_plan_identity() -> str:
    payload = {
        "schema": "ovc-lsiac-gen0002-laboratory-canon-accession-conformance-plan-identity/v0.1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "plan_document_id": PLAN_DOCUMENT_ID,
        "governing_constitution_sha256": CONSTITUTION_SHA256,
        "baseline_main": BASELINE_MAIN,
        "baseline_tree": BASELINE_TREE,
        "source_register_virtual_bundle_id": SOURCE_REGISTER_VIRTUAL_BUNDLE_ID,
        "source_architecture_reconciliation_id": SOURCE_ARCHITECTURE_RECONCILIATION_ID,
        "conformance_plan_mode": PLAN_MODE,
        "work_packet_ids": WORK_PACKET_IDS,
        "next_operator_gate": "LSIAC-SCIENCE-RESUME",
        "authority_effect": AUTHORITY_EFFECT,
    }
    return _canonical_sha256(payload)


def build_canon_conformance_plan(root: str) -> dict[str, Any]:
    reconciliation = build_architecture_reconciliation(root)
    _require(
        build_reconciliation_identity(
            algorithm_git_blob_sha=SOURCE_RECONCILIATION_ALGORITHM_BLOB_SHA
        ) == SOURCE_ARCHITECTURE_RECONCILIATION_ID,
        "LSIAC_GEN0002_CANON_PLAN_RECONCILIATION_IDENTITY_MISMATCH",
    )
    _require(
        reconciliation["source_register_virtual_bundle_id"] == SOURCE_REGISTER_VIRTUAL_BUNDLE_ID,
        "LSIAC_GEN0002_CANON_PLAN_REGISTER_BUNDLE_MISMATCH",
    )
    _require(
        reconciliation["source_pass2_virtual_view_id"] == SOURCE_PASS2_VIRTUAL_VIEW_ID,
        "LSIAC_GEN0002_CANON_PLAN_PASS2_VIEW_MISMATCH",
    )
    _require(
        reconciliation["architecture_reconciliation_disposition"] == RECONCILIATION_DISPOSITION,
        "LSIAC_GEN0002_CANON_PLAN_RECONCILIATION_DISPOSITION_MISMATCH",
    )
    _require(reconciliation["decision_traceability_count"] == 431, "LSIAC_GEN0002_CANON_PLAN_TRACEABILITY_INCOMPLETE")
    _require(reconciliation["forward_inheritance_entry_count"] == 0, "LSIAC_GEN0002_CANON_PLAN_FORWARD_LSIR_PRESENT")
    _require(reconciliation["admitted_negative_knowledge_entry_count"] == 0, "LSIAC_GEN0002_CANON_PLAN_NEGATIVE_ADMISSION_PRESENT")
    _require(reconciliation["supersession_edge_count"] == 0, "LSIAC_GEN0002_CANON_PLAN_SUPERSESSION_PRESENT")
    _require(reconciliation["non_empty_destination_binding_count"] == 0, "LSIAC_GEN0002_CANON_PLAN_DESTINATION_PRESENT")
    _require(reconciliation["architecture_effect_record_count"] == 431, "LSIAC_GEN0002_CANON_PLAN_EFFECT_ACCOUNTING_INCOMPLETE")
    _require(reconciliation["actionable_architecture_effect_count"] == 0, "LSIAC_GEN0002_CANON_PLAN_ACTIONABLE_EFFECT_PRESENT")
    _require(reconciliation["architecture_execution_count"] == 0, "LSIAC_GEN0002_CANON_PLAN_ARCHITECTURE_EXECUTION_PRESENT")
    _require(set(reconciliation["required_repository_changes"].values()) == {False}, "LSIAC_GEN0002_CANON_PLAN_REPOSITORY_CHANGE_REQUIRED")
    _require(reconciliation["reproducibility_gap_count"] >= 2, "LSIAC_GEN0002_CANON_PLAN_REPRODUCIBILITY_GAPS_UNEXPECTEDLY_ABSENT")
    _require(build_plan_identity() == PLAN_IDENTITY, "LSIAC_GEN0002_CANON_PLAN_IDENTITY_MISMATCH")

    return {
        "schema": "ovc-lsiac-gen0002-laboratory-canon-accession-conformance-plan-runtime/v0.1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "plan_document_id": PLAN_DOCUMENT_ID,
        "plan_identity": PLAN_IDENTITY,
        "baseline_main": BASELINE_MAIN,
        "baseline_tree": BASELINE_TREE,
        "source_register_virtual_bundle_id": SOURCE_REGISTER_VIRTUAL_BUNDLE_ID,
        "source_pass2_virtual_view_id": SOURCE_PASS2_VIRTUAL_VIEW_ID,
        "source_architecture_reconciliation_id": SOURCE_ARCHITECTURE_RECONCILIATION_ID,
        "source_architecture_reconciliation_disposition": RECONCILIATION_DISPOSITION,
        "decision_traceability_count": reconciliation["decision_traceability_count"],
        "forward_inheritance_entry_count": reconciliation["forward_inheritance_entry_count"],
        "admitted_negative_knowledge_entry_count": reconciliation["admitted_negative_knowledge_entry_count"],
        "supersession_edge_count": reconciliation["supersession_edge_count"],
        "non_empty_destination_binding_count": reconciliation["non_empty_destination_binding_count"],
        "architecture_effect_record_count": reconciliation["architecture_effect_record_count"],
        "actionable_architecture_effect_count": reconciliation["actionable_architecture_effect_count"],
        "architecture_execution_count": reconciliation["architecture_execution_count"],
        "reproducibility_gap_count": reconciliation["reproducibility_gap_count"],
        "reproducibility_gap_subject_ids": reconciliation["reproducibility_gap_subject_ids"],
        "required_repository_changes": dict(reconciliation["required_repository_changes"]),
        "conformance_plan_mode": PLAN_MODE,
        "preservation_requirements": [
            "PRESERVE_EFFECTIVE_GEN0002_PASS2_DECISIONS",
            "PRESERVE_SIX_REGISTER_BUNDLE_AND_ZERO_FORWARD_PAYLOAD",
            "PRESERVE_431_NO_FORWARD_IMPLEMENTATION_ARCHITECTURE_EFFECTS",
            "PRESERVE_EXPLICIT_REPRODUCIBILITY_SOURCE_BINDING_GAPS_FOR_SUCCESSOR_REENTRY",
            "PRESERVE_CURRENT_ARCHITECTURE",
            "PRESERVE_BOUNDED_SECTION_23_SCIENTIFIC_ARCHITECTURE_DEVELOPMENT_FREEZE_UNTIL_OPERATOR_DECISION",
            "PRESERVE_VALIDATION_LOCK_AND_ALL_PUBLICATION_EXPOSURE_EXECUTION_DENIALS",
        ],
        "work_packet_ids": WORK_PACKET_IDS,
        "terminal_state": "PRESERVATION_CONFORMANT_SCIENCE_RESUME_GATE_READY",
        "next_packet": "LSIAC-SCIENCE-RESUME-READINESS",
        "next_operator_gate": "LSIAC-SCIENCE-RESUME",
        "authority_effect": AUTHORITY_EFFECT,
    }
