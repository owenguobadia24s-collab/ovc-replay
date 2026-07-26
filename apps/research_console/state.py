from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, MutableMapping

WORKSPACES = ("OVERVIEW", "RESEARCH", "SYSTEM")
SYSTEM_SECTIONS = ("HEALTH", "LINEAGE", "CATALOGUE", "RELEASES", "QA_GATES", "AUDIT", "CONFIGURATION", "ABOUT")
FIXTURE_MODES = ("VALID", "EMPTY", "WARN", "BLOCK")

GLOBAL_CONTEXT_DEFAULTS: dict[str, Any] = {
    "repository": "owenguobadia24s-collab/ovc-replay",
    "branch": "main",
    "source_commit": "NOT_EVALUATED",
    "read_model_sha256": "NOT_EVALUATED",
    "instrument": "GBPUSD",
    "release_role": "DEVELOPMENT",
    "release_id": "FIXTURE.RELEASE.DEVELOPMENT.v0.3",
    "clock": "15M / 2H_A_L",
    "price_side": "BID",
    "selected_time": "2025-07-18T14:00:00Z",
    "cutoff_mode": "PROSPECTIVE",
    "freshness": "FIXTURE_ONLY",
}

SESSION_DEFAULTS: dict[str, Any] = {
    "active_workspace": "OVERVIEW",
    "active_system_section": "HEALTH",
    "fixture_mode": "VALID",
    "selected_object_id": None,
    "drawer_open": False,
    "activity_open": False,
    "command_query": "",
}


def build_global_context(identity: Mapping[str, Any] | None = None) -> dict[str, Any]:
    context = deepcopy(GLOBAL_CONTEXT_DEFAULTS)
    if identity:
        for key in ("repository", "branch", "source_commit", "read_model_sha256", "freshness"):
            value = identity.get(key)
            if value not in (None, ""):
                context[key] = value
    return context


def initialise_mapping(state: MutableMapping[str, Any], identity: Mapping[str, Any] | None = None) -> None:
    for key, value in SESSION_DEFAULTS.items():
        state.setdefault(key, deepcopy(value))
    state.setdefault("global_context", build_global_context(identity))
    context = state["global_context"]
    for key, value in build_global_context(identity).items():
        context.setdefault(key, value)


def switch_workspace(state: MutableMapping[str, Any], workspace: str) -> None:
    if workspace not in WORKSPACES:
        raise ValueError(f"Unregistered workspace: {workspace}")
    context_before = deepcopy(state.get("global_context", {}))
    state["active_workspace"] = workspace
    state["global_context"] = context_before


def select_system_section(state: MutableMapping[str, Any], section: str) -> None:
    if section not in SYSTEM_SECTIONS:
        raise ValueError(f"Unregistered System section: {section}")
    state["active_system_section"] = section


def select_fixture_mode(state: MutableMapping[str, Any], mode: str) -> None:
    if mode not in FIXTURE_MODES:
        raise ValueError(f"Unregistered fixture mode: {mode}")
    state["fixture_mode"] = mode


def select_object(state: MutableMapping[str, Any], object_id: str | None) -> None:
    state["selected_object_id"] = object_id
    state["drawer_open"] = object_id is not None


def update_context(state: MutableMapping[str, Any], key: str, value: Any) -> None:
    if key not in GLOBAL_CONTEXT_DEFAULTS:
        raise ValueError(f"Unregistered global-context field: {key}")
    state.setdefault("global_context", build_global_context())
    state["global_context"][key] = value


def context_fingerprint(context: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(context.get(key) for key in GLOBAL_CONTEXT_DEFAULTS)
