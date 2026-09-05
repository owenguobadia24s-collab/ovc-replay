from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .pass2_gen0002 import (
    AUTHORITY_EFFECT as PASS2_AUTHORITY_EFFECT,
    EXPECTED_PASS1_VIRTUAL_VIEW_ID,
    EXPECTED_PROTOCOL_BINDING_ID,
    OPERATOR_AUTHORITY_DECISION_ID,
    build_pass2_adjudication_view,
)

PROGRAMME_ID = "OVC-LSIAC-v0.1"
GENERATION_ID = "OVC-LSIAC-ACCESSION-GEN-0002"
PACKET_ID = "LSIAC-GEN0002-LSIR-REGISTER-MATERIALISATION"
PASS2_PACKET_ID = "LSIAC-GEN0002-PASS2-SURVIVAL-ROLE-DESTINATION-EFFECT"
PASS2_VIRTUAL_VIEW_ID = "58b364fbf7b8ce160877fb8bba641cb853ea1b29b5af9c4a4b1a5294648749d8"
PASS2_MERGE_COMMIT = "0c4fb692086854cd341467de7e73baae249b2910"
PROJECTION = "GEN0002_POST_PASS2_REGISTER_MATERIALISATION_V1"
AUTHORITY_EFFECT = "NONE_REGISTER_MATERIALISATION_ONLY"

