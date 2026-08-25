from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"
SCHEMAS = ROOT / "schemas/research_operations/asocs"
POINTER = ROOT / "registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json"
G6_STATE = ROOT / "records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_25_G6_PROVENANCE_SUPERSESSION_APPROVED.json"

LOCKED_SESSION1 = "9aaa80991365cf290122caef513f0e8d706a7b1283475fa041d01d8e5f9f1a0e"
NON_ADMITTED_CORRECTION = "4f0f06c8f6ba061e56079b04a6400013d12a0a6a578f653fc7abf553744c42ef"
G1_15M = "df060a22bf8a6c1d990d22af90e189848bd2c5f3090ef65a8c5637e4456bb7d9"
G3_TRACES = "22c856efdd24083d5339d2082ad9714597e326a6f40655bfb82b0afa9899f7dc"
G4_POP = "ff6eb37724aea5b2706666903f7b5a1bc063af8ef9026f4496429b5e33fa15fe"
EXPECTED_CASES = [
"ASOCS.BLIND.4754b461b4d0fff17a48b9eb","ASOCS.BLIND.66ed33d51319ec6923d4d0a5",
"ASOCS.BLIND.bc9bf3421a7e26e25f204668","ASOCS.BLIND.b29062d1bc3ebbb66455bef6",
"ASOCS.BLIND.1f8bc89c69d001ae26eececa","ASOCS.BLIND.08b1a69e8ae7a932252d6c85",
"ASOCS.BLIND.7c804e44e9649cd5ba7bd0f9","ASOCS.BLIND.2e735b1ba24f0eccd71b0d18",
"ASOCS.BLIND.b7c0e102063d8f36e0084c3b","ASOCS.BLIND.c5b46b7db1bd2110b2b98c7b",
"ASOCS.BLIND.539a860dab8f502cd93cad0f","ASOCS.BLIND.770ac4e6a4cffeb24b38dc3d",
"ASOCS.BLIND.c806f636d7e145093324e254","ASOCS.BLIND.6693a6a9f42409f28e5af384",
"ASOCS.BLIND.bd0368cea8222d7e4803bedd","ASOCS.BLIND.cdb4dcea08349fd47ba5dd4b",
"ASOCS.BLIND.eda8205f083aeccdd329b0eb","ASOCS.BLIND.7f651c59741204ac3cf210bc",
"ASOCS.BLIND.9b251b8cfedc5e9a61396830","ASOCS.BLIND.32819f869b3c3b07dd7f1e2f",
"ASOCS.BLIND.52bfd1e5b5ac49076e79857b","ASOCS.BLIND.02b2078de685b0c1dca5553d",
"ASOCS.BLIND.cd6ce56499538e84b15d00a3","ASOCS.BLIND.df8018099acd005f8c7a46ed",
"ASOCS.BLIND.d95379bbf26c667d05db8cd3",
]
EXPECTED_BLIND_HASHES = [
"ea8ee31882b0e2407232a678819af3fa51866585eda55369c3ded4e9b6ded690",
"4389355b06701978a11659d38d9a5d4f067b4b72b57709724a61d58740fb923b",
"21ef3c6395dbd511e09832babd38d85b0a73d42aca95a3795a20bf9e7d7b93fd",
"3c80631eb92b77824dac23ef4979bdad77bde8e2585670a04eac929bed0ec624",
"86cfc195f5860169e7f01fd6d9881498ee7c3282c116cebcf5603e58e4ceac96",
"c97abb0daf56e5b67721124b7f5a9495b8257bffb630ccb7de1c3db08427d438",
"1fa92b3bcb1b7b0fd004111d9ca7d07a26efa46021dbeff1d6f0c818a5d6faac",
"d528b6deb76661e53f515336411f9d785629edceefef9615a2250e622250ea4e",
"6e580a5ff7d67081d9755572981cd0f09482968052f0db7a8ca521d1c5b87adb",
"331f64eed703e04a64c602e9149564d297001be5da6480dd030c3874759ed0b5",
"643b652ac2c8e8686e75b84002f07792a4ed41895b9a89065f2ed5a9b02c79ec",
"f4f35d4fb61a59f20c31de5035c42a3d58030bbdce3b5173df20931ef5ee5ab1",
"4c2d12104ab0cecb492309616a3a910bee5d91cc039b59118638116dec8f60ab",
"af0fb3d354f7d6f24d7716d4e628b158ff10b2d8f0096475e11654b5fdf6f74f",
"9db9f25e00ac8a7dce8d55263103cad92e040288950a57fd59c1f8f0fdd6c4fb",
"f0f857c8286b3c5f78081ba34fafdb6927d484a22aec9ac1471009c2f8b8fd74",
"16cb9b0158dc73b1a7a17a29b23700279320b71e8a82c646c8e846cb8463638c",
"7341c70da163f63da13bab126391f7104f1646daa18226605583015d95ec002c",
"50abdff2c7f49301f1a7e676ab9440cb1b754a977887a38672476462550f3785",
"bc33465d25a893bd7b9fc8024ca41eb97de0eeebed0dc9901107a817bdec15d2",
"d7b3f2ff3150bcc55d768f30d77b7cec9a796bcde50b672f84ccb144f1cf2d1e",
"0a3816d8ff49027e0bc646cfdc778a9eb6103b9bdc471b1e70bf38c876ddd295",
"b59eed91abe1b220778ee16605b8e070e62d8dfafacf7aeee4dd836de7cc4b86",
"a9791c574b639fb53eee0e5f176d9c59db63af78f0bbd545010f95f13469d9cb",
"d0735edf0fe86db410073b21f6a1c59c91e90ccaae4e16b7115eadf65f1b6036",
]

