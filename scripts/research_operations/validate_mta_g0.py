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
    "docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_RULESET_MERGE_BLOCKER.json",
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
    request = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_OPERATOR_DECISION_REQUEST.json")
    decision = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_OPERATOR_DECISION.json")
    disposition_request = load("docs/releases/market-translation-audit-v0-2/mta-g0/PD_JUNE_FM_G2_DISPOSITION_DECISION_REQUEST.json")
    disposition = load("docs/releases/market-translation-audit-v0-2/mta-g0/PD_JUNE_FM_G2_DISPOSITION_DECISION.json")
    blocker = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_RULESET_MERGE_BLOCKER.json")
    fixtures = load("fixtures/research_operations/mta/MTA_G0_CAPACITY_FIXTURES_v0_1.json")

    assert state["programme_id"] == gate["programme_id"] == decision["programme_id"] == blocker["programme_id"] == "OVC-MTA-v0.2"
    assert state["baseline_commit"] == baseline["repository"]["baseline_commit"] == gate["baseline_commit"] == blocker["baseline_main"]
    assert state["programme_status"] == "BLOCKED"
    assert state["operator_decision_required"] is False
    assert state["operator_gate"]["status"] == "APPROVED_MERGE_BLOCKED_EXTERNAL_RULESET"
    assert state["operator_gate"]["recorded_decision"] == "PASS"
    assert state["packets"][0]["status"] == "BLOCKED"
    assert blocker["blocker_id"] in state["packets"][0]["blockers"]
    assert gate["status"] == "APPROVED_MERGE_BLOCKED_EXTERNAL_RULESET"
    assert gate["decision"] == "PASS"
    assert qa["technical_recommendation"] == "PASS"
    assert qa["merge_recommendation"] == "BLOCK_UNTIL_REQUIRED_CHECK_CONTEXTS_REPRODUCIBLE"
    assert blocker["blocker_id"] in qa["unresolved_issues"]

    assert request["exact_command"] == decision["operator_command"] == "OVC APPROVE MTA-G0 PASS"
    assert decision["decision"] == "PASS"
    assert decision["decision_authority"] == "OPERATOR"
    assert decision["approved_authority_delta"] == gate["approved_authority_delta"]
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

    assert blocker["status"] == "BLOCKED_EXTERNAL_REPOSITORY_RULESET"
    assert blocker["blocked_head"] == state["tested_candidate_commit"] == gate["tested_candidate_commit"]
    assert blocker["main_unchanged_at_block"] is True
    assert blocker["merge_attempt"]["result"] == "HTTP_405_REPOSITORY_RULE_VIOLATION"
    assert blocker["merge_attempt"]["message"] == "2 of 2 required status checks are expected"
    assert len(blocker["passing_final_head_checks"]) == 3
    assert all(check["result"] == "PASS" for check in blocker["passing_final_head_checks"])
    assert blocker["review_state"] == {"unresolved_review_threads": 0, "blocking_review_submissions": 0}
    assert "MERGE_WITH_EXPECTED_CHECKS_UNSATISFIED" in blocker["prohibited_resolutions"]
    assert blocker["continuation_point"] == "MTA-G0_SQUASH_MERGE_THEN_MTA-WP1"

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

    digest = hashlib.sha256((ROOT / REQUIRED[0]).read_bytes()).hexdigest()
    assert len(digest) == 64
    print("MTA-G0 approved decision and external merge blocker validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
