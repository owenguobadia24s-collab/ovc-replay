import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WP7A = ROOT / "docs/programmes/dias-v0-1/wp7a"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def test_stabilisation_and_zero_dependency_are_gate_qualified() -> None:
    result = load(WP7A / "DIASI_WP7A_STABILISATION_RESULT.json")
    aggregate = result["aggregate"]
    assert result["status"] == "PASS" and result["elapsed_seconds"] >= 300
    assert aggregate["cycles_passed"] == aggregate["cycles_denominator"] == 5
    assert all(aggregate[key] == 0 for key in ("unsafe_outcome_count", "unknown_outcome_count", "false_differential_count", "duplicate_successor_count", "a3_mismatch_count", "stale_writer_accepted_count", "integrity_incident_count", "live_side_effect_count"))
    census = load(WP7A / "DIASI_WP7A_ZERO_ACTIVE_DEPENDENCY_CENSUS.json")
    assert census["status"] == "PASS" and census["global_retirement_claimed"] is False
    assert all(row["active_old_route_dependencies"] == 0 for row in census["dimensions"])
    assert census["shared_machinery"]["global_cers_persistent_service"]["active_admission_count"] == 5


def test_historical_gate_packet_and_materialised_decision_are_exact() -> None:
    history = load(WP7A / "DIASI_WP7A_HISTORICAL_INTERPRETATION_BUNDLE.json")
    review = load(WP7A / "DIASI_WP7A_INDEPENDENT_RETIREMENT_REVIEW.json")
    gate = load(WP7A / "DIASI_G_DGS_RETIRE_REMOVE_OPERATOR_GATE_PACKET.json")
    decision = load(ROOT / "docs/programmes/dias-v0-1/retire-remove/DIASI_G_DGS_RETIRE_REMOVE_OPERATOR_DECISION.json")
    assert history["status"] == "PASS" and history["authority_effect"] == "NONE_HISTORY_ONLY"
    assert review["recommendation"] == "PASS" and review["unresolved_warning_count"] == 0
    assert gate["decision_status"] == "PENDING_OPERATOR" and gate["authority_effect"] == "NONE_PENDING_EXACT_OPERATOR_PHRASE"
    assert decision["decision"] == "PASS"
    assert decision["operator_phrase"] == gate["canonical_operator_phrase"] == "OVC APPROVE DIASI-G-DGS-RETIRE-REMOVE PASS"
    assert "NO_GLOBAL_CERS_RETIREMENT" in decision["explicit_non_grants"]
    assert "NO_GLOBAL_PES_RETIREMENT" in decision["explicit_non_grants"]


def test_vit_bindings_remain_historical_gate_preparation_evidence() -> None:
    for name in ("DIASI_WP7A_VIT_AUTHORITY_MANIFEST.json", "DIASI_WP7A_VIT_DEPENDENCY_FRONTIER.json"):
        binding = load(WP7A / name)
        assert binding["logical_id"] == canonical(binding["payload"])


def test_active_route_and_writer_are_owner_local_generation_3_after_sunset() -> None:
    route = load(ROOT / "registries/development/skills/VIT_SELECTED_CLASS_ROUTE_v0_1.json")
    writer = load(ROOT / "registries/development/skills/VIT_QUALIFICATION_WRITER_AUTHORITY_v0_1.json")
    assert route["route_generation"] == route["writer_generation"] == writer["generation"] == 3
    assert route["schema"] == "ovc-vit-owner-local-selected-class-route/v1"
    assert route["status"] == writer["status"] == "ACTIVE_OWNER_LOCAL"
    assert route["owner"] == "DSAI_VIT"
    assert writer["owner"] == "VIT_QUALIFICATION_OWNER_LOCAL"
    assert "old_route" not in route and "incumbent_writer" not in writer
    assert route["non_selected_classes"] == "SCOPED_NOT_RETIRED_UNCHANGED"
