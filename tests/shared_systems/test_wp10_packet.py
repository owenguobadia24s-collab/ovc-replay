from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess

from ovc.development.identity import canonical_sha256
from ovc.shared_systems.foundation import PILOT_HARD_FLOOR_DIMENSIONS, PILOT_NUMERIC_CAP_DIMENSIONS
from ovc.shared_systems.resolution import ResolutionManifest, SharedExecutionContext


ROOT = Path(__file__).resolve().parents[2]
PROGRAMME = ROOT / "docs/programmes/shared-systems-v0-1"
WP10 = PROGRAMME / "wp10"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g9_exact_completion_unlocks_wp10() -> None:
    row = load(WP10 / "SHSI_G9_COMPLETION_BINDING_v0_1.json")
    assert row["status"] == "COMPLETED"
    assert row["main_tree"] == row["qualified_candidate_tree"]
    assert row["physical_completion"]["exact_tree_equal"]
    assert row["physical_completion"]["four_content_addressed_receipts_present"]


def test_terminal_matrix_has_exact_frozen_contexts_for_three_shadow_consumers() -> None:
    matrix = load(WP10 / "SHSI_WP10_INTEGRATED_PILOT_MATRIX_v0_1.json")
    assert matrix["status"] == "PASS" and matrix["consumer_count"] == 3
    assert matrix["current_execution_binding_changes"] == 0
    consumers = {row["consumer_programme_id"] for row in matrix["bindings"]}
    assert consumers == {"OVC-DSAI-v0.1", "OVC-EC1-DMRP-CONFORMANCE-v0.1", "OVC-OPTB-ESL-CONFORMANCE-v0.1"}
    for row in matrix["bindings"]:
        manifest = ResolutionManifest(**row["resolution_manifest"])
        context = SharedExecutionContext(**row["execution_context"])
        assert context == SharedExecutionContext.freeze(context.context_id, manifest)
        assert row["status"] == "SHADOW_ONLY"
        assert not row["current_execution_binding_changed"]


def test_governed_corpora_and_integrated_replay_are_exact_without_cutover() -> None:
    evidence = load(WP10 / "SHSI_WP10_GOVERNED_CORPUS_EQUIVALENCE_v0_1.json")
    for row in evidence["equivalence_records"]:
        raw = (ROOT / row["corpus_ref"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row["corpus_sha256"]
        assert row["reference_logical_sha256"] == row["optimized_logical_sha256"]
        assert row["cutover_authority_effect"] == "NONE"
    replay = evidence["integrated_replay"]
    assert len({value for key, value in replay.items() if key.endswith("logical_sha256")}) == 1
    registry = load(ROOT / "registries/implementation/shared_systems_v0_1/SHSI_NON_MIGRATION_DECISION_REGISTRY_v0_1.json")
    dmrp = next(row for row in registry["decisions"] if "DMRP" in row["consumer_programme_id"])
    assert dmrp["disposition"] == "DEFER"
    assert registry["current_execution_binding_changes"] == registry["cutovers_executed"] == 0


def test_terminal_budget_burden_and_read_model_remain_bounded() -> None:
    result = load(WP10 / "SHSI_WP10_PILOT_ACCEPTANCE_RESULT_v0_1.json")
    budget = load(ROOT / "registries/implementation/shared_systems_v0_1/SHSI_PILOT_ACCEPTANCE_BUDGET_v0_1.json")["pilot_acceptance_budget"]
    caps = {key: value for key, value, _ in budget["numeric_caps"]}
    assert set(result["observed_dimensions"]) == set(PILOT_NUMERIC_CAP_DIMENSIONS) == set(caps)
    assert all(value <= caps[key] for key, value in result["observed_dimensions"].items())
    assert set(result["hard_floor_observations"]) == PILOT_HARD_FLOOR_DIMENSIONS
    assert all(value == 0 for value in result["hard_floor_observations"].values())
    burden = load(WP10 / "SHSI_WP10_OPERATIONAL_BURDEN_LEDGER_v0_1.json")
    assert burden["active_adapter_count"] == 0 and not burden["unresolved_incidents"]
    read_model = load(WP10 / "SHSI_WP10_RESEARCH_CONSOLE_READ_MODEL_v0_1.json")
    assert read_model["console_authority"] == "READ_ONLY" and read_model["mutation_routes"] == []
    assert read_model["frontend_scientific_calculation"] == "FORBIDDEN"


def test_terminal_state_mirror_pointer_and_vit_payload_are_exact() -> None:
    source = PROGRAMME / "programme_state/SHSI_PROGRAMME_STATE_v0_12_TERMINAL.json"
    mirror = ROOT / "registries/implementation/shared_systems_v0_1/SHSI_PROGRAMME_STATE_v0_12_TERMINAL.json"
    assert source.read_bytes() == mirror.read_bytes()
    pointer = load(ROOT / "registries/implementation/shared_systems_v0_1/CURRENT_STATE_POINTER.json")
    assert pointer["status"] == "COMPLETED" and pointer["next_packet"] is None
    assert pointer["terminal_state"] == "SHARED_SYSTEMS_V0_1_IMPLEMENTED_THREE_CONSUMER_SHADOW_CONFORMANT"
    vit = PROGRAMME / "vit"
    authority = load(vit / "SHSI_WP10_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load(vit / "SHSI_WP10_DEPENDENCY_FRONTIER_v0_1.json")
    pip = load(vit / "SHSI_WP10_PIP_v0_1.json")
    assert authority["logical_id"] == canonical_sha256(authority["payload"])
    assert frontier["logical_id"] == canonical_sha256(frontier["payload"])
    assert pip["logical_id"] == canonical_sha256(pip["payload"])
    assert pip["payload"]["completion_transition"] == {"status": "COMPLETED", "next_packet": None}
    for change in pip["payload"]["logical_changes"]:
        subprocess.run(["git", "cat-file", "-e", f"{change['blob_sha']}^{{blob}}"], cwd=ROOT, check=True, capture_output=True)
