from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import wraps
from typing import Any


def _validate_correspondence_series_root(
    reference_module: Any,
    *,
    projection: Mapping[str, Any],
    generation: Mapping[str, Any] | None,
    identity_history: Sequence[Mapping[str, Any]],
) -> None:
    """Prove that a correspondence generation is rooted in canonical Series identity."""
    validated_generation = reference_module._validate_projection_generation_binding(
        projection, generation
    )
    canonical_projection = reference_module._validate_projection(projection)
    direct_root_series_id = (
        "p1:series:"
        + reference_module.canonical_sha256(
            {
                "owner": canonical_projection["owner_semantic_binding"],
                "projection_sha256": canonical_projection["projection_sha256"],
            }
        )
    )
    if validated_generation["series_id"] == direct_root_series_id:
        return
    if not identity_history:
        raise reference_module.ReferenceEngineError(
            "successor correspondence requires exact canonical series/root identity history"
        )
    try:
        reconciled = reference_module._reconcile_identity_bundles(identity_history)
    except reference_module.ReferenceEngineError as exc:
        if str(exc) == "same series identity has conflicting canonical series content":
            raise reference_module.ReferenceEngineError(
                "series first-generation binding conflicts across canonical series/root identity history"
            ) from exc
        raise
    matches = [
        bundle
        for bundle in reconciled
        if bundle[1]["generation_id"] == canonical_projection["generation_id"]
    ]
    if len(matches) != 1:
        raise reference_module.ReferenceEngineError(
            "correspondence generation is unavailable from canonical series/root identity history"
        )
    series, historical_generation, historical_projection = matches[0]
    if series["series_id"] != validated_generation["series_id"]:
        raise reference_module.ReferenceEngineError(
            "correspondence generation crosses canonical series identity"
        )
    if reference_module._canonical_bytes(historical_generation) != reference_module._canonical_bytes(
        validated_generation
    ):
        raise reference_module.ReferenceEngineError(
            "correspondence generation differs from canonical identity history"
        )
    if reference_module._canonical_bytes(historical_projection) != reference_module._canonical_bytes(
        canonical_projection
    ):
        raise reference_module.ReferenceEngineError(
            "correspondence projection differs from canonical identity history"
        )


def install_reference_series_root_guard(reference_module: Any) -> None:
    if getattr(reference_module, "_P1CDII_REMEDIATION4_SERIES_ROOT_GUARD", False):
        return
    original = reference_module.stage_correspondence

    @wraps(original)
    def hardened_stage_correspondence(
        *,
        left_projection: Mapping[str, Any],
        right_projection: Mapping[str, Any],
        left_generation_record: Mapping[str, Any] | None = None,
        right_generation_record: Mapping[str, Any] | None = None,
        planes: Mapping[str, str],
        admission_basis: str,
        source_relation_ref: str | None = None,
        review_ref: str | None = None,
        plane_evidence_records: Sequence[Mapping[str, Any]] = (),
        independence_evidence: Sequence[Mapping[str, Any]] = (),
        as_of_time: str | None = None,
        left_identity_history: Sequence[Mapping[str, Any]] = (),
        right_identity_history: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        _validate_correspondence_series_root(
            reference_module,
            projection=left_projection,
            generation=left_generation_record,
            identity_history=left_identity_history,
        )
        _validate_correspondence_series_root(
            reference_module,
            projection=right_projection,
            generation=right_generation_record,
            identity_history=right_identity_history,
        )
        return original(
            left_projection=left_projection,
            right_projection=right_projection,
            left_generation_record=left_generation_record,
            right_generation_record=right_generation_record,
            planes=planes,
            admission_basis=admission_basis,
            source_relation_ref=source_relation_ref,
            review_ref=review_ref,
            plane_evidence_records=plane_evidence_records,
            independence_evidence=independence_evidence,
            as_of_time=as_of_time,
        )

    reference_module.stage_correspondence = hardened_stage_correspondence
    reference_module._P1CDII_REMEDIATION4_SERIES_ROOT_GUARD = True
