import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs/programmes/sff-v0-1/wp9/org1"


def load(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def test_org1_r4_r6_fresh_closeout_is_fail_closed_indeterminate():
    r4 = load("ORG1_R4_EVAL_A_RESULT_v0_1.json")
    r5 = load("ORG1_R5_EVAL_B_RESULT_v0_1.json")
    r6 = load("ORG1_R6_FROZEN_ADJUDICATION_v0_1.json")
    qa = load("ORG1_R4_R5_FRESH_SCORING_QA_v0_1.json")
    binding = load("ORG1_R4_R6_FRESH_RESULT_BINDING_v0_1.json")

    for r in (r4, r5):
        assert r["decision"] == "INDETERMINATE_BLOCK_SUPPORT"
        assert r["metrics"]["mean_deltas"]["delta_B1_minus_M4"] > 0
        assert r["metrics"]["primary_ci95"] is None
        assert r["metrics"]["bootstrap_support"]["status"] == "NOT_EVALUABLE_INSUFFICIENT_LAWFUL_BLOCK_SUPPORT"
        assert r["metrics"]["bootstrap_support"]["scored_origins_in_ge_32_segments"] == 0

    assert r6["primary_c1"]["disposition"] == "INDETERMINATE_SUPPORT_POPULATION_OR_INTEGRITY_UNAVAILABLE"
    assert r6["primary_c1"]["confirmation_pass"] is False
    assert r6["same_generation_rescue"] == "PROHIBITED"
    assert qa["status"] == "PASS_MECHANICAL_WITH_PRIMARY_SUPPORT_INDETERMINATE"
    assert qa["pass_count"] == qa["check_count"] == 21
    assert qa["model_retuning"] is False
    assert qa["population_substitution"] is False

    assert binding["frozen_inputs"]["model_set_sha256"] == "b139d57331830bad0d9ded1296c4fa20477bfbd0566da86b72aa9b160c6e2a29"
    assert binding["frozen_inputs"]["eval_population_freeze_sha256"] == "a895753a34af70f50d4b95e6ae87787121d9f0133823faa45e750e8c81aa56ca"
    assert binding["laboratory"]["bundle_sha256"] == "736a7c20e6470dc3f8650e6cabd50cff8b47d8b7519551fc5d7b898f6ef847f1"
    assert binding["same_generation_rescue"] == "PROHIBITED"
    assert binding["validation_state"] == "LOCKED_UNCONSUMED"


def test_sffi_programme_state_v0_4_closes_org1_without_promotion():
    state = json.loads((ROOT / "records/research_operations/sff/SFFI_PROGRAMME_STATE_v0_4.json").read_text(encoding="utf-8"))
    assert state["status"] == "ORG1_FRESH_STUDY_COMPLETE_PRIMARY_INDETERMINATE_BLOCK_SUPPORT"
    assert state["scientific_claim_status"] == "C1_INDETERMINATE_SUPPORT_POPULATION_OR_INTEGRITY_UNAVAILABLE"
    assert state["fresh_outcomes_accessed"] is True
    assert state["primary_confirmatory_ci_evaluable"] is False
    assert state["same_generation_rescue"] == "PROHIBITED"
    assert state["next_packet"] is None
    assert state["validation_state"] == "LOCKED_UNCONSUMED"
    assert state["model_promotion"] is False
    assert "CALIBRATED_PROBABILITY" in state["explicit_non_grants"]
    assert "TRADING" in state["explicit_non_grants"]
