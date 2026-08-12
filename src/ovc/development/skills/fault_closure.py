from __future__ import annotations

from typing import Any

from ovc.development.identity import canonical_sha256


FULL_E6_FAULT_SCENARIOS = (
    "MISSING_MANIFEST",
    "CORRUPT_MANIFEST",
    "UNAVAILABLE_REMOTE",
    "KILLED_TEST",
    "STALE_HASH",
    "DISK_PRESSURE",
    "REVOKED_DEPENDENCY",
    "INVALID_CACHE",
    "DENIED_TOOL",
)

_REASON_BY_SCENARIO = {
    "MISSING_MANIFEST": "MISSING_MANIFEST_FAIL_CLOSED",
    "CORRUPT_MANIFEST": "CORRUPT_MANIFEST_FAIL_CLOSED",
    "UNAVAILABLE_REMOTE": "REMOTE_UNAVAILABLE_FAIL_CLOSED",
    "KILLED_TEST": "KILLED_TEST_FAIL_CLOSED",
    "STALE_HASH": "STALE_HASH_FAIL_CLOSED",
    "DISK_PRESSURE": "CAPACITY_DISK_PRESSURE_FAIL_CLOSED",
    "REVOKED_DEPENDENCY": "REVOKED_DEPENDENCY_FAIL_CLOSED",
    "INVALID_CACHE": "INVALID_CACHE_FAIL_CLOSED",
    "DENIED_TOOL": "DENIED_TOOL_FAIL_CLOSED",
}


def run_full_fault_injection(*, scenario: str, skill_release_id: str, capability_id: str, environment_id: str) -> dict[str, Any]:
    scenario_id = str(scenario).upper()
    if scenario_id not in FULL_E6_FAULT_SCENARIOS:
        raise ValueError("unsupported full E6 fault injection scenario")
    logical = {
        "scenario": scenario_id,
        "skill_release_id": str(skill_release_id),
        "capability_id": str(capability_id),
        "environment_id": str(environment_id),
        "observed_status": "BLOCK",
        "fail_closed": True,
        "evidence_preserved": True,
        "scope_mutated": False,
        "authority_escalated": False,
        "reason_code": _REASON_BY_SCENARIO[scenario_id],
    }
    return {
        "schema": "ovc-dsai-g7-full-e6-fault-injection-result/v1",
        **logical,
        "authority_effect": "NONE",
        "result_id": canonical_sha256(logical, role="DSAI_G7_FULL_E6_FAULT"),
    }
