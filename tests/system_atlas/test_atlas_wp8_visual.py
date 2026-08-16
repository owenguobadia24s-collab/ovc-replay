import json
from pathlib import Path

from ovc.system_atlas.visual import canonical_projection_hash, load_and_validate_projection


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/system_atlas/wp8/ATLAS_VS0_ACTUAL_REPOSITORY_PROJECTION_v0_1.json"


def test_actual_projection_is_exact_tree_bound_and_read_only() -> None:
    projection = load_and_validate_projection(FIXTURE, ROOT)
    assert projection["source_tree"] == "fd19d3a062ff05b54f35da90a96841663f248c5a"
    assert len(projection["nodes"]) == 34
    assert projection["logical_hash"]


def test_required_whole_system_traces_are_exact() -> None:
    projection = json.loads(FIXTURE.read_text(encoding="utf-8"))
    traces = {trace["id"]: trace["node_ids"] for trace in projection["traces"]}
    assert traces["market-spine"] == ["opt-a", "c1", "c2", "c2e", "c2p", "esl", "c25", "c3"]
    assert traces["research-spine"] == ["question", "rccr", "protocol", "dmrp1", "dmrp2", "candidate", "opt-c", "opt-d"]
    assert traces["development-spine"] == ["continue", "packet", "qa-gate", "pip", "vit", "grt", "siq", "physical-main", "completion"]
    assert traces["c2e-deep-drill"] == ["c2e", "c2e-subsystem", "c2e-record", "c2e-contract", "c2e-module", "c2e-test"]


def test_projection_hash_is_canonical_and_stable() -> None:
    projection = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert canonical_projection_hash(projection) == canonical_projection_hash(json.loads(json.dumps(projection)))


def test_authority_and_prohibition_are_exposed() -> None:
    projection = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert any(node["family"] == "authority" for node in projection["nodes"])
    assert any(node["state"] == "forbidden" for node in projection["nodes"])
    assert any(edge["family"] == "prohibition" for edge in projection["edges"])
    assert projection["research_console_binding_created"] is False
