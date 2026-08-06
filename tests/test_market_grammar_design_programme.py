import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs" / "releases" / "c2e-c2g-c2p-market-grammar-v0-1" / "mg-d0"


def load(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def test_shadow_evidence_lock_is_inactive_and_exact():
    lock = load("MG_D0_VERIFIED_SHADOW_EVIDENCE_LOCK.json")
    assert lock["status"] == "PASS"
    replay = lock["revised_c2_replay"]
    assert replay["binding_sha256"] == "126a703b89bfef8fc60a4beb1248b20b424621334c8fff254c122555e44663f8"
    assert replay["logical_population_sha256"] == "3f1089e3a4eefe94147c8c2f912e77899e4ed21fe8b3b8b85993e47bf7151ee7"
    assert replay["counts"]["requested"] == (
        replay["counts"]["computable"]
        + replay["counts"]["censored"]
        + replay["counts"]["not_evaluable"]
    )
    assert lock["integrated_shadow_closeout"]["active_c2"] == "UNCHANGED_READ_ONLY"
    assert "NO_MARKET_OR_ACTIVATION_AUTHORITY" in lock["authority_effect"]


def test_c2e_supersession_is_narrow_and_preserves_activation_denial():
    record = load("MG_D0_OPERATOR_SCOPE_AND_C2E_SUPERSESSION.json")
    assert record["supersedes_decision_id"] == "C2E-G1.OPERATOR.BLOCK.20260803T194600+0100"
    assert "C2E_ACTIVATION" in record["preserved_denials"]
    assert "C2E_AUTHORITATIVE_CONSUMPTION" in record["preserved_denials"]
    assert record["authority_effect"] == "LIMITED_IMMUTABLE_SUPERSESSION"


def test_design_freeze_has_no_reserved_delta():
    packet = load("MG_D8_DESIGN_FREEZE_PACKET.json")
    assert packet["precondition"] == "PASS"
    assert packet["qa_recommendation"] == "PASS"
    assert packet["reserved_authority_delta"] == "NONE"
    assert packet["contracts_maturity"] == "SHADOW_EXPERIMENT_MUTABLE_UNTIL_MG_WP8"


def test_implementation_registry_prohibits_reverse_and_outcome_dependencies():
    path = ROOT / "registries" / "opt_b" / "market_grammar" / "OVC_MARKET_GRAMMAR_IMPLEMENTATION_REGISTRY_v0_1.jsonc"
    registry = json.loads(path.read_text(encoding="utf-8"))
    prohibited = set(registry["forbidden_dependencies"])
    assert "C2E_READS_C2G" in prohibited
    assert "C2G_REWRITES_C2_OR_C2E" in prohibited
    assert "OUTCOME_INPUT_TO_C2E_C2G_C2P_CONSTRUCTION" in prohibited


def test_programme_state_has_terminal_operator_gate_only():
    path = ROOT / "registries" / "opt_b" / "market_grammar" / "OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc"
    state = json.loads(path.read_text(encoding="utf-8"))
    packets = {item["packet_id"]: item for item in state["packets"]}
    assert packets["MG-WP10"]["authority_required"] == "OPERATOR_REQUIRED"
    for i in range(10):
        assert packets[f"MG-WP{i}"]["authority_required"] == "AUTO_EXECUTABLE"
