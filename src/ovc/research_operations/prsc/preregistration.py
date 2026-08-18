from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence


class PRSCPreregistrationError(ValueError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def build_protocol_generation(
    *,
    protocol_series_id: str,
    generation: int,
    scientific_generation: str,
    method_pack_refs: Sequence[str],
    hypothesis_family_registry_ref: str,
    claim_template_refs: Sequence[str],
    reviewer_constitution_ref: str,
    source_namespaces: Sequence[str],
    preregistration_state: str = "DRAFT",
) -> dict[str, Any]:
    if generation < 1:
        raise PRSCPreregistrationError("generation must be >= 1")
    if preregistration_state not in {"DRAFT", "READY_FOR_OPERATOR_FREEZE"}:
        raise PRSCPreregistrationError("build-ahead machinery cannot create FROZEN state")
    core = {
        "schema": "ovc-prsc-protocol-generation/v0.1",
        "protocol_series_id": protocol_series_id,
        "generation": generation,
        "scientific_generation": scientific_generation,
        "research_role": "DISCOVERY_POST_RECURRENCE_CHALLENGE",
        "outcome_blind": True,
        "method_pack_refs": sorted(set(method_pack_refs)),
        "hypothesis_family_registry_ref": hypothesis_family_registry_ref,
        "claim_template_refs": sorted(set(claim_template_refs)),
        "reviewer_constitution_ref": reviewer_constitution_ref,
        "source_namespaces": sorted(set(source_namespaces)),
        "preregistration_state": preregistration_state,
        "authority_effect": "NONE",
    }
    core["protocol_generation_id"] = _sha256(core)
    return core


def run_synthetic_candidate_to_q08(candidate_ref: str) -> dict[str, Any]:
    if not candidate_ref:
        raise PRSCPreregistrationError("candidate_ref is required")
    return {
        "candidate_ref": candidate_ref,
        "prsc_challenge_status": "SYNTHETIC_COMPLETE",
        "p1_candidate_review_card": {
            "candidate_ref": candidate_ref,
            "prsc_ref": f"synthetic-prsc:{candidate_ref}",
            "authority_effect": "NONE",
        },
        "q08": {
            "decision_tree": "DT-Q08",
            "prsc_ref": f"synthetic-prsc:{candidate_ref}",
            "status": "SYNTHETIC_ONLY",
        },
        "real_source_read": False,
        "candidate_freeze_effect": "NONE",
    }


def build_preregistration_bundle(
    *,
    protocol_generation: Mapping[str, Any],
    method_pack_refs: Sequence[str],
    hypothesis_family_registry_ref: str,
    claim_template_refs: Sequence[str],
    fatality_disposition_rule_refs: Sequence[str],
    reviewer_constitution_ref: str,
    pre_e1_information_only: bool,
    e1_decision_bearing_inspected: bool,
    synthetic_candidate_ref: str,
    mechanical_conformance_ref: str | None = None,
    g8_alg_decision_ref: str | None = None,
) -> dict[str, Any]:
    if not pre_e1_information_only:
        raise PRSCPreregistrationError("EC1-G1 preregistration requires pre-E1 information only")
    required_lists = [method_pack_refs, claim_template_refs, fatality_disposition_rule_refs]
    if any(not items for items in required_lists):
        raise PRSCPreregistrationError("all frozen reference families must be non-empty")
    if not hypothesis_family_registry_ref or not reviewer_constitution_ref:
        raise PRSCPreregistrationError("family and reviewer bindings are required")
    vertical_slice = run_synthetic_candidate_to_q08(synthetic_candidate_ref)
    payload = {
        "schema_version": "prsc_preregistration_bundle/v0.1",
        "protocol_generation": dict(protocol_generation),
        "method_pack_refs": sorted(set(method_pack_refs)),
        "hypothesis_family_registry_ref": hypothesis_family_registry_ref,
        "claim_template_refs": sorted(set(claim_template_refs)),
        "fatality_disposition_rule_refs": sorted(set(fatality_disposition_rule_refs)),
        "reviewer_constitution_ref": reviewer_constitution_ref,
        "pre_e1_information_only": True,
        "e1_decision_bearing_inspected": bool(e1_decision_bearing_inspected),
        "synthetic_vertical_slice": vertical_slice,
        "mechanical_conformance_ref": mechanical_conformance_ref,
        "g8_alg_decision_ref": g8_alg_decision_ref,
        "authority_effect": "NONE",
    }
    payload["bundle_id"] = _sha256(payload)
    return payload


def build_readiness_receipt(
    bundle: Mapping[str, Any], *, g8_alg_status: str
) -> dict[str, Any]:
    if g8_alg_status not in {"PASS", "NOT_YET_PASSED", "BLOCK", "QUARANTINE"}:
        raise PRSCPreregistrationError("invalid G8-ALG status")
    exposed = bool(bundle.get("e1_decision_bearing_inspected"))
    binding_fields = (
        bundle.get("method_pack_refs"),
        bundle.get("hypothesis_family_registry_ref"),
        bundle.get("claim_template_refs"),
        bundle.get("fatality_disposition_rule_refs"),
        bundle.get("reviewer_constitution_ref"),
    )
    complete = all(binding_fields)
    slice_pass = bundle.get("synthetic_vertical_slice", {}).get("status") is None and bool(
        bundle.get("synthetic_vertical_slice")
    )
    if g8_alg_status == "QUARANTINE":
        status = "QUARANTINED"
    elif exposed or g8_alg_status == "BLOCK" or not complete or not slice_pass:
        status = "BLOCKED"
    elif g8_alg_status == "PASS":
        status = "READY_FOR_OPERATOR_DECISION"
    else:
        status = "BUILD_AHEAD_READY"
    receipt = {
        "schema_version": "prsc_preregistration_readiness_receipt/v0.1",
        "bundle_id": bundle["bundle_id"],
        "protocol_generation_id": bundle["protocol_generation"]["protocol_generation_id"],
        "g8_alg_status": g8_alg_status,
        "e1_exposure_status": "E1_DECISION_BEARING_EXPOSED" if exposed else "PRE_E1_CLEAN",
        "binding_status": "COMPLETE" if complete else "INCOMPLETE",
        "synthetic_vertical_slice_status": "PASS" if slice_pass else "FAIL",
        "operator_gate": "PRSCI-G-PREREG",
        "status": status,
        "authority_effect": "NONE",
    }
    receipt["receipt_id"] = _sha256(receipt)
    return receipt
