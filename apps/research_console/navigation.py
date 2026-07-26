from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class RouteSpec:
    route_id: str
    label: str
    group: str
    authority: str
    fallback: str
    icon: str


GROUP_ORDER: tuple[str, ...] = ("HOME", "RESEARCH", "SYSTEM", "SETTINGS")
DEFAULT_ROUTE_ID = "OVERVIEW"

ROUTES: tuple[RouteSpec, ...] = (
    RouteSpec("OVERVIEW", "Overview", "HOME", "READ_ONLY", "NOT_EVALUATED", "⌂"),
    RouteSpec("RESEARCH_DESK", "Research Desk", "RESEARCH", "READ_ONLY_WHEN_MATERIALIZED", "NOT_MATERIALIZED", "◫"),
    RouteSpec("REPLAY", "Replay", "RESEARCH", "READ_ONLY_CUTOFF_SAFE", "NOT_MATERIALIZED", "▶"),
    RouteSpec("EVIDENCE", "Evidence Library", "RESEARCH", "READ_ONLY", "NOT_MATERIALIZED", "◇"),
    RouteSpec("SESSIONS", "Research Sessions", "RESEARCH", "READ_ONLY", "EXPECTED_EMPTY", "◷"),
    RouteSpec("QUEUE", "Research Queue", "RESEARCH", "READ_ONLY_DERIVED", "EXPECTED_EMPTY", "≡"),
    RouteSpec("HEALTH", "Health", "SYSTEM", "READ_ONLY", "NOT_EVALUATED", "✚"),
    RouteSpec("LINEAGE", "Lineage & Objects", "SYSTEM", "READ_ONLY", "EXPECTED_EMPTY", "⌘"),
    RouteSpec("CATALOGUE", "Data Catalogue", "SYSTEM", "READ_ONLY", "NOT_MATERIALIZED", "▤"),
    RouteSpec("RELEASES", "Releases", "SYSTEM", "READ_ONLY", "NOT_MATERIALIZED", "▣"),
    RouteSpec("QA_GATES", "QA & Gates", "SYSTEM", "READ_ONLY", "NOT_EVALUATED", "✓"),
    RouteSpec("AUDIT", "Audit Log", "SYSTEM", "READ_ONLY", "EXPECTED_EMPTY", "≋"),
    RouteSpec("CONFIG", "Configuration", "SETTINGS", "READ_ONLY_LOCAL", "NOT_EVALUATED", "⚙"),
    RouteSpec("ABOUT", "About", "SETTINGS", "READ_ONLY_STATIC", "NOT_APPLICABLE", "?"),
)

ROUTE_BY_ID = {route.route_id: route for route in ROUTES}


def get_route(route_id: str) -> RouteSpec:
    try:
        return ROUTE_BY_ID[route_id]
    except KeyError as exc:
        raise ValueError(f"Unknown console route: {route_id}") from exc


def routes_for_group(group: str) -> tuple[RouteSpec, ...]:
    if group not in GROUP_ORDER:
        raise ValueError(f"Unknown console route group: {group}")
    return tuple(route for route in ROUTES if route.group == group)


def grouped_routes() -> tuple[tuple[str, tuple[RouteSpec, ...]], ...]:
    return tuple((group, routes_for_group(group)) for group in GROUP_ORDER)


def route_ids(routes: Iterable[RouteSpec] = ROUTES) -> tuple[str, ...]:
    return tuple(route.route_id for route in routes)
