from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROGRAMME = ROOT / "docs/programmes/shared-systems-v0-1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g4_exact_completion_unlocks_wp5() -> None:
    binding = load(PROGRAMME / "wp5/SHSI_G4_COMPLETION_BINDING_v0_1.json")
    assert binding["status"] == "COMPLETED"
    assert binding["main_tree"] == binding["qualified_candidate_tree"]
    assert binding["physical_completion"]["exact_tree_equal"]
    assert binding["physical_completion"]["four_content_addressed_receipts_present"]


def test_stage0_binding_and_wp5_precedents_are_exact_and_nonmutated() -> None:
    census = load(PROGRAMME / "wp5/SHSI_WP5_PRECEDENT_CENSUS_v0_1.json")
    assert census["normative_source_basis"] == ["S10", "S12", "S13"]
    assert census["mutated_source_contracts"] == []
    assert census["current_consumer_bindings_changed"] == []
    assert census["non_migration_registry_prior_materialization"].startswith("MISSING")
    for source in census["sources"]:
        sha = subprocess.run(
            ["git", "hash-object", "--", source["path"]],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert sha == source["git_blob_sha"]
    proof = load(PROGRAMME / "wp0/SHSI_SHARED_SERVICE_BINDING_PROOF_v0_1.json")
    assert proof["result"] == "PASS_EXACT_SINGLE_CURRENT_OWNER"
    assert proof["matching_service_binding_count"] == 1
    assert proof["registry_conflict_count"] == 0


def test_wp5_state_gate_schema_and_fixture_are_non_authorising() -> None:
    state = load(
        ROOT
        / "registries/implementation/shared_systems_v0_1/SHSI_PROGRAMME_STATE_v0_7_WP5.json"
    )
    assert (
        state["current_packet"],
        state["current_gate"],
        state["next_packet"],
    ) == ("SHSI-WP5", "SHSI-G5", "SHSI-WP6")
    assert state["schema"] == "ovc-native-programme-state/v1"
    assert state["completed_packets"][-1]["packet_id"] == "SHSI-WP4"
    assert state["authority_delta"] == "NONE"
    gate = load(PROGRAMME / "gates/SHSI_G5_REGISTRY_RESOLUTION_CLOSEOUT_v0_1.json")
    assert gate["execution_class"] == "AUTO_RATIFIABLE"
    assert gate["runtime_state"] == "INACTIVE_REFERENCE_SHADOW_ONLY"
    assert gate["authority_effect"] == "NONE"
    schema = load(
        ROOT / "schemas/shared_systems/exact_resolution_migration_v0_1.schema.json"
    )
    expected = {
        "SharedServiceDescriptor",
        "RegistryDirectory",
        "ServiceConsumptionBinding",
        "ResolutionRequest",
        "ResolutionManifest",
        "SharedExecutionContext",
        "ServiceCurrentBinding",
        "MigrationInventory",
        "NonMigrationDecision",
        "NonMigrationDecisionRegistry",
    }
    assert expected <= set(schema["$defs"])
    fixture = load(
        ROOT
        / "fixtures/shared_systems/resolution/SHSI_WP5_SYNTHETIC_RESOLUTION_FIXTURES_v0_1.json"
    )
    assert fixture["authority_effect"] == "NONE"
    assert fixture["consumer_changes"] == []
    assert fixture["golden"]["status"] == "RESOLVED"


def test_wp5_vit_payload_is_content_addressed() -> None:
    from ovc.development.identity import canonical_sha256

    vit = PROGRAMME / "vit"
    authority = load(vit / "SHSI_WP5_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load(vit / "SHSI_WP5_DEPENDENCY_FRONTIER_v0_1.json")
    pip = load(vit / "SHSI_WP5_PIP_v0_1.json")
    assert authority["logical_id"] == canonical_sha256(authority["payload"])
    assert frontier["logical_id"] == canonical_sha256(frontier["payload"])
    assert pip["logical_id"] == canonical_sha256(pip["payload"])
    assert pip["payload"]["authority_manifest_id"] == authority["logical_id"]
    assert pip["payload"]["dependency_frontier_id"] == frontier["logical_id"]
    assert pip["payload"]["completion_transition"] == {
        "status": "COMPLETED",
        "next_packet": "SHSI-WP6",
    }
    for change in pip["payload"]["logical_changes"]:
        subprocess.run(
            ["git", "cat-file", "-e", f"{change['blob_sha']}^{{blob}}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
