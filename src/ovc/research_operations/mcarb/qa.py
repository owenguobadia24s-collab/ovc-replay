from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from .models import AuxiliaryMeasurement, parse_utc

RESERVED_ACTIONS = {
    "MARKET_RUN", "PROVIDER_INTAKE", "VALIDATION_READ", "SELECTOR_CHANGE",
    "C2_CHANGE", "C2E_CHANGE", "SRI_CHANGE", "FAMILY_PROMOTION", "SEMANTIC_PROMOTION",
    "PUBLICATION", "PROBABILITY", "RISK", "EXPOSURE", "EXECUTION",
}

@dataclass(frozen=True)
class QAAssertion:
    qa_id: str
    result: str
    reason_codes: tuple[str, ...] = ()


def authority_guard(action: str) -> None:
    if action in RESERVED_ACTIONS:
        raise PermissionError(f"MCARB authority reserved/denied: {action}")


def validate_causal_measurement(record: AuxiliaryMeasurement) -> QAAssertion:
    if record.missingness_state == "RETROSPECTIVE_ONLY":
        return QAAssertion("MCARB-IQA-02", "BLOCK", ("RETROSPECTIVE_ONLY",))
    if parse_utc(record.first_valid_time) < parse_utc(record.interval_end):
        return QAAssertion("MCARB-IQA-02", "BLOCK", ("FIRST_VALID_BACKDATED",))
    if parse_utc(record.first_valid_time) > parse_utc(record.admissible_cutoff):
        return QAAssertion("MCARB-IQA-02", "BLOCK", ("CUTOFF_EXCEEDED",))
    return QAAssertion("MCARB-IQA-02", "PASS")


def validate_al_candidate(candidate_id: str, eligible_candidates: Iterable[str]) -> QAAssertion:
    allowed=set(eligible_candidates)
    return QAAssertion("MCARB-IQA-03", "PASS" if candidate_id in allowed else "BLOCK",
                       () if candidate_id in allowed else ("AL_CANDIDATE_NOT_AUDIT_ELIGIBLE",))


def validate_proxy_quality(candidate_id: str, *, proxy_label: str | None, status: str,
                           information_loss: float | None) -> QAAssertion:
    if candidate_id != "AL-11":
        return QAAssertion("MCARB-IQA-05", "PASS")
    if not proxy_label or status not in {"PASS","PARTIAL","NOT_EVALUABLE","FAIL","QUARANTINED"}:
        return QAAssertion("MCARB-IQA-05", "BLOCK", ("PROXY_UNLABELLED",))
    if status == "PASS" and information_loss is None:
        return QAAssertion("MCARB-IQA-05", "BLOCK", ("PROXY_INFORMATION_LOSS_MISSING",))
    return QAAssertion("MCARB-IQA-05", "PASS")


def validate_normalization(*, causal: bool, reference_hash: str | None, refit_on_evaluation: bool) -> QAAssertion:
    if not causal or refit_on_evaluation or not reference_hash:
        return QAAssertion("MCARB-IQA-10", "BLOCK", ("NORMALIZATION_LEAKAGE_OR_UNBOUND_REFERENCE",))
    return QAAssertion("MCARB-IQA-10", "PASS")


def null_consequence(domain_results: Iterable[str]) -> str:
    results=tuple(domain_results)
    lawful_null={"REDUNDANT_WITH_PRICE_STRUCTURE","NO_ADDITIONAL_INFORMATION","NOT_EVALUABLE"}
    if results and all(result in lawful_null for result in results):
        return "NO_ADDITIONAL_INFORMATION"
    return "UNRESOLVED"
