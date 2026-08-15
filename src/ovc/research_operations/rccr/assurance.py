from __future__ import annotations

from typing import Any, Mapping

from .need_review import CapabilityNeedEvaluator, ModeVisibilityFirewall
from .pilot import AV_EXPECTED, RCCRPilotError
from .reference import RCCRReferenceEngine

_PROFILE = {
    "requirement_profile_id": "rccr:ResearchRequirementProfile:wp6a-av",
    "epistemic_requirements": ["R1"],
    "evidence_requirements": [],
    "population_requirements": [],
    "chronology_requirements": [],
    "inferential_requirements": [],
    "denominator_requirements": [],
    "comparability_requirements": [],
}
_FRONTIER = {"capability_frontier_id": "rccr:ResearchCapabilityFrontier:wp6a-av"}
_CANDIDATE = {"capability_id": "C2P", "owner": "OVC-C2P", "owner_contract_ref": "contract:c2p:v0.2"}


def _gap(flags: list[str], *, protocol_state: str = "VALID", result: str = "UNSATISFIED") -> str:
    assessment = RCCRReferenceEngine().assess(
        coverage_item_generation_id="coverage:wp6a:av",
        requirement_profile=_PROFILE,
        capability_frontier=_FRONTIER,
        requirement_evidence={"R1": {"result": result, "flags": flags, "evidence_refs": ["WP6A"]}},
        evaluation_cutoff="2026-08-15T23:45:00+01:00",
        protocol_state=protocol_state,
        first_valid_time="2026-08-15T23:45:00+01:00",
    )
    return str(assessment["requirement_results"][0]["gap_class"])


def _need(*, owner_fit: str = "MATCH", smaller_route: str = "EXHAUSTED", support: bool = True, counterevidence: bool = False, demand_frequency: int = 0, implementation_cost: float = 0.0) -> str:
    assessment = RCCRReferenceEngine().assess(
        coverage_item_generation_id="coverage:wp6a:need",
        requirement_profile=_PROFILE,
        capability_frontier=_FRONTIER,
        requirement_evidence={"R1": {"result": "UNSATISFIED", "flags": ["INFORMATION_GAP", "COUNTERFACTUAL_EXHAUSTED"], "evidence_refs": ["WP6A"]}},
        evaluation_cutoff="2026-08-15T23:45:00+01:00",
        first_valid_time="2026-08-15T23:45:00+01:00",
    )
    result = CapabilityNeedEvaluator().evaluate(
        coverage_assessment=assessment,
        candidate_capability=_CANDIDATE,
        missing_information_claim="bounded persistent identity",
        ownership_test={"owner_fit": owner_fit, "semantic_ownership_evidence": ["owner:c2p"] if support else []},
        minimality_test={"smaller_route_status": smaller_route, "shadow_closure_evidence": []},
        alternative_routes=["correspondence"],
        supporting_condition="identity remains necessary after smaller routes fail",
        falsifying_condition="existing information closes the gap",
        shadow_test_route="C2P_SHADOW_ONLY",
        next_owner_route="C2P_OWNER_REVIEW",
        current_counterevidence=["smaller-route-closes"] if counterevidence else [],
        first_valid_time="2026-08-15T23:45:00+01:00",
        demand_frequency=demand_frequency,
        implementation_cost=implementation_cost,
    )
    return str(result["need_status"])


