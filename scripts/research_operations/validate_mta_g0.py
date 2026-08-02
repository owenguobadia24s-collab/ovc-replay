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
    "docs/releases/market-translation-audit-v0-2/mta-g0/PD_JUNE_FM_G2_DISPOSITION_DECISION_REQUEST.json",
    "docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_QA_PACKET.json",
    "docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_GATE_PACKET.json",
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
    decision = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_OPERATOR_DECISION_REQUEST.json")
    disposition = load("docs/releases/market-translation-audit-v0-2/mta-g0/PD_JUNE_FM_G2_DISPOSITION_DECISION_REQUEST.json")
    fixtures = load("fixtures/research_operations/mta/MTA_G0_CAPACITY_FIXTURES_v0_1.json")

    assert state["programme_id"] == gate["programme_id"] == decision["programme_id"] == "OVC-MTA-v0.2"
    assert state["baseline_commit"] == baseline["repository"]["baseline_commit"] == gate["baseline_commit"]
    assert state["operator_decision_required"] is True
    assert state["operator_gate"]["status"] == "GATE_READY_OPERATOR_DECISION_REQUIRED"
    assert state["operator_gate"]["recorded_decision"] is None
    assert state["operator_gate"]["qa_recommendation"] == "PASS"
    assert gate["status"] == "GATE_READY_OPERATOR_DECISION_REQUIRED"
    assert gate["recommended_decision"] == "PASS"
    assert gate["qa"]["recommendation"] == "PASS"
    assert qa["status"] == "PASS_OPERATOR_DECISION_REQUIRED"
    assert qa["recommendation"] == "PASS"
    assert qa["unresolved_issues"] == ["MTA_G0_OPERATOR_DECISION_REQUIRED"]
    assert disposition["recommended_decision"] == "DEFER"
    assert disposition["review_outcome"] == "NONE"

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

    workflow_checks = {item["name"]: item for item in gate["tests"]}
    assert workflow_checks["MTA-G0 gate readiness"]["status"] == "PASS"
    assert workflow_checks["generic complete repository suite"]["status"] == "PASS"

    digest = hashlib.sha256((ROOT / REQUIRED[0]).read_bytes()).hexdigest()
    assert len(digest) == 64
    print("MTA-G0 validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
