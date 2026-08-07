from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import struct
from typing import Any, Iterable, Mapping, Sequence

from .distance import DistanceSpec, compute_distance, deterministic_pair_id
from .pair_index import PairRange, canonical_ids, iter_pairs
from .serialization import canonical_json_bytes, logical_sha256, stable_id


EXACT_MODES = frozenset({
    "CURRENT_JSON_REFERENCE",
    "COMPACT_EXACT",
    "TILED_EXACT",
    "MEMMAP_EXACT",
    "RADIUS_ADJACENCY_EXACT",
    "RADIUS_BOUNDED_DISTANCE_EXACT",
})


class DistanceSurfaceError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _decimal(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DistanceSurfaceError("G8R_SURFACE_INVALID_DECIMAL", str(value)) from exc
    if not result.is_finite():
        raise DistanceSurfaceError("G8R_SURFACE_INVALID_DECIMAL", "distance must be finite")
    return result


def decimal_to_coefficient(value: Any, precision_places: int) -> int:
    if precision_places < 0:
        raise DistanceSurfaceError("G8R_SURFACE_INVALID_PRECISION", str(precision_places))
    decimal = _decimal(value)
    scaled = decimal * (Decimal(10) ** precision_places)
    integral = scaled.to_integral_value()
    if scaled != integral:
        raise DistanceSurfaceError("G8R_SURFACE_NOT_QUANTIZED", f"{value} at precision {precision_places}")
    return int(integral)


def coefficient_to_decimal(coefficient: int, precision_places: int) -> str:
    scale = Decimal(10) ** precision_places
    value = Decimal(int(coefficient)) / scale
    return format(value, f".{precision_places}f")


def coefficient_width(coefficients: Iterable[int]) -> int:
    values = tuple(int(value) for value in coefficients)
    minimum = min(values, default=0)
    maximum = max(values, default=0)
    if -(2**63) <= minimum and maximum <= 2**63 - 1:
        return 8
    if -(2**127) <= minimum and maximum <= 2**127 - 1:
        return 16
    raise DistanceSurfaceError("G8R_SURFACE_COEFFICIENT_OVERFLOW", "coefficient exceeds signed 128-bit storage")


def _encode_signed(value: int, width: int, endian: str) -> bytes:
    if width not in {8, 16} or endian not in {"big", "little"}:
        raise DistanceSurfaceError("G8R_SURFACE_INVALID_ENCODING", f"width={width}, endian={endian}")
    limit = 2 ** (8 * width - 1)
    if not (-limit <= value < limit):
        raise DistanceSurfaceError("G8R_SURFACE_COEFFICIENT_OVERFLOW", str(value))
    return int(value).to_bytes(width, byteorder=endian, signed=True)


def _decode_signed(payload: bytes, width: int, endian: str) -> tuple[int, ...]:
    if len(payload) % width:
        raise DistanceSurfaceError("G8R_SURFACE_CORRUPT_PAYLOAD", "payload length not divisible by coefficient width")
    return tuple(int.from_bytes(payload[index:index + width], byteorder=endian, signed=True) for index in range(0, len(payload), width))


@dataclass(frozen=True)
class TileHeader:
    format_version: str
    endian: str
    coefficient_width: int
    precision_places: int
    population_hash: str
    domain_hash: str
    distance_spec_hash: str
    k_start: int
    k_end: int
    expected_count: int
    mode: str = "TILED_EXACT"

    def __post_init__(self) -> None:
        if self.mode not in EXACT_MODES:
            raise DistanceSurfaceError("G8R_SURFACE_INVALID_MODE", self.mode)
        if self.endian not in {"big", "little"} or self.coefficient_width not in {8, 16}:
            raise DistanceSurfaceError("G8R_SURFACE_INVALID_ENCODING", "invalid endian/width")
        if self.k_start < 0 or self.k_end < self.k_start or self.expected_count != self.k_end - self.k_start:
            raise DistanceSurfaceError("G8R_SURFACE_INVALID_RANGE", "header range/count mismatch")


@dataclass(frozen=True)
class TileReceipt:
    tile_id: str
    status: str
    content_hash: str
    payload_bytes: int
    header: Mapping[str, Any]
    location: str
    authority_state: str = "FIXTURE_LOCAL_CAPACITY_REMEDIATION_ONLY"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def tile_logical_hash(header: TileHeader, payload: bytes) -> str:
    return logical_sha256({"header": asdict(header), "payload_hex": payload.hex()})


def write_exact_tile(path: str | os.PathLike[str], header: TileHeader, coefficients: Sequence[int]) -> TileReceipt:
    if len(coefficients) != header.expected_count:
        raise DistanceSurfaceError("G8R_SURFACE_COUNT_MISMATCH", "coefficient count differs from header")
    for value in coefficients:
        _encode_signed(int(value), header.coefficient_width, header.endian)
    payload = b"".join(_encode_signed(int(value), header.coefficient_width, header.endian) for value in coefficients)
    header_bytes = canonical_json_bytes(asdict(header))
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(target.name + ".staging")
    with staging.open("wb") as handle:
        handle.write(struct.pack(">I", len(header_bytes)))
        handle.write(header_bytes)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    content_hash = tile_logical_hash(header, payload)
    os.replace(staging, target)
    tile_seed = {"header": asdict(header), "content_hash": content_hash}
    return TileReceipt(
        tile_id=stable_id("SRFD.DIST.TILE.", tile_seed),
        status="COMPLETE",
        content_hash=content_hash,
        payload_bytes=len(payload),
        header=asdict(header),
        location=str(target),
    )


def read_exact_tile(path: str | os.PathLike[str], receipt: Mapping[str, Any]) -> tuple[TileHeader, tuple[int, ...]]:
    target = Path(path)
    try:
        raw = target.read_bytes()
    except OSError as exc:
        raise DistanceSurfaceError("G8R_SURFACE_MISSING", str(target)) from exc
    if len(raw) < 4:
        raise DistanceSurfaceError("G8R_SURFACE_CORRUPT_PAYLOAD", "missing header length")
    header_length = struct.unpack(">I", raw[:4])[0]
    if len(raw) < 4 + header_length:
        raise DistanceSurfaceError("G8R_SURFACE_CORRUPT_PAYLOAD", "truncated header")
    header_data = json.loads(raw[4:4 + header_length].decode("utf-8"))
    header = TileHeader(**header_data)
    payload = raw[4 + header_length:]
    content_hash = tile_logical_hash(header, payload)
    if content_hash != receipt.get("content_hash"):
        raise DistanceSurfaceError("QA_CACHE_CORRUPTION", "tile content hash mismatch")
    coefficients = _decode_signed(payload, header.coefficient_width, header.endian)
    if len(coefficients) != header.expected_count:
        raise DistanceSurfaceError("G8R_SURFACE_COUNT_MISMATCH", "decoded coefficient count differs from header")
    return header, coefficients


def compact_pair_coefficients(records: Sequence[Mapping[str, Any]], spec: DistanceSpec, pair_range: PairRange | None = None) -> tuple[tuple[int, ...], tuple[dict[str, Any], ...]]:
    ids = canonical_ids(str(record.get("representation_id", "")) for record in records)
    by_id = {str(record["representation_id"]): record for record in records}
    ordered = [by_id[item] for item in ids]
    active = pair_range
    coefficients: list[int] = []
    logical: list[dict[str, Any]] = []
    for _, i, j in iter_pairs(len(ordered), active):
        result = compute_distance(ordered[i], ordered[j], spec)
        if result["status"] != "COMPUTED":
            raise DistanceSurfaceError("G8R_SURFACE_NOT_COMPARABLE", str(result.get("reason_code")))
        coefficient = decimal_to_coefficient(result["distance"], spec.precision_places)
        coefficients.append(coefficient)
        logical.append(result)
    return tuple(coefficients), tuple(logical)


def reconstruct_logical_pairs(records: Sequence[Mapping[str, Any]], spec: DistanceSpec, coefficients: Sequence[int], pair_range: PairRange | None = None) -> tuple[dict[str, Any], ...]:
    ids = canonical_ids(str(record.get("representation_id", "")) for record in records)
    start = pair_range.k_start if pair_range is not None else 0
    expected = (pair_range.count if pair_range is not None else len(ids) * (len(ids) - 1) // 2)
    if len(coefficients) != expected:
        raise DistanceSurfaceError("G8R_SURFACE_COUNT_MISMATCH", "reconstruction coefficient count mismatch")
    output: list[dict[str, Any]] = []
    for offset, (k, i, j) in enumerate(iter_pairs(len(ids), pair_range)):
        left_id, right_id = ids[i], ids[j]
        pair_id = deterministic_pair_id(left_id, right_id, spec, comparability_domain_id=str(records[0].get("comparability_domain_id", "")))
        output.append({
            "pair_id": pair_id,
            "distance_spec_id": spec.distance_spec_id,
            "status": "COMPUTED",
            "reason_code": None,
            "distance": coefficient_to_decimal(coefficients[offset], spec.precision_places),
            "compute_invoked": True,
            "exact": spec.exact,
            "authority_state": "FIXTURE_ONLY",
            "physical_pair_index": start + offset,
        })
    return tuple(output)


def radius_adjacency_exact(logical_pairs: Sequence[Mapping[str, Any]], *, radius: Any, configuration_id: str) -> dict[str, Any]:
    threshold = _decimal(radius)
    edges = tuple(sorted(str(item["pair_id"]) for item in logical_pairs if item.get("status") == "COMPUTED" and _decimal(item["distance"]) <= threshold))
    payload = {
        "mode": "RADIUS_ADJACENCY_EXACT",
        "configuration_id": configuration_id,
        "radius": format(threshold, "f"),
        "edge_pair_ids": list(edges),
        "absence_semantics": "DISTANCE_GREATER_THAN_RADIUS",
        "complete_input_pair_count": len(logical_pairs),
        "authority_state": "FIXTURE_LOCAL_CAPACITY_REMEDIATION_ONLY",
    }
    return {**payload, "surface_id": stable_id("SRFD.RADIUS.ADJ.", payload), "logical_hash": logical_sha256(payload)}


def radius_bounded_distance_exact(logical_pairs: Sequence[Mapping[str, Any]], *, r_max: Any, configuration_id: str) -> dict[str, Any]:
    threshold = _decimal(r_max)
    retained = [
        {"pair_id": str(item["pair_id"]), "distance": str(item["distance"])}
        for item in logical_pairs
        if item.get("status") == "COMPUTED" and _decimal(item["distance"]) <= threshold
    ]
    retained.sort(key=lambda item: item["pair_id"])
    payload = {
        "mode": "RADIUS_BOUNDED_DISTANCE_EXACT",
        "configuration_id": configuration_id,
        "r_max": format(threshold, "f"),
        "retained": retained,
        "absence_semantics": "DISTANCE_GREATER_THAN_R_MAX",
        "complete_input_pair_count": len(logical_pairs),
        "generic_all_distance_surface": False,
        "authority_state": "FIXTURE_LOCAL_CAPACITY_REMEDIATION_ONLY",
    }
    return {**payload, "surface_id": stable_id("SRFD.RADIUS.BOUNDED.", payload), "logical_hash": logical_sha256(payload)}
