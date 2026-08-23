from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "registries/development/skills/VIT_PHYSICAL_MAIN_EXCLUSIVITY_v0_1.json"
DECISION = ROOT / "docs/releases/development-skills-v0-3/vit-ruleset-compatibility/VIT_GITHUB_RULESET_LATE_BINDING_OPERATOR_DECISION_v0_1.json"
PAYLOAD = ROOT / "docs/releases/development-skills-v0-3/vit-ruleset-compatibility/VIT_GITHUB_RULESET_LATE_BINDING_UPDATE_PAYLOAD_v0_1.json"
CONTRACT = ROOT / "contracts/development/v0_5/OVC_VIT_ASSURANCE_DECOUPLING_MAIN_EXCLUSIVITY_CONTRACT_v0_1.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_operator_approved_only_native_strict_currentness_delta() -> None:
    decision = load(DECISION)
    assert decision["decision"] == "PASS"
    assert decision["operator_instruction"] == "OVC APPROVE"
    assert decision["approved_delta"] == {
        "ruleset_id": 20229411,
        "field": "required_status_checks.strict_required_status_checks_policy",
        "from": True,
        "to": False,
    }
    preserved = decision["preserved_exactly"]
    assert preserved["required_status_check"] == "OVC merge readiness"
    assert preserved["required_check_provider_integration_id"] == 15368
    assert preserved["pull_request_required"] is True
    assert preserved["allowed_merge_methods"] == ["squash"]
    assert preserved["non_fast_forward_prohibited"] is True
    assert preserved["deletion_prohibited"] is True
    assert preserved["bypass_actors"] == []
    assert preserved["exclusive_writer_identity"] == "DSAI_VIT_PHYSICAL_CONTROLLER"
    assert preserved["physical_gateway"] == "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY"


def test_active_policy_delegates_current_main_assurance_to_final_lease() -> None:
    policy = load(POLICY)
    ruleset = policy["github_ruleset"]
    assert ruleset["ruleset_id"] == 20229411
    assert ruleset["strict_required_status_checks"] is False
    assert ruleset["required_status_checks"] == ["OVC merge readiness"]
    assert ruleset["required_check_provider_integration_id"] == 15368
    assert ruleset["current_main_assurance_owner"] == "OVC_MERGE_READINESS_LATE_BINDING_LEASE"
    assert ruleset["branch_up_to_date_as_physical_placement"] == "PROHIBITED"
    assert ruleset["bypass_actor_count"] == 0
    assert ruleset["pull_request_required"] is True
    assert ruleset["allowed_merge_methods"] == ["squash"]
    assert ruleset["non_fast_forward_prohibited"] is True
    assert ruleset["deletion_prohibited"] is True


def test_exact_ruleset_payload_preserves_all_guards_except_strictness() -> None:
    payload = load(PAYLOAD)
    assert payload["name"] == "OVC main protection"
    assert payload["enforcement"] == "active"
    assert payload["bypass_actors"] == []
    rules = {rule["type"]: rule for rule in payload["rules"]}
    assert "deletion" in rules
    assert "non_fast_forward" in rules
    pr = rules["pull_request"]["parameters"]
    assert pr["required_review_thread_resolution"] is True
    assert pr["allowed_merge_methods"] == ["squash"]
    checks = rules["required_status_checks"]["parameters"]
    assert checks["strict_required_status_checks_policy"] is False
    assert checks["do_not_enforce_on_create"] is False
    assert checks["required_status_checks"] == [
        {"context": "OVC merge readiness", "integration_id": 15368}
    ]
    assert payload["ovc_change_control"]["only_semantic_delta"] == (
        "strict_required_status_checks_policy:true->false"
    )


def test_contract_forbids_native_strictness_as_second_placement_system() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "native strict branch-up-to-date enforcement disabled" in text
    assert "Native required-check strictness MUST NOT be used as an additional physical-placement mechanism" in text
    assert "OVC merge readiness` required from the bound GitHub Actions provider" in text
