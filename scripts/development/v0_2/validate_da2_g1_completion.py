#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs/releases/development-acceleration-v0-2/da2-wp1"
RAW = BASE / "DA2_G1_RULESET_AFTER.json"
VERIFY = BASE / "DA2_G1_RULESET_VERIFICATION.json"
QA = BASE / "DA2_G1_COMPLETION_QA.json"
DECISION = BASE / "DA2_G1_COMPLETION_DECISION.json"
INCIDENT = BASE / "DA2_G1_ASSEMBLY_INCIDENT.json"
PROGRAMME = ROOT / "registries/development/v0_2/OVC_DEVELOPMENT_ACCELERATION_V0_2_PROGRAMME_REGISTRY_v0_1.json"
EXPECTED_RAW_SHA256 = "e346492b2e8f3df93f2801e4f69d9b7be04798652d00edee0ec18c5c184f306d"

def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    assert isinstance(value, dict)
    return value

def main() -> int:
    for path in (RAW, VERIFY, QA, DECISION, INCIDENT, PROGRAMME):
        assert path.is_file(), path
    assert hashlib.sha256(RAW.read_bytes()).hexdigest() == EXPECTED_RAW_SHA256
    raw = load(RAW)
    assert raw["id"] == 20229411
    assert raw["name"] == "OVC main protection"
    assert raw["target"] == "branch"
    assert raw["enforcement"] == "active"
    assert raw["bypass_actors"] == []
    assert raw["current_user_can_bypass"] == "never"
    types = {rule["type"] for rule in raw["rules"]}
    assert {"deletion", "non_fast_forward", "pull_request", "required_status_checks"} <= types
    pull = next(rule for rule in raw["rules"] if rule["type"] == "pull_request")["parameters"]
    assert pull["required_review_thread_resolution"] is True
    assert pull["allowed_merge_methods"] == ["squash"]
    status = next(rule for rule in raw["rules"] if rule["type"] == "required_status_checks")["parameters"]
    assert status["strict_required_status_checks_policy"] is True
    assert status["required_status_checks"] == [{"context": "OVC merge readiness", "integration_id": 15368}]
    verify = load(VERIFY)
    assert verify["evidence_sha256"] == EXPECTED_RAW_SHA256
    assert verify["result"] == "PASS"
    assert verify["blocking_issues"] == []
    qa = load(QA)
    assert qa["status"] == "PASS"
    assert qa["qa_recommendation"] == "PASS"
    assert qa["blocking_issues"] == []
    decision = load(DECISION)
    assert decision["decision"] == "PASS"
    assert decision["operator_decision_id"] == "DA2-G1.OPERATOR.PASS.20260803T100600+0100"
    assert decision["new_authority_outside_operator_approval"] == "NONE"
    incident = load(INCIDENT)
    assert incident["disposition"] == "SUPERSEDED_PRESERVED"
    assert incident["merge_authority"] == "DENIED"
    programme = load(PROGRAMME)
    assert programme["status"] in {"APPROVED", "COMPLETED"}
    if programme["status"] == "APPROVED":
        assert programme["current_packet"]["blockers"] == []
    else:
        assert programme["current_packet"] is None
    print("DA2-G1 completion validation PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
