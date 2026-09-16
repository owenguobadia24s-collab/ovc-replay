from __future__ import annotations

from typing import Any, Mapping

COMPARABLE_GAMMA = {"AVAILABLE", "NONE", "SOURCE_BREAK"}
COMPARABLE_Z = {"AVAILABLE", "NOT_ESTABLISHED"}
COMPARABLE_S = {"AVAILABLE"}
COMPARABLE_PHI = {"AVAILABLE", "NOT_EVALUABLE"}


def _candidate_signature(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        candidate.get("side"),
        candidate.get("stage"),
        candidate.get("dominance_state"),
        bool(candidate.get("H4_overlap")),
        bool(candidate.get("H8_overlap")),
        candidate.get("support_depth"),
        bool(candidate.get("expiry_critical")),
    )


def task_organisational_signature(state: Mapping[str, Any]) -> tuple[str, Any]:
    components = state.get("components")
    if not isinstance(components, Mapping):
        return "NOT_EVALUABLE", "COMPONENTS_MISSING"
    e = components.get("E_t")
    if not isinstance(e, Mapping):
        return "NOT_EVALUABLE", "E_T_MISSING"
    if bool(e.get("source_break")):
        return "CENSORED", "SOURCE_BREAK"

    gamma = components.get("Gamma_t")
    z = components.get("Z_t")
    s = components.get("S_t")
    phi = components.get("Phi_t")
    if not all(isinstance(x, Mapping) for x in (gamma, z, s, phi)):
        return "NOT_EVALUABLE", "TASK_COMPONENT_MISSING"

    if gamma.get("status") not in COMPARABLE_GAMMA:
        return "NOT_EVALUABLE", "GAMMA_NOT_COMPARABLE"
    if z.get("status") not in COMPARABLE_Z:
        return "NOT_EVALUABLE", "Z_NOT_COMPARABLE"
    if s.get("status") not in COMPARABLE_S:
        return "NOT_EVALUABLE", "S_NOT_COMPARABLE"
    if phi.get("status") not in COMPARABLE_PHI:
        return "NOT_EVALUABLE", "PHI_NOT_COMPARABLE"

    relation = gamma.get("relation") if isinstance(gamma.get("relation"), Mapping) else {}
    current = relation.get("current") if isinstance(relation.get("current"), Mapping) else {}
    gamma_sig = (
        gamma.get("status"), gamma.get("current_family"), current.get("code"),
        current.get("layer"), current.get("polarity"),
    )
    z_sig = (
        z.get("status"),
        z.get("masking_regime") if z.get("status") == "AVAILABLE" else None,
        z.get("regime") if z.get("status") == "AVAILABLE" else None,
        z.get("current_masking_family") if z.get("status") == "AVAILABLE" else None,
        z.get("initial_concealer_family") if z.get("status") == "AVAILABLE" else None,
    )
    candidates = s.get("candidates")
    if not isinstance(candidates, list):
        return "NOT_EVALUABLE", "S_CANDIDATES_INVALID"
    s_sig = tuple(sorted(_candidate_signature(c) for c in candidates if isinstance(c, Mapping)))
    if len(s_sig) != len(candidates):
        return "NOT_EVALUABLE", "S_CANDIDATE_INVALID"
    coupling = phi.get("coupling") if isinstance(phi.get("coupling"), Mapping) else {}
    phi_sig = (
        phi.get("status"),
        phi.get("phase_t") if phi.get("status") == "AVAILABLE" else None,
        coupling.get("status"),
        bool(coupling.get("handover_ready")) if coupling else None,
    )
    return "EVALUABLE", (gamma_sig, z_sig, s_sig, phi_sig)


def task_invariant_preserved(anchor_state: Mapping[str, Any], horizon_state: Mapping[str, Any]) -> dict[str, Any]:
    anchor_status, anchor_sig = task_organisational_signature(anchor_state)
    horizon_status, horizon_sig = task_organisational_signature(horizon_state)
    if "CENSORED" in {anchor_status, horizon_status}:
        return {"state": "CENSORED", "reason": "SOURCE_BREAK"}
    if anchor_status != "EVALUABLE" or horizon_status != "EVALUABLE":
        return {
            "state": "NOT_EVALUABLE",
            "reason": "TASK_SIGNATURE_NOT_COMPARABLE",
            "anchor_status": anchor_status,
            "horizon_status": horizon_status,
        }
    preserved = anchor_sig == horizon_sig
    return {
        "state": "PRESERVED" if preserved else "RECONFIGURED",
        "reason": "EXACT_TASK_SIGNATURE_EQUALITY" if preserved else "EXACT_TASK_SIGNATURE_CHANGE",
    }
