from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .core import SFFContractError, canonical_bytes, content_identity


REQUIRED_FIELDS = (
    "scientific_endpoint_manifest",
    "executable_method_binding",
    "outcome_access_embargo_manifest",
    "feasibility_evidence",
    "evaluation_population_ledger",
    "target_complexity_budget",
    "study_population",
    "cutoff_schedule",
    "risk_set_policy",
    "denominator_policy",
    "static_model_generation",
    "search_exposure",
    "calibration_partition",
    "credible_challengers",
    "materiality_rule",
    "multiplicity_plan",
    "dependence_plan",
    "uncertainty_requirements",
    "falsification_contract",
    "claim_decision_rule",
    "failure_disposition",
    "capacity_restart_plan",
    "source_authority",
    "external_artifact_root",
)


FORBIDDEN_DECISION_VALUES = {"", "UNKNOWN", "DEFAULT", "TBD", "UNRESOLVED", "AMBIGUOUS", "CONTAMINATED", "AUTHORITY_BLOCKED"}


@dataclass(frozen=True)
class SFFPreregistrationFreezeReceipt:
    receipt_id: str
    bundle_id: str
    bundle_sha256: str
    atomic: bool = True
    protected_outcomes_accessed: bool = False
    real_study_frozen: bool = False


@dataclass(frozen=True)
class CompiledPreregistration:
    bundle_id: str
    fields: Mapping[str, Any]
    freeze_receipt: SFFPreregistrationFreezeReceipt
    status: str = "SYNTHETIC_COMPILER_OUTPUT_ONLY"


def _validate_value(path: str, value: Any) -> None:
    if value is None:
        raise SFFContractError(f"PREREG_FIELD_UNRESOLVED:{path}")
    if isinstance(value, str) and value.strip().upper() in FORBIDDEN_DECISION_VALUES:
        raise SFFContractError(f"PREREG_FIELD_UNRESOLVED:{path}")
    if isinstance(value, Mapping):
        if not value:
            raise SFFContractError(f"PREREG_FIELD_EMPTY:{path}")
        for key, nested in value.items():
            _validate_value(f"{path}.{key}", nested)
    elif isinstance(value, (list, tuple)):
        if not value:
            raise SFFContractError(f"PREREG_FIELD_EMPTY:{path}")
        for index, nested in enumerate(value):
            _validate_value(f"{path}[{index}]", nested)


def compile_preregistration(fields: Mapping[str, Any]) -> CompiledPreregistration:
    missing = [field for field in REQUIRED_FIELDS if field not in fields]
    extras = sorted(set(fields) - set(REQUIRED_FIELDS))
    if missing:
        raise SFFContractError(f"PREREG_REQUIRED_FIELDS_MISSING:{','.join(missing)}")
    if extras:
        raise SFFContractError(f"PREREG_UNDECLARED_FIELDS:{','.join(extras)}")
    for field in REQUIRED_FIELDS:
        _validate_value(field, fields[field])
    embargo = fields["outcome_access_embargo_manifest"]
    if not isinstance(embargo, Mapping) or embargo.get("protected_outcomes_accessed") is not False:
        raise SFFContractError("PREREG_OUTCOME_EMBARGO_NOT_PROVEN")
    if fields["static_model_generation"].get("mode") != "STATIC":
        raise SFFContractError("PREREG_MODEL_NOT_STATIC")
    payload = {field: fields[field] for field in REQUIRED_FIELDS}
    bundle_id = content_identity("sff-prereg-bundle", payload)
    bundle_sha256 = bundle_id.rsplit(":", 1)[1]
    receipt_payload = {"bundle_id": bundle_id, "bundle_sha256": bundle_sha256, "atomic": True, "protected_outcomes_accessed": False, "real_study_frozen": False}
    receipt = SFFPreregistrationFreezeReceipt(content_identity("sff-prereg-freeze-receipt", receipt_payload), bundle_id, bundle_sha256)
    return CompiledPreregistration(bundle_id, payload, receipt)


def amend_frozen_bundle(compiled: CompiledPreregistration, *, successor_generation_id: str | None) -> str:
    if not successor_generation_id:
        raise SFFContractError("APPEND_ONLY_PREREG_AMENDMENT_REQUIRES_SUCCESSOR")
    return f"SUCCESSOR_REQUIRED:{successor_generation_id}:{compiled.bundle_id}"
