from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SECTION_ORDER = ("system", "capabilities", "skills", "qualifications", "executions", "incidents", "dependencies", "health", "orchestration", "agents")
FORBIDDEN_CONTROL_TOKENS = {"TRUST", "REVOKE", "ENABLE", "RUN", "MERGE", "APPROVE"}


def _project_value(value: Any, source_identity: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "value": deepcopy(value),
        "source_identity": deepcopy(dict(source_identity)),
        "missing": value is None,
        "authority_effect": "NONE",
    }


def build_skill_control_read_model(source: Mapping[str, Any]) -> dict[str, Any]:
    """Build the Research Console DSAI Control projection deterministically.

    Inputs are already-authorised read-only source snapshots. The builder never resolves
    authority, executes Skills or converts inferred graph edges into prerequisites.
    Every projected top-level value carries source identity and explicit missingness.
    """
    source_identity = source.get("source_identity")
    if not isinstance(source_identity, Mapping):
        raise ValueError("DSAI_CONTROL_SOURCE_IDENTITY_REQUIRED")
    sections = source.get("sections")
    if not isinstance(sections, Mapping):
        raise ValueError("DSAI_CONTROL_SECTIONS_REQUIRED")

    projected: dict[str, Any] = {}
    for name in SECTION_ORDER:
        projected[name] = _project_value(sections.get(name), source_identity)

    dependencies_value = projected["dependencies"]["value"]
    if isinstance(dependencies_value, list):
        safe_edges = []
        for edge in dependencies_value:
            row = deepcopy(dict(edge)) if isinstance(edge, Mapping) else {"value": deepcopy(edge)}
            if row.get("inferred") is True:
                row["hard_prerequisite"] = False
                row["authority_effect"] = "NONE"
            safe_edges.append(row)
        projected["dependencies"]["value"] = safe_edges

    return {
        "schema_id": "ovc-dsai-skill-control-read-model/v1",
        "mode": "READ_ONLY_PROJECTION",
        "authority_effect": "NONE",
        "source_identity": deepcopy(dict(source_identity)),
        "missing_sections": [name for name in SECTION_ORDER if sections.get(name) is None],
        "sections": projected,
        "forbidden_controls": sorted(FORBIDDEN_CONTROL_TOKENS),
    }
