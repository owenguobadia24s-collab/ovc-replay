"""Observational-only ASOCS instrumentation for preregistration assurance.

The instrumentation surface is deliberately sidecar-only. It never mutates, replaces,
filters, enriches, or reserializes owner records in-place. Scientific identity is
computed from an explicit projection and the owner record is returned unchanged.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping


class ASOCSInstrumentationError(RuntimeError):
    """Raised when observational-equivalence requirements are violated."""


@dataclass(frozen=True)
class InstrumentationObservation:
    layer: str
    object_id: str
    first_valid_time: str
    logical_scientific_hash: str


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def scientific_projection(record: Mapping[str, Any]) -> dict[str, Any]:
    required = ("layer", "object_id", "first_valid_time", "scientific_payload")
    missing = [key for key in required if key not in record]
    if missing:
        raise ASOCSInstrumentationError(
            "INSTRUMENTATION_FIXTURE_MISSING_FIELDS:" + ",".join(missing)
        )
    return {key: deepcopy(record[key]) for key in required}


def logical_scientific_hash(record: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(scientific_projection(record))).hexdigest()


def observe_record(
    record: Mapping[str, Any], *, enabled: bool
) -> tuple[dict[str, Any], InstrumentationObservation | None]:
    """Return an unchanged copy plus optional detached observation evidence."""
    output = deepcopy(dict(record))
    if not enabled:
        return output, None
    projection = scientific_projection(record)
    return output, InstrumentationObservation(
        layer=str(projection["layer"]),
        object_id=str(projection["object_id"]),
        first_valid_time=str(projection["first_valid_time"]),
        logical_scientific_hash=logical_scientific_hash(record),
    )


def prove_chain_equivalence(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Prove OFF/ON identity equality for a fixed C1/C2/C2E fixture chain."""
    original = [deepcopy(dict(record)) for record in records]
    off_outputs = [observe_record(record, enabled=False)[0] for record in original]
    on_pairs = [observe_record(record, enabled=True) for record in original]
    on_outputs = [pair[0] for pair in on_pairs]
    observations = [pair[1] for pair in on_pairs]

    if _canonical_json(off_outputs) != _canonical_json(on_outputs):
        raise ASOCSInstrumentationError("INSTRUMENTATION_OUTPUT_MUTATION")
    if _canonical_json(original) != _canonical_json(on_outputs):
        raise ASOCSInstrumentationError("INSTRUMENTATION_OWNER_RECORD_MUTATION")

    off_hashes = [logical_scientific_hash(record) for record in off_outputs]
    on_hashes = [logical_scientific_hash(record) for record in on_outputs]
    if off_hashes != on_hashes:
        raise ASOCSInstrumentationError("INSTRUMENTATION_SCIENTIFIC_HASH_DRIFT")

    off_fvt = [str(record["first_valid_time"]) for record in off_outputs]
    on_fvt = [str(record["first_valid_time"]) for record in on_outputs]
    if off_fvt != on_fvt:
        raise ASOCSInstrumentationError("INSTRUMENTATION_FIRST_VALID_DRIFT")

    layers = [str(record["layer"]) for record in original]
    if layers != ["C1", "C2", "C2E"]:
        raise ASOCSInstrumentationError("INSTRUMENTATION_FIXTURE_LAYER_ORDER_INVALID")
    if any(observation is None for observation in observations):
        raise ASOCSInstrumentationError("INSTRUMENTATION_OBSERVATION_MISSING")

    return {
        "result": "PASS",
        "layers": layers,
        "record_count": len(original),
        "scientific_hashes": off_hashes,
        "first_valid_identities": off_fvt,
        "scientific_hash_differences": 0,
        "first_valid_identity_differences": 0,
        "record_mutations": 0,
    }
