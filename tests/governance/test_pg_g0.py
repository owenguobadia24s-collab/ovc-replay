import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "registries/governance/programme_genesis/OVC_PG_PROGRAMME_STATE_v0_2.json"
BASELINE_PATH = ROOT / "docs/releases/programme-genesis-v0-2/pg-g0/PG_G0_BASELINE_MANIFEST.json"
QA_PATH = ROOT / "docs/releases/programme-genesis-v0-2/pg-g0/PG_G0_QA_PACKET.json"
MAINTENANCE_PATH = ROOT / "registries/governance/programme_genesis/MAINTENANCE_AUTHORITY_REGISTRY_v0_1.json"
SYNC_PATH = ROOT / "contracts/governance/programme_genesis/STATE_SYNCHRONISATION_CONTRACT_v0_1.md"
PLAN_PATH = ROOT / "docs/plans/governance/OVC_Programme_Genesis_Portfolio_Ledger_and_Dependency_Graph_v0_2_REVISED_Implementation_Plan.md"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_pg_g0_packet_is_operator_gated_and_non_market() -> None:
    state = load_json(STATE_PATH)

    assert state["programme_id"] == "OVC-PG-v0.2"
    assert state["plan_version"] == "0.2"
    assert state["status"] == "GATE_READY"
    assert state["current_packet"] == "PG-00"
    assert state["current_gate"] == "PG-G0"
    assert state["operator_decision_required"] is True
    assert state["next_action"] == "OPERATOR_DECIDE_PG_G0"

    authority = state["authority"]
    assert authority["programme_governance_build"] == "DENIED_PENDING_PG_G0"
    assert authority["portfolio_migration"] == "DENIED_PENDING_PG_G3A"
    assert authority["admission_enforcement"] == "DENIED_PENDING_PG_G6"
    assert authority["automatic_upkeep"] == "DENIED_PENDING_PG_G7"
    assert authority["market_model_selector_release_validation"] == "NONE"
    assert authority["agent_probability_risk_exposure_execution"] == "NONE"


def test_pg_mandatory_operator_stops_are_preserved() -> None:
    state = load_json(STATE_PATH)
    assert state["mandatory_operator_gates"] == ["PG-G0", "PG-G3A", "PG-G6", "PG-G7"]

    packets = {packet["packet_id"]: packet for packet in state["packets"]}
    assert packets["PG-WP3"]["next_packet"] == "PG-G3A"
    assert packets["PG-G3A"]["authority_required"] == "OPERATOR_REQUIRED_ACKNOWLEDGEMENT"
    assert packets["PG-WP4"]["prerequisites"] == ["PG-G3A_ACKNOWLEDGE_CONTINUE_MERGED"]
    assert packets["PG-G6"]["authority_required"] == "OPERATOR_REQUIRED_FOUR_PART_DECISION"
    assert packets["PG-WP6"]["authority_required"] == "OPERATOR_REQUIRED_AT_PG_G7"


def test_pg_g0_baseline_and_source_identity_are_pinned() -> None:
    baseline = load_json(BASELINE_PATH)

    assert baseline["baseline_commit"] == "5fb26ce08ff1a386f76bc8c6784350ab6fddcfb7"
    assert baseline["candidate_branch"] == "gate/pg-g0-ratification"
    assert baseline["namespace_freeze"]["short_code"] == "PG"
    assert baseline["blockers"] == []

    plan_sources = {
        source["document_id"]: source
        for source in baseline["governing_source_documents"]
    }
    pg_source = plan_sources["OVC-PG-IMPLEMENTATION-PLAN-0.2"]
    assert pg_source["external_identity"] == "file_00000000a0e4822f8ed73a5903ded4d7"
    assert pg_source["repository_path"] == str(PLAN_PATH.relative_to(ROOT)).replace("\\", "/")


def test_maintenance_registry_fails_closed_and_denies_reserved_authority() -> None:
    registry = load_json(MAINTENANCE_PATH)

    assert registry["status"] == "PROPOSED_PENDING_PG_G0"
    assert registry["default_outcome"] == "NOT_EVALUABLE_REQUIRES_SCOPE_REVIEW"
    assert registry["decision_gate"] == "PG-G0"
    assert registry["activation_gate"] == "PG-G6"
    assert len(registry["entries"]) >= 5

    denials = set(registry["reserved_authority_denials"])
    assert {
        "SELECTOR_ACTIVATION",
        "ACTIVE_DISCOVERY",
        "ACTIVE_DEVELOPMENT",
        "ACTIVE_VALIDATION",
        "CANONICAL_OR_R2_PUBLICATION",
        "AGENT_WRITE",
        "PROBABILITY_RISK_EXPOSURE_EXECUTION",
    }.issubset(denials)


def test_state_synchronisation_preserves_source_authority() -> None:
    contract = SYNC_PATH.read_text(encoding="utf-8")
    assert "programme-owned machine-readable state" in contract
    assert "STATE_SOURCE_CONFLICT" in contract
    assert "STALE_PROJECTION" in contract
    assert "PG never repairs a programme-owned source file" in contract
    assert "Before `PG-G6`, all enforcement consumers remain disabled" in contract


def test_qa_packet_has_no_hidden_blocker_or_self_ratification() -> None:
    qa = load_json(QA_PATH)

    assert qa["status"] == "QA_REVIEW_PENDING_EXACT_HEAD_CI"
    assert qa["blockers"] == []
    assert qa["qa_recommendation"] == "PASS_IF_EXACT_HEAD_REQUIRED_CHECKS_PASS"
    assert qa["authority_delta"] == "NONE_UNTIL_OPERATOR_PG_G0_PASS"

    checks = {check["check_id"]: check for check in qa["checks"]}
    assert checks["PG-G0-MANDATORY-OPERATOR-STOPS"]["status"] == "PASS"
    assert checks["PG-G0-FOCUSED-TEST"]["status"] == "PENDING_CI"
    assert checks["PG-G0-REPOSITORY-SUITE"]["status"] == "PENDING_CI"
