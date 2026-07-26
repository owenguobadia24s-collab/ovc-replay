from __future__ import annotations

from copy import deepcopy
from typing import Any

from apps.research_console.navigation import ROUTES, get_route


FIXTURE_MODES: tuple[str, ...] = ("VALID", "EMPTY", "WARN", "BLOCK")

EMPTY_STATE_BY_FALLBACK: dict[str, dict[str, str]] = {
    "EXPECTED_EMPTY": {
        "status": "NOT_APPLICABLE",
        "reason": "No objects are currently expected for this surface.",
        "consequence": "NONE",
        "next_action": "Inspect source scope or return after lawful records exist.",
    },
    "NOT_MATERIALIZED": {
        "status": "NOT_EVALUATED",
        "reason": "The approved read model does not contain this source object family.",
        "consequence": "SURFACE_UNAVAILABLE",
        "next_action": "Materialize or register the lawful source through its own work packet.",
    },
    "NOT_EVALUATED": {
        "status": "NOT_EVALUATED",
        "reason": "Required checks or evidence have not been run.",
        "consequence": "NO_HEALTH_CLAIM",
        "next_action": "Run the approved bounded check or inspect the missing gate packet.",
    },
    "NOT_APPLICABLE": {
        "status": "NOT_APPLICABLE",
        "reason": "The surface is outside the selected object or route scope.",
        "consequence": "NONE",
        "next_action": "Select an applicable object or route.",
    },
}


def _base_route_fixture(route_id: str) -> dict[str, Any]:
    route = get_route(route_id)
    return {
        "route_id": route.route_id,
        "label": route.label,
        "group": route.group,
        "authority": route.authority,
        "status": "PASS",
        "summary": "Fixture-only RC-WP1 presentation. No live v0.2 projection authority is active.",
        "metrics": [
            {"label": "Represented objects", "value": "12", "note": "Fixture inventory"},
            {"label": "Health signals", "value": "6", "note": "Explicit fixture assertions"},
            {"label": "Blocking issues", "value": "0", "note": "Fixture state only"},
        ],
        "rows": [
            {"object": f"{route.route_id}-FIXTURE-001", "status": "PASS", "authority": route.authority, "source": "fixture://rc-wp1/valid"},
            {"object": f"{route.route_id}-FIXTURE-002", "status": "WARN", "authority": route.authority, "source": "fixture://rc-wp1/warn"},
        ],
        "source_refs": [
            "contracts/research_operations/console/OVC_RESEARCH_CONSOLE_UI_AUTHORITY_CONTRACT_v0_2.md",
            "registries/research_operations/RESEARCH_CONSOLE_ROUTE_REGISTRY_v0_2.yaml",
        ],
    }


def fixture_for_route(route_id: str, mode: str = "VALID") -> dict[str, Any]:
    if mode not in FIXTURE_MODES:
        raise ValueError(f"Unknown fixture mode: {mode}")
    route = get_route(route_id)
    fixture = deepcopy(_base_route_fixture(route_id))
    fixture["fixture_mode"] = mode

    if mode == "EMPTY":
        fixture["status"] = EMPTY_STATE_BY_FALLBACK[route.fallback]["status"]
        fixture["metrics"] = []
        fixture["rows"] = []
        fixture["empty_state"] = deepcopy(EMPTY_STATE_BY_FALLBACK[route.fallback])
    elif mode == "WARN":
        fixture["status"] = "WARN"
        fixture["summary"] = "Fixture limitation is named; the affected surface remains read-only and source-linked."
        fixture["metrics"][2] = {"label": "Warnings", "value": "1", "note": "Named fixture limitation"}
        fixture["rows"][0]["status"] = "WARN"
    elif mode == "BLOCK":
        fixture["status"] = "BLOCK"
        fixture["summary"] = "A named fixture integrity condition blocks the represented surface."
        fixture["metrics"] = [{"label": "Blocking issues", "value": "1", "note": "No progression"}]
        fixture["rows"] = []
        fixture["empty_state"] = {
            "status": "BLOCK",
            "reason": "A named QA, authority or integrity condition blocks this fixture surface.",
            "consequence": "NO_PROGRESSION",
            "next_action": "Open the blocking assertion and its issue or decision record.",
        }
    return fixture


def fixture_matrix() -> dict[str, dict[str, dict[str, Any]]]:
    return {
        route.route_id: {mode: fixture_for_route(route.route_id, mode) for mode in FIXTURE_MODES}
        for route in ROUTES
    }
