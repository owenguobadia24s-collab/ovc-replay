from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLOCKER_ID = "MTA-G0-BLOCK-002-CHECKS-PASS-RULESET-STILL-EXPECTED"


def load(relative: str) -> dict:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object:{relative}")
    return value


def main() -> int:
    required = [
        "docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_OPERATOR_DECISION.json",
        "docs/releases/market-translation-audit-v0-2/mta-g0/PD_JUNE_FM_G2_DISPOSITION_DECISION.json",
        "docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_QA_PACKET.json",
        "docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_GATE_PACKET.json",
        "docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_REQUIRED_CHECK_ENFORCEMENT_BLOCKER.json",
        "docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_MERGE_RECEIPT.json",
        "docs/releases/development-acceleration-v0-1/da-wp4b/main-ruleset.json",
        "registries/research_operations/mta/OVC_MTA_PROGRAMME_STATE_v0_2.json",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    assert not missing, missing

    state = load("registries/research_operations/mta/OVC_MTA_PROGRAMME_STATE_v0_2.json")
    gate = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_GATE_PACKET.json")
    qa = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_QA_PACKET.json")
    decision = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_OPERATOR_DECISION.json")
    disposition = load("docs/releases/market-translation-audit-v0-2/mta-g0/PD_JUNE_FM_G2_DISPOSITION_DECISION.json")
    blocker = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_REQUIRED_CHECK_ENFORCEMENT_BLOCKER.json")
    receipt = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_MERGE_RECEIPT.json")

    assert decision["operator_command"] == "OVC APPROVE MTA-G0 PASS"
    assert decision["decision"] == gate["decision"] == "PASS"
    assert decision["decision_authority"] == "OPERATOR"
    assert decision["downstream_authority_created"] is False
    assert disposition["decision"] == "DEFER"
    assert disposition["review_outcome"] == "NONE"
    assert disposition["pull_request_202_disposition"] == "PRESERVE_OPEN_UNMERGED"

    # The original external-enforcement blocker remains immutable historical evidence.
    assert blocker["blocker_id"] == BLOCKER_ID
    assert blocker["status"] == "BLOCKED_EXTERNAL_REPOSITORY_RULESET_ENFORCEMENT"
    assert len(blocker["passing_assurance"]) == 2
    assert all(item["mta_workflow"]["result"] == "PASS" for item in blocker["passing_assurance"])
    assert all(item["tests"]["result"] == "PASS" for item in blocker["passing_assurance"])
    assert all(item["tiered"]["result"] == "PASS" for item in blocker["passing_assurance"])

    # The later merge receipt resolves continuation without editing the blocker record.
    assert receipt["decision"] == "COMPLETED"
    assert receipt["merge_method"] == "SQUASH"
    assert receipt["merge_commit"] == "eacf7a71e6242ee9adf5206b5e21e7ed66e1d85d"
    assert receipt["transport_history"]["final_pull_request"] == 219
    assert receipt["transport_history"]["final_head_sha"] == "da6e33f67a5b978e57c3ff99e35b29335823115f"
    contexts = [item["context"] for item in receipt["required_checks"]]
    assert contexts == ["tests", "OVC tiered test selection shadow", "Market Translation Audit MTA-G0 gate readiness"]
    assert all(item["result"] == "PASS" for item in receipt["required_checks"])

    packet0 = next(item for item in state["packets"] if item["packet_id"] == "MTA-00")
    assert packet0["status"] == "COMPLETED"
    assert packet0["merge_commit"] == receipt["merge_commit"]
    assert packet0["blockers"] == []
    assert state["programme_status"] in {"READY", "RUNNING", "IMPLEMENTED", "QA_REVIEW", "GATE_READY", "APPROVED", "COMPLETED"}
    assert state["current_packet"] != "MTA-00"
    assert state["authority"]["selectors"] == "UNCHANGED"
    assert state["authority"]["formula_threshold_reset_clock"] == "UNCHANGED"
    assert state["authority"]["c2e_c2_5_c3"] == "DENIED"
    assert state["authority"]["validation"] == "LOCKED_UNCONSUMED"

    ruleset = load("docs/releases/development-acceleration-v0-1/da-wp4b/main-ruleset.json")
    ruleset_path = ROOT / "docs/releases/development-acceleration-v0-1/da-wp4b/main-ruleset.json"
    digest = hashlib.sha256(ruleset_path.read_bytes()).hexdigest()
    assert digest == blocker["ruleset"]["sha256"]
    required_rule = next(rule for rule in ruleset["rules"] if rule["type"] == "required_status_checks")
    required_contexts = [entry["context"] for entry in required_rule["parameters"]["required_status_checks"]]
    assert required_contexts == ["tests", "OVC tiered test selection shadow"]
    assert ruleset["bypass_actors"] == []
    assert ruleset["current_user_can_bypass"] == "never"

    # Historical gate/QA packets retain their pre-merge status and are superseded by the receipt.
    assert gate["status"] == "APPROVED_MERGE_BLOCKED_EXTERNAL_RULESET_ENFORCEMENT"
    assert gate["unresolved_issues"] == [BLOCKER_ID]
    assert qa["recommendation"] == "PASS_MERGE_BLOCKED_EXTERNAL_RULESET_ENFORCEMENT"

    print("MTA-G0 completed-merge retention validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
