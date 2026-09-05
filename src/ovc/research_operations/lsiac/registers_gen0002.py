from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .pass2_gen0002 import (
    AUTHORITY_EFFECT as PASS2_AUTHORITY_EFFECT,
    EXPECTED_PASS1_VIRTUAL_VIEW_ID,
    EXPECTED_PROTOCOL_BINDING_ID,
    OPERATOR_AUTHORITY_DECISION_ID,
    build_pass2_adjudication_view,
    build_virtual_view_identity as build_pass2_virtual_view_identity,
)

PACKET_ID = "LSIAC-GEN0002-LSIR-REGISTER-MATERIALISATION"
GENERATION_ID = "OVC-LSIAC-ACCESSION-GEN-0002"
EXPECTED_PASS2_VIRTUAL_VIEW_ID = "58b364fbf7b8ce160877fb8bba641cb853ea1b29b5af9c4a4b1a5294648749d8"
PASS2_ALGORITHM_GIT_BLOB_SHA = "9ef62432a43ea0fffce529fd181bdb17662c2f04"
AUTHORITY_EFFECT = "NONE_REGISTER_MATERIALISATION_ONLY"
GAP_CLASS = "SOURCE_BINDING_GAP_NOT_ARCHITECTURE_ACTIVATION_REQUEST"


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _sorted(values: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    return sorted(values, key=lambda item: json.dumps(item.get(key), sort_keys=True, separators=(",", ":")))


def _register(name: str, members: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "register_id": name,
        "generation_id": GENERATION_ID,
        "members": members,
    }
    return {
        **payload,
        "member_count": len(members),
        "members_canonical_sha256": _canonical_sha256(members),
    }


def _assert_source_binding(pass2: Mapping[str, Any]) -> None:
    if pass2.get("subject_count") != 431 or pass2.get("passport_count") != 434:
        raise ValueError("LSIAC_GEN0002_REGISTERS_CARDINALITY_MISMATCH")
    if pass2.get("pass1_virtual_view_id") != EXPECTED_PASS1_VIRTUAL_VIEW_ID:
        raise ValueError("LSIAC_GEN0002_REGISTERS_PASS1_VIEW_MISMATCH")
    if pass2.get("protocol_binding_id") != EXPECTED_PROTOCOL_BINDING_ID:
        raise ValueError("LSIAC_GEN0002_REGISTERS_PROTOCOL_BINDING_MISMATCH")
    if pass2.get("operator_authority_decision_id") != OPERATOR_AUTHORITY_DECISION_ID:
        raise ValueError("LSIAC_GEN0002_REGISTERS_OPERATOR_AUTHORITY_MISMATCH")
    expected_pass2 = build_pass2_virtual_view_identity(
        algorithm_git_blob_sha=PASS2_ALGORITHM_GIT_BLOB_SHA
    )
    if expected_pass2 != EXPECTED_PASS2_VIRTUAL_VIEW_ID:
        raise ValueError("LSIAC_GEN0002_REGISTERS_PASS2_VIEW_IDENTITY_MISMATCH")


def build_gen0002_register_bundle(root: str | Path) -> dict[str, Any]:
    """Build zero-copy post-Pass2 register projections without adding scientific authority."""
    pass2 = build_pass2_adjudication_view(Path(root))
    _assert_source_binding(pass2)

    lsir_members: list[dict[str, Any]] = []
    negative_members: list[dict[str, Any]] = []
    supersession_members: list[dict[str, Any]] = []
    destination_members: list[dict[str, Any]] = []
    architecture_effect_members: list[dict[str, Any]] = []
    gap_members: list[dict[str, Any]] = []

    for decision in pass2["decisions"]:
        subject_id = str(decision["source_subject_ids"][0])
        lsir = {
            "decision_id": decision["decision_id"],
            "inheritance_id": decision["inheritance_id"],
            "source_subject_id": subject_id,
            "source_standing": decision["source_standing"],
            "scientific_disposition": decision["scientific_disposition"],
            "exposure_state": decision["exposure_state"],
            "claim_strength": decision["claim_strength"],
            "inheritance_roles": list(decision["inheritance_roles"]),
            "lifecycle_state": decision["lifecycle_state"],
            "docket_status": decision["docket_status"],
            "authority_state": decision["authority_state"],
            "counterevidence_manifest_sha256": decision["counterevidence_manifest_sha256"],
            "authority_effect": decision["authority_effect"],
        }
        lsir_members.append(lsir)

        if decision["scientific_disposition"] == "NEGATIVE_SUPPORTED":
            negative_members.append(
                {
                    "decision_id": decision["decision_id"],
                    "source_subject_id": subject_id,
                    "scientific_disposition": "NEGATIVE_SUPPORTED",
                    "claim_strength": decision["claim_strength"],
                    "inheritance_roles": list(decision["inheritance_roles"]),
                    "interpretation": "PRESERVE_NEGATIVE_KNOWLEDGE_NO_REPLACEMENT_THEORY_INFERENCE",
                }
            )

        for edge in decision.get("supersession_edges", []):
            supersession_members.append(
                {
                    "decision_id": decision["decision_id"],
                    "source_subject_id": subject_id,
                    "edge": edge,
                }
            )

        destination = decision["destination_binding_set"]
        if destination.get("controlling_destination") or destination.get("consumer_destinations"):
            destination_members.append(
                {
                    "decision_id": decision["decision_id"],
                    "source_subject_id": subject_id,
                    "destination_binding_set": destination,
                }
            )

        architecture_effect_members.append(
            {
                "decision_id": decision["decision_id"],
                "source_subject_id": subject_id,
                "architecture_effect_set": decision["architecture_effect_set"],
                "execution_authority": "NONE",
            }
        )

        if decision["docket_status"] == "SOURCE_BINDING_REQUIRED":
            gap_members.append(
                {
                    "decision_id": decision["decision_id"],
                    "source_subject_id": subject_id,
                    "gap_class": GAP_CLASS,
                    "claim_strength": decision["claim_strength"],
                    "lifecycle_state": decision["lifecycle_state"],
                    "authority_effect": "NONE",
                }
            )

    registers = {
        "laboratory_scientific_inheritance_register": _register(
            "LSIR_GEN0002", _sorted(lsir_members, "source_subject_id")
        ),
        "negative_knowledge_register": _register(
            "NEGATIVE_KNOWLEDGE_GEN0002", _sorted(negative_members, "source_subject_id")
        ),
        "supersession_register": _register(
            "SUPERSESSION_GEN0002", _sorted(supersession_members, "source_subject_id")
        ),
        "destination_binding_sets": _register(
            "DESTINATION_BINDINGS_GEN0002", _sorted(destination_members, "source_subject_id")
        ),
        "architecture_effect_sets": _register(
            "ARCHITECTURE_EFFECTS_GEN0002", _sorted(architecture_effect_members, "source_subject_id")
        ),
        "architecture_gap_register": _register(
            "ARCHITECTURE_GAPS_GEN0002", _sorted(gap_members, "source_subject_id")
        ),
    }

    source_binding = {
        "pass2_virtual_view_id": EXPECTED_PASS2_VIRTUAL_VIEW_ID,
        "pass2_algorithm_git_blob_sha": PASS2_ALGORITHM_GIT_BLOB_SHA,
        "pass1_virtual_view_id": EXPECTED_PASS1_VIRTUAL_VIEW_ID,
        "protocol_binding_id": EXPECTED_PROTOCOL_BINDING_ID,
        "operator_authority_decision_id": OPERATOR_AUTHORITY_DECISION_ID,
        "source_universe_id": pass2["source_universe_id"],
        "frontier_receipt_id": pass2["frontier_receipt_id"],
        "source_passport_set_sha256": pass2["source_passport_set_sha256"],
        "post_v0_5_delta_sha256": pass2["post_v0_5_delta_sha256"],
        "pass2_authority_effect": PASS2_AUTHORITY_EFFECT,
    }
    register_roots = {
        key: {
            "member_count": value["member_count"],
            "members_canonical_sha256": value["members_canonical_sha256"],
        }
        for key, value in sorted(registers.items())
    }
    bundle_core = {
        "schema": "ovc-lsiac-gen0002-register-bundle/v0.1",
        "programme_id": "OVC-LSIAC-v0.1",
        "packet_id": PACKET_ID,
        "generation_id": GENERATION_ID,
        "source_binding": source_binding,
        "registers": registers,
        "register_roots": register_roots,
        "authority_effect": AUTHORITY_EFFECT,
        "anti_inference": [
            "NO_NEW_SCIENTIFIC_CLAIM",
            "NO_ROLE_PROMOTION",
            "NO_SUPERSESSION_INFERENCE",
            "NO_DESTINATION_INFERENCE",
            "NO_ARCHITECTURE_NEED_FROM_MISSING_ROLE_ADMISSIBILITY",
            "NO_ARCHITECTURE_EFFECT_EXECUTION",
        ],
    }
    return {**bundle_core, "bundle_id": _canonical_sha256(bundle_core)}
