#!/usr/bin/env python3
"""Run the frozen MG-WP1 predicate-classifier fixture deterministically."""

from __future__ import annotations

import json
from pathlib import Path

from ovc.opt_b.market_grammar import (
    ComponentStats,
    ExclusivityRule,
    classify_component,
    validate_predicate_domain,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/market_grammar/wp1/predicate_classifier_cases.json"
EXCLUSIVITY = ROOT / "registries/opt_b/market_grammar/MG_EXCLUSIVITY_REGISTRY_v0_1.json"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path.relative_to(ROOT)}")
    return value


def stats_from(value: dict) -> ComponentStats:
    return ComponentStats(**value)


def rule_from(value: dict) -> ExclusivityRule:
    return ExclusivityRule(
        rule_id=value["rule_id"],
        feature_key=value["feature_key"],
        domain=value["domain"],
        object_scope=value["object_scope"],
        clock_scope=value["clock_scope"],
        time_scope=value["time_scope"],
        mutually_exclusive_values=tuple(value["mutually_exclusive_values"]),
        registry_version=value["registry_version"],
    )


def run() -> dict:
    fixture = load(FIXTURE)
    registry = load(EXCLUSIVITY)
    rules_by_id = {item["rule_id"]: rule_from(item) for item in registry["rules"]}
    results: list[dict] = []

    for case in sorted(fixture["cases"], key=lambda item: item["case_id"]):
        rule_id = case.get("exclusivity_rule_id")
        rules = [rules_by_id[rule_id]] if rule_id else []
        actual = classify_component(stats_from(case["stats"]), rules).value
        if actual != case["expected_class"]:
            raise AssertionError(
                f"{case['case_id']}: expected {case['expected_class']}, got {actual}"
            )
        results.append({"case_id": case["case_id"], "class": actual})

    invalid_results: list[dict] = []
    for case in sorted(fixture["invalid_cases"], key=lambda item: item["case_id"]):
        try:
            if case["operation"] == "VALIDATE_DOMAIN":
                validate_predicate_domain(case["feature_key"], case["requested_domain"])
            elif case["operation"] == "CREATE_EXCLUSIVITY_RULE":
                rule_from(case["rule"])
            elif case["operation"] == "CREATE_STATS":
                stats_from(case["stats"])
            else:
                raise AssertionError(f"unknown operation: {case['operation']}")
        except ValueError as exc:
            if case["expected_error_contains"] not in str(exc):
                raise AssertionError(
                    f"{case['case_id']}: unexpected error {exc!s}"
                ) from exc
            invalid_results.append(
                {"case_id": case["case_id"], "rejected": True}
            )
        else:
            raise AssertionError(f"{case['case_id']}: invalid fixture was accepted")

    return {
        "fixture_id": fixture["fixture_id"],
        "valid_case_count": len(results),
        "invalid_case_count": len(invalid_results),
        "results": results,
        "invalid_results": invalid_results,
        "status": "PASS",
    }


def main() -> int:
    print(
        "MG_WP1_FIXTURE_RESULT="
        + json.dumps(run(), sort_keys=True, separators=(",", ":"))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
