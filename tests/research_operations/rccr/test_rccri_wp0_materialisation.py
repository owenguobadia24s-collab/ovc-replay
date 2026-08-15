import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


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


def test_wp0_reviewer_binding_does_not_fake_independent_pass():
    reviewers = load("docs/releases/rccr-v0-1/rccri-wp0/RCCRI_REVIEWER_BINDINGS.json")
    assert reviewers["no_self_review"] is True
    assert all(item["decision"] == "PENDING" for item in reviewers["bindings"])
    assert reviewers["implementation_author"] != reviewers["bindings"][0]["reviewer_identity"]


def test_wp0_programme_state_is_not_prematurely_completed():
    state = load("registries/implementation/rccr_v0_1/RCCR_V0_1_STATE_v0_1.json")
    pointer = load("registries/implementation/rccr_v0_1/CURRENT_STATE_POINTER.json")
    assert state["status"] == "QA_REVIEW"
    assert pointer["status"] == "QA_REVIEW"
    assert state["merge_commit"] is None
    assert state["next_operator_gate"] == "RCCRI-G-PILOT-EXIT"
    assert state["blockers"] == []
    assert "RCCRI-WP0-BLOCK-001" in state["resolved_blockers"]


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
