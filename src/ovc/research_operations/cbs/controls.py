from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .identity import CBSContractError, seal_object


REQUIRED_CONTROL_CLASSES = frozenset(
    {
        "NO_SEGMENTATION", "BOUNDARY_PRESERVING_SHIFT", "DEPENDENCE_PRESERVING_OFFSET_OR_BLOCK",
        "PARAMETER_NEIGHBOUR", "REPRESENTATION_PERTURBATION", "CONTEXT_TIME_PARTITION",
    }
)


def build_null_execution_manifest(
    *, control_id: str, control_class: str, algorithm_id: str, code_hash: str,
    dependency_ids: Sequence[str], initialization: Mapping[str, Any], seed: int | None,
    source_segment_lengths: Sequence[int], break_censor_policy: str, randomisation_rule: str,
    preserved_structures: Sequence[str], destroyed_structures: Sequence[str],
    retained_dependence: Sequence[str], adequacy_invalidators: Sequence[str], frozen_before_results: bool,
) -> dict[str, Any]:
    if control_class not in REQUIRED_CONTROL_CLASSES:
        raise CBSContractError("NULL_EXECUTION_UNFROZEN:UNKNOWN_CONTROL_CLASS")
    if not frozen_before_results:
        raise CBSContractError("INVALID_GENERATION:POST_RESULT_NULL_SELECTION")
    if not algorithm_id or len(code_hash) != 64 or not source_segment_lengths:
        raise CBSContractError("NULL_EXECUTION_UNFROZEN")
    if any(not isinstance(length, int) or length <= 0 for length in source_segment_lengths):
        raise CBSContractError("NULL_EXECUTION_UNFROZEN:SEGMENT_LENGTH")
    return seal_object(
        {
            "schema": "ovc-cbs-null-execution-manifest/v0.1", "control_id": control_id,
            "control_class": control_class, "algorithm_id": algorithm_id, "code_hash": code_hash,
            "dependency_ids": sorted(set(dependency_ids)), "initialization": dict(initialization), "seed": seed,
            "source_segment_lengths": list(source_segment_lengths), "break_censor_policy": break_censor_policy,
            "randomisation_rule": randomisation_rule, "preserved_structures": sorted(set(preserved_structures)),
            "destroyed_structures": sorted(set(destroyed_structures)),
            "retained_dependence": sorted(set(retained_dependence)),
            "adequacy_invalidators": sorted(set(adequacy_invalidators)), "output_completeness_required": True,
            "frozen_before_results": True,
        }, id_field="null_execution_manifest_id"
    )


def assess_null_adequacy(*, manifest: Mapping[str, Any], output_complete: bool, invalidators_observed: Sequence[str]) -> dict[str, Any]:
    known = set(manifest.get("adequacy_invalidators", []))
    observed = sorted(set(invalidators_observed))
    unexpected = sorted(set(observed) - known)
    adequate = output_complete and not observed and not unexpected
    return seal_object(
        {"schema": "ovc-cbs-null-adequacy-assessment/v0.1", "null_execution_manifest_id": manifest.get("null_execution_manifest_id"),
         "output_complete": output_complete, "invalidators_observed": observed, "unexpected_invalidators": unexpected,
         "adequate": adequate, "disposition": "PASS" if adequate else "NOT_EVALUABLE"},
        id_field="null_adequacy_assessment_id",
    )


def validate_control_coverage(manifests: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    classes = {str(item.get("control_class")) for item in manifests}
    missing = sorted(REQUIRED_CONTROL_CLASSES - classes)
    if missing:
        raise CBSContractError(f"NULL_EXECUTION_UNFROZEN:MISSING:{','.join(missing)}")
    if len(manifests) < len(REQUIRED_CONTROL_CLASSES):
        raise CBSContractError("NULL_EXECUTION_UNFROZEN")
    return {"required_control_classes": sorted(REQUIRED_CONTROL_CLASSES), "covered_control_classes": sorted(classes),
            "complete": True, "b9_substitution": False}
