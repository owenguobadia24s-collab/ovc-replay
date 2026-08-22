from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def validate_correspondence_series_root(
    reference_module: Any,
    *,
    projection: Mapping[str, Any],
    generation: Mapping[str, Any] | None,
    identity_history: Sequence[Mapping[str, Any]],
) -> None:
    """Prove canonical Series/root reachability before correspondence admission.

    A deterministic Series identifier is identity evidence only.  It never proves that
    the generation being staged is ``Series.first_generation_id``.  Every admission
    therefore requires an exact, reconciled identity history containing both the
    canonical Series root and the generation/projection currently being staged.
    """

    validated_generation = reference_module._validate_projection_generation_binding(
        projection, generation
    )
    canonical_projection = reference_module._validate_projection(projection)

    if not identity_history:
        raise reference_module.ReferenceEngineError(
            "correspondence requires exact canonical series/root identity history"
        )

    try:
        reconciled = reference_module._reconcile_identity_bundles(identity_history)
    except reference_module.ReferenceEngineError as exc:
        if str(exc) == "same series identity has conflicting canonical series content":
            raise reference_module.ReferenceEngineError(
                "series first-generation binding conflicts across canonical series/root identity history"
            ) from exc
        raise

    current_matches = [
        bundle
        for bundle in reconciled
        if bundle[1]["generation_id"] == canonical_projection["generation_id"]
    ]
    if len(current_matches) != 1:
        raise reference_module.ReferenceEngineError(
            "correspondence generation is unavailable from canonical series/root identity history"
        )

    series, historical_generation, historical_projection = current_matches[0]
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

    first_generation_id = series["first_generation_id"]
    root_matches = [
        bundle
        for bundle in reconciled
        if bundle[1]["generation_id"] == first_generation_id
    ]
    if len(root_matches) != 1:
        raise reference_module.ReferenceEngineError(
            "series first-generation binding is unavailable or unverifiable"
        )
    root_series, root_generation, root_projection = root_matches[0]
    if (
        root_series["series_id"] != series["series_id"]
        or root_generation["series_id"] != series["series_id"]
    ):
        raise reference_module.ReferenceEngineError(
            "series first-generation binding crosses series identity"
        )
    if reference_module._canonical_bytes(root_series) != reference_module._canonical_bytes(series):
        raise reference_module.ReferenceEngineError(
            "series root record differs from canonical current-series record"
        )

    expected_root_series_id = (
        "p1:series:"
        + reference_module.canonical_sha256(
            {
                "owner": root_projection["owner_semantic_binding"],
                "projection_sha256": root_projection["projection_sha256"],
            }
        )
    )
    if series["series_id"] != expected_root_series_id:
        raise reference_module.ReferenceEngineError(
            "series first-generation deterministic identity mismatch"
        )

    current_direct_series_id = (
        "p1:series:"
        + reference_module.canonical_sha256(
            {
                "owner": canonical_projection["owner_semantic_binding"],
                "projection_sha256": canonical_projection["projection_sha256"],
            }
        )
    )
    current_generation_id = validated_generation["generation_id"]
    if validated_generation["series_id"] == current_direct_series_id:
        if first_generation_id != current_generation_id:
            raise reference_module.ReferenceEngineError(
                "deterministic series identity does not prove first-generation binding; "
                "exact rediscovery must resolve to the canonical root generation"
            )
    elif first_generation_id == current_generation_id:
        raise reference_module.ReferenceEngineError(
            "first-generation series identity does not bind its canonical projection"
        )

    if (
        reference_module.exact_semantic_equal(canonical_projection, root_projection)
        and current_generation_id != first_generation_id
    ):
        raise reference_module.ReferenceEngineError(
            "unchanged semantic rediscovery must resolve to the canonical first generation"
        )
