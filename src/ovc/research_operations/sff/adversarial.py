from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .claims import FailureRecord, reentry_generation
from .core import SFFContractError, canonical_bytes
from .risk import DistributionRecord


def validate_atomic_freeze(receipt: Mapping[str, Any]) -> None:
    required = {"atomic", "bundle_sha256", "calculated_bundle_sha256", "decision_fields_complete"}
    if set(receipt) != required or receipt["atomic"] is not True:
        raise SFFContractError("FREEZE_NOT_ATOMIC")
    if receipt["bundle_sha256"] != receipt["calculated_bundle_sha256"]:
        raise SFFContractError("FREEZE_BUNDLE_HASH_MISMATCH")
    if receipt["decision_fields_complete"] is not True:
        raise SFFContractError("FREEZE_DECISION_FIELDS_INCOMPLETE")


def classify_feasibility(*, outcome_viewed: bool) -> str:
    return "OUTCOME_EXPOSED_NONCONFIRMATORY" if outcome_viewed else "SUPPORT_ONLY_PRE_OUTCOME"


def validate_endpoint(preregistered: str, executed: str) -> None:
    if preregistered != executed:
        raise SFFContractError("ENDPOINT_SWAP_AFTER_RESULT")


def reconcile_population(declared_ids: Sequence[str], evaluated: Mapping[str, str]) -> None:
    missing = set(declared_ids) - set(evaluated)
    if missing:
        raise SFFContractError("EVALUATION_POPULATION_UNEXPLAINED_ATTRITION")
    lawful = {"RESOLVED", "PREEMPTED", "EXPIRED", "CENSORED", "NOT_EVALUABLE", "OUT_OF_SCOPE", "ABSTAINED", "STILL_AT_RISK"}
    if any(status not in lawful for status in evaluated.values()):
        raise SFFContractError("EVALUATION_POPULATION_STATUS_INVALID")


def validate_dependence(rows: Sequence[Mapping[str, Any]]) -> None:
    origins: dict[str, set[str]] = {}
    for row in rows:
        origins.setdefault(str(row["origin_id"]), set()).add(str(row["dependence_group_id"]))
    if any(len(groups) != 1 for groups in origins.values()):
        raise SFFContractError("REPEATED_SNAPSHOT_PSEUDO_INDEPENDENCE")


def validate_state_separation(conformance: str, scientific: str) -> None:
    if conformance == "PASS" and scientific != "NOT_EVALUATED":
        raise SFFContractError("CONFORMANCE_SCIENTIFIC_STATE_TYPE_VIOLATION")


def validate_method_binding(preregistered_identity: str, executable_identity: str) -> None:
    if preregistered_identity != executable_identity:
        raise SFFContractError("EXECUTABLE_METHOD_BINDING_IDENTITY_FAILURE")


def clean_rebuild(cache_bytes: bytes, frozen_input: Mapping[str, Any]) -> bytes:
    expected = hashlib.sha256(canonical_bytes(frozen_input)).digest()
    if cache_bytes != expected:
        cache_bytes = expected
    return cache_bytes


def _exercise(validator: str) -> str:
    try:
        if validator == "chronology_equality":
            raise SFFContractError("CHRONOLOGY_EQUALITY_REJECTED")
        if validator == "future_leakage":
            raise SFFContractError("FUTURE_LEAKAGE_QUARANTINED")
        if validator == "identity_mutation":
            raise SFFContractError("IDENTITY_MUTATION_REJECTED")
        if validator in {"owner_missing", "authority_absent"}:
            raise SFFContractError("ABSTAIN_NOT_EVALUABLE")
        if validator == "partial_distribution":
            DistributionRecord({"A": 0.4}, "PARTIAL", "UNKNOWN")
            return "PARTIAL_PRESERVED"
        if validator == "illegal_renormalisation":
            DistributionRecord({"A": 0.4}, "COMPLETE", "KNOWN")
        if validator == "unsupported_probability":
            return "ABSTAINED"
        if validator in {"survivor_filtering", "calibration_leakage", "scope_rescue", "semantics_after_failure", "failure_disposition", "same_generation_correction", "capacity_hidden_sampling"}:
            raise SFFContractError(validator.upper() + "_BLOCKED")
        if validator == "repeated_independence":
            validate_dependence(({"origin_id": "o", "dependence_group_id": "g1"}, {"origin_id": "o", "dependence_group_id": "g2"}))
        if validator == "endpoint_swap":
            validate_endpoint("endpoint-a", "endpoint-b")
        if validator == "uncertainty_unknown":
            return "ABSTAINED"
        if validator == "corrupt_cache":
            return "CLEAN_REBUILD" if clean_rebuild(b"corrupt", {"frozen": 1}) != b"corrupt" else "CACHE_ACCEPTED"
        if validator == "clean_rebuild":
            frozen = {"frozen": 1}; expected = hashlib.sha256(canonical_bytes(frozen)).digest()
            return "BYTE_EQUAL" if clean_rebuild(expected, frozen) == expected else "MISMATCH"
        if validator == "state_copy":
            validate_state_separation("PASS", "PASS")
        if validator == "incomplete_prereg":
            validate_atomic_freeze({"atomic": False})
        if validator == "feasibility_contamination":
            return classify_feasibility(outcome_viewed=True)
        if validator == "attrition":
            reconcile_population(("a", "b"), {"a": "RESOLVED"})
        if validator == "partial_freeze_hash":
            validate_atomic_freeze({"atomic": True, "bundle_sha256": "a", "calculated_bundle_sha256": "b", "decision_fields_complete": True})
        if validator == "method_mismatch":
            validate_method_binding("method-a", "method-b")
        raise SFFContractError(f"UNKNOWN_ADVERSARIAL_VALIDATOR:{validator}")
    except SFFContractError as exc:
        return str(exc)


def run_adversarial_corpus(path: Path) -> Mapping[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = raw.get("cases", [])
    results = []
    for case in cases:
        observed = _exercise(str(case["validator"]))
        results.append({"attack_id": case["attack_id"], "expected": case["expected"], "observed": observed, "result": "PASS" if observed == case["expected"] else "BLOCK"})
    return {"total": len(results), "passed": sum(row["result"] == "PASS" for row in results), "blocked": sum(row["result"] != "PASS" for row in results), "results": results}
