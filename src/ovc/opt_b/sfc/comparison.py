from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import sqrt
from typing import Any, Iterable, Mapping, Sequence

from .serialization import logical_hash


class SFCComparisonError(ValueError):
    pass


BASE_DIMENSIONS = (
    "instrument_id", "side", "units", "clock_scale", "representation_schema",
    "source_quality", "normalization_transport", "context_binding", "chronology_basis",
    "missingness_policy",
)

REASON_CODES = {
    "instrument_id": "SFC_NOT_COMPARABLE_INSTRUMENT",
    "side": "SFC_NOT_COMPARABLE_SIDE",
    "units": "SFC_NOT_COMPARABLE_UNITS",
    "clock_scale": "SFC_NOT_COMPARABLE_CLOCK_SCALE",
    "representation_schema": "SFC_NOT_COMPARABLE_SCHEMA",
    "source_quality": "SFC_NOT_COMPARABLE_SOURCE_QUALITY",
    "normalization_transport": "SFC_NOT_COMPARABLE_NORMALIZATION",
    "context_binding": "SFC_NOT_COMPARABLE_CONTEXT",
    "chronology_basis": "SFC_NOT_COMPARABLE_CHRONOLOGY",
    "missingness_policy": "SFC_NOT_EVALUABLE",
}


@dataclass(frozen=True)
class ComparabilityDomain:
    comparability_domain_id: str
    dimensions: tuple[str, ...] = BASE_DIMENSIONS
    authority_state: str = "INACTIVE_CONFORMANCE_ONLY"


@dataclass(frozen=True)
class ComparisonSpec:
    spec_id: str
    kind: str
    formula: str
    dimensions: tuple[str, ...]
    namespace: str = "structural_normalized"
    precision: str = "DECIMAL_12"
    equivalence_kind: str = "EXACT"
    abs_tolerance: str = "0"
    rel_tolerance: str = "0"
    symmetry: bool = True
    declared_properties: tuple[str, ...] = ("NONNEGATIVE", "SYMMETRIC", "IDENTITY")

    def __post_init__(self) -> None:
        if self.kind not in {"DISTANCE", "SIMILARITY"}:
            raise SFCComparisonError("SFC_COMPARISON_SPEC_INVALID_KIND")
        if self.formula not in {"EUCLIDEAN", "MANHATTAN", "COSINE"}:
            raise SFCComparisonError("SFC_COMPARISON_SPEC_INVALID_FORMULA")


def comparability_metadata(rep: Mapping[str, Any], *, units: str = "DIMENSIONLESS", source_quality: str = "SYNTHETIC_VALID", normalization_transport: str = "FROZEN", context_binding: str = "STRATIFICATION_ONLY", chronology_basis: str = "AS_OF_FVT", missingness_policy: str = "EXPLICIT_MASK") -> dict[str, str]:
    return {
        "instrument_id": str(rep.get("instrument_id") or rep.get("context", {}).get("instrument_id") or "GBPUSD"),
        "side": str(rep.get("side") or rep.get("context", {}).get("side") or "BID"),
        "units": units,
        "clock_scale": str(rep.get("scale_id", "")),
        "representation_schema": str(rep.get("representation_pack_id", "")),
        "source_quality": source_quality,
        "normalization_transport": normalization_transport,
        "context_binding": context_binding,
        "chronology_basis": chronology_basis,
        "missingness_policy": missingness_policy,
    }


def decide_comparability(left: Mapping[str, Any], right: Mapping[str, Any], domain: ComparabilityDomain, *, evaluation_cutoff: str) -> dict[str, Any]:
    reasons: list[str] = []
    for dimension in domain.dimensions:
        if left.get(dimension) != right.get(dimension):
            reasons.append(REASON_CODES[dimension])
    status = "ADMIT" if not reasons else "NOT_COMPARABLE"
    payload = {"left": dict(left), "right": dict(right), "comparability_domain_id": domain.comparability_domain_id, "status": status, "reason_codes": sorted(set(reasons)), "evaluation_cutoff": evaluation_cutoff}
    return {**payload, "first_valid_time": evaluation_cutoff, "logical_hash": logical_hash(payload)}


def pair_id(left_representation_id: str, right_representation_id: str, *, decision: Mapping[str, Any], spec: ComparisonSpec) -> str:
    if decision.get("status") != "ADMIT":
        raise SFCComparisonError("SFC_PAIR_ID_BEFORE_ADMISSION")
    ids = sorted([str(left_representation_id), str(right_representation_id)]) if spec.symmetry else [str(left_representation_id), str(right_representation_id)]
    return "SFC.PAIR." + logical_hash({"ids": ids, "domain": decision["comparability_domain_id"], "decision": decision["logical_hash"], "spec": spec.spec_id})[:24]


def _decimal(value: Any) -> Decimal:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SFCComparisonError("SFC_NOT_EVALUABLE") from exc
    if not d.is_finite():
        raise SFCComparisonError("SFC_NOT_EVALUABLE")
    return d


