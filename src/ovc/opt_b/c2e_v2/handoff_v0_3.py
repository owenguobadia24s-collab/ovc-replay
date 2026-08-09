"""Versioned C2 -> C2E handoff adapter carrying stable comparison signatures.

This is an additive candidate adapter authorised by the operator supersession.
The historical v0.2 adapter remains unchanged and import-compatible.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from .handoff import C2EHandoffError, build_input_frame as build_v0_2_input_frame
from .serialization import sha256_hex
from .stable_signatures import StableSignatureError, build_comparison_signatures

CONTRACT_ID = "C2E.HANDOFF.SIGNATURE.v0_3"
SCHEMA_ID = "c2e_input_frame/v0_3"
ALLOWED_TOP_LEVEL = {
    "source_binding", "identity", "chronology", "structural", "context",
    "evidence", "lineage", "parent_records", "diagnostic_namespace",
    "comparison_source",
}


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise C2EHandoffError(marker)


def build_input_frame_v0_3(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw = copy.deepcopy(dict(payload))
    unknown = sorted(set(raw) - ALLOWED_TOP_LEVEL)
    _require(not unknown, f"UNKNOWN_HANDOFF_FIELD:{','.join(unknown)}")
    _require("comparison_source" in raw, "COMPARISON_SOURCE_REQUIRED")
    identity = dict(raw.get("identity", {}))
    _require(identity.get("contract_id") == CONTRACT_ID, "SIGNATURE_HANDOFF_CONTRACT_ID_REQUIRED")
    _require(identity.get("schema_id") == SCHEMA_ID, "SIGNATURE_HANDOFF_SCHEMA_ID_REQUIRED")

    comparison_source = raw.pop("comparison_source")
    base = build_v0_2_input_frame(raw)
    try:
        comparison = build_comparison_signatures(dict(comparison_source))
    except StableSignatureError as exc:
        raise C2EHandoffError(str(exc)) from exc

    base["schema"] = SCHEMA_ID
    base["comparison"] = comparison
    # frame_id already binds contract_id/schema_id from the v0.3 input identity.
    # Recompute only the whole-frame logical hash after adding comparison content.
    base.pop("logical_hash", None)
    base["logical_hash"] = sha256_hex(base)
    return base
