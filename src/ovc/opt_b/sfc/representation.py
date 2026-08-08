from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping, Sequence

from .c2e_adapter import extract_structural_axes
from .serialization import logical_hash


class SFCRepresentationError(ValueError):
    pass


def _time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise SFCRepresentationError("SFC_SOURCE_SCHEMA_INVALID:INVALID_TIME") from exc
    if parsed.tzinfo is None:
        raise SFCRepresentationError("SFC_SOURCE_SCHEMA_INVALID:TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc)


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SFCRepresentationError("SFC_REQUIRED_DIMENSION_MISSING:" + field) from exc
    if not result.is_finite():
        raise SFCRepresentationError("SFC_REQUIRED_DIMENSION_MISSING:" + field)
    return result


@dataclass(frozen=True)
class RepresentationPack:
    representation_pack_id: str
    representation_class: str
    required_dimensions: tuple[str, ...]
    optional_dimensions: tuple[str, ...] = ()
    comparability_domain_id: str = "SFC.COMP.DOMAIN.BASE.v0_1"
    context_roles: tuple[str, ...] = ("STRATIFICATION_ONLY",)


@dataclass(frozen=True)
class NormalizationPack:
    normalization_pack_id: str
    fit_population_id: str
    fit_cutoff: str
    bounds: Mapping[str, tuple[str, str]]
    estimator: str = "MINMAX_V0_1"


def compile_population(records: Iterable[Mapping[str, Any]], *, population_rule_pack_id: str, population_cutoff: str) -> dict[str, Any]:
    seen: list[str] = []
    eligible: list[str] = []
    exclusions: list[dict[str, str]] = []
    source_hashes: list[str] = []
    cutoff = _time(population_cutoff)
    for record in records:
        item = dict(record)
        episode_id = str(item.get("episode_id", ""))
        if not episode_id:
            raise SFCRepresentationError("SFC_SOURCE_SCHEMA_INVALID:EPISODE_ID")
        seen.append(episode_id)
        source_hashes.append(str(item.get("source_record_hash") or logical_hash(item)))
        if _time(str(item.get("first_valid_time", ""))) > cutoff:
            exclusions.append({"episode_id": episode_id, "reason_code": "SFC_NOT_COMPARABLE_CHRONOLOGY"})
        elif item.get("availability_missingness") == "NOT_EVALUABLE":
            exclusions.append({"episode_id": episode_id, "reason_code": "SFC_NOT_EVALUABLE"})
        else:
            eligible.append(episode_id)
    identity = {
        "population_rule_pack_id": population_rule_pack_id,
        "population_cutoff": population_cutoff,
        "source_hashes": sorted(source_hashes),
        "eligible": sorted(eligible),
        "exclusions": sorted(exclusions, key=lambda row: row["episode_id"]),
    }
    return {
        "population_id": "SFC.POP." + logical_hash(identity)[:24],
        "population_rule_pack_id": population_rule_pack_id,
        "population_cutoff": population_cutoff,
        "eligible_source_ids": sorted(eligible),
        "exclusion_records": sorted(exclusions, key=lambda row: row["episode_id"]),
        "denominator_total_seen": len(seen),
        "denominator_eligible": len(eligible),
        "denominator_excluded": len(exclusions),
        "source_hashes": sorted(source_hashes),
        "logical_hash": logical_hash(identity),
    }


def fit_minmax(records: Sequence[Mapping[str, Any]], fields: Sequence[str], *, fit_population_id: str, fit_cutoff: str) -> NormalizationPack:
    cutoff = _time(fit_cutoff)
    values: dict[str, list[Decimal]] = {field: [] for field in fields}
    for record in records:
        if _time(str(record["first_valid_time"])) > cutoff:
            raise SFCRepresentationError("SFC_NORMALIZATION_FIT_CUTOFF_INVALID")
        axes = extract_structural_axes(record)
        for field in fields:
            for value in axes.get(field, []):
                values[field].append(_decimal(value, field))
    bounds: dict[str, tuple[str, str]] = {}
    for field in fields:
        if not values[field]:
            raise SFCRepresentationError("SFC_REQUIRED_DIMENSION_MISSING:" + field)
        bounds[field] = (str(min(values[field])), str(max(values[field])))
    identity = {"fit_population_id": fit_population_id, "fit_cutoff": fit_cutoff, "bounds": bounds, "estimator": "MINMAX_V0_1"}
    return NormalizationPack("SFC.NORM." + logical_hash(identity)[:24], fit_population_id, fit_cutoff, bounds)


def _mean(values: Sequence[Any], field: str) -> str:
    if not values:
        raise SFCRepresentationError("SFC_REQUIRED_DIMENSION_MISSING:" + field)
    numbers = [_decimal(value, field) for value in values]
    return format(sum(numbers, Decimal("0")) / Decimal(len(numbers)), "f")


def _normalize(raw: Mapping[str, Any], pack: NormalizationPack) -> dict[str, str]:
    output: dict[str, str] = {}
    for field, value in raw.items():
        if field not in pack.bounds:
            raise SFCRepresentationError("SFC_NORMALIZATION_FIT_CUTOFF_INVALID:" + field)
        lo, hi = (Decimal(part) for part in pack.bounds[field])
        current = _decimal(value, field)
        result = Decimal("0.5") if lo == hi else (current - lo) / (hi - lo)
        output[field] = format(result, "f")
    return output


def compile_representation(adapted: Mapping[str, Any], pack: RepresentationPack, *, source_population_id: str, normalization_pack: NormalizationPack | None = None) -> dict[str, Any]:
    axes = extract_structural_axes(adapted)
    raw: dict[str, Any] = {}
    derived: dict[str, Any] = {}
    normalized: dict[str, Any] = {}
    missing: dict[str, bool] = {}
    for field in pack.required_dimensions:
        if not axes.get(field):
            raise SFCRepresentationError("SFC_REQUIRED_DIMENSION_MISSING:" + field)
        raw[field] = _mean(axes[field], field)
        missing[field] = False
    for field in pack.optional_dimensions:
        if axes.get(field):
            raw[field] = _mean(axes[field], field)
            missing[field] = False
        else:
            missing[field] = True
    if pack.representation_class in {"SRI-R2", "SRI-R5"}:
        derived["membership_count"] = len(adapted["membership_references"])
        derived["boundary_event_count"] = len(adapted["boundary_event_references"])
    if pack.representation_class in {"SRI-R3", "SRI-R5"}:
        derived["ordered_membership"] = list(adapted["membership_references"])
    if pack.representation_class == "SRI-R9":
        raw = {}
        derived = {"null_control_token": "SFC.NULL." + logical_hash({"episode": adapted["episode_id"], "pack": pack.representation_pack_id})[:24]}
    if normalization_pack is not None:
        if _time(normalization_pack.fit_cutoff) > _time(str(adapted["evaluation_cutoff"])):
            raise SFCRepresentationError("SFC_NORMALIZATION_FIT_CUTOFF_INVALID")
        normalized = _normalize(raw, normalization_pack)
    comparison_only = {
        "missingness_mask": missing,
        "lifecycle_status": adapted["lifecycle_status"],
        "availability_missingness": adapted["availability_missingness"],
    }
    if "REMAP" in adapted:
        comparison_only["remap"] = adapted["REMAP"]
    payload = {
        "source_ids": [adapted["episode_id"]],
        "source_schema_versions": ["c2e/v0_2", "sfc/v0_1"],
        "source_population_id": source_population_id,
        "representation_pack_id": pack.representation_pack_id,
        "representation_class": pack.representation_class,
        "structural_raw": raw,
        "structural_derived": derived,
        "structural_normalized": normalized,
        "comparison_only": comparison_only,
        "missingness": missing,
        "ordering": "FVT_THEN_SOURCE_ID",
        "scale_id": adapted["scale_id"],
        "context": {"roles": list(pack.context_roles)},
        "comparability_domain_id": pack.comparability_domain_id,
        "first_valid_time": adapted["first_valid_time"],
        "evaluation_cutoff": adapted["evaluation_cutoff"],
        "parent_first_valid_lineage": sorted((ref, obj["first_valid_time"]) for ref, obj in adapted["source_objects"].items()),
        "authority_state": "INACTIVE_CONFORMANCE_ONLY",
    }
    payload["representation_id"] = "SFC.REP." + logical_hash(payload)[:24]
    payload["logical_hash"] = logical_hash(payload)
    return payload


def compile_bundle(records: Sequence[Mapping[str, Any]], *, bundle_role: str, source_population_id: str, representation_pack_id: str, comparability_domain_id: str) -> dict[str, Any]:
    ids = sorted(str(record["representation_id"]) for record in records)
    identity = {"ids": ids, "role": bundle_role, "population": source_population_id, "pack": representation_pack_id, "domain": comparability_domain_id}
    return {"bundle_id":"SFC.BUNDLE."+logical_hash(identity)[:24],"ordered_representation_ids":ids,"bundle_role":bundle_role,"source_population_id":source_population_id,"representation_pack_id":representation_pack_id,"comparability_domain_id":comparability_domain_id,"context_binding":"EXPLICIT","logical_hash":logical_hash(identity)}
