from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .representation import RepresentationError, RepresentationPack, compile_representation
from .serialization import stable_id


AXES = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY")
AVAILABLE = "AVAILABLE_PREBENCHMARK"


class RealSourcePackError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RealSourcePackError("REP_REQUIRED_DIMENSION_MISSING", f"{label} must be an object")
    return value


def _axis(record: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    return _mapping(_mapping(_mapping(record.get("native_c2"), "native_c2").get("axes"), "native_c2.axes").get(name), f"native_c2.axes.{name}")


def _status_value_token(record: Mapping[str, Any], axis_name: str) -> str:
    item = _axis(record, axis_name)
    status = str(item.get("status") or "")
    value = item.get("value")
    reason = item.get("reason_code")
    if value is not None:
        return f"VALUE::{value}"
    if not status:
        raise RealSourcePackError("REP_REQUIRED_DIMENSION_MISSING", f"{axis_name}.status required")
    if not reason:
        raise RealSourcePackError("REP_REQUIRED_DIMENSION_MISSING", f"{axis_name}.reason_code required when value is null")
    return f"MISSING::{status}::{reason}"


def find_pack(registry: Mapping[str, Any], implementation_class_id: str) -> Mapping[str, Any]:
    for item in registry.get("packs", ()):
        if isinstance(item, Mapping) and item.get("id") == implementation_class_id:
            return item
    raise RealSourcePackError("REP_PACK_NOT_FOUND", implementation_class_id)


def _variant(pack: Mapping[str, Any], variant_id: str | None) -> Mapping[str, Any] | None:
    variants = pack.get("variants")
    if not variants:
        if variant_id is not None:
            raise RealSourcePackError("REP_VARIANT_NOT_FOUND", variant_id)
        return None
    if variant_id is None:
        raise RealSourcePackError("REP_VARIANT_REQUIRED", str(pack.get("id")))
    for item in variants:
        if isinstance(item, Mapping) and item.get("variant_id") == variant_id:
            return item
    raise RealSourcePackError("REP_VARIANT_NOT_FOUND", variant_id)


def _ensure_source_envelope(record: Mapping[str, Any]) -> None:
    if record.get("adapter_semantics") != "SCHEMA_PRESERVING_NO_REPRESENTATION_FIELD_SELECTION":
        raise RealSourcePackError("AUTH_SCOPE_EXPANSION", "WP2C schema-preserving adapter record required")
    for field in ("record_id", "first_valid_time", "instrument", "side", "clock", "representation_schema", "source_quality", "native_c2", "source_lineage"):
        if field not in record:
            raise RealSourcePackError("REP_REQUIRED_DIMENSION_MISSING", field)


def _project_structural(
    record: Mapping[str, Any],
    registry: Mapping[str, Any],
    pack: Mapping[str, Any],
    variant: Mapping[str, Any] | None,
) -> dict[str, Any]:
    implementation = str(pack["id"])
    if implementation == "SRFDI-R8":
        return {f"{axis}.token": _status_value_token(record, axis) for axis in pack.get("axis_order", AXES)}
    if implementation == "SRFDI-R9":
        return {}
    if implementation == "SRFDI-R1":
        axes = tuple(str(axis) for axis in pack.get("axis_order", AXES))
    elif implementation == "SRFDI-R6":
        base_pack = find_pack(registry, str(pack.get("base") or "SRFDI-R1"))
        drop_axis = str((variant or {}).get("drop_axis") or "")
        axes = tuple(str(axis) for axis in base_pack.get("axis_order", AXES) if str(axis) != drop_axis)
    else:
        raise RealSourcePackError("REP_DEPENDENCY_UNAVAILABLE", implementation)
    structural: dict[str, Any] = {}
    for axis_name in axes:
        value = _axis(record, axis_name).get("value")
        if value is None:
            raise RealSourcePackError("REP_REQUIRED_DIMENSION_MISSING", f"native_c2.axes.{axis_name}.value")
        structural[f"{axis_name}.value"] = value
    return structural


def compile_real_source_representation(
    adapted_record: Mapping[str, Any],
    pack_registry: Mapping[str, Any],
    implementation_class_id: str,
    *,
    source_population_id: str,
    variant_id: str | None = None,
) -> dict[str, Any]:
    """Compile one WP2C-adapted C2 record under an exact WP9S pack.

    This function is deliberately I/O-free. It cannot fetch a provider, read June,
    fit a normalization pack, inspect benchmark outcomes, or mutate source bytes.
    """
    _ensure_source_envelope(adapted_record)
    pack_spec = find_pack(pack_registry, implementation_class_id)
    if pack_spec.get("status") != AVAILABLE:
        raise RealSourcePackError(str(pack_spec.get("reason_code") or "REP_DEPENDENCY_UNAVAILABLE"), str(pack_spec.get("reason") or implementation_class_id))
    variant = _variant(pack_spec, variant_id)

    source = deepcopy(dict(adapted_record))
    structural = _project_structural(source, pack_registry, pack_spec, variant)
    generic = {
        "record_id": source["record_id"],
        "first_valid_time": source["first_valid_time"],
        "instrument": source["instrument"],
        "side": source["side"],
        "clock": source["clock"],
        "units": str(pack_spec.get("units") or source.get("units") or "MIXED_TYPED_C2"),
        "representation_schema": f"{source['representation_schema']}::{implementation_class_id}::{variant_id or 'BASE'}::v0.2",
        "source_quality": source["source_quality"],
        "structural": structural,
    }
    required_fields = tuple(structural)
    ablate_fields: tuple[str, ...] = ()
    if implementation_class_id == "SRFDI-R6":
        required_fields = tuple(structural)
        ablate_fields = (f"{variant['drop_axis']}.value",) if variant is not None else ()
    if implementation_class_id == "SRFDI-R9":
        required_fields = ()

    pack_id = f"{implementation_class_id}.REAL.v0.2::{variant_id or 'BASE'}"
    comparability_domain_id = stable_id("SRFD.COMP.", {
        "instrument": source["instrument"],
        "side": source["side"],
        "clock": source["clock"],
        "representation_schema": source["representation_schema"],
        "source_quality": source["source_quality"],
        "representation_pack_id": pack_id,
    })
    rep_pack = RepresentationPack(
        representation_pack_id=pack_id,
        implementation_class_id=implementation_class_id,
        architecture_candidate_id=str(pack_spec["architecture_candidate_id"]),
        required_fields=required_fields,
        comparability_domain_id=comparability_domain_id,
        ordering_semantics=str(pack_spec.get("ordering_semantics") or "STATIC_VECTOR"),
        ablate_fields=ablate_fields,
    )
    try:
        result = compile_representation(generic, rep_pack, source_population_id=source_population_id)
    except RepresentationError:
        raise
    result["source_record_id"] = source["record_id"]
    result["source_lineage"] = deepcopy(source["source_lineage"])
    result["pack_registry_id"] = str(pack_registry.get("registry_id"))
    result["pack_registry_version"] = str(pack_registry.get("version"))
    result["representation_variant_id"] = variant_id
    result["allowed_distance_ids"] = list((variant or {}).get("allowed_distance_ids") or pack_spec.get("allowed_distance_ids") or ())
    result["authority_state"] = "CANDIDATE_NOT_FROZEN"
    return result
