import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP1 = ROOT / "docs/programmes/lsiac-v0-1/rrscg-core-wp1"
STATE = ROOT / "records/research_operations/lsiac/LSIAC_PROGRAMME_STATE_v0_22.json"
WP0 = ROOT / "docs/programmes/lsiac-v0-1/rrscg-core-wp0-successor/RRSCG_CORE_WP0_SUCCESSOR_SOURCE_BINDING_MANIFEST_v0_1.json"
ARTIFACT_POLICY = ROOT / "artifacts/README.md"
EXPECTED_R2 = "5426cd9340c93a2aff0f5c8f3093f9db876647d1790aaa82da3e444a4f3029b5"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp1_distinguishes_exact_identity_from_execution_availability():
    wp0 = load(WP0)
    blocker = load(WP1 / "RRSCG_CORE_WP1_PREFLIGHT_AND_BLOCKER_v0_1.json")
    r2 = next(row for row in wp0["bindings"] if row["object"] == "RRSCG_R2_CONTINUATION_CONSTRAINT_KERNEL")
    assert r2["status"] == "BOUND_EXACT"
    assert r2["actual_sha256"] == EXPECTED_R2
    assert blocker["court_record_source_binding"]["expected_sha256"] == EXPECTED_R2
    assert blocker["execution_availability"]["state"] == "SOURCE_BYTES_UNAVAILABLE_AT_EXECUTION"
    assert blocker["preflight_disposition"] == "BLOCKED"


def test_wp1_fails_closed_without_reconstruction():
    blocker = load(WP1 / "RRSCG_CORE_WP1_PREFLIGHT_AND_BLOCKER_v0_1.json")
    qa = load(WP1 / "RRSCG_CORE_WP1_QA_v0_1.json")
    authority = load(WP1 / "RRSCG_CORE_WP1_AUTHORITY_MANIFEST_v0_1.json")
    assert blocker["no_reconstruction_rule"]["effect"] == "NO_R2_IMPLEMENTATION_WRITTEN"
    assert blocker["algorithm_implementation_written"] is False
    assert qa["qa_recommendation"] == "BLOCK"
    assert qa["algorithm_implementation_written"] is False
    assert "RECONSTRUCT_R2_FROM_SUMMARIES_OUTPUTS_OR_BEHAVIOUR" in authority["denied"]


def test_wp1_programme_state_is_blocked_not_deauthorised():
    state = load(STATE)
    assert state["status"] == "BLOCKED"
    assert state["implementation_allowed"] is True
    assert state["implementation_exercisable_now"] is False
    assert state["rrscg_persistent_accession_construction_allowed"] is True
    assert state["operator_decision_required_now"] is False
    assert state["algorithm_implementation_written"] is False
    assert state["blockers"][0]["required_sha256"] == EXPECTED_R2
    assert state["next_packet"] == "RRSCG-CORE-WP1-R2-KERNEL-CONFORMANCE-IMPLEMENTATION"


def test_external_artifact_policy_explains_why_git_is_not_source_bytes():
    policy = ARTIFACT_POLICY.read_text(encoding="utf-8")
    assert "duplicate engine ZIPs" in policy
    assert "ovc-replay-external-artifacts" in policy


def test_dependency_frontier_has_one_artifact_availability_blocker():
    frontier = load(WP1 / "RRSCG_CORE_WP1_DEPENDENCY_FRONTIER_v0_1.json")
    assert frontier["status"] == "BLOCKED"
    assert len(frontier["blocked"]) == 1
    assert frontier["blocked"][0]["id"] == "R2_EXACT_SOURCE_BYTES_EXECUTION_AVAILABILITY"
    assert frontier["blocked"][0]["required_sha256"] == EXPECTED_R2
