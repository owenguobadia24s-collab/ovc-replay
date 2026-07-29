from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from apps.research_console.system_workspace import build_system_projection

FIXTURE_MODES = ("VALID", "EMPTY", "WARN", "BLOCK")

HEALTH_DOMAINS = (
    {"object_id": "HEALTH.DATA", "label": "Data", "status": "PASS", "progress": 0.92, "detail": "Fixture coverage and chronology checks passed.", "consequence": "Fixture surfaces available."},
    {"object_id": "HEALTH.READ_MODEL", "label": "Read model", "status": "PASS", "progress": 1.0, "detail": "Represented identity is available; live projections remain denied.", "consequence": "Identity may be displayed."},
    {"object_id": "HEALTH.ARTIFACTS", "label": "Artifacts", "status": "WARN", "progress": 0.52, "detail": "One fixture artifact reference is intentionally unresolved.", "consequence": "Affected fixture card is marked non-reproducible."},
    {"object_id": "HEALTH.QA", "label": "QA", "status": "PASS", "progress": 0.88, "detail": "Fixture shell assertions are represented.", "consequence": "RC-G1 review may inspect the presentation."},
    {"object_id": "HEALTH.RESEARCH_RECORDS", "label": "Research records", "status": "NOT_EVALUATED", "progress": 0.0, "detail": "Research-record health is not evaluated in fixture-only RC-WP1.", "consequence": "No research-record health claim is made."},
    {"object_id": "HEALTH.REPOSITORY", "label": "Repository", "status": "PASS", "progress": 0.94, "detail": "Fixture registry and source references resolve.", "consequence": "Fixture shell can be reviewed."},
)

OBJECTS: tuple[dict[str, Any], ...] = (
    {"object_id": "RELEASE.DEV.2025", "object_type": "RELEASE", "label": "Development release", "status": "PASS", "authority": "FIXTURE_ONLY", "summary": "Development role fixture for shell rendering.", "source_refs": ["fixtures/research_operations/research_console_v0_3/RC_WP1_SHELL_FIXTURES.json", "RC-A1_GATE_PACKET.json"], "lineage": ["RC-A1", "WORKSPACE.RESEARCH"], "consequence": "May populate fixture-only context controls.", "next_action": "Review layout and source visibility."},
    {"object_id": "GATE.RC_A1", "object_type": "GATE", "label": "RC-A1 acceptance", "status": "PASS", "authority": "GOVERNANCE_SOURCE", "summary": "v0.3 information architecture accepted.", "source_refs": ["docs/releases/research-console-v0-3/rc-a1/RC_A1_GATE_PACKET.json"], "lineage": ["RC-A0", "RC-A1"], "consequence": "RC-WP1 fixture-only shell implementation is authorised.", "next_action": "Complete RC-WP1 and submit RC-G1 review."},
    {"object_id": "EVIDENCE.SUPPORT.001", "object_type": "EVIDENCE", "label": "Support evidence", "status": "PASS", "authority": "FIXTURE_ONLY", "summary": "Observed structure remains consistent with the fixture developmental reading.", "source_refs": ["FIXTURE.CASE.001", "FIXTURE.OBSERVATION.001"], "lineage": ["FIXTURE.CLAIM.001"], "consequence": "Supports presentation demonstration only.", "next_action": "Inspect contrasting fixture evidence."},
    {"object_id": "EVIDENCE.CONTRADICTION.001", "object_type": "EVIDENCE", "label": "Contradiction evidence", "status": "WARN", "authority": "FIXTURE_ONLY", "summary": "A competing rotational interpretation remains eligible.", "source_refs": ["FIXTURE.CASE.002", "FIXTURE.OBSERVATION.002"], "lineage": ["FIXTURE.CLAIM.001"], "consequence": "Prevents false certainty in the demonstration.", "next_action": "Compare against support and boundary cases."},
    {"object_id": "EVIDENCE.BOUNDARY.001", "object_type": "EVIDENCE", "label": "Boundary evidence", "status": "WARN", "authority": "FIXTURE_ONLY", "summary": "The fixture is near a declared structural boundary.", "source_refs": ["FIXTURE.CASE.003"], "lineage": ["FIXTURE.CLAIM.001"], "consequence": "Interpretation remains conditional.", "next_action": "Inspect boundary construction in the drawer."},
    {"object_id": "EVIDENCE.NULL.001", "object_type": "EVIDENCE", "label": "Null evidence", "status": "NOT_EVALUATED", "authority": "FIXTURE_ONLY", "summary": "An auxiliary measure is intentionally non-discriminating.", "source_refs": ["FIXTURE.CASE.004"], "lineage": ["FIXTURE.CLAIM.001"], "consequence": "No directional conclusion may be drawn.", "next_action": "Retain as a visible null result."},
    {"object_id": "QUEUE.REALIZATION.001", "object_type": "QUEUE_ITEM", "label": "Realization due", "status": "WARN", "authority": "DERIVED_FIXTURE_ONLY", "summary": "Two fixture realizations are due.", "source_refs": ["FIXTURE.SESSION.001"], "lineage": ["FIXTURE.OBSERVATION.001"], "consequence": "Research completion would be at risk in a live programme.", "next_action": "Inspect the linked fixture session."},
    {"object_id": "QUEUE.CENSORED.001", "object_type": "QUEUE_ITEM", "label": "Censored path", "status": "CENSORED", "authority": "DERIVED_FIXTURE_ONLY", "summary": "A required fixture path is unavailable.", "source_refs": ["FIXTURE.INCIDENT.001"], "lineage": ["FIXTURE.SESSION.002"], "consequence": "No silent exclusion is permitted.", "next_action": "Inspect the censoring reason."},
    {"object_id": "SYSTEM.CONFIG.001", "object_type": "CONFIGURATION", "label": "Local presentation authority", "status": "PASS", "authority": "CONTRACT_DERIVED_READ_ONLY", "summary": "Local fixture-only shell; no remote deploy or mutation authority.", "source_refs": ["contracts/research_operations/console/OVC_RESEARCH_CONSOLE_INFORMATION_ARCHITECTURE_CONTRACT_v0_3.md"], "lineage": ["RC-A1"], "consequence": "Only local presentation actions are available.", "next_action": "Proceed to RC-G1 review after verification."},
)

