from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any, Iterable, Mapping, Sequence

from .serialization import logical_sha256, stable_id


class DistanceError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DistanceError("DIST_NONFINITE_RESULT", f"{field} is not numeric") from exc
    if not result.is_finite():
        raise DistanceError("DIST_NONFINITE_RESULT", f"{field} is non-finite")
    return result


@dataclass(frozen=True)
class DistanceSpec:
    distance_spec_id: str
    method: str
    fields: tuple[str, ...]
    weights: Mapping[str, str] | None = None
    precision_places: int = 12
    exact: bool = True

    def __post_init__(self) -> None:
        if self.method not in {"L1_TYPED", "L2_TYPED", "GOWER_MIXED", "DTW_SEQUENCE"}:
            raise DistanceError("DIST_INVALID_PARAMETER", f"unsupported method {self.method}")
        if not self.distance_spec_id or self.precision_places < 0:
            raise DistanceError("DIST_INVALID_PARAMETER", "invalid distance spec")
        if self.method != "DTW_SEQUENCE" and not self.fields:
            raise DistanceError("DIST_INVALID_PARAMETER", "static distance requires fields")

    @property
    def logical_hash(self) -> str:
        return logical_sha256({
            "distance_spec_id": self.distance_spec_id,
            "method": self.method,
            "fields": list(self.fields),
            "weights": dict(self.weights or {}),
            "precision_places": self.precision_places,
            "exact": self.exact,
        })


def compatibility(left: Mapping[str, Any], right: Mapping[str, Any]) -> tuple[bool, str | None]:
    if left.get("comparability_domain_id") != right.get("comparability_domain_id"):
        return False, "COMP_DOMAIN_INCOMPATIBLE"
    if left.get("ordering_semantics") != right.get("ordering_semantics"):
        return False, "COMP_ORDERING_INCOMPATIBLE"
    if left.get("missingness") or right.get("missingness"):
        return False, "COMP_REQUIRED_DIMENSION_MISSING"
    return True, None


def deterministic_pair_id(left_id: str, right_id: str, spec: DistanceSpec, *, comparability_domain_id: str) -> str:
    if left_id == right_id:
        raise DistanceError("DIST_INVALID_PARAMETER", "self-pair is not a benchmark pair")
    endpoints = sorted((left_id, right_id))
    return stable_id("SRFD.PAIR.", {
        "left_id": endpoints[0], "right_id": endpoints[1],
        "distance_spec_hash": spec.logical_hash,
        "comparability_domain_id": comparability_domain_id,
    })


def _static_values(record: Mapping[str, Any], fields: Sequence[str]) -> dict[str, Any]:
    combined: dict[str, Any] = {}
    for namespace in ("structural_raw", "structural_derived", "structural_normalized", "comparison_only"):
        values = record.get(namespace)
        if isinstance(values, Mapping):
            for key, value in values.items():
                combined.setdefault(str(key), value)
    missing = [field for field in fields if field not in combined or combined[field] is None]
    if missing:
        raise DistanceError("COMP_REQUIRED_DIMENSION_MISSING", ",".join(missing))
    return {field: combined[field] for field in fields}


def _weight(spec: DistanceSpec, field: str) -> Decimal:
    raw = (spec.weights or {}).get(field, "1")
    value = _decimal(raw, f"weight.{field}")
    if value <= 0:
        raise DistanceError("DIST_INVALID_PARAMETER", f"weight.{field} must be positive")
    return value


def _static_distance(left: Mapping[str, Any], right: Mapping[str, Any], spec: DistanceSpec) -> Decimal:
    lvals = _static_values(left, spec.fields)
    rvals = _static_values(right, spec.fields)
    if spec.method in {"L1_TYPED", "L2_TYPED"}:
        weighted: list[tuple[Decimal, Decimal]] = []
        for field in spec.fields:
            weight = _weight(spec, field)
            delta = abs(_decimal(lvals[field], field) - _decimal(rvals[field], field))
            weighted.append((weight, delta))
        denominator = sum((weight for weight, _ in weighted), Decimal("0"))
        if spec.method == "L1_TYPED":
            return sum((weight * delta for weight, delta in weighted), Decimal("0")) / denominator
        with localcontext() as context:
            context.prec = max(28, spec.precision_places + 8)
            value = sum((weight * delta * delta for weight, delta in weighted), Decimal("0")) / denominator
            return value.sqrt()
    # Gower mixed: numeric fields use absolute difference; categorical fields 0/1.
    scores: list[Decimal] = []
    for field in spec.fields:
        try:
            score = abs(_decimal(lvals[field], field) - _decimal(rvals[field], field))
        except DistanceError:
            score = Decimal("0") if lvals[field] == rvals[field] else Decimal("1")
        scores.append(score)
    return sum(scores, Decimal("0")) / Decimal(len(scores))


