import json
from pathlib import Path

from ovc.system_atlas.visual import load_and_validate_workbench_projection


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/system_atlas/wp9/ATLAS_WORKBENCH_ACTUAL_REPOSITORY_PROJECTION_v0_1.json"


def test_wp9_projection_is_exact_current_tree_and_source_bound() -> None:
    projection = load_and_validate_workbench_projection(FIXTURE, ROOT)
    assert projection["source_commit"] == "9bd1da036eee96e2e66c6acdb7a4ddfef44f7c7a"
    assert projection["source_tree"] == "a06565acaf031616cf592ff1818313cfd34f7395"
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