ACTIVITY = (
    {"time": "12:05", "type": "GATE", "status": "PASS", "object_id": "GATE.RC_A1", "description": "v0.3 information architecture accepted.", "source_refs": ["docs/releases/research-console-v0-3/rc-a1/RC_A1_GATE_PACKET.json"]},
    {"time": "12:12", "type": "SHELL", "status": "PASS", "object_id": "SYSTEM.CONFIG.001", "description": "Fixture-only unified shell loaded.", "source_refs": ["contracts/research_operations/console/OVC_RESEARCH_CONSOLE_INFORMATION_ARCHITECTURE_CONTRACT_v0_3.md"]},
    {"time": "12:18", "type": "ARTIFACT", "status": "WARN", "object_id": "HEALTH.ARTIFACTS", "description": "Fixture artifact warning remains visible.", "source_refs": ["fixtures/research_operations/research_console_v0_3/RC_WP1_SHELL_FIXTURES.json"]},
    {"time": "12:24", "type": "RESEARCH", "status": "CENSORED", "object_id": "QUEUE.CENSORED.001", "description": "Fixture realization path unavailable.", "source_refs": ["FIXTURE.INCIDENT.001"]},
)

RELEASES = (
    {"release_id": "FIXTURE.DISCOVERY.2021_2023", "role": "DISCOVERY", "lifecycle": "FROZEN", "authority": "FIXTURE_ONLY", "qa": "PASS", "availability": "LOCAL_FIXTURE"},
    {"release_id": "FIXTURE.DEVELOPMENT.2024", "role": "DEVELOPMENT", "lifecycle": "FROZEN", "authority": "FIXTURE_ONLY", "qa": "WARN", "availability": "LOCAL_FIXTURE"},
    {"release_id": "FIXTURE.VALIDATION.2025", "role": "VALIDATION", "lifecycle": "LOCKED_UNCONSUMED", "authority": "NONE", "qa": "NOT_EVALUATED", "availability": "LOCAL_FIXTURE"},
)

