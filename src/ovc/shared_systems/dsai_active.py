"""Prospective DSAI-only active Shared Systems consumption route.

This module does not switch the DSAI current binding. It constructs and verifies
an identity-preserving ACTIVE_CANDIDATE route under SHSI-G-DSAI-ADOPTION-1.
Historical SHSI-WP7 shadow contracts remain unchanged.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping


class DSAIAdoptionError(ValueError):
    """A fail-closed DSAI Shared Systems adoption contract violation."""


DSAI_ADOPTION_SURFACES = frozenset(
    {"ENVIRONMENT", "RUN", "ASSURANCE", "RECEIPT", "CURRENTNESS"}
)
DSAI_ADOPTION_AUTHORITY = (
    "DSAI_ONLY_SHARED_SYSTEMS_CONSUMER_ADOPTION_AND_CURRENT_BINDING_CUTOVER_"
    "SUBJECT_TO_EXACT_FINAL_ASSURANCE"
)


def _text(value: str, field: str, *, exact: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise DSAIAdoptionError(f"{field.upper()}_REQUIRED")
    if exact and "latest" in value.casefold():
        raise DSAIAdoptionError(f"{field.upper()}_EXACT_REF_REQUIRED")
    return value


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DSAIAdoptionError("NON_CANONICAL_DSAI_ADOPTION_VALUE") from exc


def _logical_id(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class DSAIActiveConsumptionBinding:
    binding_id: str
    consumer_programme_id: str
    consumer_generation: str
    shared_service_id: str
    shared_release_id: str
    surfaces: tuple[str, ...]
    authority_ref: str
    status: str = "ACTIVE_CANDIDATE"
    current_binding_changed: bool = False
    authority_effect: str = DSAI_ADOPTION_AUTHORITY

    def __post_init__(self) -> None:
        for field in (
            "binding_id",
            "consumer_programme_id",
            "consumer_generation",
            "shared_service_id",
            "shared_release_id",
            "authority_ref",
        ):
            _text(
                getattr(self, field),
                field,
                exact=field in {"consumer_generation", "shared_release_id"},
            )
        if self.consumer_programme_id != "OVC-DSAI-v0.1":
            raise DSAIAdoptionError("NON_DSAI_CONSUMER_FORBIDDEN")
        if set(self.surfaces) != DSAI_ADOPTION_SURFACES or len(self.surfaces) != len(
            DSAI_ADOPTION_SURFACES
        ):
            raise DSAIAdoptionError("DSAI_ADOPTION_SURFACE_SET_INVALID")
        if self.status != "ACTIVE_CANDIDATE" or self.current_binding_changed:
            raise DSAIAdoptionError("PREMATURE_DSAI_CURRENT_BINDING_SWITCH_FORBIDDEN")
        if self.authority_effect != DSAI_ADOPTION_AUTHORITY:
            raise DSAIAdoptionError("DSAI_ADOPTION_AUTHORITY_MISMATCH")

    @property
    def logical_id(self) -> str:
        return _logical_id(asdict(self))


@dataclass(frozen=True)
class DSAIActiveSurfaceEnvelope:
    binding_ref: str
    surface: str
    source_schema: str
    source_record: Mapping[str, Any]
    source_logical_sha256: str
    status: str = "ACTIVE_CANDIDATE"
    writes_performed: tuple[str, ...] = ()
    semantic_inventions: tuple[str, ...] = ()
    authority_effect: str = DSAI_ADOPTION_AUTHORITY

    def __post_init__(self) -> None:
        _text(self.binding_ref, "binding_ref")
        _text(self.source_schema, "source_schema", exact=True)
        if self.surface not in DSAI_ADOPTION_SURFACES:
            raise DSAIAdoptionError("DSAI_ADOPTION_SURFACE_UNKNOWN")
        if not isinstance(self.source_record, Mapping):
            raise DSAIAdoptionError("DSAI_ADOPTION_SOURCE_RECORD_INVALID")
        if _logical_id(dict(self.source_record)) != self.source_logical_sha256:
            raise DSAIAdoptionError("DSAI_ADOPTION_SOURCE_IDENTITY_MISMATCH")
        if self.status != "ACTIVE_CANDIDATE" or self.writes_performed:
            raise DSAIAdoptionError("DSAI_ADOPTION_WRITE_OR_CURRENT_ACTIVATION_FORBIDDEN")
        if self.semantic_inventions:
            raise DSAIAdoptionError("DSAI_ADOPTION_SEMANTIC_FABRICATION")
        if self.authority_effect != DSAI_ADOPTION_AUTHORITY:
            raise DSAIAdoptionError("DSAI_ADOPTION_AUTHORITY_MISMATCH")

    @property
    def logical_id(self) -> str:
        return _logical_id(
            {
                **asdict(self),
                "source_record": dict(self.source_record),
            }
        )


def consume_dsai_surface(
    binding: DSAIActiveConsumptionBinding,
    surface: str,
    source_record: Mapping[str, Any],
) -> DSAIActiveSurfaceEnvelope:
    if surface not in binding.surfaces:
        raise DSAIAdoptionError("DSAI_ADOPTION_SURFACE_NOT_BOUND")
    schema = source_record.get("schema")
    if not isinstance(schema, str) or not schema:
        raise DSAIAdoptionError("DSAI_ADOPTION_SOURCE_SCHEMA_REQUIRED")
    source = dict(source_record)
    return DSAIActiveSurfaceEnvelope(
        binding.logical_id,
        surface,
        schema,
        source,
        _logical_id(source),
    )


def unwrap_dsai_active_surface(envelope: DSAIActiveSurfaceEnvelope) -> dict[str, Any]:
    source = dict(envelope.source_record)
    if _logical_id(source) != envelope.source_logical_sha256:
        raise DSAIAdoptionError("DSAI_ADOPTION_SOURCE_IDENTITY_MISMATCH")
    return source


@dataclass(frozen=True)
class DSAIAdoptionEquivalenceReceipt:
    receipt_id: str
    surface: str
    reference_logical_sha256: str
    candidate_logical_sha256: str
    divergent_paths: tuple[str, ...]
    status: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        _text(self.receipt_id, "receipt_id")
        if self.surface not in DSAI_ADOPTION_SURFACES:
            raise DSAIAdoptionError("DSAI_ADOPTION_SURFACE_UNKNOWN")
        expected = "PASS" if not self.divergent_paths else "BLOCK"
        if self.status != expected:
            raise DSAIAdoptionError("DSAI_ADOPTION_EQUIVALENCE_STATUS_INCONSISTENT")
        if self.authority_effect != "NONE":
            raise DSAIAdoptionError("DSAI_ADOPTION_RECEIPT_AUTHORITY_EFFECT_FORBIDDEN")


def compare_active_candidate(
    receipt_id: str,
    surface: str,
    reference: Mapping[str, Any],
    envelope: DSAIActiveSurfaceEnvelope,
) -> DSAIAdoptionEquivalenceReceipt:
    candidate = unwrap_dsai_active_surface(envelope)
    divergent = () if dict(reference) == candidate else ("$",)
    return DSAIAdoptionEquivalenceReceipt(
        receipt_id,
        surface,
        _logical_id(dict(reference)),
        _logical_id(candidate),
        divergent,
        "PASS" if not divergent else "BLOCK",
    )


@dataclass(frozen=True)
class DSAIRollbackReceipt:
    receipt_id: str
    pre_adoption_current_binding_ref: str
    candidate_binding_ref: str
    restored_binding_ref: str
    active_route_disabled: bool
    historical_shadow_preserved: bool
    requalification_required: bool
    status: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in (
            "receipt_id",
            "pre_adoption_current_binding_ref",
            "candidate_binding_ref",
            "restored_binding_ref",
        ):
            _text(getattr(self, field), field)
        passed = (
            self.restored_binding_ref == self.pre_adoption_current_binding_ref
            and self.active_route_disabled
            and self.historical_shadow_preserved
            and self.requalification_required
        )
        if self.status != ("PASS" if passed else "BLOCK"):
            raise DSAIAdoptionError("DSAI_ADOPTION_ROLLBACK_STATUS_INCONSISTENT")
        if self.authority_effect != "NONE":
            raise DSAIAdoptionError("DSAI_ADOPTION_ROLLBACK_AUTHORITY_EFFECT_FORBIDDEN")


def prove_rollback(
    receipt_id: str,
    *,
    pre_adoption_current_binding_ref: str,
    candidate_binding_ref: str,
    restored_binding_ref: str,
    active_route_disabled: bool,
    historical_shadow_preserved: bool,
    requalification_required: bool,
) -> DSAIRollbackReceipt:
    passed = (
        restored_binding_ref == pre_adoption_current_binding_ref
        and active_route_disabled
        and historical_shadow_preserved
        and requalification_required
    )
    return DSAIRollbackReceipt(
        receipt_id,
        pre_adoption_current_binding_ref,
        candidate_binding_ref,
        restored_binding_ref,
        active_route_disabled,
        historical_shadow_preserved,
        requalification_required,
        "PASS" if passed else "BLOCK",
    )
