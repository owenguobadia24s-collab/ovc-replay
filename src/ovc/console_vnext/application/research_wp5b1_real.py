"""Source-bound real DMRP projection for RCN-RN-WP5B1.

The adapter is presentation-only. It validates the exact operator grant and exact
DMRP owner court records before exposing them. It does not discover or repair
research objects, and it never falls back to synthetic fixtures in real mode.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from .errors import AuthorityDenied, ContractError, SourceConflict
from .research_wp5a import git_blob_sha

_BINDING_SCHEMA = "ovc-rcn-rn-wp5b1-dmrp-real-source-bindings/v1"
_REQUIRED_SOURCE_IDS = {
    "DMRP_CURRENT_STATE_POINTER",
    "DMRP_GREAL_EC1_STATE",
    "DMRP_OBJECT_TYPE_REGISTRY",
}
_REQUIRED_OBJECT_TYPES = {
    "ResearchCandidateGeneration",
    "Path1CandidateProposal",
    "CrossModeExposureLedger",
    "ResearchInfluenceEdge",
}


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{label}_OBJECT_REQUIRED")
    return dict(value)


def _load(path: Path, label: str) -> dict[str, Any]:
    try:
        return _object(json.loads(path.read_text(encoding="utf-8")), label)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label}_INVALID_JSON") from exc


def _repo_path(root: Path, relative: str) -> Path:
    if not relative or Path(relative).is_absolute():
        raise ContractError("WP5B1_REAL_SOURCE_PATH_RELATIVE_REQUIRED")
    base = root.resolve()
    candidate = (base / relative).resolve(strict=False)
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ContractError("WP5B1_REAL_SOURCE_PATH_ESCAPES_REPOSITORY") from exc
    if not candidate.is_file():
        raise ContractError(f"WP5B1_REAL_SOURCE_FILE_MISSING:{relative}")
    return candidate


def _load_bound(root: Path, binding: Mapping[str, Any], label: str) -> dict[str, Any]:
    path = _repo_path(root, str(binding.get("path", "")))
    if git_blob_sha(path) != binding.get("git_blob_sha"):
        raise SourceConflict(f"WP5B1_REAL_SOURCE_BLOB_MISMATCH:{label}")
    value = _load(path, label)
    if value.get("schema") != binding.get("schema"):
        raise SourceConflict(f"WP5B1_REAL_SOURCE_SCHEMA_MISMATCH:{label}")
    return value


def build_wp5b1_dmrp_real_envelope(
    *, repository_root: Path, bindings: Mapping[str, Any] | Path
) -> dict[str, Any]:
    root = Path(repository_root)
    registry = copy.deepcopy(dict(bindings)) if isinstance(bindings, Mapping) else _load(Path(bindings), "WP5B1_REAL_BINDINGS")

    if registry.get("schema") != _BINDING_SCHEMA:
        raise ContractError("WP5B1_REAL_BINDING_SCHEMA_INVALID")
    expected = {
        "packet_id": "RCN-RN-WP5B1",
        "owner": "DMRP",
        "transport": "GET_ONLY",
        "writes": "NONE",
        "presentation_mode": "REAL_SOURCE_READ_ONLY",
        "authority_effect": "NONE",
        "validation_consumption": "LOCKED_UNCONSUMED",
        "first_new_real_research_source": True,
        "gate_id": "RCN-RN-G5-FIRST-NEW-SOURCE[DMRP]",
        "fixture_fallback": "PROHIBITED_IN_REAL_MODE",
        "source_admission_transitivity": "PROHIBITED",
        "independence_inference_from_missing_exposure": "PROHIBITED",
        "candidate_mutation": "PROHIBITED",
    }
    for key, value in expected.items():
        if registry.get(key) != value:
            raise AuthorityDenied(f"WP5B1_REAL_BINDING_AUTHORITY_INVALID:{key}")

    decision_binding = _object(registry.get("gate_decision"), "WP5B1_GATE_DECISION_BINDING")
    decision_path = _repo_path(root, str(decision_binding.get("path", "")))
    if git_blob_sha(decision_path) != decision_binding.get("git_blob_sha"):
        raise SourceConflict("WP5B1_GATE_DECISION_BLOB_MISMATCH")
    decision = _load(decision_path, "WP5B1_GATE_DECISION")
    if decision.get("gate_id") != registry["gate_id"] or decision.get("decision") != "PASS":
        raise AuthorityDenied("WP5B1_DMRP_SOURCE_GATE_NOT_PASSED")
    if decision.get("source_scope") != "DMRP" or decision.get("non_transitive") is not True:
        raise AuthorityDenied("WP5B1_DMRP_GATE_SCOPE_INVALID")
    if decision.get("transport") != "GET_ONLY" or decision.get("read_only") is not True:
        raise AuthorityDenied("WP5B1_DMRP_GATE_READ_ONLY_REQUIRED")

    rows = registry.get("sources")
    if not isinstance(rows, list):
        raise ContractError("WP5B1_REAL_SOURCE_BINDINGS_LIST_REQUIRED")
    by_id = {str(row.get("source_id")): _object(row, "WP5B1_REAL_SOURCE_BINDING") for row in rows if isinstance(row, Mapping)}
    if set(by_id) != _REQUIRED_SOURCE_IDS:
        raise SourceConflict("WP5B1_REAL_SOURCE_SET_INVALID")

    pointer = _load_bound(root, by_id["DMRP_CURRENT_STATE_POINTER"], "DMRP_CURRENT_STATE_POINTER")
    state = _load_bound(root, by_id["DMRP_GREAL_EC1_STATE"], "DMRP_GREAL_EC1_STATE")
    object_registry = _load_bound(root, by_id["DMRP_OBJECT_TYPE_REGISTRY"], "DMRP_OBJECT_TYPE_REGISTRY")

    if pointer.get("programme_id") != "OVC-EC1-DMRP-CONFORMANCE-v0.1":
        raise SourceConflict("WP5B1_DMRP_PROGRAMME_ID_MISMATCH")
    if pointer.get("current_state") != "DMRPI_GREAL_EC1_STATE.json":
        raise SourceConflict("WP5B1_DMRP_CURRENT_STATE_MISMATCH")
    if pointer.get("status") != "COMPLETED" or pointer.get("gate_status") != "COMPLETED":
        raise AuthorityDenied("WP5B1_DMRP_OWNER_STATE_NOT_COMPLETED")
    if pointer.get("real_source_authority") != "AUTHORISED_BOUNDED":
        raise AuthorityDenied("WP5B1_DMRP_OWNER_REAL_SOURCE_NOT_AUTHORISED")
    if pointer.get("validation") != "LOCKED_UNCONSUMED":
        raise AuthorityDenied("WP5B1_DMRP_VALIDATION_MUST_REMAIN_LOCKED")

    if state.get("programme_id") != pointer.get("programme_id") or state.get("status") != "COMPLETED":
        raise SourceConflict("WP5B1_DMRP_STATE_POINTER_COHERENCE_FAILURE")
    approved = _object(state.get("approved_authority"), "WP5B1_DMRP_APPROVED_AUTHORITY")
    if approved.get("dmrp_real_ec1_execution") != "AUTHORISED_BOUNDED":
        raise AuthorityDenied("WP5B1_DMRP_REAL_EXECUTION_OWNER_AUTHORITY_MISSING")
    if state.get("validation") != "LOCKED_UNCONSUMED":
        raise AuthorityDenied("WP5B1_DMRP_STATE_VALIDATION_MUST_REMAIN_LOCKED")
    if state.get("candidate_freeze") != "NONE":
        raise SourceConflict("WP5B1_DMRP_CANDIDATE_FREEZE_CHANGED_REBIND_REQUIRED")

    object_types = object_registry.get("object_types")
    if not isinstance(object_types, list) or not _REQUIRED_OBJECT_TYPES.issubset(set(map(str, object_types))):
        raise SourceConflict("WP5B1_DMRP_OBJECT_TYPE_REGISTRY_INCOMPLETE")

    scope = _object(state.get("scope"), "WP5B1_DMRP_SCOPE")
    source_refs = {
        key: {
            "path": by_id[key]["path"],
            "git_blob_sha": by_id[key]["git_blob_sha"],
        }
        for key in sorted(by_id)
    }

    snapshot = {
        "schema": "ovc-rcn-rn-wp5b1-dmrp-real-snapshot/v1",
        "packet_id": "RCN-RN-WP5B1",
        "mode": "REAL_SOURCE_READ_ONLY",
        "data_classification": "DMRP_OWNER_COURT_RECORD",
        "evidence_status": "OWNER_SOURCE_BOUND",
        "authority_effect": "NONE",
        "source_preflight": {
            "status": "PASS_OPERATOR_APPROVED_DMRP_SOURCE",
            "gate_id": registry["gate_id"],
            "decision_ref": decision_binding["path"],
            "first_new_real_research_source": True,
            "source_binding_registry": "registries/research_console_vnext/research_native/wp5b1_dmrp_real_source_bindings_v1.json",
            "source_ids": sorted(by_id),
            "fixture_fallback": "PROHIBITED",
            "source_admission_transitivity": "PROHIBITED",
        },
        "path1": {
            "availability": "AVAILABLE_OWNER_STATE",
            "research_mode": "PATH_1_EMPIRICAL",
            "research_role": scope.get("research_role"),
            "study_id": state.get("programme_id"),
            "cycle_id": state.get("packet_id"),
            "question_id": "NOT_MATERIALIZED_IN_BOUND_OWNER_RECORDS",
            "validation_access_state": state.get("validation"),
            "source_id": "DMRP_GREAL_EC1_STATE",
            "scope": scope,
        },
        "path2": {
            "availability": "REFERENCE_ONLY",
            "training_id": None,
            "guided_formalisation_id": None,
            "ready_intake_id": None,
            "divergent_intake_id": None,
            "divergent_disposition": "UNRESOLVED_NOT_BOUND",
            "real_source_authority": "OWNER_RECORD_NOT_BOUND_TO_THIS_SURFACE",
            "parallel_path2_reference": pointer.get("parallel_path2_resume"),
            "source_id": "DMRP_CURRENT_STATE_POINTER",
        },
        "candidate_generation": {
            "availability": "NO_FROZEN_GENERATION_IN_BOUND_OWNER_STATE",
            "candidate_freeze": state.get("candidate_freeze"),
            "series_id": None,
            "origin_mode": None,
            "generation": None,
            "population_id": None,
            "required_dependencies": [],
            "membership": {},
            "source_id": "DMRP_GREAL_EC1_STATE",
        },
        "cross_mode": [],
        "cross_mode_state": {
            "status": "UNRESOLVED_NO_BOUND_CORRESPONDENCE_EXPOSURE_RECORDS",
            "independence": "UNKNOWN",
            "missing_exposure_implies_independence": False,
        },
        "negative_divergent_evidence": [],
        "negative_evidence_state": "NO_BOUND_OWNER_RECORDS_DO_NOT_INFER_ABSENCE",
        "owner_object_types": sorted(set(map(str, object_types)) & _REQUIRED_OBJECT_TYPES),
        "source_refs": source_refs,
        "presentation_guardrails": {
            "candidate_construction": "PROHIBITED",
            "candidate_repair": "PROHIBITED",
            "candidate_identity_merge": "PROHIBITED",
            "candidate_promotion": "NONE",
            "path_winner": None,
            "ranking": "NONE",
            "correspondence_is_independence": False,
            "missing_exposure_implies_independence": False,
            "frontend_scientific_calculation": "PROHIBITED",
            "writes": "NONE",
            "validation_consumption": "LOCKED_UNCONSUMED",
            "first_new_real_research_source": True,
            "source_admission_transitivity": "PROHIBITED",
        },
    }

    return {
        "real_source_banner": {
            "mode": "REAL_SOURCE_READ_ONLY",
            "data_classification": "DMRP_OWNER_COURT_RECORD",
            "presentation_authority": registry["gate_id"],
            "source_owner_authority": "UNCHANGED",
            "authority_effect": "NONE",
            "fixture_fallback": "PROHIBITED",
            "source_admission_transitivity": "PROHIBITED",
        },
        "schema_id": "ovc-rcn-rn-wp5b1-dmrp-real-snapshot/v1",
        "resource": "research.dmrp.snapshot",
        "source_identity": {
            "source_id": "DMRP_OWNER_RECORD_SET",
            "source_commit": state.get("merge_commit"),
            "members": source_refs,
        },
        "chronology": {
            "status": "OWNER_STATE_CURRENT_POINTER",
            "ordering": "OWNER_RECORDED",
            "current_packet": pointer.get("current_packet"),
            "current_gate": pointer.get("current_gate"),
        },
        "missingness": {
            "status": "EXPLICIT_UNBOUND_OPTIONAL_RECORDS",
            "reason_codes": [
                "NO_BOUND_RESEARCH_CANDIDATE_GENERATION_RECORD",
                "NO_BOUND_CROSS_MODE_CORRESPONDENCE_OR_EXPOSURE_RECORD",
                "NO_BOUND_PATH2_OBJECT_PAYLOAD"
            ],
        },
        "qa": {
            "status": "PASS",
            "provenance": [decision_binding["path"], *[source_refs[key]["path"] for key in sorted(source_refs)]],
        },
        "capability": {
            "capability_id": "RESEARCH_DMRP",
            "available": True,
            "authorised": True,
            "active": False,
            "authority_effect": "NONE",
        },
        "payload": snapshot,
    }
