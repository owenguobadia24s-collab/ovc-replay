import hashlib
import json
from pathlib import Path

from ovc.development.identity import canonical_sha256
from ovc.system_atlas.visual import load_and_validate_workbench_projection


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/system_atlas/wp9/ATLAS_WORKBENCH_ACTUAL_REPOSITORY_PROJECTION_v0_1.json"
WP9 = ROOT / "docs/programmes/system-atlas-v0-1/wp9"
EXTERNAL_EVIDENCE = ROOT.parent.parent / "ovc-replay-external-artifacts/system_atlas/generations/wp9/ATLAS_WP9_WORKBENCH_EVIDENCE.json"


def test_wp9_projection_is_exact_current_tree_and_source_bound() -> None:
    projection = load_and_validate_workbench_projection(FIXTURE, ROOT)
    assert projection["source_commit"] == "513a95e518f75867dde3a920deb0a49c1dfca88d"
    assert projection["source_tree"] == "bad40e20d71cc5129cb942391fc2f1204f9ba239"
    assert projection["logical_hash"]


def test_wp9_surface_and_query_contract_is_complete() -> None:
    projection = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert [surface["id"] for surface in projection["surface_definitions"]] == [
        "architecture", "research", "execution", "authority", "repository", "history"
    ]
    assert {query["id"] for query in projection["query_definitions"]} == {
        "SEARCH", "TRACE", "DEPENDENCY", "IMPACT", "EXPLAIN", "AUTHORITY", "OWNERSHIP", "WHY_BLOCKED", "HISTORY", "DIFF"
    }
    assert all(query["representations"] == ["GRAPH", "TABLE"] for query in projection["query_definitions"])


def test_wp9_presentation_and_deep_link_state_have_no_authority_effect() -> None:
    projection = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert projection["presentation_state"] == {
        "features": ["SAVED_VIEW", "PIN", "LAYOUT_OVERRIDE", "BOOKMARK"],
        "storage": "BROWSER_LOCAL_ONLY",
        "authority_effect": "NONE",
    }
    assert projection["deep_link_contract"]["typed_context_only"] is True
    assert projection["deep_link_contract"]["source_mutation_effect"] == "NONE"
    assert projection["research_console_binding_created"] is False


def test_wp9_l4_and_accessibility_alternative_are_present() -> None:
    projection = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert any(node["depth"] == 4 for node in projection["nodes"])
    assert projection["accessibility"]["non_graph_alternative"] == "TABLE"
    assert projection["accessibility"]["keyboard_navigation"] is True


def test_wp9_gate_and_vit_bindings_are_auto_pass_and_content_addressed() -> None:
    gate = json.loads((WP9 / "ATLAS_G9_GATE_PACKET.json").read_text(encoding="utf-8"))
    implementation = json.loads((WP9 / "ATLAS_WP9_IMPLEMENTATION_PACKET.json").read_text(encoding="utf-8"))
    authority = json.loads((WP9 / "ATLAS_WP9_VIT_AUTHORITY_MANIFEST.json").read_text(encoding="utf-8"))
    dependency = json.loads((WP9 / "ATLAS_WP9_VIT_DEPENDENCY_FRONTIER.json").read_text(encoding="utf-8"))
    assert gate["gate_class"] == "AUTO_NON_RESERVED"
    assert gate["decision"] == "AUTO_PASS"
    assert authority["logical_id"] == canonical_sha256(authority["payload"])
    assert dependency["logical_id"] == canonical_sha256(dependency["payload"])
    assert implementation["write_routes"] == 0
    assert implementation["research_console_binding_created"] is False
    assert "ATLAS-G-OBSERVABILITY-ACTIVATE" in authority["payload"]["reserved_boundaries"]


def test_wp9_programme_state_advances_only_to_wp10() -> None:
    state = json.loads((ROOT / "registries/implementation/system_atlas_v0_1/ATLAS_PROGRAMME_STATE_v0_1.json").read_text(encoding="utf-8"))
    pointer = json.loads((ROOT / "registries/implementation/system_atlas_v0_1/CURRENT_STATE_POINTER.json").read_text(encoding="utf-8"))
    assert state["current_packet"] == pointer["current_packet"] == "ATLAS-WP9"
    assert state["current_gate"] == pointer["current_gate"] == "ATLAS-G9"
    assert state["next_packet"] == pointer["next_packet"] == "ATLAS-WP10"
    assert state["gate_status"] == "AUTO_PASS"


def test_wp9_external_evidence_matches_bound_hash_when_available() -> None:
    qa = json.loads((WP9 / "ATLAS_WP9_QA_PACKET.json").read_text(encoding="utf-8"))
    assert len(qa["external_workbench_evidence"]["sha256"]) == 64
    if EXTERNAL_EVIDENCE.is_file():
        assert hashlib.sha256(EXTERNAL_EVIDENCE.read_bytes()).hexdigest() == qa["external_workbench_evidence"]["sha256"]
