import json
from pathlib import Path

from ovc.development.identity import canonical_sha256
from ovc.development.skills.dias_history import interpret_diasi_history


ROOT = Path(__file__).resolve().parents[3]
WP9 = ROOT / "docs/programmes/dias-v0-1/wp9"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_terminal_state_is_read_only_and_has_no_successor_or_control_role() -> None:
    state = load(ROOT / "registries/implementation/dias_v0_1/DIASI_CURRENT_v0_13_TERMINAL.json")
    assert state["status"] == state["terminal_state"] == "DIAS_COMPLETED_REFERENCE_SAFE"
    assert state["programme_mode"] == "TERMINAL_READ_ONLY" and state["read_only"] is True
    assert state["next_packet"] is None and state["next_gate"] is None
    assert state["active_diasi_control_registries"] == []
    assert all(state[field] is False for field in ("active_scheduler", "active_physical_writer", "independent_currentness_authority", "liveness_service", "generic_authority_platform"))


def test_terminal_gate_is_delegated_pass_without_crossing_proof_gates() -> None:
    decision = load(WP9 / "DIASI_G_TERMINAL_DELEGATED_PASS.json")
    assert decision["decision"] == "PASS"
    assert decision["decision_authority"] == "AUTO_RATIFIABLE_INSIDE_GRANTED_AUTHORITY"
    assert all(decision["conditions"].values())
    assert decision["reserved_proof_gates_crossed"] is False
    assert decision["next_packet"] is None and decision["next_gate"] is None


def test_absorption_and_sunset_has_exact_owner_mapping_and_no_diasi_runtime() -> None:
    manifest = load(WP9 / "DIASI_ABSORPTION_AND_SUNSET_MANIFEST.json")
    assert {row["owner"] for row in manifest["owner_absorption"]} == {"DSAI_VIT", "RAC_ASYNC_ASSURANCE", "DSAI_SIQ_PHYSICAL_CONTROLLER", "VIT_SIQ_OWNER_LOCAL_SURFACES", "GOVERNED_HISTORY"}
    assert manifest["active_diasi_control_registries"] == []
    assert manifest["programme_mode"] == "TERMINAL_READ_ONLY"
    for field in ("diasi_active_scheduler", "diasi_active_physical_writer", "diasi_independent_currentness_authority", "diasi_liveness_service", "diasi_generic_authority_platform", "generic_replacement_supervisor"):
        assert manifest[field] is False


def test_active_selected_class_registries_are_vit_owner_local_not_diasi_control() -> None:
    route = load(ROOT / "registries/development/skills/VIT_SELECTED_CLASS_ROUTE_v0_1.json")
    writer = load(ROOT / "registries/development/skills/VIT_QUALIFICATION_WRITER_AUTHORITY_v0_1.json")
    assert route["schema"] == "ovc-vit-owner-local-selected-class-route/v1"
    assert writer["schema"] == "ovc-vit-qualification-writer-authority/v3"
    assert route["status"] == writer["status"] == "ACTIVE_OWNER_LOCAL"
    assert route["owner"] == "DSAI_VIT" and writer["owner"] == "VIT_QUALIFICATION_OWNER_LOCAL"
    forbidden = {"programme_id", "packet_id", "cutover_gate_id", "retirement_gate_id", "retirement_operator_phrase", "retirement_authority"}
    assert forbidden.isdisjoint(route) and forbidden.isdisjoint(writer)


def test_every_programme_state_remains_historically_interpretable() -> None:
    states = sorted((ROOT / "registries/implementation/dias_v0_1").glob("DIASI_*.json"))
    assert len(states) >= 13
    assert all(interpret_diasi_history(load(path)).authority_effect == "NONE_INTERPRETATION_ONLY" for path in states)


def test_racpr_reference_safe_performance_and_fallback_are_explicit() -> None:
    disposition = load(ROOT / "docs/programmes/dias-v0-1/wp7b/DIASI_WP7B_RACPR_REFERENCE_SAFE_DISPOSITION.json")
    performance = disposition["performance"]
    assert disposition["classification"] == "REFERENCE_ONLY"
    assert disposition["reference_fallback"] == "COMPLETE_INDEPENDENTLY_USABLE"
    assert performance["cohort_denominator"] == performance["eligible_count"] == 0
    assert performance["eligible_share"] == 0.0 and performance["p90_t_certificate_seconds"] is None
    assert len(performance["exclusions"]) == 4


def test_mandatory_adversarial_population_including_av16_passes() -> None:
    result = load(WP9 / "DIASI_WP9_MANDATORY_ADVERSARIAL_RESULT.json")
    assert result["passed"] == result["denominator"] == len(result["population"]) == 16
    assert result["unsafe_survivals"] == 0
    assert result["population"][-1] == "DIAS-AV-16_ACTIVE_DIASI_REGISTRY_AFTER_SUNSET"
    assert result["active_diasi_registry_after_sunset"] is False


def test_final_matrix_qa_and_vit_bindings_close_wp0_through_wp9() -> None:
    matrix = load(WP9 / "DIASI_WP9_FINAL_CONFORMANCE_MATRIX.json")
    assert matrix["terminal_state"] == "DIAS_COMPLETED_REFERENCE_SAFE"
    assert [row["packet"] for row in matrix["packets"]] == ["DIASI-WP0", "DIASI-WP1", "DIASI-WP2", "DIASI-WP3", "DIASI-WP4A", "DIASI-WP4B", "DIASI-WP5", "DIASI-WP6", "DIASI-WP7A", "DIASI-WP7B", "DIASI-WP8", "DIASI-WP9"]
    assert matrix["packets"][-2]["status"] == "NOT_APPLICABLE_REFERENCE_SAFE"
    qa = load(WP9 / "DIASI_WP9_QA_PACKET.json")
    assert qa["status"] == "PASS" and qa["checks_passed"] == qa["checks_denominator"] == 10
    for name in ("DIASI_WP9_VIT_AUTHORITY_MANIFEST.json", "DIASI_WP9_VIT_DEPENDENCY_FRONTIER.json"):
        binding = load(WP9 / name)
        assert binding["logical_id"] == canonical_sha256(binding["payload"])