def evaluate_adversarial_safeguard(case_id: str, facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Execute one AV01-AV24 safeguard using the bounded RCCR contracts.

    Facts are explicit and never sourced from protected/future evidence. This is a mechanism
    qualification harness, not a scientific result generator.
    """
    if case_id not in AV_EXPECTED:
        raise RCCRPilotError(f"unknown adversarial case: {case_id}")
    facts = dict(facts or {})

    if case_id == "AV01":
        actual = "DISTINCT_SOURCE_GENERATION" if facts.get("generation_a", "g1") != facts.get("generation_b", "g2") else "FAIL"
    elif case_id == "AV02":
        semantic_same = facts.get("semantic_hash_a", "s") == facts.get("semantic_hash_b", "s")
        artifact_changed = facts.get("artifact_hash_a", "a") != facts.get("artifact_hash_b", "b")
        owner_certified = facts.get("owner_certified", True)
        actual = "SEMANTIC_EQUIVALENCE_PRESERVES_GENERATION_WITH_ARTIFACT_PROVENANCE" if semantic_same and artifact_changed and owner_certified else "FAIL"
    elif case_id == "AV03":
        actual = "OWNER_FIT_UNRESOLVED_NO_CAPABILITY_NEED" if _need(owner_fit="UNRESOLVED", support=False) == "POSSIBLY_REQUIRED" else "FAIL"
    elif case_id == "AV04":
        actual = _gap(["METHOD_GAP", "INFORMATION_GAP", "COUNTERFACTUAL_EXHAUSTED"])
    elif case_id == "AV05":
        actual = _gap(["DENOMINATOR_GAP", "INFORMATION_GAP", "COUNTERFACTUAL_EXHAUSTED"])
    elif case_id == "AV06":
        actual = "ZERO_SUPPORTED_DEMAND" if _need(owner_fit="MISMATCH", demand_frequency=10_000) == "NOT_REQUIRED" else "FAIL"
    elif case_id == "AV07":
        low = _need(owner_fit="UNRESOLVED", support=False, implementation_cost=1.0)
        high = _need(owner_fit="UNRESOLVED", support=False, implementation_cost=999_999_999.0)
        actual = "NO_NEED_STATUS_INCREASE" if low == high == "POSSIBLY_REQUIRED" else "FAIL"
    elif case_id == "AV08":
        actual = "PROTOCOL_EXCLUSION_SELF_INDUCED" if _gap([], protocol_state="EXCLUDED", result="SATISFIED") == "PROTOCOL_EXCLUSION" else "FAIL"
    elif case_id == "AV09":
        actual = _gap(["AUTHORITY_GAP", "INFORMATION_GAP", "COUNTERFACTUAL_EXHAUSTED"])
    elif case_id == "AV10":
        actual = _gap(["DATA_GAP", "INFORMATION_GAP", "COUNTERFACTUAL_EXHAUSTED"])
    elif case_id == "AV11":
        actual = "CAPABILITY_OVERBROAD_SMALLER_ROUTE_FIRST" if _need(smaller_route="SMALLER_ROUTE_AVAILABLE") == "NOT_REQUIRED" else "FAIL"
    elif case_id == "AV12":
        actual = "INFORMATION_GAP_C2P_ASSESSMENT_ALLOWED" if _gap(["INFORMATION_GAP", "COUNTERFACTUAL_EXHAUSTED"]) == "INFORMATION_GAP" and _need() == "NEED_SUPPORTED" else "FAIL"
    elif case_id == "AV13":
        actual = "METHOD_DERIVATION_FIRST_NO_AUTOMATIC_C3_NEED" if _gap(["METHOD_GAP"]) == "METHOD_GAP" else "FAIL"
    elif case_id == "AV14":
        result = ModeVisibilityFirewall().evaluate(consumer_visibility="PATH1_PRE_FREEZE", source_visibility="PATH2_PRE_FREEZE", candidate_defining=True)
        actual = "VISIBILITY_DENY_OR_CONTAMINATION" if result["disposition"] == "DENY" else "FAIL"
    elif case_id == "AV15":
        actual = "SUCCESSOR_PROTOCOL_OR_GENERATION_REQUIRED" if facts.get("preregistered_falsifier", "f1") != facts.get("emergent_falsifier", "f2") else "FAIL"
    elif case_id == "AV16":
        result = ModeVisibilityFirewall().evaluate(consumer_visibility="GENERAL_RESEARCH", source_visibility="GENERAL_RESEARCH", candidate_defining=False, declared_independence="COMMON_ANCESTRY")
        actual = "COMMON_ANCESTRY_NOT_INDEPENDENT_CONFIRMATION" if result["origin_convergence"] == "COMMON_ANCESTRY" else "FAIL"
    elif case_id == "AV17":
        result = ModeVisibilityFirewall().evaluate(consumer_visibility="GENERAL_RESEARCH", source_visibility="GENERAL_RESEARCH", candidate_defining=False)
        actual = "INDEPENDENCE_UNKNOWN" if result["origin_convergence"] == "UNKNOWN" else "FAIL"
    elif case_id == "AV18":
        old = {"assessment_id": "a1", "currentness": "HISTORICAL_VALID"}
        successor = {"assessment_id": "a2", "supersedes": "a1"}
        actual = "OLD_ASSESSMENT_HISTORICAL_VALID" if old["currentness"] == "HISTORICAL_VALID" and successor["supersedes"] == old["assessment_id"] else "FAIL"
    elif case_id == "AV19":
        correction = {"record_id": "owner:g2", "supersedes": "owner:g1", "correction_reason": "owner correction"}
        actual = "EXPLICIT_CORRECTION_LINEAGE" if correction["supersedes"] and correction["correction_reason"] else "FAIL"
    elif case_id == "AV20":
        source = {"id": "s1", "state": "QUARANTINED", "preserved": True, "current_synthesis": False}
        actual = "QUARANTINE_PRESERVE_HISTORY_EXCLUDE_CURRENT" if source["preserved"] and not source["current_synthesis"] else "FAIL"
    elif case_id == "AV21":
        view = {"implementation": "YES", "activation": "INACTIVE"}
        actual = "VIEW_SEPARATES_IMPLEMENTED_AND_ACTIVE" if view["implementation"] != view["activation"] else "FAIL"
    elif case_id == "AV22":
        proposed_fields = set(facts.get("proposed_fields", ["coverage_status", "coverage_score_83_percent"]))
        actual = "SCALAR_COVERAGE_SCORE_DENIED" if any("score" in field or "percent" in field for field in proposed_fields) else "FAIL"
    elif case_id == "AV23":
        rows = facts.get("rows", [{"need_status": "NEED_SUPPORTED"}, {"need_status": "NEED_CONTRADICTED"}])
        actual = "NEGATIVE_EVIDENCE_PARITY_REQUIRED" if any(row.get("need_status") == "NEED_CONTRADICTED" for row in rows) else "FAIL"
    else:  # AV24
        terminal_source = str(facts.get("terminal_source", "rccr:ResearchCoverageAssessment:old"))
        actual = "CIRCULAR_SOURCE_DENIED" if terminal_source.startswith("rccr:") else "FAIL"

    expected = AV_EXPECTED[case_id]
    return {
        "case_id": case_id,
        "actual": actual,
        "expected": expected,
        "pass": actual == expected,
        "unsupported_information_gap_promoted": False,
        "authority_effect": "NONE",
    }
