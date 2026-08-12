from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from ovc.development.identity import canonical_sha256, normalize_relative_path


_BLOCKING = {"BLOCK", "QUARANTINE", "NOT_EVALUABLE", "FAIL"}
_RESERVED = {
    "TRUSTED_PROMOTION", "ORCH_1_ASSISTED_WRITE", "ORCH_2_AUTOMATIC_INTEGRATION",
    "MERGE_CAPABILITY_TRUSTED_PROMOTION", "SELECTOR_ACTIVATION", "ACTIVE_DISCOVERY",
    "ACTIVE_DEVELOPMENT", "ACTIVE_VALIDATION", "SCIENTIFIC_PROMOTION", "CANONICAL_PUBLICATION",
    "R2_PUBLICATION", "VALIDATION", "PROBABILITY", "RISK", "EXPOSURE", "TRADING", "EXECUTION",
}


def plan_tests(
    *,
    changed_paths: Sequence[str],
    direct_tests: Sequence[str],
    dependent_tests: Sequence[str] = (),
    impact_known: bool,
) -> dict[str, Any]:
    paths = sorted({normalize_relative_path(value) for value in changed_paths})
    selected = sorted(set(str(value) for value in direct_tests) | set(str(value) for value in dependent_tests))
    widened = not impact_known
    if widened:
        selected.append("REPOSITORY_WIDE_SUITE")
    logical = {"changed_paths": paths, "selected_tests": sorted(set(selected)), "impact_known": bool(impact_known), "widened": widened}
    return {"schema":"ovc-dsai-test-plan/v1", **logical, "plan_id":canonical_sha256(logical, role="DSAI_TEST_PLAN"), "authority_effect":"NONE"}


def test_execution_plan(*, test_plan: Mapping[str, Any]) -> dict[str, Any]:
    tests = list(test_plan.get("selected_tests", []))
    return {
        "schema":"ovc-dsai-test-execution-plan/v1", "status":"READY" if tests else "BLOCKED",
        "tests":tests, "tool_profile_id":"WP4-LOCAL-TEST", "execution_mode":"LOCAL_TEST_ONLY",
        "authority_effect":"NONE", "writes_performed":[],
    }


# Public helper name is contract-bearing, but it is not a pytest test function.
# Mark it explicitly non-collectable so importing it into test modules cannot
# create fixture-injection collection errors under pytest-native execution.
test_execution_plan.__test__ = False


def evaluate_qa(assertions: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in assertions]
    if not rows:
        acceptance = "NOT_EVALUABLE"
    elif any(str(row.get("status")) in _BLOCKING for row in rows):
        acceptance = "BLOCK"
    elif any(str(row.get("status")) == "WARN" for row in rows):
        acceptance = "WARN"
    else:
        acceptance = "PASS"
    logical = {"assertions": rows, "acceptance_result": acceptance}
    return {
        "schema":"ovc-dsai-qa-evaluation/v1", **logical,
        "authority_result":"NO_AUTHORITY_DECISION", "authority_effect":"NONE",
        "evaluation_id":canonical_sha256(logical, role="DSAI_QA_EVALUATION"),
    }


def audit_evidence(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    failures: list[str] = []
    count = 0
    for row in records:
        count += 1
        digest = str(row.get("sha256", ""))
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            failures.append("INVALID_HASH")
        if row.get("stale") is True:
            failures.append("STALE_EVIDENCE")
    status = "PASS" if not failures and count else "BLOCK"
    return {"schema":"ovc-dsai-evidence-audit/v1", "status":status, "record_count":count, "reason_codes":sorted(set(failures)), "authority_effect":"NONE"}


def evaluate_gate(
    *,
    gate_title: str,
    acceptance_conditions: Sequence[bool],
    qa_status: str,
    authority_delta: str,
) -> dict[str, Any]:
    acceptance = "PASS" if acceptance_conditions and all(acceptance_conditions) and qa_status == "PASS" else "BLOCK"
    reserved = str(authority_delta) in _RESERVED
    authority_result = "OPERATOR_REQUIRED" if reserved else "AUTO_EXECUTABLE"
    auto_ratifiable = acceptance == "PASS" and not reserved
    logical = {
        "gate_title": str(gate_title), "acceptance_result": acceptance, "qa_status": str(qa_status),
        "authority_delta": str(authority_delta), "authority_result": authority_result, "auto_ratifiable": auto_ratifiable,
    }
    return {
        "schema":"ovc-dsai-gate-evaluation/v1", **logical,
        "recommended_decision":"PASS" if acceptance == "PASS" else "BLOCK",
        "authority_granted":False, "authority_effect":"NONE",
        "evaluation_id":canonical_sha256(logical, role="DSAI_GATE_EVALUATION"),
    }
