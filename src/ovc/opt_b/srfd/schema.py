from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

VALID_OBJECT_TYPES = frozenset({
    "SRFDRepresentationSpec",
    "SRFDRepresentationRecord",
    "SRFDSegmentationBenchmarkSpec",
    "SRFDSegmentationResult",
    "SRFDDistanceSpec",
    "SRFDDistanceResult",
    "SRFDFamilyMethodSpec",
    "SRFDFamilyCatalog",
    "SRFDAssignmentRecord",
    "SRFDSensitivityPack",
    "SRFDOccurrenceContext",
    "SRFDComparabilityDomain",
    "SRFDFamilyCorrespondence",
    "SRFDInvariantCore",
    "SRFDResidualAmbiguity",
    "SRFDMethodDisagreement",
    "SRFDStabilityMetricSpec",
    "SRFDStabilityMetricResult",
    "SRFDBenchmarkRun",
    "SRFDFailureAttribution",
    "SRFDCapacityReceipt",
    "SRFDCheckpointReceipt",
    "SRFDPreregistration",
    "SRFDDecisionPacket",
})
ALLOWED_AUTHORITY_STATES = frozenset({"FIXTURE_ONLY", "CANDIDATE", "SHADOW_EXPERIMENT"})
ALLOWED_QA_STATES = frozenset({"NOT_EVALUATED", "PASS", "WARN", "BLOCK", "QUARANTINED"})
FORBIDDEN_FIELD_NAMES = frozenset({
    "outcome", "outcomes", "future_return", "return_label", "mfe", "mae",
    "probability", "edge", "risk", "exposure", "trade", "trade_label",
    "order", "execution", "validation_consumed", "selector_activation",
    "canonical_family",
})
COMMON_REQUIRED = ("object_type", "schema_version", "authority_state")


@dataclass(frozen=True)
class SRFDValidationError(ValueError):
    reason_code: str
    detail: str

    def __str__(self) -> str:
        return f"{self.reason_code}: {self.detail}"


def _walk_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise SRFDValidationError("QA_SCHEMA_FAILURE", f"{path} has non-string key")
            if key.lower() in FORBIDDEN_FIELD_NAMES:
                raise SRFDValidationError("AUTH_SCOPE_EXPANSION", f"forbidden field {path}.{key}")
            _walk_keys(child, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _walk_keys(child, f"{path}[{index}]")


def _require_text(document: Mapping[str, Any], field: str) -> None:
    value = document.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SRFDValidationError("QA_SCHEMA_FAILURE", f"{field} must be non-empty text")


def validate_document(document: Mapping[str, Any], object_type: str | None = None) -> None:
    if not isinstance(document, Mapping):
        raise SRFDValidationError("QA_SCHEMA_FAILURE", "document must be an object")
    _walk_keys(document)
    for field in COMMON_REQUIRED:
        _require_text(document, field)
    declared = document["object_type"]
    if declared not in VALID_OBJECT_TYPES:
        raise SRFDValidationError("QA_SCHEMA_FAILURE", f"unknown object_type {declared}")
    if object_type is not None and declared != object_type:
        raise SRFDValidationError("QA_SCHEMA_FAILURE", f"expected {object_type}, got {declared}")
    if document["authority_state"] not in ALLOWED_AUTHORITY_STATES:
        raise SRFDValidationError("AUTH_SCOPE_EXPANSION", "authority_state exceeds SRFD fixture/shadow envelope")
    if "qa_state" in document and document["qa_state"] not in ALLOWED_QA_STATES:
        raise SRFDValidationError("QA_SCHEMA_FAILURE", "unknown qa_state")
    if declared == "SRFDRepresentationSpec":
        for field in (
            "representation_pack_id", "implementation_class_id", "lawful_inputs",
            "output_schema", "missingness_policy", "comparability_domain_id",
            "ordering_semantics", "canonical_serialization", "prohibited_interpretation",
        ):
            if field not in document:
                raise SRFDValidationError("QA_SCHEMA_FAILURE", f"representation spec missing {field}")
        output_schema = document["output_schema"]
        if not isinstance(output_schema, Mapping):
            raise SRFDValidationError("QA_SCHEMA_FAILURE", "output_schema must be an object")
        namespaces = output_schema.get("namespaces", {})
        if not isinstance(namespaces, Mapping):
            raise SRFDValidationError("QA_SCHEMA_FAILURE", "output_schema.namespaces must be an object")
        allowed = {"structural_raw", "structural_derived", "structural_normalized", "comparison_only"}
        if set(namespaces) - allowed:
            raise SRFDValidationError("QA_SCHEMA_FAILURE", "representation contains undeclared namespace")
    elif declared == "SRFDPreregistration":
        required = (
            "research_questions", "hypotheses", "falsifiers", "eligible_population",
            "representation_candidates", "segmentation_candidates", "distance_candidates",
            "family_method_candidates", "configuration_bounds", "stability_metrics",
            "family_strength_rules", "invariant_core_rules", "ambiguity_rules",
            "residual_rules", "failure_attribution_order", "capacity_limits",
            "stop_conditions", "required_output_tables", "operator_decision_surfaces",
        )
        missing = [field for field in required if field not in document]
        if missing:
            raise SRFDValidationError("QA_SCHEMA_FAILURE", "preregistration missing " + ",".join(missing))