def _sequence_values(record: Mapping[str, Any]) -> list[Decimal]:
    derived = record.get("structural_derived")
    sequence = derived.get("ordered_sequence") if isinstance(derived, Mapping) else None
    if not isinstance(sequence, Sequence) or isinstance(sequence, (str, bytes, bytearray)) or not sequence:
        raise DistanceError("COMP_REQUIRED_DIMENSION_MISSING", "ordered_sequence required")
    output: list[Decimal] = []
    for index, item in enumerate(sequence):
        if isinstance(item, Mapping):
            numeric = [value for value in item.values() if isinstance(value, (int, float, Decimal, str))]
            if len(numeric) != 1:
                raise DistanceError("DIST_INVALID_PARAMETER", "DTW fixture sequence entries must carry one numeric channel")
            item = numeric[0]
        output.append(_decimal(item, f"sequence[{index}]"))
    return output


def _dtw(left: Mapping[str, Any], right: Mapping[str, Any]) -> Decimal:
    a = _sequence_values(left)
    b = _sequence_values(right)
    inf = Decimal("Infinity")
    previous = [inf] * (len(b) + 1)
    previous[0] = Decimal("0")
    for avalue in a:
        current = [inf] * (len(b) + 1)
        for j, bvalue in enumerate(b, start=1):
            current[j] = abs(avalue - bvalue) + min(current[j - 1], previous[j], previous[j - 1])
        previous = current
    return previous[-1] / Decimal(max(len(a), len(b)))


def compute_distance(left: Mapping[str, Any], right: Mapping[str, Any], spec: DistanceSpec) -> dict[str, Any]:
    comparable, reason = compatibility(left, right)
    left_id = str(left.get("representation_id", ""))
    right_id = str(right.get("representation_id", ""))
    if not left_id or not right_id:
        raise DistanceError("QA_SCHEMA_FAILURE", "representation_id required")
    domain = str(left.get("comparability_domain_id") or right.get("comparability_domain_id") or "")
    pair_id = deterministic_pair_id(left_id, right_id, spec, comparability_domain_id=domain)
    if not comparable:
        return {
            "pair_id": pair_id, "distance_spec_id": spec.distance_spec_id,
            "status": "NOT_COMPARABLE", "reason_code": reason, "distance": None,
            "compute_invoked": False, "authority_state": "FIXTURE_ONLY",
        }
    value = _dtw(left, right) if spec.method == "DTW_SEQUENCE" else _static_distance(left, right, spec)
    quantum = Decimal(1).scaleb(-spec.precision_places)
    rounded = value.quantize(quantum)
    return {
        "pair_id": pair_id, "distance_spec_id": spec.distance_spec_id,
        "status": "COMPUTED", "reason_code": None, "distance": format(rounded, "f"),
        "compute_invoked": True, "exact": spec.exact, "authority_state": "FIXTURE_ONLY",
    }


def pair_tiles(representation_ids: Iterable[str], *, tile_size: int) -> list[list[tuple[str, str]]]:
    if tile_size < 1:
        raise DistanceError("DIST_INVALID_PARAMETER", "tile_size must be positive")
    ids = sorted(set(str(value) for value in representation_ids))
    pairs = [(ids[i], ids[j]) for i in range(len(ids)) for j in range(i + 1, len(ids))]
    return [pairs[index:index + tile_size] for index in range(0, len(pairs), tile_size)]


class DistanceCache:
    def __init__(self) -> None:
        self._entries: dict[str, dict[str, Any]] = {}
        self._quarantine: dict[str, str] = {}

    @staticmethod
    def key(result: Mapping[str, Any], spec: DistanceSpec) -> str:
        return stable_id("SRFD.CACHE.", {"pair_id": result["pair_id"], "distance_spec_hash": spec.logical_hash})

    def put(self, result: Mapping[str, Any], spec: DistanceSpec) -> str:
        key = self.key(result, spec)
        payload = dict(result)
        self._entries[key] = {"payload": payload, "logical_hash": logical_sha256(payload), "distance_spec_hash": spec.logical_hash}
        return key

    def get(self, key: str, spec: DistanceSpec) -> dict[str, Any] | None:
        entry = self._entries.get(key)
        if entry is None or entry["distance_spec_hash"] != spec.logical_hash:
            return None
        if logical_sha256(entry["payload"]) != entry["logical_hash"]:
            self._quarantine[key] = "QA_CACHE_CORRUPTION"
            self._entries.pop(key, None)
            return None
        return dict(entry["payload"])

    def corrupt_for_fixture(self, key: str) -> None:
        if key in self._entries:
            self._entries[key]["payload"] = {**self._entries[key]["payload"], "distance": "999"}

    @property
    def quarantined(self) -> Mapping[str, str]:
        return dict(self._quarantine)
