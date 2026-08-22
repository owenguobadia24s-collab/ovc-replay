from __future__ import annotations

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
PROGRAMME = ROOT / "docs/programmes/shared-systems-v0-1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g5_exact_completion_unlocks_wp6() -> None:
    binding = load(PROGRAMME / "wp6/SHSI_G5_COMPLETION_BINDING_v0_1.json")
    assert binding["status"] == "COMPLETED"
    assert binding["main_tree"] == binding["qualified_candidate_tree"]
    assert binding["physical_completion"]["exact_tree_equal"]
    assert binding["physical_completion"]["four_content_addressed_receipts_present"]


def test_wp6_reuses_exact_dsai_and_ro_contracts_without_parallel_stores() -> None:
    census = load(PROGRAMME / "wp6/SHSI_WP6_REUSE_CENSUS_v0_1.json")
    assert census["dsai_current_state"] == "IMPLEMENTED_ORCH2_BOUNDED_PILOTED"
    assert census["dsai_broker_reused"] and census["ro_artifact_services_reused"]
    assert census["mutated_source_contracts"] == []
    assert census["protected_reads_executed"] == 0
    for field in (
        "credential_stores_created",
        "permission_stores_created",
        "authority_stores_created",
        "artifact_stores_created",
    ):
        assert census[field] == []
    for source in census["sources"]:
        sha = subprocess.run(
            ["git", "hash-object", "--", source["path"]],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert sha == source["git_blob_sha"], source["path"]


def test_wp6_state_gate_and_budget_are_complete_non_authorising() -> None:
    state = load(
        ROOT
        / "registries/implementation/shared_systems_v0_1/SHSI_PROGRAMME_STATE_v0_8_WP6.json"
    )
    assert (state["current_packet"], state["current_gate"], state["next_packet"]) == (
        "SHSI-WP6", "SHSI-G6", "SHSI-WP7"
    )
    assert state["completed_packets"][-1]["packet_id"] == "SHSI-WP5"
    assert state["authority_delta"] == "NONE"
    gate = load(PROGRAMME / "gates/SHSI_G6_FOUNDATION_BUDGET_CLOSEOUT_v0_1.json")
    assert gate["execution_class"] == "AUTO_RATIFIABLE"
    assert gate["security_ambiguity_policy"] == "BLOCKING"
    assert gate["runtime_state"] == "INACTIVE_REFERENCE_BUDGET_FROZEN"
    budget = load(ROOT / state["pilot_acceptance_budget"])
    assert len(budget["baseline_measurements"]) == 18
    assert len(budget["pilot_acceptance_budget"]["numeric_caps"]) == 18
    assert len(budget["pilot_acceptance_budget"]["zero_tolerance_floor"]) == 9
    assert all(value == 0 for value in budget["hard_floor_observed_values"].values())
    assert budget["budget_relaxable_within_pilot"] is False


def test_wp6_state_mirror_is_exact() -> None:
    registry = ROOT / "registries/implementation/shared_systems_v0_1/SHSI_PROGRAMME_STATE_v0_8_WP6.json"
    source = PROGRAMME / "programme_state/SHSI_PROGRAMME_STATE_v0_8_WP6.json"
    assert registry.read_bytes() == source.read_bytes()


def test_wp6_vit_payload_is_content_addressed() -> None:
    from ovc.development.identity import canonical_sha256

    vit = PROGRAMME / "vit"
    authority = load(vit / "SHSI_WP6_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load(vit / "SHSI_WP6_DEPENDENCY_FRONTIER_v0_1.json")
    pip = load(vit / "SHSI_WP6_PIP_v0_1.json")
    assert authority["logical_id"] == canonical_sha256(authority["payload"])
    assert frontier["logical_id"] == canonical_sha256(frontier["payload"])
    assert pip["logical_id"] == canonical_sha256(pip["payload"])
    assert pip["payload"]["authority_manifest_id"] == authority["logical_id"]
    assert pip["payload"]["dependency_frontier_id"] == frontier["logical_id"]
    assert pip["payload"]["completion_transition"] == {
        "status": "COMPLETED",
        "next_packet": "SHSI-WP7",
    }
    for change in pip["payload"]["logical_changes"]:
        subprocess.run(
            ["git", "cat-file", "-e", f"{change['blob_sha']}^{{blob}}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
