from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping, Sequence

from .serialization import logical_sha256, stable_id

FORBIDDEN_SOURCE_KEYS = frozenset({
    "outcome", "outcomes", "future_return", "return_label", "mfe", "mae",
    "probability", "edge", "risk", "exposure", "trade", "trade_label",
    "order", "execution", "validation_consumed",
})
IMPLEMENTATION_CLASSES = frozenset({f"SRFDI-R{i}" for i in range(1, 10)})
COMPARABILITY_FIELDS = ("instrument", "side", "units", "clock", "representation_schema", "source_quality")


class RepresentationError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _parse_time(value: str) -> datetime:
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise RepresentationError("TIME_PARENT_NOT_FIRST_VALID", f"invalid ISO time: {value}") from exc
    if parsed.tzinfo is None:
        raise RepresentationError("TIME_PARENT_NOT_FIRST_VALID", "time must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _walk_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_SOURCE_KEYS:
                raise RepresentationError("AUTH_SCOPE_EXPANSION", f"forbidden source field {path}.{key}")
            _walk_forbidden(child, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _walk_forbidden(child, f"{path}[{index}]")


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RepresentationError("REP_REQUIRED_DIMENSION_MISSING", f"{field} is not numeric") from exc
    if not result.is_finite():
        raise RepresentationError("REP_REQUIRED_DIMENSION_MISSING", f"{field} is non-finite")
    return result


@dataclass(frozen=True)
class RepresentationPack:
    representation_pack_id: str
    implementation_class_id: str
    architecture_candidate_id: str
    required_fields: tuple[str, ...]
    comparability_domain_id: str
    ordering_semantics: str = "STATIC_VECTOR"
    ablate_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.implementation_class_id not in IMPLEMENTATION_CLASSES:
            raise RepresentationError("QA_SCHEMA_FAILURE", "unknown implementation class")
        if not self.representation_pack_id or not self.comparability_domain_id:
            raise RepresentationError("QA_SCHEMA_FAILURE", "pack and comparability IDs are required")


@dataclass(frozen=True)
class NormalizationPack:
    normalization_pack_id: str
    fit_population_id: str
    fit_cutoff: str
    estimator: str
    bounds: Mapping[str, tuple[str, str]]
    transport_rule: str = "FROZEN_REFERENCE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "normalization_pack_id": self.normalization_pack_id,
            "fit_population_id": self.fit_population_id,
            "fit_cutoff": self.fit_cutoff,
            "estimator": self.estimator,
            "bounds": {key: list(self.bounds[key]) for key in sorted(self.bounds)},
            "transport_rule": self.transport_rule,
        }


def compile_population(records: Iterable[Mapping[str, Any]], *, population_name: str) -> dict[str, Any]:
    accepted: list[str] = []
    excluded: list[dict[str, str]] = []
    source_hashes: list[str] = []
    for item in records:
        record = dict(item)
        _walk_forbidden(record)
        record_id = str(record.get("record_id", "")).strip()
        if not record_id:
            raise RepresentationError("QA_SCHEMA_FAILURE", "source record_id required")
        if record.get("computability_status") == "NOT_EVALUABLE":
            excluded.append({"record_id": record_id, "reason": str(record.get("not_evaluable_reason") or "NOT_EVALUABLE")})
        else:
            accepted.append(record_id)
        source_hashes.append(logical_sha256(record))
    payload = {
        "population_name": population_name,
        "eligible_record_ids": sorted(accepted),
        "exclusions": sorted(excluded, key=lambda value: value["record_id"]),
        "source_hashes": sorted(source_hashes),
    }
    return {**payload, "population_id": stable_id("SRFD.POP.", payload)}


def fit_minmax_normalization(
    records: Iterable[Mapping[str, Any]],
    fields: Sequence[str],
    *,
    fit_population_id: str,
    fit_cutoff: str,
) -> NormalizationPack:
    cutoff = _parse_time(fit_cutoff)
    values: dict[str, list[Decimal]] = {field: [] for field in fields}
    for source in records:
        record = dict(source)
        _walk_forbidden(record)
        if _parse_time(str(record.get("first_valid_time", ""))) > cutoff:
            raise RepresentationError("REP_NORMALIZATION_FIT_CUTOFF_INVALID", "fit record exceeds cutoff")
        structural = record.get("structural")
        if not isinstance(structural, Mapping):
            raise RepresentationError("REP_REQUIRED_DIMENSION_MISSING", "structural mapping required")
        for field in fields:
            if field in structural and structural[field] is not None:
                values[field].append(_decimal(structural[field], field))
    bounds: dict[str, tuple[str, str]] = {}
    for field in fields:
        if not values[field]:
            raise RepresentationError("REP_REQUIRED_DIMENSION_MISSING", f"no fit values for {field}")
        bounds[field] = (str(min(values[field])), str(max(values[field])))
    identity = {
        "fit_population_id": fit_population_id,
        "fit_cutoff": cutoff.isoformat().replace("+00:00", "Z"),
        "estimator": "MINMAX_V0_1",
        "bounds": bounds,
        "transport_rule": "FROZEN_REFERENCE",
    }
    return NormalizationPack(stable_id("SRFD.NORM.", identity), estimator="MINMAX_V0_1", **{key: identity[key] for key in ("fit_population_id", "fit_cutoff", "bounds", "transport_rule")})


def _selected_structural(record: Mapping[str, Any], fields: Sequence[str]) -> dict[str, Any]:
    structural = record.get("structural")
    if not isinstance(structural, Mapping):
        raise RepresentationError("REP_REQUIRED_DIMENSION_MISSING", "structural mapping required")
    missing = [field for field in fields if field not in structural or structural[field] is None]
    if missing:
        raise RepresentationError("REP_REQUIRED_DIMENSION_MISSING", ",".join(missing))
    return {field: structural[field] for field in fields}


def _normalized(raw: Mapping[str, Any], pack: NormalizationPack) -> dict[str, str]:
    output: dict[str, str] = {}
    for field, value in raw.items():
        if field not in pack.bounds:
            raise RepresentationError("REP_REQUIRED_DIMENSION_MISSING", f"normalization missing bound for {field}")
        lo = Decimal(pack.bounds[field][0])
        hi = Decimal(pack.bounds[field][1])
        current = _decimal(value, field)
        if hi == lo:
            result = Decimal("0.5")
        else:
            result = (current - lo) / (hi - lo)
        output[field] = format(result, "f")
    return output


def compile_representation(
    source: Mapping[str, Any],
    pack: RepresentationPack,
    *,
    source_population_id: str,
    normalization_pack: NormalizationPack | None = None,
) -> dict[str, Any]:
    record = dict(source)
    _walk_forbidden(record)
    record_id = str(record.get("record_id", "")).strip()
    if not record_id:
        raise RepresentationError("QA_SCHEMA_FAILURE", "source record_id required")
    first_valid_time = str(record.get("first_valid_time", "")).strip()
    _parse_time(first_valid_time)
    raw: dict[str, Any] = {}
    derived: dict[str, Any] = {}
    normalized: dict[str, Any] = {}
    comparison_only: dict[str, Any] = {}
    missingness: list[str] = []

    if pack.implementation_class_id in {"SRFDI-R1", "SRFDI-R4", "SRFDI-R6", "SRFDI-R7", "SRFDI-R8"}:
        if pack.implementation_class_id == "SRFDI-R8":
            structural = record.get("structural") if isinstance(record.get("structural"), Mapping) else {}
            for field in pack.required_fields:
                if field not in structural or structural[field] is None:
                    missingness.append(field)
                else:
                    raw[field] = structural[field]
            comparison_only["missingness_mask"] = {field: field in missingness for field in pack.required_fields}
        else:
            raw = _selected_structural(record, pack.required_fields)
        if pack.implementation_class_id == "SRFDI-R6":
            for field in pack.ablate_fields:
                raw.pop(field, None)
            derived["ablation_fields"] = list(pack.ablate_fields)
        if pack.implementation_class_id == "SRFDI-R7":
            context = record.get("parent_context")
            derived["parent_context"] = context if isinstance(context, Mapping) else None
        if pack.implementation_class_id == "SRFDI-R4":
            if normalization_pack is None:
                raise RepresentationError("REP_NORMALIZATION_FIT_CUTOFF_INVALID", "normalization pack required")
            normalized = _normalized(raw, normalization_pack)
    elif pack.implementation_class_id == "SRFDI-R2":
        sequence = record.get("sequence")
        if not isinstance(sequence, Sequence) or isinstance(sequence, (str, bytes, bytearray)) or not sequence:
            raise RepresentationError("REP_REQUIRED_DIMENSION_MISSING", "sequence required")
        for field in pack.required_fields:
            field_values = [_decimal(item[field], field) for item in sequence if isinstance(item, Mapping) and item.get(field) is not None]
            if not field_values:
                raise RepresentationError("REP_REQUIRED_DIMENSION_MISSING", field)
            derived[field + "_mean"] = format(sum(field_values, Decimal("0")) / Decimal(len(field_values)), "f")
        derived["duration_count"] = len(sequence)
    elif pack.implementation_class_id == "SRFDI-R3":
        sequence = record.get("sequence")
        if not isinstance(sequence, Sequence) or isinstance(sequence, (str, bytes, bytearray)):
            raise RepresentationError("REP_REQUIRED_DIMENSION_MISSING", "sequence required")
        derived["ordered_sequence"] = [dict(item) if isinstance(item, Mapping) else item for item in sequence]
    elif pack.implementation_class_id == "SRFDI-R5":
        sequence = record.get("sequence")
        if not isinstance(sequence, Sequence) or isinstance(sequence, (str, bytes, bytearray)) or not sequence:
            raise RepresentationError("REP_REQUIRED_DIMENSION_MISSING", "sequence required")
        derived["ordered_sequence"] = [dict(item) if isinstance(item, Mapping) else item for item in sequence]
        derived["duration_count"] = len(sequence)
    elif pack.implementation_class_id == "SRFDI-R9":
        comparison_only["null_control_token"] = stable_id("SRFD.NULL.", {"record_id": record_id, "pack": pack.representation_pack_id})

    payload = {
        "representation_pack_id": pack.representation_pack_id,
        "architecture_candidate_id": pack.architecture_candidate_id,
        "implementation_class_id": pack.implementation_class_id,
        "source_population_id": source_population_id,
        "source_record_ids": [record_id],
        "structural_raw": raw,
        "structural_derived": derived,
        "structural_normalized": normalized,
        "comparison_only": comparison_only,
        "missingness": missingness,
        "comparability_domain_id": pack.comparability_domain_id,
        "ordering_semantics": pack.ordering_semantics,
        "first_valid_time": first_valid_time,
        "evaluation_cutoff": first_valid_time,
        "normalization_pack_id": normalization_pack.normalization_pack_id if normalization_pack else None,
        "authority_state": "FIXTURE_ONLY",
    }
    return {**payload, "representation_id": stable_id("SRFD.REP.", payload), "logical_hash": logical_sha256(payload)}


def check_comparable(left: Mapping[str, Any], right: Mapping[str, Any]) -> tuple[bool, str | None]:
    for field in COMPARABILITY_FIELDS:
        if left.get(field) != right.get(field):
            code = "COMP_NOT_COMPARABLE_INSTRUMENT" if field == "instrument" else "COMP_" + field.upper() + "_INCOMPATIBLE"
            return False, code
    return True, None
