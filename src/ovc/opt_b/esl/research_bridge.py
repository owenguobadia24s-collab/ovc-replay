from __future__ import annotations

from typing import Any, Mapping, Sequence

from .canonical import sha256_canonical
from .term_qualification import build_language_candidate_binding


class ResearchBridgeError(ValueError):
    pass


RESEARCH_MODES = frozenset({"PATH_1", "PATH_2"})
BRIDGE_MATURITY = "INTERFACE_ONLY"


def build_research_evidence_handoff(*, mode: str, evidence_refs: Sequence[Any], evidence_frontier_ref: str, research_operations_owner: str = "OVC_RESEARCH_OPERATIONS", mechanism_refs: Sequence[Any] = (), runtime_available: bool = False) -> dict[str, Any]:
    mode_value = str(mode)
    if mode_value not in RESEARCH_MODES:
        raise ResearchBridgeError("ESL_DMRP_MODE_INVALID")
    evidence = sorted({str(x) for x in evidence_refs})
    if not evidence:
        raise ResearchBridgeError("ESL_DMRP_EVIDENCE_REQUIRED")
    mechanisms = sorted({str(x) for x in mechanism_refs})
    if mechanisms and research_operations_owner != "OVC_RESEARCH_OPERATIONS":
        raise ResearchBridgeError("ESL_DMRP_MECHANISM_OWNER_MUST_BE_RESEARCH_OPERATIONS")
    payload = {
        "schema":"ovc-esl-research-evidence-handoff/v1",
        "research_mode":mode_value,
        "evidence_refs":evidence,
        "evidence_frontier_ref":str(evidence_frontier_ref),
        "mechanism_refs":mechanisms,
        "mechanism_owner":"OVC_RESEARCH_OPERATIONS",
        "bridge_maturity":BRIDGE_MATURITY,
        "runtime_state":"AVAILABLE" if runtime_available else "DOWNSTREAM_RUNTIME_NOT_MATERIALIZED",
        "execution_boundary":"FULL_RESEARCH_RUNTIME" if runtime_available else "FULL_RESEARCH_HANDOFF",
        "authority_effect":"NONE",
        "candidate_freeze":"NOT_GRANTED",
        "semantic_admission":"NOT_GRANTED",
    }
    payload["handoff_id"] = "roh1:" + sha256_canonical(payload)
    return payload


def bind_research_candidate_generation(*, handoff: Mapping[str, Any], research_candidate_generation_id: str, structural_term_candidate_id: str, vocabulary_exposure: str = "UNKNOWN") -> dict[str, Any]:
    if handoff.get("schema") != "ovc-esl-research-evidence-handoff/v1":
        raise ResearchBridgeError("ESL_DMRP_HANDOFF_SCHEMA_INVALID")
    if handoff.get("bridge_maturity") != BRIDGE_MATURITY:
        raise ResearchBridgeError("ESL_DMRP_BRIDGE_NOT_INTERFACE_ONLY")
    binding = build_language_candidate_binding(
        research_candidate_generation_id=research_candidate_generation_id,
        structural_term_candidate_id=structural_term_candidate_id,
        source_mode=str(handoff["research_mode"]),
        vocabulary_exposure=vocabulary_exposure,
    )
    return {
        "schema":"ovc-esl-research-candidate-handoff-binding/v1",
        "handoff_id":handoff["handoff_id"],
        "research_mode":handoff["research_mode"],
        "language_candidate_binding":binding,
        "identity_merge":"FORBIDDEN",
        "mechanism_owner":"OVC_RESEARCH_OPERATIONS",
        "authority_effect":"NONE",
        "candidate_freeze":"OPERATOR_RESERVED",
        "semantic_admission":"OPERATOR_RESERVED",
    }


def assert_no_runtime_fabrication(handoff: Mapping[str, Any]) -> None:
    if handoff.get("runtime_state") == "DOWNSTREAM_RUNTIME_NOT_MATERIALIZED" and handoff.get("execution_boundary") != "FULL_RESEARCH_HANDOFF":
        raise ResearchBridgeError("FULL_RESEARCH_RUNTIME_FABRICATION_FORBIDDEN")
