from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROGRAMME = ROOT / "docs/programmes/shared-systems-v0-1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g3_exact_completion_unlocks_wp4() -> None:
    binding = load(PROGRAMME / "wp4/SHSI_G3_COMPLETION_BINDING_v0_1.json")
    assert binding["status"] == "COMPLETED"
    assert binding["main_tree"] == binding["qualified_candidate_tree"]
    assert binding["physical_completion"]["exact_tree_equal"]
    assert binding["physical_completion"]["four_content_addressed_receipts_present"]


def test_wp4_precedents_are_exact_and_nonmutated() -> None:
    census = load(PROGRAMME / "wp4/SHSI_WP4_PRECEDENT_CENSUS_v0_1.json")
    assert {item["owner"] for item in census["sources"]} == {"DSAI", "GRT"}
    assert census["normative_source_basis"] == ["S5", "S6", "S9", "S10", "S12"]
    assert census["mutated_source_contracts"] == []
    assert not census["owner_qualification_replaced"]
    assert census["scientific_runs_executed"] == 0
    for source in census["sources"]:
        sha = subprocess.run(
            ["git", "hash-object", "--", source["path"]],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert sha == source["git_blob_sha"]


def test_wp4_state_gate_schema_and_fixture_are_non_authorising() -> None:
    pointer = load(
        ROOT / "registries/implementation/shared_systems_v0_1/CURRENT_STATE_POINTER.json"
    )
    assert (
        pointer["current_packet"],
        pointer["current_gate"],
        pointer["next_packet"],
    ) == ("SHSI-WP4", "SHSI-G4", "SHSI-WP5")
    state = load(ROOT / pointer["state_record"])
    assert state["schema"] == "ovc-native-programme-state/v1"
    assert state["authority_delta"] == "NONE"
    assert state["completed_packets"][-1]["packet_id"] == "SHSI-WP3"
    gate = load(PROGRAMME / "gates/SHSI_G4_ASSURANCE_IMPACT_CLOSEOUT_v0_1.json")
    assert gate["execution_class"] == "AUTO_RATIFIABLE"
    assert gate["authority_effect"] == "NONE"
    schema = load(
        ROOT / "schemas/shared_systems/assurance_currentness_impact_v0_1.schema.json"
    )
    expected = {
        "AssuranceAssertionSpec",
        "AssuranceAssertionResult",
        "AssuranceSuite",
        "AssurancePacket",
        "QualificationRecord",
        "QualificationCurrentness",
        "ChangeAssessment",
        "ImpactDependencyEdge",
        "InvalidationPlan",
        "ReplayObligation",
        "IncidentRecord",
        "QuarantineRecord",
    }
    assert expected <= set(schema["$defs"])
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    fixture = load(
        ROOT
        / "fixtures/shared_systems/assurance/SHSI_WP4_ASSURANCE_IMPACT_FIXTURES_v0_1.json"
    )
    assert fixture["authority_effect"] == "NONE"
    qualification_required = set(schema["$defs"]["QualificationRecord"]["required"])
    assert qualification_required <= set(fixture["qualification"])
    assert fixture["qualification"]["authority_effect"] == "NONE"
    assert fixture["authority_laundering"]["expected"] == "FAIL_CLOSED"
    assert not fixture["incident"]["quarantine_deleted"]


def test_wp4_vit_payload_is_content_addressed() -> None:
    from ovc.development.identity import canonical_sha256

    vit = PROGRAMME / "vit"
    authority = load(vit / "SHSI_WP4_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load(vit / "SHSI_WP4_DEPENDENCY_FRONTIER_v0_1.json")
    pip = load(vit / "SHSI_WP4_PIP_v0_1.json")
    assert authority["logical_id"] == canonical_sha256(authority["payload"])
    assert frontier["logical_id"] == canonical_sha256(frontier["payload"])
    assert pip["logical_id"] == canonical_sha256(pip["payload"])
    assert pip["payload"]["authority_manifest_id"] == authority["logical_id"]
    assert pip["payload"]["dependency_frontier_id"] == frontier["logical_id"]
    assert pip["payload"]["completion_transition"] == {
        "status": "COMPLETED",
        "next_packet": "SHSI-WP5",
    }
    for change in pip["payload"]["logical_changes"]:
        sha = subprocess.run(
            ["git", "hash-object", "--", change["path"]],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert sha == change["blob_sha"], change["path"]
