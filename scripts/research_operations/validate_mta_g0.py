from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED = [
    "docs/plans/research_operations/OVC_Market_Translation_and_Option_Flow_Audit_Implementation_Plan_v0_2_REVISED.md",
    "contracts/research_operations/mta/OVC_MTA_PROGRAMME_CHARTER_v0_2.md",
    "contracts/research_operations/mta/OVC_MTA_AUTHORITY_CONTRACT_v0_2.md",
    "contracts/research_operations/mta/OVC_MTA_PERFORMANCE_AND_CAPACITY_CONTRACT_v0_1.md",
    "contracts/research_operations/mta/OVC_MTA_REGISTRY_AMENDMENT_PROTOCOL_v0_1.md",
    "contracts/research_operations/mta/OVC_MTA_RO4_INTEGRATION_CONTRACT_v0_1.md",
    "registries/research_operations/mta/OVC_MTA_CLUSTER_VARIANT_PROFILE_v0_1.yaml",
    "registries/research_operations/mta/OVC_MTA_PROGRAMME_STATE_v0_2.json",
    "docs/releases/market-translation-audit-v0-2/mta-00/OVC_MTA_BASELINE_MANIFEST_v0_2.json",
    "docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_OPERATOR_DECISION_REQUEST.json",
    "docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_OPERATOR_DECISION.json",
    "docs/releases/market-translation-audit-v0-2/mta-g0/PD_JUNE_FM_G2_DISPOSITION_DECISION_REQUEST.json",
    "docs/releases/market-translation-audit-v0-2/mta-g0/PD_JUNE_FM_G2_DISPOSITION_DECISION.json",
    "docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_QA_PACKET.json",
    "docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_GATE_PACKET.json",
    "docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_MERGE_ELIGIBILITY.json",
    "docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_RULESET_MERGE_BLOCKER.json",
    "docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_RULESET_MERGE_RESOLUTION.json",
    "docs/releases/development-acceleration-v0-1/da-wp4b/main-ruleset.json",
    "schemas/research_operations/mta/mta_programme_state_v0_2.schema.json",
    "schemas/research_operations/mta/mta_g0_operator_decision_v0_1.schema.json",
    "fixtures/research_operations/mta/MTA_G0_CAPACITY_FIXTURES_v0_1.json",
]


