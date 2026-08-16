import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET_SEQUENCE = (
    "RCCRI-WP0",
    "RCCRI-WP1",
    "RCCRI-WP2",
    "RCCRI-WP3",
    "RCCRI-WP4",
    "RCCRI-WP5",
    "RCCRI-WP6A",
    "RCCRI-WP7A",
    "RCCRI-WP6B",
    "RCCRI-WP7B",
    "RCCRI-WP8",
)


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def packet_ordinal(packet_id):
    assert packet_id in PACKET_SEQUENCE
    return PACKET_SEQUENCE.index(packet_id)


def test_wp0_exact_plan_and_design_bindings():
    binding = load("docs/plans/rccr-v0-1/RCCRI_WP0_PLAN_BINDING.json")
    assert binding["implementation_plan"]["sha256"] == "13d065d09eb012980a076e84667d674452659c79d92d0ab2a3b53a66477e1a6e"
    assert binding["governing_design"]["sha256"] == "16f3b52a790bd6fa4d144d29065087b733a6fd4cb2162963a623090f030e9ee3"
    assert binding["real_source_ec1_authority"] == "NONE"
    assert binding["validation"] == "LOCKED_UNCONSUMED"


def test_wp0_authority_is_bounded_and_scaleout_denied():
    auth = load("docs/releases/rccr-v0-1/rccri-wp0/RCCRI_WP0_AUTHORITY_CROSSWALK.json")
    denied = set(auth["denied"])
    assert "REAL_SOURCE_EC1" in denied
    assert "PATH2_PREREGISTRATION_OR_EXECUTION" in denied
    assert "DEVELOPMENT_VALIDATION_CONSUMPTION" in denied
    assert "PILOT_SCALEOUT_BEFORE_RCCRI-G-PILOT-EXIT" in denied
    assert auth["next_operator_gate"] == "RCCRI-G-PILOT-EXIT"


def test_wp0_preserves_orthogonal_c2p_state_and_ec1_gate():
    census = load("docs/releases/rccr-v0-1/rccri-wp0/RCCRI_WP0_OWNER_SOURCE_CENSUS.json")
    assert census["c2p"]["implementation"] == "YES"
    assert census["c2p"]["active_stack_classification"] == "NON_EVALUABLE"
    assert census["ec1"]["gate"] == "DMRPI-GREAL-EC1"
    assert census["ec1"]["real_source_authority"] == "NONE"
    assert census["authority_discrepancy"] == "NONE_OBSERVED"


def test_wp0_reviewer_binding_requires_real_independent_decision_evidence():
    reviewers = load("docs/releases/rccr-v0-1/rccri-wp0/RCCRI_REVIEWER_BINDINGS.json")
    assert reviewers["no_self_review"] is True
    by_gate = {item["gate"]: item for item in reviewers["bindings"]}
    assert set(by_gate) == {"RCCRI-G4-ALG", "RCCRI-G-ADVERSARIAL-REVIEW"}
    for item in by_gate.values():
        assert reviewers["implementation_author"] != item["reviewer_identity"]

    g4_alg = by_gate["RCCRI-G4-ALG"]
    assert g4_alg["reviewer_identity"] == "OVC_HUMAN_OPERATOR"
    assert g4_alg["reviewer_class"] == "INDEPENDENT_REVIEWER"
    assert g4_alg["decision"] in {"PENDING", "PASS"}
    if g4_alg["decision"] == "PASS":
        assert g4_alg["decision_ref"] == "docs/releases/rccr-v0-1/rccri-wp4/RCCRI_G4_ALG_OPERATOR_DECISION.json"
        decision = load(g4_alg["decision_ref"])
        assert decision["decision"] == "PASS"
        assert decision["decided_by"] == g4_alg["reviewer_identity"]
        assert decision["reviewer_class"] == g4_alg["reviewer_class"]
        assert decision["decision_instruction"] == "OVC APPROVE RCCRI-G4-ALG"
        assert decision["authority_effect"] == "NONE"

    adversarial = by_gate["RCCRI-G-ADVERSARIAL-REVIEW"]
    assert adversarial["decision"] in {"PENDING", "PASS"}
    assert adversarial["reviewer_identity"] == "OVC_HUMAN_OPERATOR"
    assert adversarial["reviewer_class"] == "INDEPENDENT_OUTSIDE_RCCR_IMPLEMENTATION"
    if adversarial["decision"] == "PASS":
        expected_ref = "docs/releases/rccr-v0-1/rccri-g-adversarial-review/RCCRI_G_ADVERSARIAL_REVIEW_OPERATOR_DECISION.json"
        assert adversarial["decision_ref"] == expected_ref
        decision = load(expected_ref)
        assert decision["decision"] == "PASS"
        assert decision["decided_by"] == adversarial["reviewer_identity"]
        assert decision["reviewer_class"] == adversarial["reviewer_class"]
        assert decision["decision_instruction"] == "OVC APPROVE RCCRI-G-ADVERSARIAL-REVIEW"
        assert decision["authority_effect"] == "NONE"
        assert decision["scaleout_authority"] == "DENIED"
        assert decision["real_source_ec1_authority"] == "NONE"
        assert decision["validation"] == "LOCKED_UNCONSUMED"


