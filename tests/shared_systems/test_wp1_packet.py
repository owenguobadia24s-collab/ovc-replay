from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROGRAMME = ROOT / "docs" / "programmes" / "shared-systems-v0-1"
IMPLEMENTATION = ROOT / "registries" / "implementation" / "shared_systems_v0_1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g0b_exact_main_completion_unlocks_wp1() -> None:
    binding = load(PROGRAMME / "wp1" / "SHSI_G0B_COMPLETION_BINDING_v0_1.json")
    assert binding["status"] == "COMPLETED"
    assert binding["main_merge_commit"] == "18827c2c1eff4bedcba7717c2c1a7ecf935cde45"
    assert binding["main_tree"] == "be26e18f40872377ef3f3de31ea250d43ce5054b"
    assert binding["physical_completion"]["exact_tree_equal"] is True
    assert binding["physical_completion"]["four_content_addressed_receipts_present"] is True
    assert binding["authority_effect"] == "NONE"


def test_wp1_historical_state_records_its_qa_review_and_wp0_completion() -> None:
    state = load(IMPLEMENTATION / "SHSI_PROGRAMME_STATE_v0_3_WP1.json")
    assert state["status"] == "QA_REVIEW"
    assert state["completed_packets"] == [{
        "packet_id": "SHSI-WP0",
        "gate_id": "SHSI-G0B",
        "status": "COMPLETED",
        "merge_commit": "18827c2c1eff4bedcba7717c2c1a7ecf935cde45",
        "completion_receipt_id": "339faaaab946562068b0c9abebef6a1ea9763fc042c36e2024d258b08162c6b8",
    }]


def test_g1_is_auto_ratifiable_and_non_authorising() -> None:
    gate = load(PROGRAMME / "gates" / "SHSI_G1_IDENTITY_CLOSEOUT_v0_1.json")
    assert gate["execution_class"] == "AUTO_RATIFIABLE"
    assert gate["proposed_delta"] == "NONE"
    assert gate["authority_effect"] == "NONE"
    assert gate["recommended_decision"] == "AUTO_PASS_PENDING_EXACT_HEAD_ASSURANCE"


def test_wp1_vit_payload_and_frontiers_are_content_addressed() -> None:
    from ovc.development.identity import canonical_sha256

    vit = PROGRAMME / "vit"
    authority = load(vit / "SHSI_WP1_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load(vit / "SHSI_WP1_DEPENDENCY_FRONTIER_v0_1.json")
    pip = load(vit / "SHSI_WP1_PIP_v0_1.json")
    assert authority["logical_id"] == canonical_sha256(authority["payload"])
    assert frontier["logical_id"] == canonical_sha256(frontier["payload"])
    assert pip["logical_id"] == canonical_sha256(pip["payload"])
    assert pip["payload"]["authority_manifest_id"] == authority["logical_id"]
    assert pip["payload"]["dependency_frontier_id"] == frontier["logical_id"]
    assert pip["payload"]["completion_transition"] == {"status": "COMPLETED", "next_packet": "SHSI-WP2"}
    for change in pip["payload"]["logical_changes"]:
        # A completed packet binds immutable Git blobs, not the mutable current path.
        # Successor packets may lawfully create later generations of the same file.
        subprocess.run(
            ["git", "cat-file", "-e", f"{change['blob_sha']}^{{blob}}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
