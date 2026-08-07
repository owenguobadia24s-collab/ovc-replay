from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Any, Mapping, Sequence

from .distance import DistanceSpec, compatibility, compute_distance, deterministic_pair_id
from .pair_index import PairRange, canonical_ids, iter_pairs, pair_ranges


class OptimizedDistanceError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _combined(record: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for namespace in ("structural_raw", "structural_derived", "structural_normalized", "comparison_only"):
        values = record.get(namespace)
        if isinstance(values, Mapping):
            for key, value in values.items():
                output.setdefault(str(key), value)
    return output


@dataclass(frozen=True)
class PreparedRecord:
    representation_id: str
    comparability_domain_id: str
    ordering_semantics: Any
    missingness: Any
    values: tuple[Decimal, ...]


def prepare_records(records: Sequence[Mapping[str, Any]], spec: DistanceSpec) -> tuple[PreparedRecord, ...]:
    if spec.method not in {"L1_TYPED", "L2_TYPED"}:
        raise OptimizedDistanceError("G8R_OPT_REFERENCE_FALLBACK_REQUIRED", spec.method)
    by_id = {str(record.get("representation_id", "")): record for record in records}
    ids = canonical_ids(by_id)
    output: list[PreparedRecord] = []
    for record_id in ids:
        record = by_id[record_id]
        combined = _combined(record)
        if record.get("missingness") or any(field not in combined or combined[field] is None for field in spec.fields):
            raise OptimizedDistanceError("COMP_REQUIRED_DIMENSION_MISSING", record_id)
        try:
            values = tuple(Decimal(str(combined[field])) for field in spec.fields)
        except Exception as exc:
            raise OptimizedDistanceError("DIST_NONFINITE_RESULT", record_id) from exc
        if any(not value.is_finite() for value in values):
            raise OptimizedDistanceError("DIST_NONFINITE_RESULT", record_id)
        output.append(PreparedRecord(
            record_id,
            str(record.get("comparability_domain_id", "")),
            record.get("ordering_semantics"),
            record.get("missingness"),
            values,
        ))
    return tuple(output)


def _prepared_distance(left: PreparedRecord, right: PreparedRecord, spec: DistanceSpec) -> dict[str, Any]:
    if left.comparability_domain_id != right.comparability_domain_id:
        comparable, reason = False, "COMP_DOMAIN_INCOMPATIBLE"
    elif left.ordering_semantics != right.ordering_semantics:
        comparable, reason = False, "COMP_ORDERING_INCOMPATIBLE"
    elif left.missingness or right.missingness:
        comparable, reason = False, "COMP_REQUIRED_DIMENSION_MISSING"
    else:
        comparable, reason = True, None
    pair_id = deterministic_pair_id(left.representation_id, right.representation_id, spec, comparability_domain_id=left.comparability_domain_id or right.comparability_domain_id)
    if not comparable:
        return {"pair_id":pair_id,"distance_spec_id":spec.distance_spec_id,"status":"NOT_COMPARABLE","reason_code":reason,"distance":None,"compute_invoked":False,"authority_state":"FIXTURE_ONLY"}
    weights = tuple(Decimal(str((spec.weights or {}).get(field, "1"))) for field in spec.fields)
    if any(weight <= 0 for weight in weights):
        raise OptimizedDistanceError("DIST_INVALID_PARAMETER", "weights must be positive")
    denominator = sum(weights, Decimal("0"))
    deltas = tuple(abs(a - b) for a, b in zip(left.values, right.values))
    if spec.method == "L1_TYPED":
        value = sum((weight * delta for weight, delta in zip(weights, deltas)), Decimal("0")) / denominator
    else:
        with localcontext() as context:
            context.prec = max(28, spec.precision_places + 8)
            value = (sum((weight * delta * delta for weight, delta in zip(weights, deltas)), Decimal("0")) / denominator).sqrt()
    quantum = Decimal(1).scaleb(-spec.precision_places)
    rounded = value.quantize(quantum)
    return {"pair_id":pair_id,"distance_spec_id":spec.distance_spec_id,"status":"COMPUTED","reason_code":None,"distance":format(rounded,"f"),"compute_invoked":True,"exact":spec.exact,"authority_state":"FIXTURE_ONLY"}


def batch_compute_prepared(records: Sequence[Mapping[str, Any]], spec: DistanceSpec, pair_range: PairRange | None = None) -> tuple[dict[str, Any], ...]:
    if spec.method not in {"L1_TYPED", "L2_TYPED"}:
        ids = canonical_ids(str(record.get("representation_id", "")) for record in records)
        by_id = {str(record["representation_id"]): record for record in records}
        ordered = [by_id[item] for item in ids]
        return tuple(compute_distance(ordered[i], ordered[j], spec) for _, i, j in iter_pairs(len(ordered), pair_range))
    prepared = prepare_records(records, spec)
    return tuple(_prepared_distance(prepared[i], prepared[j], spec) for _, i, j in iter_pairs(len(prepared), pair_range))


def _tile_worker(args: tuple[tuple[Mapping[str, Any], ...], DistanceSpec, PairRange]) -> tuple[int, tuple[dict[str, Any], ...]]:
    records, spec, pair_range = args
    return pair_range.k_start, batch_compute_prepared(records, spec, pair_range)


def deterministic_parallel_tiles(records: Sequence[Mapping[str, Any]], spec: DistanceSpec, *, tile_pair_count: int, worker_count: int) -> tuple[dict[str, Any], ...]:
    if worker_count < 1:
        raise OptimizedDistanceError("G8R_OPT_INVALID_WORKERS", str(worker_count))
    immutable_records = tuple(dict(item) for item in records)
    ranges = pair_ranges(len(records), tile_pair_count=tile_pair_count)
    if worker_count == 1 or len(ranges) < 2:
        pieces = [_tile_worker((immutable_records, spec, item)) for item in ranges]
    else:
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            pieces = list(executor.map(_tile_worker, ((immutable_records, spec, item) for item in ranges)))
    pieces.sort(key=lambda item: item[0])
    return tuple(result for _, values in pieces for result in values)


def exact_equivalence(records: Sequence[Mapping[str, Any]], spec: DistanceSpec) -> bool:
    ids = canonical_ids(str(record.get("representation_id", "")) for record in records)
    by_id = {str(record["representation_id"]): record for record in records}
    ordered = [by_id[item] for item in ids]
    reference = tuple(compute_distance(ordered[i], ordered[j], spec) for _, i, j in iter_pairs(len(ordered)))
    candidate = batch_compute_prepared(records, spec)
    return reference == candidate
