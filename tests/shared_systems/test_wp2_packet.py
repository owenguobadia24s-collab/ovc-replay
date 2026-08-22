from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROGRAMME = ROOT / "docs/programmes/shared-systems-v0-1"
IMPLEMENTATION = ROOT / "registries/implementation/shared_systems_v0_1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g1_completion_exactly_unlocks_wp2() -> None:
    binding = load(PROGRAMME / "wp2/SHSI_G1_COMPLETION_BINDING_v0_1.json")
    assert binding["status"] == "COMPLETED"
    assert binding["main_tree"] == binding["qualified_candidate_tree"] == "6a16c6dfe9e061289933f086afa43446b4cb624f"
    assert binding["physical_completion"]["exact_tree_equal"] is True
    assert binding["physical_completion"]["four_content_addressed_receipts_present"] is True
    assert binding["authority_effect"] == "NONE"


def test_exact_owner_source_census_is_immutable_and_non_mutating() -> None:
    census = load(PROGRAMME / "wp2/SHSI_WP2_SOURCE_CONTRACT_CENSUS_v0_1.json")
    assert {s["owner"] for s in census["sources"]} == {"ESL", "RESEARCH_OPERATIONS", "GRT", "DSAI"}
    assert census["mutated_source_contracts"] == []
    assert census["current_consumer_paths_changed"] is False
    for source in census["sources"]:
        observed = subprocess.run(["git", "hash-object", "--", source["path"]], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
        assert observed == source["git_blob_sha"], source["path"]


def test_wp2_state_and_gate_remain_non_authorising() -> None:
    pointer = load(IMPLEMENTATION / "CURRENT_STATE_POINTER.json")
    assert pointer["current_packet"] == "SHSI-WP2"
    assert pointer["current_gate"] == "SHSI-G2"
    assert pointer["next_packet"] == "SHSI-WP3"
    gate = load(PROGRAMME / "gates/SHSI_G2_ENVELOPE_CLOSEOUT_v0_1.json")
    assert gate["execution_class"] == "AUTO_RATIFIABLE"
    assert gate["proposed_delta"] == gate["authority_effect"] == "NONE"


def test_combined_schema_is_closed_and_covers_all_required_artifacts() -> None:
    schema = load(ROOT / "schemas/shared_systems/evidence_state_interface_v0_1.schema.json")
    required = {"EvidenceFrontier","DependencyDescriptor","StatePlaneValue","LineageEdgeEnvelope","CompatibilityContract","AdapterDescriptor","InterfaceBinding"}
    assert required <= set(schema["$defs"])
    for name in required:
        assert schema["$defs"][name]["additionalProperties"] is False


def test_wp2_vit_payload_and_frontiers_are_content_addressed() -> None:
    from ovc.development.identity import canonical_sha256

    vit = PROGRAMME / "vit"
    authority = load(vit / "SHSI_WP2_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load(vit / "SHSI_WP2_DEPENDENCY_FRONTIER_v0_1.json")
    pip = load(vit / "SHSI_WP2_PIP_v0_1.json")
    assert authority["logical_id"] == canonical_sha256(authority["payload"])
    assert frontier["logical_id"] == canonical_sha256(frontier["payload"])
    assert pip["logical_id"] == canonical_sha256(pip["payload"])
    assert pip["payload"]["authority_manifest_id"] == authority["logical_id"]
    assert pip["payload"]["dependency_frontier_id"] == frontier["logical_id"]
    assert pip["payload"]["completion_transition"] == {"status":"COMPLETED", "next_packet":"SHSI-WP3"}
    for change in pip["payload"]["logical_changes"]:
        observed = subprocess.run(["git", "hash-object", "--", change["path"]], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
        assert observed == change["blob_sha"], change["path"]
