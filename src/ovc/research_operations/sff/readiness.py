from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .core import SFFContractError, content_identity
from .preregistration import FORBIDDEN_DECISION_VALUES, compile_preregistration


REQUIRED_GREAL_FIELDS = (
    "selected_target_grammar_candidate_provenance",
    "exposure_class",
    "pre_outcome_support_feasibility_evidence",
    "target_complexity_budget",
    "population",
    "cutoff_schedule",
    "risk_set_semantics",
    "denominator_semantics",
    "static_model_generation",
    "forecast_search_exposure_manifest",
    "calibration_generation_partition",
    "credible_simpler_challengers",
    "uncertainty_plane_requirements",
    "falsification_contract",
    "endpoint",
    "materiality_rule",
    "multiplicity_policy",
    "dependence_policy",
    "failure_disposition_contract",
    "executable_method_binding",
    "evaluation_population_ledger_constitution",
    "source_authority",
    "independent_reviewer_binding",
    "external_artifact_root",
    "capacity_restart_plan",
    "no_outcome_access_embargo_proof",
    "atomic_freeze_receipt_candidate",
    "rollback",
    "proposed_successor_after_operator_pass",
)

SUPPLIED_GREAL_FIELDS = tuple(
    field for field in REQUIRED_GREAL_FIELDS if field != "atomic_freeze_receipt_candidate"
)


@dataclass(frozen=True)
class GREALCandidateBundle:
    candidate_id: str
    bundle_sha256: str
    fields: Mapping[str, Any]
    preregistration_bundle_id: str
    preregistration_freeze_receipt_id: str
    status: str = "REAL_SCIENTIFIC_PREREG_READY_CANDIDATE_ONLY"
    scientific_forecastability: str = "NOT_EVALUATED"
    authority_effect: str = "NONE_PACKET_PREPARATION_ONLY"


def _validate_explicit(path: str, value: Any) -> None:
    if value is None:
        raise SFFContractError(f"GREAL_FIELD_UNRESOLVED:{path}")
    if isinstance(value, str) and value.strip().upper() in FORBIDDEN_DECISION_VALUES:
        raise SFFContractError(f"GREAL_FIELD_UNRESOLVED:{path}")
    if isinstance(value, Mapping):
        if not value:
            raise SFFContractError(f"GREAL_FIELD_EMPTY:{path}")
        for key, nested in value.items():
            _validate_explicit(f"{path}.{key}", nested)
    elif isinstance(value, (list, tuple)):
        if not value:
            raise SFFContractError(f"GREAL_FIELD_EMPTY:{path}")
        for index, nested in enumerate(value):
            _validate_explicit(f"{path}[{index}]", nested)


def _compiler_fields(fields: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "scientific_endpoint_manifest": fields["endpoint"],
        "executable_method_binding": fields["executable_method_binding"],
        "outcome_access_embargo_manifest": fields["no_outcome_access_embargo_proof"],
        "feasibility_evidence": fields["pre_outcome_support_feasibility_evidence"],
        "evaluation_population_ledger": fields["evaluation_population_ledger_constitution"],
        "target_complexity_budget": fields["target_complexity_budget"],
        "study_population": fields["population"],
        "cutoff_schedule": fields["cutoff_schedule"],
        "risk_set_policy": fields["risk_set_semantics"],
        "denominator_policy": fields["denominator_semantics"],
        "static_model_generation": fields["static_model_generation"],
        "search_exposure": fields["forecast_search_exposure_manifest"],
        "calibration_partition": fields["calibration_generation_partition"],
        "credible_challengers": fields["credible_simpler_challengers"],
        "materiality_rule": fields["materiality_rule"],
        "multiplicity_plan": fields["multiplicity_policy"],
        "dependence_plan": fields["dependence_policy"],
        "uncertainty_requirements": fields["uncertainty_plane_requirements"],
        "falsification_contract": fields["falsification_contract"],
        "claim_decision_rule": fields["falsification_contract"]["claim_decision_rule"],
        "failure_disposition": fields["failure_disposition_contract"],
        "capacity_restart_plan": fields["capacity_restart_plan"],
        "source_authority": fields["source_authority"],
        "external_artifact_root": fields["external_artifact_root"],
    }


def compile_greal_candidate(supplied_fields: Mapping[str, Any]) -> GREALCandidateBundle:
    missing = [field for field in SUPPLIED_GREAL_FIELDS if field not in supplied_fields]
    extras = sorted(set(supplied_fields) - set(SUPPLIED_GREAL_FIELDS))
    if missing:
        raise SFFContractError(f"GREAL_REQUIRED_FIELDS_MISSING:{','.join(missing)}")
    if extras:
        raise SFFContractError(f"GREAL_UNDECLARED_FIELDS:{','.join(extras)}")
    for field in SUPPLIED_GREAL_FIELDS:
        _validate_explicit(field, supplied_fields[field])

    provenance = supplied_fields["selected_target_grammar_candidate_provenance"]
    embargo = supplied_fields["no_outcome_access_embargo_proof"]
    review = supplied_fields["independent_reviewer_binding"]
    if provenance.get("activation_state") != "PROPOSED_NOT_ACTIVE" or provenance.get("selected_pre_outcome") is not True:
        raise SFFContractError("GREAL_TARGET_PROVENANCE_NOT_PREOUTCOME_CANDIDATE")
    if embargo.get("protected_outcomes_accessed") is not False or embargo.get("embargo_state") != "LOCKED_UNCONSUMED":
        raise SFFContractError("GREAL_OUTCOME_EMBARGO_NOT_PROVEN")
    if review.get("decision") != "PASS" or review.get("independence") != "PASS":
        raise SFFContractError("GREAL_INDEPENDENT_REVIEW_NOT_PASS")
    if supplied_fields["static_model_generation"].get("mode") != "STATIC":
        raise SFFContractError("GREAL_MODEL_NOT_STATIC")
    if supplied_fields["source_authority"].get("real_source_sff_execution_currently_authorized") is not False:
        raise SFFContractError("GREAL_PREMATURE_REAL_SOURCE_AUTHORITY")

    compiled = compile_preregistration(_compiler_fields(supplied_fields))
    receipt = compiled.freeze_receipt
    freeze_candidate = {
        "schema": "ovc-sff-preregistration-freeze-receipt-candidate/v0.1",
        "receipt_id": receipt.receipt_id,
        "bundle_id": receipt.bundle_id,
        "bundle_sha256": receipt.bundle_sha256,
        "atomic": receipt.atomic,
        "protected_outcomes_accessed": receipt.protected_outcomes_accessed,
        "real_study_frozen": receipt.real_study_frozen,
        "candidate_effect": "NONE_UNTIL_OPERATOR_PASS",
    }
    fields = {
        field: (freeze_candidate if field == "atomic_freeze_receipt_candidate" else supplied_fields[field])
        for field in REQUIRED_GREAL_FIELDS
    }
    candidate_id = content_identity("sff-greal-candidate", fields)
    return GREALCandidateBundle(
        candidate_id=candidate_id,
        bundle_sha256=candidate_id.rsplit(":", 1)[1],
        fields=fields,
        preregistration_bundle_id=compiled.bundle_id,
        preregistration_freeze_receipt_id=receipt.receipt_id,
    )
