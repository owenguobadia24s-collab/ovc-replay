from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .errors import ContractError

_FORBIDDEN_C2_COMPOSITES = {"confidence_score", "overall_state", "winner_axis"}
_REQUIRED_CANDIDATE_KEYS = {
    "capability_id", "owner", "namespace", "activation_state",
    "real_source_presented", "authority_effect", "gate_required",
}


def _mapping(value: Any, reason: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(reason)
    return value


def build_fixture_investigate_snapshot(
    *,
    market: Mapping[str, Any],
    structure: Mapping[str, Any],
    preparation: Mapping[str, Any],
) -> dict[str, Any]:
    """Compose the WP4A Investigate contract from fixture-owned inputs only.

    This function intentionally does not discover repository sources, open provider
    locators, infer transitions, or reconstruct C2E. It is the preparation seam
    that a separately-authorised G4 binding may later feed.
    """
    market = _mapping(market, "WP4A_MARKET_MAPPING_REQUIRED")
    structure = _mapping(structure, "WP4A_STRUCTURE_MAPPING_REQUIRED")
    preparation = _mapping(preparation, "WP4A_PREPARATION_MAPPING_REQUIRED")

    if preparation.get("mode") != "FIXTURE_ONLY_G4_PREPARATION":
        raise ContractError("WP4A_FIXTURE_ONLY_MODE_REQUIRED")

    c1 = deepcopy(dict(_mapping(structure.get("c1"), "WP4A_C1_MAPPING_REQUIRED")))
    c2 = deepcopy(dict(_mapping(structure.get("c2"), "WP4A_C2_MAPPING_REQUIRED")))
    collisions = sorted(_FORBIDDEN_C2_COMPOSITES.intersection(c2))
    if collisions:
        raise ContractError(f"WP4A_C2_COMPOSITE_FORBIDDEN:{collisions}")

    raw_c2e = deepcopy(dict(_mapping(structure.get("c2e"), "WP4A_C2E_MAPPING_REQUIRED")))
    if raw_c2e.get("availability") == "AVAILABLE":
        c2e = raw_c2e
    else:
        c2e = {
            "availability": str(raw_c2e.get("availability", "NOT_MATERIALIZED")),
            "reason_code": str(raw_c2e.get("reason_code", "C2E_CURRENT_GENERATION_NOT_MATERIALIZED")),
            "episodes": [],
            "events": [],
            "reconstruction": "PROHIBITED",
        }

    transitions = deepcopy(dict(_mapping(preparation.get("transitions"), "WP4A_TRANSITIONS_MAPPING_REQUIRED")))
    if transitions.get("availability") != "AVAILABLE":
        transitions["items"] = []
        transitions["synthesis"] = "PROHIBITED"

    candidates_raw = preparation.get("binding_candidates")
    if not isinstance(candidates_raw, list) or not candidates_raw:
        raise ContractError("WP4A_BINDING_CANDIDATES_REQUIRED")
    candidates: list[dict[str, Any]] = []
    for row in candidates_raw:
        candidate = dict(_mapping(row, "WP4A_BINDING_CANDIDATE_MAPPING_REQUIRED"))
        if set(candidate) != _REQUIRED_CANDIDATE_KEYS:
            raise ContractError("WP4A_BINDING_CANDIDATE_CONTRACT_MISMATCH")
        if candidate["activation_state"] != "PREPARED_NOT_BOUND":
            raise ContractError("WP4A_BINDING_ACTIVATION_FORBIDDEN")
        if candidate["real_source_presented"] is not False:
            raise ContractError("WP4A_REAL_SOURCE_PRESENTATION_FORBIDDEN")
        if candidate["authority_effect"] != "NONE" or candidate["gate_required"] != "RCN-RN-G4":
            raise ContractError("WP4A_BINDING_AUTHORITY_BOUNDARY_MISMATCH")
        candidates.append(candidate)

    bars = market.get("bars", [])
    if not isinstance(bars, list):
        raise ContractError("WP4A_MARKET_BARS_LIST_REQUIRED")

    population = deepcopy(dict(_mapping(preparation.get("population"), "WP4A_POPULATION_MAPPING_REQUIRED")))
    return {
        "packet_id": "RCN-RN-WP4A",
        "mode": "FIXTURE_ONLY_G4_PREPARATION",
        "authority_effect": "NONE",
        "real_source_presentation": "DENIED_PENDING_RCN_RN_G4",
        "population": population,
        "market_context": {
            "availability": "AVAILABLE",
            "bar_count": len(bars),
            "scientific_role": "OPTIONAL_CONTEXT_ONLY",
        },
        "translation": {"c1": c1},
        "structure": {"c2": c2, "c2e": c2e, "transitions": transitions},
        "binding_candidates": candidates,
        "invariants": [
            "C2_USABLE_WHEN_C2E_NOT_MATERIALIZED",
            "NO_HISTORICAL_C2E_FALLBACK",
            "NO_TRANSITION_SYNTHESIS_FROM_C2_DELTAS",
            "NO_FRONTEND_SCIENTIFIC_DERIVATION",
            "REAL_SOURCE_PRESENTATION_REQUIRES_RCN_RN_G4",
        ],
    }
