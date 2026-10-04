import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
R3 = ROOT / "docs/programmes/price-state-morph-v0-1/r3"
R4 = ROOT / "docs/programmes/price-state-morph-v0-1/r4/g0"
STATE = ROOT / "records/research_operations/price_state_morph/OVC_PRICE_STATE_MORPH_PROGRAMME_STATE_v0_1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_operator_pass_is_bounded_to_consumed_r3_discovery():
    record = load(R3 / "OVC_PRICE_STATE_MORPH_R3_GATE_DECISION_AND_CLOSEOUT_v0_1.json")
    authority = load(R3 / "OVC_PRICE_STATE_MORPH_R3_AUTHORITY_MANIFEST_v0_1.json")
    assert record["gate_id"] == "OVC-PRICE-STATE-MORPH-R3-G0"
    assert record["operator_decision"]["decision"] == "PASS"
    assert record["operator_decision"]["operator_command"] == "APPROVE OVC-PRICE-STATE-MORPH-R3-G0"
    assert record["operator_decision"]["approved_delta"] == "ACTIVE_DISCOVERY_R3_CONSUMED_ONLY"
    assert "FRESH_SOURCE_SELECTION_OR_INTAKE" in authority["denies"]
    assert "ACTIVE_VALIDATION" in authority["denies"]
    assert "CALIBRATED_PROBABILITY" in authority["denies"]


def test_r3_primary_nonpass_and_positive_information_are_both_preserved():
    record = load(R3 / "OVC_PRICE_STATE_MORPH_R3_GATE_DECISION_AND_CLOSEOUT_v0_1.json")
    result = record["results"]
    assert record["decision"] == "A0_A1_EQUIVALENCE_UNSTABLE_ACROSS_GRID"
    assert result["module_m"] == "PASS_BOUNDED_MEMORY_CLOSURE"
    assert result["a0_positive_information_all_18_cells"] is True
    assert [row["cell"] for row in result["a0_a1_equivalence_failures"]] == [
        "K4__R0_EXACT_7ZONE_TRACE",
        "B16__R0_EXACT_7ZONE_TRACE",
    ]
    assert record["qa"]["no_post_result_rescue"] is True


def test_external_custody_and_replay_are_exactly_bound():
    record = load(R3 / "OVC_PRICE_STATE_MORPH_R3_GATE_DECISION_AND_CLOSEOUT_v0_1.json")
    manifest = load(R3 / "OVC_PRICE_STATE_MORPH_R3_EXTERNAL_ARTIFACT_MANIFEST_v0_1.json")
    assert record["laboratory_custody"]["status"] == "VERIFIED"
    assert record["qa"]["replay"] == "PASS_TWO_RUNS_BYTE_IDENTICAL"
    assert record["qa"]["frozen_components_replayed"] == 19
    assert manifest["canonical_package"]["sha256"] == "9cb4d3da2f4e3ad11c6d768271c6785ead87af962c43243923fdbc11b0ecda71"
    assert manifest["custody_verification"] == {"catalogue": "PASS", "routing_events": "PASS", "decision_log": "PASS"}
    assert manifest["fresh_source_opened"] is False


def test_programme_state_stops_at_r4_fresh_source_gate():
    state = load(STATE)
    gate = load(R4 / "OVC_PRICE_STATE_MORPH_R4_G0_GATE_v0_1.json")
    assert state["status"] == "COMPLETED"
    assert state["scientific_decision"] == "A0_A1_EQUIVALENCE_UNSTABLE_ACROSS_GRID"
    assert state["next_gate"] == "OVC-PRICE-STATE-MORPH-R4-G0"
    assert state["next_gate_status"] == "GATE_READY_AWAITING_OPERATOR"
    assert state["fresh_source_selected"] is False
    assert gate["authority_required"] == "OPERATOR_REQUIRED_NEW_REAL_PROVIDER_OR_SOURCE_INTAKE"
    assert gate["fresh_source_selected"] is False
    assert gate["authority_effect"] == "NONE"
