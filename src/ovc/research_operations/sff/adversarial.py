from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .claims import FailureRecord, reentry_generation
from .core import SFFContractError, TargetComplexityBudget, canonical_bytes, content_identity, require_first_valid_chronology
from .forecast import ForecastModelGeneration, UncertaintyRecord, build_forecast_snapshot
from .preregistration import compile_preregistration
from .risk import DistributionRecord, ForecastRiskSetManifest, RiskSetEntry, RiskStatus, evaluate_with_opt_c


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


def validate_frozen_identity(expected: Mapping[str, Any], observed: Mapping[str, Any]) -> None:
    if content_identity("sff-frozen", expected) != content_identity("sff-frozen", observed):
        raise SFFContractError("IDENTITY_MUTATION_REJECTED")


def validate_no_future_leakage(*, observed_at: datetime, cutoff_at: datetime) -> None:
    if observed_at > cutoff_at:
        raise SFFContractError("FUTURE_LEAKAGE_QUARANTINED")


def validate_declared_population(declared: Sequence[str], evaluated: Sequence[str]) -> None:
    if set(evaluated) != set(declared):
        raise SFFContractError("SURVIVOR_FILTERING_BLOCKED")


def validate_calibration_separation(calibration_ids: Sequence[str], evaluation_ids: Sequence[str]) -> None:
    if set(calibration_ids) & set(evaluation_ids):
        raise SFFContractError("CALIBRATION_LEAKAGE_BLOCKED")


def validate_frozen_scope(frozen_scope: str, proposed_scope: str) -> None:
    if proposed_scope != frozen_scope:
        raise SFFContractError("SCOPE_RESCUE_BLOCKED")


def validate_capacity_budget(budget: TargetComplexityBudget, requested_targets: int) -> None:
    if requested_targets > budget.maximum_targets:
        raise SFFContractError("CAPACITY_HIDDEN_SAMPLING_BLOCKED")


def _exercise(validator: str) -> str:
    try:
        if validator == "chronology_equality":
            now = datetime(2026, 1, 1, tzinfo=timezone.utc)
            require_first_valid_chronology(antecedent_at=now, cutoff_at=now)
        if validator == "future_leakage":
            cutoff = datetime(2026, 1, 1, tzinfo=timezone.utc)
            validate_no_future_leakage(observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc), cutoff_at=cutoff)
        if validator == "identity_mutation":
            validate_frozen_identity({"label": "CONTINUATION"}, {"label": "REVERSAL"})
        if validator in {"owner_missing", "authority_absent"}:
            return evaluate_with_opt_c(None, "synthetic-target")["status"]
        if validator == "partial_distribution":
            distribution = DistributionRecord({"A": 0.4}, "PARTIAL", "UNKNOWN")
            return "PARTIAL_PRESERVED" if distribution.probability("UNOBSERVED") is None else "UNKNOWN_COLLAPSED"
        if validator == "illegal_renormalisation":
            DistributionRecord({"A": 0.4}, "COMPLETE", "KNOWN")
        if validator == "unsupported_probability":
            return evaluate_with_opt_c(None, "unsupported-target")["status"]
        if validator == "survivor_filtering":
            validate_declared_population(("a", "b"), ("a",))
        if validator == "repeated_independence":
            ForecastRiskSetManifest.build(
                "p",
                (
                    RiskSetEntry("t", "o", 0, RiskStatus.STILL_AT_RISK, "g1"),
                    RiskSetEntry("t", "o", 1, RiskStatus.RESOLVED, "g2"),
                ),
            )
        if validator == "calibration_leakage":
            validate_calibration_separation(("shared",), ("shared",))
        if validator == "endpoint_swap":
            validate_endpoint("endpoint-a", "endpoint-b")
        if validator == "scope_rescue":
            validate_frozen_scope("FULL_POPULATION", "SURVIVORS_ONLY")
        if validator == "semantics_after_failure":
            failure = FailureRecord.create("g1", "semantics-v1", "FAILED", "FAILED_CONFIRMATORY")
            disposition = reentry_generation(failure, proposed_generation_id="g2", proposed_target_semantics_id="semantics-v2")
            if disposition != "SUCCESSOR_GENERATION_REENTRY_ELIGIBLE":
                raise SFFContractError("SEMANTICS_AFTER_FAILURE_BLOCKED")
        if validator == "uncertainty_unknown":
            generation = ForecastModelGeneration.freeze("m", {"alpha": 0.5}, "cal")
            snapshot = build_forecast_snapshot(
                target_id="t",
                generation=generation,
                distribution=DistributionRecord({"A": 1.0}, "COMPLETE", "KNOWN"),
                uncertainty=UncertaintyRecord("UNKNOWN", "ESTIMATED", "IN_ENVELOPE", "e"),
                support_currentness="CURRENT_SUPPORTED",
            )
            return snapshot.status
        if validator == "corrupt_cache":
            return "CLEAN_REBUILD" if clean_rebuild(b"corrupt", {"frozen": 1}) != b"corrupt" else "CACHE_ACCEPTED"
        if validator == "clean_rebuild":
            frozen = {"frozen": 1}; expected = hashlib.sha256(canonical_bytes(frozen)).digest()
            return "BYTE_EQUAL" if clean_rebuild(expected, frozen) == expected else "MISMATCH"
        if validator == "failure_disposition":
            FailureRecord.create("g1", "s1", "FAILED", "SUCCESS")
        if validator == "same_generation_correction":
            ForecastModelGeneration.freeze("m", {"alpha": 0.5}, "cal").update_from_outcomes({"result": 1})
        if validator == "state_copy":
            validate_state_separation("PASS", "PASS")
        if validator == "incomplete_prereg":
            compile_preregistration({})
        if validator == "feasibility_contamination":
            return classify_feasibility(outcome_viewed=True)
        if validator == "attrition":
            reconcile_population(("a", "b"), {"a": "RESOLVED"})
        if validator == "capacity_hidden_sampling":
            validate_capacity_budget(TargetComplexityBudget("b", 1, 1, 1), 2)
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