def load(relative: str) -> dict:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object:{relative}")
    return value


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    assert not missing, missing

    state = load("registries/research_operations/mta/OVC_MTA_PROGRAMME_STATE_v0_2.json")
    baseline = load("docs/releases/market-translation-audit-v0-2/mta-00/OVC_MTA_BASELINE_MANIFEST_v0_2.json")
    gate = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_GATE_PACKET.json")
    qa = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_QA_PACKET.json")
    eligibility = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_MERGE_ELIGIBILITY.json")
    request = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_OPERATOR_DECISION_REQUEST.json")
    decision = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_OPERATOR_DECISION.json")
    disposition_request = load("docs/releases/market-translation-audit-v0-2/mta-g0/PD_JUNE_FM_G2_DISPOSITION_DECISION_REQUEST.json")
    disposition = load("docs/releases/market-translation-audit-v0-2/mta-g0/PD_JUNE_FM_G2_DISPOSITION_DECISION.json")
    blocker = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_RULESET_MERGE_BLOCKER.json")
    resolution = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_RULESET_MERGE_RESOLUTION.json")
    fixtures = load("fixtures/research_operations/mta/MTA_G0_CAPACITY_FIXTURES_v0_1.json")
    decision_schema = load("schemas/research_operations/mta/mta_g0_operator_decision_v0_1.schema.json")
    state_schema = load("schemas/research_operations/mta/mta_programme_state_v0_2.schema.json")

    plan_baseline = "d8a7f07f5abe376b917cf6f95f6e9ccc1864b7c3"
    branch_creation_base = "544dc2f6477ce415321f9419a62586fcffa0d02c"
    current_pr_base = "eaefbf55d1702d689d59765558af65e87c0b37fc"

    assert state["programme_id"] == gate["programme_id"] == decision["programme_id"] == "OVC-MTA-v0.2"
    assert state["plan_baseline_commit"] == baseline["repository"]["baseline_commit"] == decision["baseline_main_commit"] == plan_baseline
    assert state["branch_creation_base_commit"] == gate["branch_creation_base_commit"] == eligibility["branch_creation_base_main"] == resolution["branch_creation_base_main"] == branch_creation_base
    assert state["baseline_commit"] == gate["baseline_commit"] == eligibility["base_main"] == resolution["current_pull_request_base_main"] == current_pr_base
    assert state["branch"] == gate["candidate_branch"] == eligibility["replacement_branch"] == resolution["replacement_branch"] == "gate/mta-g0-ratification-resume"
    assert state["pull_request"] == gate["candidate_pull_request"] == eligibility["replacement_pull_request"] == resolution["replacement_pull_request"] == 216
    assert state["operator_decision_required"] is False
    assert state["operator_gate"]["recorded_decision"] == "PASS"
    assert gate["decision"] == "PASS"
    assert gate["status"] == "APPROVED_PENDING_SQUASH_MERGE"
    assert state["programme_status"] == "APPROVED"
    assert qa["recommendation"] == "PASS"
    assert eligibility["status"] == "ELIGIBLE"
    assert not qa["unresolved_issues"]

    assert request["exact_command"] == decision["operator_command"] == "OVC APPROVE MTA-G0 PASS"
    assert decision["decision"] == "PASS"
    assert decision["decision_authority"] == "OPERATOR"
    assert decision["approved_authority_delta"] == gate["approved_authority_delta"]
    assert decision["authority_active"] is True
    assert decision["downstream_authority_created"] is False
    assert decision["subdecisions"]["june_blinded_review"] == "DEFER_NO_REVIEW_OUTCOME"
    assert decision["subdecisions"]["pr_202"] == "PRESERVE_OPEN_UNMERGED"
    assert decision["subdecisions"]["capacity_contract"] == "APPROVE_4_HOURS_10GB"
    assert decision["subdecisions"]["cluster_variants"] == "APPROVE_EXACT_THREE_PRIMARY_PLUS_1"
    assert decision["subdecisions"]["acknowledgements"] == "REQUIRE_MTA_A3_AND_MTA_A6"

    assert disposition_request["recommended_decision"] == "DEFER"
    assert disposition["decision"] == "DEFER"
    assert disposition["review_outcome"] == "NONE"
    assert disposition["pull_request_202_disposition"] == "PRESERVE_OPEN_UNMERGED"
    assert "WHOLESALE_MERGE_PR_202" in disposition["prohibited"]

    assert blocker["status"] == "RESOLVED"
    assert blocker["resolution_record"].endswith("MTA_G0_RULESET_MERGE_RESOLUTION.json")
    assert resolution["resolution_result"] == "PASS_RULESET_REPRODUCIBLE_REQUIRED_CONTEXTS_IDENTIFIED"
    assert resolution["base_change_review"]["result"] == "PASS"
    assert resolution["base_change_review"]["conflicts"] == []

    ruleset_relative = resolution["resolution_source"]["ruleset_path"]
    ruleset_path = ROOT / ruleset_relative
    ruleset = json.loads(ruleset_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(ruleset_path.read_bytes()).hexdigest()
    assert digest == resolution["resolution_source"]["ruleset_sha256"]
    assert ruleset["id"] == resolution["resolution_source"]["ruleset_id"]
    assert ruleset["enforcement"] == "active"
    assert ruleset["bypass_actors"] == []
    assert ruleset["current_user_can_bypass"] == "never"
    required_rule = next(rule for rule in ruleset["rules"] if rule["type"] == "required_status_checks")
    contexts = [entry["context"] for entry in required_rule["parameters"]["required_status_checks"]]
    assert contexts == ["tests", "OVC tiered test selection shadow"]
    assert eligibility["required_status_checks"] == contexts

    cap = fixtures["valid"]
    assert cap["max_runtime_s"] == 14400
    assert cap["max_retained_bytes"] == 10737418240
    assert cap["checkpoint_before_pct"] == 75
    assert cap["shard_hierarchy"] == ["role", "clock", "side", "week"]

    profile = (ROOT / "registries/research_operations/mta/OVC_MTA_CLUSTER_VARIANT_PROFILE_v0_1.yaml").read_text(encoding="utf-8")
    for marker in ("STRICT_OVERLAP", "PRIMARY_OVERLAP_PLUS_1", "PERMISSIVE_OVERLAP_PLUS_4"):
        assert profile.count(marker) == 1, marker
    assert "parameter_search: PROHIBITED" in profile
    assert "primary_override_by_sensitivity: PROHIBITED" in profile

    authority = (ROOT / "contracts/research_operations/mta/OVC_MTA_AUTHORITY_CONTRACT_v0_2.md").read_text(encoding="utf-8")
    for denial in ("Validation", "C2E", "C2.5", "C3", "force-push"):
        assert denial in authority

    integration = (ROOT / "contracts/research_operations/mta/OVC_MTA_RO4_INTEGRATION_CONTRACT_v0_1.md").read_text(encoding="utf-8")
    assert "CROSS_PROGRAMME_INCONSISTENCY" in integration
    assert "separate analytical objects" in integration

    assert baseline["june_wp2"]["run_id"] == "PD-JUNE-FM.RUN.9810cfa8a2e2930be2e503b9"
    assert baseline["june_wp2"]["target"] == {"c1": 4526, "c2_states": 8598, "c2_transitions": 6783}
    assert baseline["june_wp3"]["eligible_windows"] == 7116
    assert baseline["june_wp2"]["not_evaluable_markers"] == 13993
    assert baseline["active_authority"]["validation"] == "LOCKED_UNCONSUMED"

    assert decision_schema["properties"]["authority_active"]["const"] is True
    assert decision_schema["properties"]["downstream_authority_created"]["const"] is False
    assert state_schema["properties"]["tested_candidate_commit"]["type"] == ["string", "null"]

    print("MTA-G0 resumed packet validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
