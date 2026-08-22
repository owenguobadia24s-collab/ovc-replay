from __future__ import annotations

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
PROGRAMME = ROOT / "docs/programmes/shared-systems-v0-1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g8_exact_completion_unlocks_wp9() -> None:
    row = load(PROGRAMME / "wp9/SHSI_G8_COMPLETION_BINDING_v0_1.json")
    assert row["status"] == "COMPLETED"
    assert row["main_tree"] == row["qualified_candidate_tree"]
    assert row["physical_completion"]["exact_tree_equal"]
    assert row["physical_completion"]["four_content_addressed_receipts_present"]


def test_wp9_census_pins_esl_and_all_historical_identities() -> None:
    census = load(PROGRAMME / "wp9/SHSI_WP9_ESL_CONSUMPTION_CENSUS_v0_1.json")
    assert census["mode"] == "SHADOW_ONLY"
    assert set(census["surfaces"]) == {
        "PROFILE", "EVIDENCE_FRONTIER", "LINEAGE", "INTERFACE", "READ_MODEL"
    }
    for field in (
        "active_adapter_count", "declared_loss_count", "mandatory_divergence_count",
        "family_promotions", "topology_promotions", "source_expansions", "semantic_promotions",
    ):
        assert census[field] == 0
    assert census["c3_activation_state"] == "NONE"
    assert census["optional_missing_preserves_base"]
    for item in census["sources"]:
        blob = subprocess.run(
            ["git", "hash-object", "--", item["path"]], cwd=ROOT,
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        assert blob == item["git_blob_sha"], item["path"]


def test_wp9_current_state_and_gate_are_shadow_only() -> None:
    pointer = load(ROOT / "registries/implementation/shared_systems_v0_1/CURRENT_STATE_POINTER.json")
    assert (pointer["current_packet"], pointer["current_gate"], pointer["next_packet"]) == (
        "SHSI-WP9", "SHSI-G9", "SHSI-WP10"
    )
    state = load(ROOT / pointer["state_record"])
    assert state["completed_packets"][-1]["packet_id"] == "SHSI-WP8"
    assert state["authority_delta"] == "NONE"
    gate = load(PROGRAMME / "gates/SHSI_G9_ESL_SHADOW_CLOSEOUT_v0_1.json")
    assert gate["execution_class"] == "AUTO_RATIFIABLE"
    assert gate["runtime_state"] == "SHADOW_ONLY_INACTIVE"
    assert gate["proposed_delta"] == gate["authority_effect"] == "NONE"


def test_wp9_state_mirror_is_exact() -> None:
    source = PROGRAMME / "programme_state/SHSI_PROGRAMME_STATE_v0_11_WP9.json"
    mirror = ROOT / "registries/implementation/shared_systems_v0_1/SHSI_PROGRAMME_STATE_v0_11_WP9.json"
    assert source.read_bytes() == mirror.read_bytes()


def test_wp9_vit_payload_is_content_addressed() -> None:
    from ovc.development.identity import canonical_sha256

    vit = PROGRAMME / "vit"
    authority = load(vit / "SHSI_WP9_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load(vit / "SHSI_WP9_DEPENDENCY_FRONTIER_v0_1.json")
    pip = load(vit / "SHSI_WP9_PIP_v0_1.json")
    assert authority["logical_id"] == canonical_sha256(authority["payload"])
    assert frontier["logical_id"] == canonical_sha256(frontier["payload"])
    assert pip["logical_id"] == canonical_sha256(pip["payload"])
    assert pip["payload"]["authority_manifest_id"] == authority["logical_id"]
    assert pip["payload"]["dependency_frontier_id"] == frontier["logical_id"]
    assert pip["payload"]["completion_transition"] == {
        "status":"COMPLETED", "next_packet":"SHSI-WP10"
    }
    for change in pip["payload"]["logical_changes"]:
        subprocess.run(
            ["git", "cat-file", "-e", f"{change['blob_sha']}^{{blob}}"],
            cwd=ROOT, check=True, capture_output=True,
        )