def _j(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def _cid(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

def test_preparation_preserves_current_g6_operator_pass_across_later_stage1_interface() -> None:
    g6 = _j(G6_STATE)
    assert g6["status"] == "APPROVED"
    assert g6["gate_id"] == "ASOCSI-G6-PROVENANCE-SUPERSESSION"
    assert g6["authority_required"] == "SATISFIED_OPERATOR_PASS"
    assert g6["preserved"]["wp8_g3_reproduction_block"] is True
    assert g6["preserved"]["unrecoverable_provenance_warning"] is True

    pointer = _j(POINTER)
    state = _j(ROOT / pointer["current_state"])
    assert pointer["status"] == state["status"]
    assert state["gate_id"] == "ASOCSI-G6-PROVENANCE-SUPERSESSION"
    assert state["authority_required"] == "SATISFIED_OPERATOR_PASS"
    assert pointer["next_packet"] == "ASOCSI-WP8-STAGE1-HUMAN-FIDELITY-ADJUDICATION"
    assert state["preserved"]["wp8_g3_reproduction_block"] is True
    assert state["preserved"]["unrecoverable_provenance_warning"] is True
    assert state.get("human_adjudication_started", False) is False
    assert state.get("stage2_reveal_started", False) is False

def test_session1_pack_is_exact_locked_prefix_and_stage1_only() -> None:
    pack = _j(WP8 / "ASOCSI_WP8_STAGE1_SESSION_01_REVEAL_PACK_v0_1.json")
    assert pack["status"] == "REVEAL_PREPARED_NOT_YET_HUMAN_FROZEN"
    assert pack["stage"] == "SOURCE_C1_FIDELITY"
    assert len(pack["cases"]) == 25
    assert [c["case_id"] for c in pack["cases"]] == EXPECTED_CASES
    assert [c["blind_sha256"] for c in pack["cases"]] == EXPECTED_BLIND_HASHES
    assert pack["locked_session1_human_input_sha256"] == LOCKED_SESSION1
    assert pack["non_admitted_corrected_upload_sha256"] == NON_ADMITTED_CORRECTION
    assert pack["g1_audit_15m_sha256"] == G1_15M
    assert pack["g3_trace_artifact_sha256"] == G3_TRACES
    assert pack["g4_review_population_sha256"] == G4_POP
    assert pack["human_judgements"] == []
    assert pack["stage2_reveal_started"] is False
    assert "PROHIBITED" in pack["construct_survival_decision"]

def test_anchor_cases_bind_exact_source_and_frozen_c1_without_upper_stack_reveal() -> None:
    pack = _j(WP8 / "ASOCSI_WP8_STAGE1_SESSION_01_REVEAL_PACK_v0_1.json")
    anchors = [c for c in pack["cases"] if c["kind"] == "ANCHOR_15M"]
    gaps = [c for c in pack["cases"] if c["kind"] == "SOURCE_GAP"]
    assert len(anchors) == 24 and len(gaps) == 1
    assert pack["c1_formula_registry_id"] == "C1.FORMULAS.v0.1"
    assert pack["c1_implementation_id"] == "C1.IMPLEMENTATION.v0.2"
    assert pack["mechanical_arithmetic_check"] == "PASS_EXACT_FROZEN_TRACE_PAYLOAD_FOR_ANCHOR_CASES"
    for case in anchors:
        assert len(case["trace_sha256"]) == 64
        assert len(case["parents_sha256"]) == 64
        assert len(case["ohlc"]) == 4
    gap = gaps[0]
    assert gap["review_unit_id"].startswith("asocs:gap:")
    assert gap["repair_applied"] is False
    assert gap["c1_disposition"] == "C1_NOT_EVALUABLE_SOURCE"

def test_human_fidelity_is_not_formula_recalculation_and_freezes_before_stage2() -> None:
    prep = _j(WP8 / "ASOCSI_WP8_STAGE1_SESSION_01_PREPARATION_v0_1.json")
    assert prep["human_reviewer_does_not_recompute_formula_arithmetic"] is True
    assert prep["mechanical_checks"]
    assert len(prep["human_questions"]) == 4
    assert prep["freeze_rule"].endswith("BEFORE_ANY_C2_PRIMITIVE_REVEAL")
    assert prep["information_gap_rule"].startswith("EVALUATE_SOURCE_MEASUREMENT_ADEQUACY")
    assert prep["construct_survival_rule"].startswith("NO_CONSTRUCT_SURVIVAL_STATE")

def test_authority_frontier_and_schemas_remain_bounded() -> None:
    authority = _j(WP8 / "ASOCSI_WP8_STAGE1_AUTHORITY_MANIFEST_v0_1.json")
    frontier = _j(WP8 / "ASOCSI_WP8_STAGE1_SESSION_01_DEPENDENCY_FRONTIER_v0_1.json")
    pack = _j(WP8 / "ASOCSI_WP8_STAGE1_SESSION_01_REVEAL_PACK_v0_1.json")
    assert authority["authority_delta"] == "NONE"
    assert authority["human_judgement_authority"] == "HUMAN_REVIEWER_ONLY_NO_AGENT_SYNTHESIS"
    assert "STAGE2_C2_PRIMITIVE_REVEAL_BEFORE_STAGE1_FREEZE" in authority["non_grants"]
    assert frontier["physical_main_binding"] == "LATE_ONLY"
    assert frontier["blocked_until_human_input"] == ["STAGE2_C2_PRIMITIVE_REVEAL"]
    assert pack["authority_manifest_id"] == _cid(authority)
    assert pack["dependency_frontier_id"] == _cid(frontier)
    j = _j(SCHEMAS / "asocs_stage1_fidelity_judgement_v0_1.schema.json")
    assert j["properties"]["construct_survival_decision"]["const"] == "PROHIBITED_DURING_CASE_REVIEW"
    assert set(j["properties"]["fidelity_disposition"]["enum"]) == {"PASS_FIDELITY","MATERIAL_MISMATCH","SOURCE_LIMITED","INDETERMINATE"}
    r = _j(SCHEMAS / "asocs_reveal_stage_record_v0_1.schema.json")
    assert r["properties"]["frozen_before_next_reveal"]["const"] is True
    f = _j(SCHEMAS / "asocs_failure_attribution_v0_1.schema.json")
    assert f["properties"]["information_gap_evaluated_first"]["const"] is True
