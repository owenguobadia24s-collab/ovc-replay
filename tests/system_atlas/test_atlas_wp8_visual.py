import json
import hashlib
from pathlib import Path

from ovc.system_atlas.visual import canonical_projection_hash, load_and_validate_projection


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/system_atlas/wp8/ATLAS_VS0_ACTUAL_REPOSITORY_PROJECTION_v0_1.json"
WP8 = ROOT / "docs/programmes/system-atlas-v0-1/wp8"


def test_actual_projection_is_exact_tree_bound_and_read_only() -> None:
    projection = load_and_validate_projection(FIXTURE, ROOT)
    assert projection["source_tree"] == "1ba79ad839986b7294a00a82b348c210c9c107ce"
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


def test_wp8_gate_and_programme_state_are_bounded_and_eligible() -> None:
    gate = json.loads((WP8 / "ATLAS_G8_GATE_PACKET.json").read_text(encoding="utf-8"))
    state = json.loads((ROOT / "registries/implementation/system_atlas_v0_1/ATLAS_PROGRAMME_STATE_v0_1.json").read_text(encoding="utf-8"))
    pointer = json.loads((ROOT / "registries/implementation/system_atlas_v0_1/CURRENT_STATE_POINTER.json").read_text(encoding="utf-8"))
    assert gate["decision"] == "AUTO_PASS"
    assert gate["authority_effect"] == "NONE"
    assert state["current_packet"] == pointer["current_packet"] == "ATLAS-WP8"
    assert state["next_packet"] == pointer["next_packet"] == "ATLAS-WP9"


def test_wp8_vit_bindings_are_content_addressed() -> None:
    for name in ("ATLAS_WP8_VIT_AUTHORITY_MANIFEST.json", "ATLAS_WP8_VIT_DEPENDENCY_FRONTIER.json"):
        document = json.loads((WP8 / name).read_text(encoding="utf-8"))
        encoded = json.dumps(document["payload"], sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        assert document["logical_id"] == hashlib.sha256(encoded).hexdigest()


def test_workbench_does_not_bind_the_primary_console_source() -> None:
    source_root = ROOT / "apps/research_console_vnext/src"
    references = []
    for path in source_root.rglob("*"):
        if not path.is_file() or "systemAtlasWorkbench" in path.parts:
            continue
        if path.suffix in {".ts", ".tsx", ".js", ".jsx"} and "systemAtlasWorkbench" in path.read_text(encoding="utf-8"):
            references.append(path.relative_to(ROOT).as_posix())
    assert references == []
