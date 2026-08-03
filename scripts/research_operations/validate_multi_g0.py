from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(path: str) -> dict:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"NOT_OBJECT:{path}")
    return value


def main() -> int:
    decision = load("docs/releases/multi-g0-operator-decisions-v0-1/MULTI_G0_OPERATOR_DECISION.json")
    assert decision["decision_id"] == "MULTI-G0.OPERATOR.PASS.20260803T125100+0100"
    assert {gate: item["decision"] for gate, item in decision["decisions"].items()} == {
        "CCR-G0": "PASS",
        "C2E-G0": "PASS",
        "C25-G0": "PASS",
    }
    assert "CLOCK_OR_CONTINUITY_ACTIVATION" in decision["shared_denials"]
    assert "C2E_ACTIVATION" in decision["shared_denials"]
    assert "C2_5_EVENT_PROMOTION_OR_ACTIVATION" in decision["shared_denials"]

    ccr = load("registries/research_operations/clock_continuity/OVC_CCR_PROGRAMME_STATE_v0_1.json")
    c2e = load("registries/research_operations/c2e/OVC_C2E_PROGRAMME_STATE_v0_1.json")
    c25 = load("registries/research_operations/c2_5/OVC_C25_PROGRAMME_STATE_v0_1.json")
    assert (ccr["current_packet"], ccr["current_gate"], ccr["operator_decision_required"]) == ("CCR-WP1", "CCR-G1", False)
    assert (c2e["current_packet"], c2e["current_gate"], c2e["operator_decision_required"]) == ("C2E-WP1", "C2E-G1", False)
    assert (c25["current_packet"], c25["current_gate"], c25["operator_decision_required"]) == ("C25-WP1", "C25-G1", False)
    assert ccr["authority"]["clock_or_continuity_activation"] == "DENIED"
    assert c2e["authority"]["c2e_activation"] == "DENIED"
    assert c25["authority"]["event_promotion_or_activation"] == "DENIED"

    variants = load("registries/research_operations/clock_continuity/OVC_CCR_VARIANT_AND_METRIC_REGISTRY_v0_1.json")
    assert [item["variant_id"] for item in variants["variants"]] == [
        "V0_CURRENT_STRICT_CONTINUITY_AUTHORITATIVE",
        "V1_PLANNED_CLOSURE_CLASSIFIED_CONTINUITY_SHADOW_ONLY",
        "V2_PROVIDER_GAP_SEGMENTED_CONTINUITY_SHADOW_ONLY",
    ]
    assert all(item["create_missing_bars"] is False for item in variants["variants"])

    lifecycle = load("registries/research_operations/c2e/OVC_C2E_BOUNDARY_AND_LIFECYCLE_REGISTRY_v0_1.json")
    assert lifecycle["primary_variant"] == "PRIMARY"
    assert lifecycle["activation"] == "DENIED"
    assert set(lifecycle["variants"]) == {"STRICT", "PRIMARY", "PERMISSIVE"}

    rules = load("registries/research_operations/c2_5/OVC_C25_BOUNDED_RULE_REGISTRY_v0_1.json")
    assert [item["rule_id"] for item in rules["included_rules"]] == [
        "BOUNDARY_ZONE_ENTRY", "BREACH_ACTIVE", "LONG_PERSISTENCE", "REPEATED_SWITCHING"
    ]
    assert len(rules["excluded_rules"]) == 4
    assert rules["event_authority"] == "DENIED"
    assert rules["single_readiness_badge"] == "PROHIBITED"

    print("MULTI-G0 validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
