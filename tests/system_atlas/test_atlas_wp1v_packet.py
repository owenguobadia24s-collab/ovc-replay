from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ovc.development.identity import canonical_sha256


ROOT = Path(__file__).resolve().parents[2]
WP1V = ROOT / "docs/programmes/system-atlas-v0-1/wp1v"
APP = ROOT / "apps/research_console_vnext"
STATE = ROOT / "registries/implementation/system_atlas_v0_1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_exact_graph_dependencies_are_locked_with_no_transitive_runtime_dependencies() -> None:
    admission = load(WP1V / "ATLAS_WP1V_DEPENDENCY_ADMISSION.json")
    lock = load(APP / "package-lock.json")
    assert hashlib.sha256((APP / "package-lock.json").read_bytes()).hexdigest() == admission["lockfile"]["sha256"]
    assert lock["lockfileVersion"] == 3
    expected = {"cytoscape": "3.31.2", "elkjs": "0.12.0"}
    assert {item["name"]: item["version"] for item in admission["admitted_runtime_dependencies"]} == expected
    for name, version in expected.items():
        package = lock["packages"][f"node_modules/{name}"]
        assert package["version"] == version
        assert package.get("dependencies", {}) == {}
    assert admission["undeclared_transitive_runtime_requirement"] is False


def test_feasibility_host_is_unlinked_synthetic_and_authority_neutral() -> None:
    html = (APP / "atlas-feasibility.html").read_text(encoding="utf-8")
    main = (APP / "src/systemAtlasFeasibility/main.tsx").read_text(encoding="utf-8")
    production_main = (APP / "src/main.tsx").read_text(encoding="utf-8")
    assert "systemAtlasFeasibility/main.tsx" in html
    assert "SYNTHETIC_NOT_COURT_RECORD" in main
    assert "Authority</dt><dd>None" in main
    assert "systemAtlasFeasibility" not in production_main


def test_g1v_is_auto_pass_without_source_or_authority_delta() -> None:
    gate = load(WP1V / "ATLAS_G1V_GATE_PACKET.json")
    implementation = load(WP1V / "ATLAS_WP1V_IMPLEMENTATION_PACKET.json")
    assert gate["gate_class"] == "AUTO"
    assert gate["proposed_delta"] == "NONE"
    assert gate["recommended_decision"] == "AUTO_PASS"
    assert gate["blockers"] == []
    assert implementation["research_console_source_admitted"] is False
    assert implementation["authority_effect"] == "NONE_PRESENTATION_ONLY"


def test_wp1v_vit_bindings_are_canonical() -> None:
    authority = load(WP1V / "ATLAS_WP1V_VIT_AUTHORITY_MANIFEST.json")
    frontier = load(WP1V / "ATLAS_WP1V_VIT_DEPENDENCY_FRONTIER.json")
    assert canonical_sha256(authority["payload"]) == authority["logical_id"]
    assert canonical_sha256(frontier["payload"]) == frontier["logical_id"]
    assert authority["payload"]["authority_delta"].startswith("NONE_")
    assert frontier["payload"]["predecessor_requirement"] == "QUALIFIED_VIT_GENERATION_REQUIRED"


def test_programme_state_advances_to_wp2_without_activation() -> None:
    pointer = load(STATE / "CURRENT_STATE_POINTER.json")
    state = load(STATE / pointer["current_state"])
    assert state["current_packet"] == "ATLAS-WP1V"
    assert state["current_gate"] == "ATLAS-G1V"
    assert state["next_packet"] == "ATLAS-WP2"
    assert state["blockers"] == []
    assert state["stop_boundary"] == "ATLAS-G-OBSERVABILITY-ACTIVATE"
    assert pointer["next_operator_gate"] == "ATLAS-G-OBSERVABILITY-ACTIVATE"