def test_wp0_programme_state_is_approved_and_successor_pointer_advances_lawfully():
    state = load("registries/implementation/rccr_v0_1/RCCR_V0_1_STATE_v0_1.json")
    pointer = load("registries/implementation/rccr_v0_1/CURRENT_STATE_POINTER.json")
    assert state["status"] == "APPROVED"
    assert state["merge_commit"] is None
    assert state["integration_condition"] == "FINAL_EVIDENCE_ONLY_HEAD_REQUIRED_CHECKS_PASS"
    assert state["next_operator_gate"] == "RCCRI-G-PILOT-EXIT"
    assert state["blockers"] == []
    assert "RCCRI-WP0-BLOCK-001" in state["resolved_blockers"]
    if pointer["current_packet"] == "RCCRI-WP0":
        assert pointer["status"] == "APPROVED"
        assert pointer["gate_status"] == "PASS_DELEGATED_PENDING_FINAL_HEAD_INTEGRATION"
    else:
        current_ordinal = packet_ordinal(pointer["current_packet"])
        completed_ordinal = packet_ordinal(pointer["last_completed_packet"])
        assert current_ordinal > 0
        if completed_ordinal == current_ordinal:
            assert packet_ordinal(pointer["next_packet"]) == current_ordinal + 1
            if pointer["status"] == "GATE_READY":
                assert pointer["operator_pending"]
                assert pointer["current_gate"] in pointer["operator_pending"]
            else:
                assert pointer["status"] == "APPROVED"
                assert pointer["operator_pending"] == []
                assert pointer["gate_status"].startswith("PASS_")
                assert pointer["next_operator_gate"] == "RCCRI-G-PILOT-EXIT"
                assert pointer["scaleout_authority"] == "DENIED"
        else:
            assert completed_ordinal == current_ordinal - 1
        assert pointer["last_merge_commit"]
        assert pointer["next_packet"] != "RCCRI-WP0"
        assert "RCCRI-WP0-BLOCK-001" in pointer["resolved_blockers"]


def test_wp0_pr_929_provenance_is_integrated_without_authority_expansion():
    census = load("docs/releases/rccr-v0-1/rccri-wp0/RCCRI_WP0_OWNER_SOURCE_CENSUS.json")
    pr = census["reconciled_relevant_prs"][0]
    assert pr["pr"] == 929
    assert pr["state"] == "MERGED"
    assert pr["merge_commit"] == "89d0628efbda9588f4ae1c5d7d632424e8c10be3"
    assert pr["authority_effect"] == "NONE"


def test_wp0_prior_blocker_is_resolved_not_erased():
    blocker = load("docs/releases/rccr-v0-1/rccri-wp0/RCCRI_WP0_BLOCKER.json")
    assert blocker["status"] == "RESOLVED_UPSTREAM"
    assert blocker["resolution"]["pr"] == 929
    assert blocker["resolution"]["merge_commit"] == "89d0628efbda9588f4ae1c5d7d632424e8c10be3"
