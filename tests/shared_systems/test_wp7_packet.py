from __future__ import annotations

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
PROGRAMME = ROOT / "docs/programmes/shared-systems-v0-1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g6_exact_completion_unlocks_wp7() -> None:
    binding = load(PROGRAMME / "wp7/SHSI_G6_COMPLETION_BINDING_v0_1.json")
    assert binding["status"] == "COMPLETED"
    assert binding["main_merge_commit"] == "76af1614e5681e73030f47980d41f5d3e7594d1b"
    assert binding["main_tree"] == binding["qualified_candidate_tree"]
    assert binding["physical_completion"]["exact_tree_equal"]
    assert binding["physical_completion"]["four_content_addressed_receipts_present"]


def test_wp7_census_pins_exact_dsai_sources_and_keeps_authority() -> None:
    census = load(PROGRAMME / "wp7/SHSI_WP7_DSAI_CONSUMPTION_CENSUS_v0_1.json")
    assert census["consumer_programme_id"] == "OVC-DSAI-v0.1"
    assert census["consumer_generation"] == "OVC_DSAI_STATE_v0_31"
    assert census["mode"] == "SHADOW_ONLY"
    assert census["surfaces"] == ["ENVIRONMENT", "RUN", "ASSURANCE", "RECEIPT", "CURRENTNESS"]
    assert census["active_adapter_count"] == 0
    assert census["mandatory_divergence_count"] == census["security_false_allow_count"] == 0
    assert not census["current_binding_changed"] and census["writes_performed"] == []
    for item in census["sources"]:
        blob = subprocess.run(
            ["git", "hash-object", "--", item["path"]],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert blob == item["git_blob_sha"], item["path"]


def test_wp7_current_state_and_gate_are_shadow_only_non_authorising() -> None:
    pointer = load(ROOT / "registries/implementation/shared_systems_v0_1/CURRENT_STATE_POINTER.json")
    assert (pointer["current_packet"], pointer["current_gate"], pointer["next_packet"]) == (
        "SHSI-WP7", "SHSI-G7", "SHSI-WP8"
    )
    state = load(ROOT / pointer["state_record"])
    assert state["completed_packets"][-1]["packet_id"] == "SHSI-WP6"
    assert state["authority_delta"] == "NONE"
    assert state["authority_effect"] == "NONE_SHADOW_ONLY"
    gate = load(PROGRAMME / "gates/SHSI_G7_DSAI_SHADOW_CLOSEOUT_v0_1.json")
    assert gate["execution_class"] == "AUTO_RATIFIABLE"
    assert gate["runtime_state"] == "SHADOW_ONLY_INACTIVE"
    assert gate["proposed_delta"] == gate["authority_effect"] == "NONE"


def test_wp7_state_mirror_is_exact() -> None:
    registry = ROOT / "registries/implementation/shared_systems_v0_1/SHSI_PROGRAMME_STATE_v0_9_WP7.json"
    source = PROGRAMME / "programme_state/SHSI_PROGRAMME_STATE_v0_9_WP7.json"
    assert registry.read_bytes() == source.read_bytes()


def test_wp7_vit_payload_is_content_addressed() -> None:
    from ovc.development.identity import canonical_sha256

    vit = PROGRAMME / "vit"
    authority = load(vit / "SHSI_WP7_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load(vit / "SHSI_WP7_DEPENDENCY_FRONTIER_v0_1.json")
    pip = load(vit / "SHSI_WP7_PIP_v0_1.json")
    assert authority["logical_id"] == canonical_sha256(authority["payload"])
    assert frontier["logical_id"] == canonical_sha256(frontier["payload"])
    assert pip["logical_id"] == canonical_sha256(pip["payload"])
    assert pip["payload"]["authority_manifest_id"] == authority["logical_id"]
    assert pip["payload"]["dependency_frontier_id"] == frontier["logical_id"]
    assert pip["payload"]["completion_transition"] == {
        "status": "COMPLETED", "next_packet": "SHSI-WP8"
    }
    for change in pip["payload"]["logical_changes"]:
        subprocess.run(
            ["git", "cat-file", "-e", f"{change['blob_sha']}^{{blob}}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
