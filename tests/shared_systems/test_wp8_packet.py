from __future__ import annotations

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
PROGRAMME = ROOT / "docs/programmes/shared-systems-v0-1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g7_exact_completion_unlocks_wp8() -> None:
    binding = load(PROGRAMME / "wp8/SHSI_G7_COMPLETION_BINDING_v0_1.json")
    assert binding["status"] == "COMPLETED"
    assert binding["main_tree"] == binding["qualified_candidate_tree"]
    assert binding["physical_completion"]["exact_tree_equal"]
    assert binding["physical_completion"]["four_content_addressed_receipts_present"]


def test_wp8_census_is_synthetic_metadata_only_and_exact() -> None:
    census = load(PROGRAMME / "wp8/SHSI_WP8_RO_DMRP_CONSUMPTION_CENSUS_v0_1.json")
    assert census["mode"] == "READ_ONLY_SHADOW_ONLY"
    assert census["owner_provider_refs"] == ["REPOSITORY_GIT"]
    assert census["owner_research_roles"] == ["DISCOVERY"]
    for field in (
        "external_artifact_fetches", "real_source_payload_reads",
        "research_operations_writes", "artifact_stores_created",
        "provider_additions", "source_additions", "research_role_additions",
    ):
        assert census[field] == 0
    assert not census["current_binding_changed"]
    assert census["validation"] == "LOCKED_UNCONSUMED"
    for item in census["sources"]:
        blob = subprocess.run(
            ["git", "hash-object", "--", item["path"]], cwd=ROOT,
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        assert blob == item["git_blob_sha"], item["path"]


def test_wp8_current_state_and_gate_are_read_only_non_authorising() -> None:
    state = load(
        ROOT / "registries/implementation/shared_systems_v0_1/SHSI_PROGRAMME_STATE_v0_10_WP8.json"
    )
    assert (state["current_packet"], state["current_gate"], state["next_packet"]) == (
        "SHSI-WP8", "SHSI-G8", "SHSI-WP9"
    )
    assert state["completed_packets"][-1]["packet_id"] == "SHSI-WP7"
    assert state["authority_delta"] == "NONE"
    assert state["authority_effect"] == "NONE_READ_ONLY_SHADOW_ONLY"
    gate = load(PROGRAMME / "gates/SHSI_G8_RO_DMRP_SHADOW_CLOSEOUT_v0_1.json")
    assert gate["execution_class"] == "AUTO_RATIFIABLE"
    assert gate["runtime_state"] == "READ_ONLY_SHADOW_ONLY_INACTIVE"
    assert gate["proposed_delta"] == gate["authority_effect"] == "NONE"


def test_wp8_state_mirror_is_exact() -> None:
    source = PROGRAMME / "programme_state/SHSI_PROGRAMME_STATE_v0_10_WP8.json"
    mirror = ROOT / "registries/implementation/shared_systems_v0_1/SHSI_PROGRAMME_STATE_v0_10_WP8.json"
    assert source.read_bytes() == mirror.read_bytes()


def test_wp8_vit_payload_is_content_addressed() -> None:
    from ovc.development.identity import canonical_sha256

    vit = PROGRAMME / "vit"
    authority = load(vit / "SHSI_WP8_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load(vit / "SHSI_WP8_DEPENDENCY_FRONTIER_v0_1.json")
    pip = load(vit / "SHSI_WP8_PIP_v0_1.json")
    assert authority["logical_id"] == canonical_sha256(authority["payload"])
    assert frontier["logical_id"] == canonical_sha256(frontier["payload"])
    assert pip["logical_id"] == canonical_sha256(pip["payload"])
    assert pip["payload"]["authority_manifest_id"] == authority["logical_id"]
    assert pip["payload"]["dependency_frontier_id"] == frontier["logical_id"]
    assert pip["payload"]["completion_transition"] == {
        "status":"COMPLETED", "next_packet":"SHSI-WP9"
    }
    for change in pip["payload"]["logical_changes"]:
        subprocess.run(
            ["git", "cat-file", "-e", f"{change['blob_sha']}^{{blob}}"],
            cwd=ROOT, check=True, capture_output=True,
        )