REGISTER_KINDS = (
    "LSIR",
    "NEGATIVE_KNOWLEDGE",
    "SUPERSESSION",
    "DESTINATION_BINDING",
    "ARCHITECTURE_EFFECT",
    "ARCHITECTURE_GAP",
)


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _with_id(payload: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    return {**body, "register_id": _canonical_sha256(body)}


def _decision_subject(decision: Mapping[str, Any]) -> str:
    subjects = decision.get("source_subject_ids")
    if not isinstance(subjects, list) or len(subjects) != 1:
        raise ValueError("LSIAC_GEN0002_REGISTER_DECISION_SUBJECT_CARDINALITY_INVALID")
    return str(subjects[0])


def _counterevidence_by_candidate(view: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for manifest in view.get("counterevidence_manifests", []):
        candidate_id = str(manifest.get("inheritance_candidate_id", ""))
        if not candidate_id or candidate_id in result:
            raise ValueError("LSIAC_GEN0002_REGISTER_COUNTEREVIDENCE_ID_INVALID")
        result[candidate_id] = manifest
    return result


def _lsir(view: Mapping[str, Any]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    decision_index: list[dict[str, Any]] = []
    for decision in view["decisions"]:
        subject_id = _decision_subject(decision)
        roles = [str(role) for role in decision["inheritance_roles"]]
        decision_index.append(
            {
                "subject_id": subject_id,
                "decision_id": str(decision["decision_id"]),
                "inheritance_id": str(decision["inheritance_id"]),
                "inheritance_roles": roles,
                "lifecycle_state": str(decision["lifecycle_state"]),
                "docket_status": str(decision["docket_status"]),
            }
        )
        if set(roles) != {"NONE"}:
            entries.append(
                {
                    "subject_id": subject_id,
                    "decision_id": str(decision["decision_id"]),
                    "inheritance_id": str(decision["inheritance_id"]),
                    "inheritance_roles": roles,
                    "lifecycle_state": str(decision["lifecycle_state"]),
                    "claim_strength": str(decision["claim_strength"]),
                }
            )
    payload = {
        "schema": "ovc-lsiac-gen0002-lsir/v0.1",
        "programme_id": PROGRAMME_ID,
        "generation_id": GENERATION_ID,
        "source_pass2_virtual_view_id": PASS2_VIRTUAL_VIEW_ID,
        "entry_count": len(entries),
        "entries": entries,
        "decision_index_count": len(decision_index),
        "decision_index": decision_index,
        "rule": "ONLY_NON_NONE_PASS2_INHERITANCE_ROLES_ENTER_FORWARD_LSIR_ENTRIES",
        "authority_effect": AUTHORITY_EFFECT,
    }
    return _with_id(payload)


def _negative_knowledge(view: Mapping[str, Any]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    deferred: list[str] = []
    for decision in view["decisions"]:
        subject_id = _decision_subject(decision)
        roles = {str(role) for role in decision["inheritance_roles"]}
        if "NEGATIVE_KNOWLEDGE" in roles:
            entries.append(
                {
                    "subject_id": subject_id,
                    "decision_id": str(decision["decision_id"]),
                    "claim_strength": str(decision["claim_strength"]),
                    "surviving_statement": str(decision["surviving_statement"]),
                }
            )
        elif decision.get("scientific_disposition") == "NEGATIVE_SUPPORTED":
            deferred.append(subject_id)
    payload = {
        "schema": "ovc-lsiac-gen0002-negative-knowledge-register/v0.1",
        "programme_id": PROGRAMME_ID,
        "generation_id": GENERATION_ID,
        "source_pass2_virtual_view_id": PASS2_VIRTUAL_VIEW_ID,
        "entry_count": len(entries),
        "entries": entries,
        "deferred_negative_subject_count": len(deferred),
        "deferred_negative_subject_ids": sorted(deferred),
        "rule": "NEGATIVE_SUPPORTED_SOURCE_DISPOSITION_DOES_NOT_ENTER_REGISTER_WITHOUT_NEGATIVE_KNOWLEDGE_INHERITANCE_ROLE",
        "authority_effect": AUTHORITY_EFFECT,
    }
    return _with_id(payload)


def _supersession(view: Mapping[str, Any]) -> dict[str, Any]:
    edges: list[dict[str, str]] = []
    for decision in view["decisions"]:
        subject_id = _decision_subject(decision)
        for edge in decision.get("supersession_edges", []):
            edges.append(
                {
                    "subject_id": subject_id,
                    "decision_id": str(decision["decision_id"]),
                    "edge_ref": str(edge),
                }
            )
    payload = {
        "schema": "ovc-lsiac-gen0002-supersession-register/v0.1",
        "programme_id": PROGRAMME_ID,
        "generation_id": GENERATION_ID,
        "source_pass2_virtual_view_id": PASS2_VIRTUAL_VIEW_ID,
        "edge_count": len(edges),
        "edges": sorted(edges, key=lambda value: (value["subject_id"], value["edge_ref"])),
        "rule": "NO_SUPERSESSION_EDGE_IS_INFERRED_FROM_TITLE_LINEAGE_OR_NO_FORWARD_DISPOSITION",
        "authority_effect": AUTHORITY_EFFECT,
    }
    return _with_id(payload)


def _destination_bindings(view: Mapping[str, Any]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    empty_count = 0
    for decision in view["decisions"]:
        binding = decision["destination_binding_set"]
        controlling = binding.get("controlling_destination")
        consumers = list(binding.get("consumer_destinations", []))
        if controlling is None and not consumers:
            empty_count += 1
            continue
        entries.append(
            {
                "subject_id": _decision_subject(decision),
                "decision_id": str(decision["decision_id"]),
                "controlling_destination": controlling,
                "consumer_destinations": consumers,
            }
        )
    payload = {
        "schema": "ovc-lsiac-gen0002-destination-binding-register/v0.1",
        "programme_id": PROGRAMME_ID,
        "generation_id": GENERATION_ID,
        "source_pass2_virtual_view_id": PASS2_VIRTUAL_VIEW_ID,
        "binding_count": len(entries),
        "entries": entries,
        "empty_binding_decision_count": empty_count,
        "rule": "REGISTER_IS_DECLARATIVE_ONLY_AND_CANNOT_EXECUTE_OWNER_OR_ARCHITECTURE_CHANGES",
        "authority_effect": AUTHORITY_EFFECT,
    }
    return _with_id(payload)


def _architecture_effects(view: Mapping[str, Any]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    actionable_count = 0
    for decision in view["decisions"]:
        effect = decision["architecture_effect_set"]
        primary = str(effect["primary_effect"])
        secondary = sorted(str(value) for value in effect.get("secondary_effects", []))
        counts[primary] = counts.get(primary, 0) + 1
        actionable = primary != "NO_FORWARD_IMPLEMENTATION" or bool(secondary)
        actionable_count += int(actionable)
        records.append(
            {
                "subject_id": _decision_subject(decision),
                "decision_id": str(decision["decision_id"]),
                "primary_effect": primary,
                "secondary_effects": secondary,
                "actionable_under_current_authority": False,
            }
        )
    payload = {
        "schema": "ovc-lsiac-gen0002-architecture-effect-register/v0.1",
        "programme_id": PROGRAMME_ID,
        "generation_id": GENERATION_ID,
        "source_pass2_virtual_view_id": PASS2_VIRTUAL_VIEW_ID,
        "record_count": len(records),
        "records": records,
        "primary_effect_counts": dict(sorted(counts.items())),
        "actionable_effect_count": actionable_count,
        "execution_count": 0,
        "rule": "ARCHITECTURE_EFFECT_RECORDS_ARE_ADJUDICATION_METADATA_ONLY_UNTIL_SEPARATELY_AUTHORISED",
        "authority_effect": AUTHORITY_EFFECT,
    }
    return _with_id(payload)


def _architecture_gaps(view: Mapping[str, Any]) -> dict[str, Any]:
    counterevidence = _counterevidence_by_candidate(view)
    gaps: list[dict[str, Any]] = []
    for decision in view["decisions"]:
        candidate_id = str(decision["inheritance_id"])
        manifest = counterevidence.get(candidate_id)
        if manifest is None:
            raise ValueError("LSIAC_GEN0002_REGISTER_COUNTEREVIDENCE_MISSING")
        debt = sorted(str(value) for value in manifest.get("source_binding_debt", []))
        if not debt:
            continue
        gaps.append(
            {
                "gap_id": "LSIAC-GEN0002-GAP-" + hashlib.sha256(
                    f"{_decision_subject(decision)}|{'|'.join(debt)}".encode("utf-8")
                ).hexdigest()[:24],
                "subject_id": _decision_subject(decision),
                "decision_id": str(decision["decision_id"]),
                "severity": "REPRODUCIBILITY_BLOCKER",
                "basis": debt,
                "downstream_effect": "NO_FORWARD_IMPLEMENTATION",
                "resolution_route": "SUCCESSOR_SOURCE_BINDING_OR_SEPARATELY_AUTHORISED_SUCCESSOR_ADJUDICATION",
            }
        )
    payload = {
        "schema": "ovc-lsiac-gen0002-architecture-gap-register/v0.1",
        "programme_id": PROGRAMME_ID,
        "generation_id": GENERATION_ID,
        "source_pass2_virtual_view_id": PASS2_VIRTUAL_VIEW_ID,
        "gap_count": len(gaps),
        "gaps": sorted(gaps, key=lambda value: value["gap_id"]),
        "rule": "ONLY_EXPLICIT_PASS2_COUNTEREVIDENCE_SOURCE_BINDING_DEBT_MAY_CREATE_A_REPRODUCIBILITY_BLOCKER_GAP",
        "authority_effect": AUTHORITY_EFFECT,
    }
    return _with_id(payload)


def build_register_bundle(root: str) -> dict[str, Any]:
    view = build_pass2_adjudication_view(root)
    if view.get("packet_id") != PASS2_PACKET_ID:
        raise ValueError("LSIAC_GEN0002_REGISTER_PASS2_PACKET_MISMATCH")
    if view.get("operator_authority_decision_id") != OPERATOR_AUTHORITY_DECISION_ID:
        raise ValueError("LSIAC_GEN0002_REGISTER_OPERATOR_AUTHORITY_MISMATCH")
    if view.get("pass1_virtual_view_id") != EXPECTED_PASS1_VIRTUAL_VIEW_ID:
        raise ValueError("LSIAC_GEN0002_REGISTER_PASS1_VIEW_MISMATCH")
    if view.get("protocol_binding_id") != EXPECTED_PROTOCOL_BINDING_ID:
        raise ValueError("LSIAC_GEN0002_REGISTER_PROTOCOL_BINDING_MISMATCH")
    if view.get("authority_effect") != PASS2_AUTHORITY_EFFECT:
        raise ValueError("LSIAC_GEN0002_REGISTER_PASS2_AUTHORITY_EFFECT_MISMATCH")

    registers = {
        "lsir": _lsir(view),
        "negative_knowledge": _negative_knowledge(view),
        "supersession": _supersession(view),
        "destination_binding": _destination_bindings(view),
        "architecture_effect": _architecture_effects(view),
        "architecture_gap": _architecture_gaps(view),
    }
    identities = {name: register["register_id"] for name, register in sorted(registers.items())}
    payload = {
        "schema": "ovc-lsiac-gen0002-register-bundle/v0.1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "generation_id": GENERATION_ID,
        "source_pass2_virtual_view_id": PASS2_VIRTUAL_VIEW_ID,
        "source_pass2_merge_commit": PASS2_MERGE_COMMIT,
        "registers": registers,
        "register_identities": identities,
        "register_kind_count": len(registers),
        "projection": PROJECTION,
        "authority_effect": AUTHORITY_EFFECT,
    }
    return {**payload, "bundle_id": _canonical_sha256(payload)}


def build_virtual_bundle_identity(*, algorithm_git_blob_sha: str) -> str:
    payload = {
        "schema": "ovc-lsiac-gen0002-register-bundle-identity/v0.1",
        "programme_id": PROGRAMME_ID,
        "generation_id": GENERATION_ID,
        "packet_id": PACKET_ID,
        "source_pass2_virtual_view_id": PASS2_VIRTUAL_VIEW_ID,
        "source_pass2_merge_commit": PASS2_MERGE_COMMIT,
        "operator_authority_decision_id": OPERATOR_AUTHORITY_DECISION_ID,
        "protocol_binding_id": EXPECTED_PROTOCOL_BINDING_ID,
        "algorithm_git_blob_sha": algorithm_git_blob_sha,
        "register_kinds": list(REGISTER_KINDS),
        "projection": PROJECTION,
        "authority_effect": AUTHORITY_EFFECT,
    }
    return _canonical_sha256(payload)
