"""FSR adapter from revised-C2 shadow snapshots to the existing neutral C2E ledger.

The adapter is intentionally lossy only where the C2E contract is narrower than the
revised C2 evidence surface. It does not invent semantic episode labels, structural
completion, family fields, or a structural parent when no authorised structural-parent
record exists. Continuity resets and non-computability remain explicit.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping, Sequence

from .episode_ledger import build_episode_ledger

PROGRAMME_ID = "OVC-FULL-STACK-SYNTHETIC-FRESH-DISCOVERY-REHEARSAL-v0.1"
AUTHORITY = "INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT_SYNTHETIC_ONLY"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _state_key(snapshot: Mapping[str, Any]) -> str:
    axes = []
    for output in snapshot["formula_outputs"]:
        axes.append(
            {
                "axis": output["axis"],
                "profile_id": output["profile_id"],
                "computability": output["computability"],
                "facts": output.get("facts", {}),
                "reason_codes": output.get("reason_codes", []),
            }
        )
    return "FSR.C2.STATE." + _sha(axes)[:24]


def _transition_kind(snapshot: Mapping[str, Any]) -> str:
    classes = [
        str(item.get("primary_class", "NO_CHANGE"))
        for item in snapshot.get("transition_records", [])
        if str(item.get("primary_class", "NO_CHANGE")) != "NO_CHANGE"
    ]
    if not classes:
        return "NONE"
    # C2E treats any non-NONE value as a neutral transition phase unless it is an
    # explicitly registered interruption/completion value. Do not invent either.
    return "+".join(sorted(set(classes)))


def _computability(snapshot: Mapping[str, Any]) -> tuple[str, str | None]:
    failures = [
        f"{output['axis']}:{','.join(map(str, output.get('reason_codes', []))) or output['computability']}"
        for output in snapshot["formula_outputs"]
        if output["computability"] != "COMPUTABLE"
    ]
    if failures:
        return "NOT_EVALUABLE", "AXIS_NOT_COMPUTABLE|" + "|".join(sorted(failures))
    return "EVALUABLE", None


def _structural_parent(snapshot: Mapping[str, Any]) -> str | None:
    structural = snapshot.get("parent_context", {}).get("structural_parent_episode_link", {})
    if structural.get("computability") != "COMPUTABLE":
        return None
    value = structural.get("structural_parent_episode_id") or structural.get("parent_episode_id")
    return str(value) if value else None


def c2e_inputs(c2_manifest: Mapping[str, Any], *, side: str) -> list[dict[str, Any]]:
    snapshots = sorted(
        (item for item in c2_manifest["snapshots"] if item["side"] == side),
        key=lambda item: (str(item["as_of_time"]), str(item["snapshot_id"])),
    )
    if not snapshots:
        raise ValueError(f"NO_C2_SNAPSHOTS_FOR_SIDE:{side}")
    records: list[dict[str, Any]] = []
    previous_segment: str | None = None
    for snapshot in snapshots:
        segment = str(snapshot["continuity_segment_id"])
        reset_reason = None
        if previous_segment is not None and segment != previous_segment:
            reset_reason = "C2_CONTINUITY_SEGMENT_RESET"
        status, reason = _computability(snapshot)
        records.append(
            {
                "record_id": str(snapshot["snapshot_id"]),
                "source_release_id": str(c2_manifest["fixture_id"]),
                "instrument_id": "GBPUSD",
                "side": side,
                "scope_id": "FSR.REVISED_C2.LOCAL",
                "clock_id": "15M",
                "first_valid_time": str(snapshot["as_of_time"]),
                "state_key": _state_key(snapshot),
                "transition_kind": _transition_kind(snapshot),
                "parent_record_id": _structural_parent(snapshot),
                "computability_status": status,
                "not_evaluable_reason": reason,
                "reset_reason": reset_reason,
                "source_sha256": _sha(snapshot),
            }
        )
        previous_segment = segment
    return records


def run_fsr_c2e(c2_manifest: Mapping[str, Any]) -> dict[str, Any]:
    ledgers: list[dict[str, Any]] = []
    input_counts: dict[str, int] = {}
    for side in ("BID", "ASK"):
        records = c2e_inputs(c2_manifest, side=side)
        input_counts[side] = len(records)
        cutoff = max(str(item["first_valid_time"]) for item in records)
        ledger = build_episode_ledger(records, build_cutoff=cutoff).to_dict()
        ledgers.append(ledger)

    status_counts = Counter(
        episode["status"] for ledger in ledgers for episode in ledger["episodes"]
    )
    boundary_counts = Counter(
        episode["boundary_cause"] for ledger in ledgers for episode in ledger["episodes"]
    )
    body = {
        "schema": "ovc-fsr-c2e-rehearsal/v1",
        "programme_id": PROGRAMME_ID,
        "fixture_id": c2_manifest["fixture_id"],
        "source_c2_logical_sha256": c2_manifest["logical_sha256"],
        "input_counts": input_counts,
        "ledgers": ledgers,
        "episode_count": sum(len(item["episodes"]) for item in ledgers),
        "not_evaluable_count": sum(len(item["not_evaluable"]) for item in ledgers),
        "status_counts": dict(sorted(status_counts.items())),
        "boundary_counts": dict(sorted(boundary_counts.items())),
        "hidden_construction_consumed": False,
        "authority": {
            "mode": AUTHORITY,
            "canonical_episode_definition": "NONE",
            "c2g_promotion": "NONE",
            "c3_handoff": "NONE",
            "publication": "NONE",
            "validation_consumption": "DENIED",
            "semantic_probability_risk_exposure_execution": "NONE",
        },
    }
    body["logical_sha256"] = _sha(body)
    return body