GATES = (
    {"gate": "RC-A0", "status": "PASS", "effect": "v0.3 architecture frozen"},
    {"gate": "RC-A1", "status": "PASS", "effect": "fixture-only shell authorised"},
    {"gate": "RC-G1", "status": "NOT_EVALUATED", "effect": "shell acceptance pending"},
)

CATALOGUE = (
    {"artifact_id": "FIXTURE.CONSOLE.CSS", "availability": "LOCAL_FIXTURE", "authority": "PRESENTATION_ONLY"},
    {"artifact_id": "FIXTURE.RC_WP1.PACK", "availability": "LOCAL_FIXTURE", "authority": "GOVERNANCE_SOURCE"},
)

REPLAY_VALUES = (1.2712, 1.2718, 1.2709, 1.2724, 1.2731, 1.2727, 1.2740, 1.2735, 1.2746, 1.2751)


def _mode_health(mode: str) -> list[dict[str, Any]]:
    rows = deepcopy(list(HEALTH_DOMAINS))
    if mode == "EMPTY":
        return [{**item, "status": "NOT_EVALUATED", "progress": 0.0, "detail": "No fixture signal is present.", "consequence": "No health claim is made."} for item in rows]
    if mode == "WARN":
        rows[0].update(status="WARN", progress=0.45, detail="Fixture coverage is partial.", consequence="Affected fixture panels remain conditional.")
    if mode == "BLOCK":
        rows[1].update(status="BLOCK", progress=0.0, detail="Fixture read-model identity is invalid.", consequence="Main fixture panels must fail closed.")
    return rows


def fixture_bundle(mode: str = "VALID") -> dict[str, Any]:
    normalized = str(mode).upper()
    if normalized not in FIXTURE_MODES:
        raise ValueError(f"Unknown fixture mode: {mode}")
    empty = normalized == "EMPTY"
    blocked = normalized == "BLOCK"
    if empty:
        objects, activity, releases, gates, system_projection = [], [], [], [], None
    else:
        system_projection = build_system_projection(
            source_commit="RC_WP4_FIXTURE_SOURCE",
            read_model_sha256="RC_WP4_FIXTURE_READ_MODEL",
            objects=OBJECTS,
            releases=RELEASES,
            gates=GATES,
            activity=ACTIVITY,
            catalogue=CATALOGUE,
            configuration={"local_only": True, "writes": "NONE"},
        )
        objects = deepcopy(system_projection["panels"]["OBJECTS_LINEAGE"])
        activity = deepcopy(system_projection["activity"])
        releases = deepcopy(system_projection["panels"]["RELEASES"])
        gates = deepcopy(system_projection["panels"]["QA_GATES"])
    return {
        "fixture_mode": normalized,
        "health": _mode_health(normalized),
        "objects": objects,
        "activity": activity,
        "releases": releases,
        "gates": gates,
        "system_projection": system_projection,
        "replay": [] if empty or blocked else list(REPLAY_VALUES),
        "summary_status": "BLOCK" if blocked else ("NOT_EVALUATED" if empty else ("WARN" if normalized == "WARN" else "PASS")),
    }


def object_index(bundle: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    index = {str(item["object_id"]): item for item in bundle.get("objects", [])}
    for item in bundle.get("health", []):
        index[str(item["object_id"])] = {
            **item,
            "object_type": "HEALTH_DOMAIN",
            "authority": "DERIVED_ASSURANCE_ONLY",
            "summary": item.get("detail"),
            "source_refs": ["RESEARCH_CONSOLE_STATUS_REGISTRY_v0_2.yaml", "RC_WP1_SHELL_FIXTURES.json"],
            "lineage": ["AMBIENT_HEALTH"],
            "next_action": "Open the affected fixture source or wait for a later live-projection gate.",
        }
    return index


def search_objects(bundle: Mapping[str, Any], query: str) -> list[dict[str, Any]]:
    needle = str(query).strip().lower()
    if not needle:
        return []
    matches = []
    for item in object_index(bundle).values():
        haystack = " ".join(str(item.get(key, "")) for key in ("object_id", "object_type", "label", "status", "summary")).lower()
        if needle in haystack:
            matches.append(item)
    return sorted(matches, key=lambda item: str(item.get("object_id")))
