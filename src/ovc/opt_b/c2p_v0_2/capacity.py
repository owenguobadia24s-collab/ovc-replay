from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping

from .canonical import canonical_bytes


class CapacityPolicyError(ValueError):
    pass


_ALLOWED_TIERS = {
    "T0_IDENTITY_BEARING",
    "T1_OPTIONAL_ENRICHMENT",
    "T2_REBUILDABLE_PROJECTION",
    "T3_OPTIMIZED_INDEX",
}


def _hash(payload: Any) -> str:
    return sha256(canonical_bytes(payload)).hexdigest()


def evaluate_capacity(
    *,
    tier: str,
    authorized_envelope: Mapping[str, int],
    observed_consumption: Mapping[str, int],
    semantic_change: Mapping[str, Any] | None = None,
    last_completed_checkpoint: str | None = None,
) -> dict[str, Any]:
    """Return a deterministic capacity disposition without weakening semantics."""

    if tier not in _ALLOWED_TIERS:
        raise CapacityPolicyError("C2P_CAPACITY_TIER_INVALID")
    forbidden_change = {
        key: value
        for key, value in (semantic_change or {}).items()
        if value not in (None, False, 0, "NONE", "UNCHANGED")
    }
    if forbidden_change:
        raise CapacityPolicyError(f"C2P_CAPACITY_SEMANTIC_CHANGE_FORBIDDEN:{sorted(forbidden_change)[0]}")
    if not authorized_envelope:
        raise CapacityPolicyError("C2P_CAPACITY_ENVELOPE_REQUIRED")
    if set(observed_consumption) - set(authorized_envelope):
        raise CapacityPolicyError("C2P_CAPACITY_UNBOUND_RESOURCE")
    exceeded = {
        key: {
            "authorized": int(authorized_envelope[key]),
            "observed": int(observed_consumption.get(key, 0)),
        }
        for key in sorted(authorized_envelope)
        if int(observed_consumption.get(key, 0)) > int(authorized_envelope[key])
    }
    if not exceeded:
        disposition = "PASS"
    elif tier == "T0_IDENTITY_BEARING":
        disposition = "CAPACITY_EXCEEDED"
    elif tier == "T1_OPTIONAL_ENRICHMENT":
        disposition = "DEFER_OPTIONAL_ENRICHMENT"
    elif tier == "T2_REBUILDABLE_PROJECTION":
        disposition = "DEFER_REBUILDABLE_PROJECTION"
    else:
        disposition = "FALLBACK_TO_EXACT_REFERENCE"

    body = {
        "schema": "c2p-capacity-receipt/v0.2",
        "tier": tier,
        "disposition": disposition,
        "authorized_envelope": {key: int(value) for key, value in sorted(authorized_envelope.items())},
        "observed_consumption": {key: int(value) for key, value in sorted(observed_consumption.items())},
        "exceeded": exceeded,
        "last_completed_checkpoint": last_completed_checkpoint,
        "semantic_contract": {
            "sampling": "FORBIDDEN",
            "reduced_precision": "FORBIDDEN",
            "population_change": "FORBIDDEN",
            "predicate_weakening": "FORBIDDEN",
            "object_pack_change": "FORBIDDEN",
        },
    }
    return {"capacity_receipt_id": _hash(body), **deepcopy(body)}