def vector(rep: Mapping[str, Any], spec: ComparisonSpec) -> list[Decimal]:
    namespace = rep.get(spec.namespace)
    if not isinstance(namespace, Mapping):
        raise SFCComparisonError("SFC_NOT_EVALUABLE")
    result = []
    for dimension in spec.dimensions:
        if dimension not in namespace or namespace[dimension] is None:
            raise SFCComparisonError("SFC_NOT_EVALUABLE")
        result.append(_decimal(namespace[dimension]))
    return result


def _value(left: Sequence[Decimal], right: Sequence[Decimal], formula: str) -> Decimal:
    if formula == "MANHATTAN":
        return sum((abs(a-b) for a,b in zip(left,right)), Decimal("0"))
    if formula == "EUCLIDEAN":
        return Decimal(str(sqrt(float(sum(((a-b)*(a-b) for a,b in zip(left,right)), Decimal("0"))))))
    dot = sum((a*b for a,b in zip(left,right)), Decimal("0"))
    na = sqrt(float(sum((a*a for a in left), Decimal("0"))))
    nb = sqrt(float(sum((b*b for b in right), Decimal("0"))))
    if na == 0 or nb == 0:
        raise SFCComparisonError("SFC_NOT_EVALUABLE")
    return Decimal(str(float(dot)/(na*nb)))


def compare(left_rep: Mapping[str, Any], right_rep: Mapping[str, Any], *, left_meta: Mapping[str, Any], right_meta: Mapping[str, Any], domain: ComparabilityDomain, spec: ComparisonSpec, evaluation_cutoff: str) -> dict[str, Any]:
    decision = decide_comparability(left_meta, right_meta, domain, evaluation_cutoff=evaluation_cutoff)
    if decision["status"] != "ADMIT":
        return {"pair_id": None, "status": "NOT_COMPARABLE", "value": None, "reason_codes": decision["reason_codes"], "comparability_decision_hash": decision["logical_hash"], "comparison_spec_id": spec.spec_id, "comparability_domain_id": domain.comparability_domain_id, "logical_hash": logical_hash(decision)}
    pid = pair_id(left_rep["representation_id"], right_rep["representation_id"], decision=decision, spec=spec)
    try:
        value = _value(vector(left_rep, spec), vector(right_rep, spec), spec.formula)
    except SFCComparisonError:
        value = None
    status = "EVALUATED" if value is not None else "NOT_EVALUABLE"
    payload = {"pair_id": pid, "left_representation_id": left_rep["representation_id"], "right_representation_id": right_rep["representation_id"], "comparability_decision_hash": decision["logical_hash"], "comparison_spec_id": spec.spec_id, "comparability_domain_id": domain.comparability_domain_id, "status": status, "value": None if value is None else format(value, "f"), "reason_codes": [] if value is not None else ["SFC_NOT_EVALUABLE"]}
    return {**payload, "logical_hash": logical_hash(payload)}


def equivalent(reference: str, candidate: str, *, kind: str = "EXACT", abs_tolerance: str = "0", rel_tolerance: str = "0") -> bool:
    if kind == "EXACT":
        return str(reference) == str(candidate)
    ref, cand = _decimal(reference), _decimal(candidate)
    delta = abs(ref-cand)
    abs_ok = delta <= Decimal(abs_tolerance)
    rel_base = abs(ref) if ref != 0 else Decimal("1")
    rel_ok = delta/rel_base <= Decimal(rel_tolerance)
    return abs_ok if kind == "ABS_TOL" else rel_ok if kind == "REL_TOL" else abs_ok or rel_ok


def build_surface(pair_records: Iterable[Mapping[str, Any]], *, population_id: str, representation_pack_id: str, spec: ComparisonSpec, domain: ComparabilityDomain, tile_size: int = 2) -> dict[str, Any]:
    ordered = sorted((dict(row) for row in pair_records), key=lambda row: str(row.get("pair_id")))
    tiles = [ordered[i:i+tile_size] for i in range(0, len(ordered), tile_size)]
    tile_manifest = [{"tile": i, "pair_ids": [row.get("pair_id") for row in tile], "logical_hash": logical_hash(tile)} for i,tile in enumerate(tiles)]
    identity = {"population_id": population_id, "representation_pack_id": representation_pack_id, "spec": spec.spec_id, "domain": domain.comparability_domain_id, "pair_hashes": [row["logical_hash"] for row in ordered]}
    return {"surface_id":"SFC.SURFACE."+logical_hash(identity)[:24],"population_id":population_id,"representation_pack_id":representation_pack_id,"comparison_spec_id":spec.spec_id,"comparability_domain_id":domain.comparability_domain_id,"pair_index":[row.get("pair_id") for row in ordered],"exclusions":[row for row in ordered if row["status"]!="EVALUATED"],"tile_manifest":tile_manifest,"cache_manifest":{"semantic_key":logical_hash(identity)},"logical_hash":logical_hash(identity)}


def semantic_cache_key(rep_hashes: Sequence[str], spec: ComparisonSpec, domain: ComparabilityDomain) -> str:
    return logical_hash({"representations": sorted(rep_hashes), "spec": spec.spec_id, "domain": domain.comparability_domain_id, "formula": spec.formula, "dimensions": spec.dimensions, "equivalence": [spec.equivalence_kind, spec.abs_tolerance, spec.rel_tolerance]})
