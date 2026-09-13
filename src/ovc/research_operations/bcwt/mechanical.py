from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from ovc.research_operations.canonical import canonical_sha256

MEASUREMENTS = (
    "SIGNED_DISPLACEMENT_TICKS",
    "ABSOLUTE_DISPLACEMENT_TICKS",
    "MAX_UP_EXCURSION_TICKS",
    "MAX_DOWN_EXCURSION_TICKS",
    "OBSERVED_RANGE_TICKS",
    "GROSS_CLOSE_TRAVEL_TICKS",
    "SIGNED_EFFICIENCY",
    "REVERSAL_RATE",
)
TERMINAL_STATUSES = frozenset(
    {
        "OBSERVED",
        "CENSORED_GAP",
        "CENSORED_RELEASE_END",
        "NOT_EVALUABLE",
        "NOT_COMPARABLE",
        "QUARANTINED",
        "PROCESS_INVALID",
    }
)
R2_ALLOWED_SOURCE_ROLES = frozenset({"MECHANICAL_ASSURANCE", "CONSUMED_REFERENCE_MECHANICAL"})


class BCWTValidationError(ValueError):
    pass


def logical_id(kind: str, value: dict[str, Any]) -> str:
    material = deepcopy(value)
    material.pop("logical_id", None)
    return f"bcwt:{kind}:{canonical_sha256(material)}"


def compile_mechanical_origins(
    events: Iterable[dict[str, Any]], *, reference_id: str
) -> list[dict[str, Any]]:
    origins: list[dict[str, Any]] = []
    seen_states: set[str] = set()
    for event in events:
        if event.get("event_kind") != "FINAL_RETURNED_STRUCTURAL_UPDATE":
            continue
        state_id = str(event["observer_state_id"])
        if state_id in seen_states:
            raise BCWTValidationError("duplicate final returned observer_state_id")
        seen_states.add(state_id)
        origin = {
            "schema": "ovc-bcwt-b-to-c-origin/v0_1",
            "origin_contract_id": "OVC-BCWT-B-TO-C-ORIGIN-CONTRACT-0.1",
            "reference_id": reference_id,
            "observer_state_id": state_id,
            "observer_generation": str(event["observer_generation"]),
            "segment_id": str(event["segment_id"]),
            "origin_cutoff_fvt_ms": int(event["origin_cutoff_fvt_ms"]),
            "input_prefix_chain_sha256": str(event["input_prefix_chain_sha256"]),
            "shared_fixed_asset_set_id": str(event["shared_fixed_asset_set_id"]),
            "source_population_ref": str(event["source_population_ref"]),
            "state_row_sha256": str(event["state_row_sha256"]),
            "component_status_map": deepcopy(event.get("component_status_map", {})),
            "epistemic_non_knowledge": list(event.get("epistemic_non_knowledge", [])),
            "source_break_state": str(event.get("source_break_state", "NONE")),
            "candidate_generation_id_or_none": None,
            "candidate_occurrence_id_or_none": None,
            "candidate_evaluation_admission_id_or_none": None,
            "origin_role": "MECHANICAL_REFERENCE_ORIGIN",
            "authority_effect": "NONE",
            "scientific_effect": "NONE",
        }
        origin["logical_id"] = logical_id("origin", origin)
        origins.append(origin)
    return origins


def assert_r2_origin(origin: dict[str, Any]) -> None:
    if origin.get("authority_effect") != "NONE" or origin.get("scientific_effect") != "NONE":
        raise BCWTValidationError("mechanical origin cannot grant authority/scientific effect")
    role = origin.get("origin_role")
    candidate_fields = (
        "candidate_generation_id_or_none",
        "candidate_occurrence_id_or_none",
        "candidate_evaluation_admission_id_or_none",
    )
    if role == "MECHANICAL_REFERENCE_ORIGIN":
        if any(origin.get(key) is not None for key in candidate_fields):
            raise BCWTValidationError("mechanical origin must have null candidate/admission refs")
        return
    if role == "C_ADMITTED_SCIENTIFIC_ORIGIN":
        if any(not origin.get(key) for key in candidate_fields):
            raise BCWTValidationError(
                "scientific origin requires frozen candidate occurrence + C admission"
            )
        raise PermissionError("BCWT-R2 mechanical slice forbids scientific C execution")
    raise BCWTValidationError(f"unknown origin role: {role}")


def make_consequence_pack(
    *, source_binding: dict[str, Any], horizons: list[int]
) -> dict[str, Any]:
    if source_binding.get("role") not in R2_ALLOWED_SOURCE_ROLES:
        raise PermissionError("BCWT-R2 source role is not mechanical/consumed-reference")
    if not horizons or any((not isinstance(h, int) or isinstance(h, bool) or h <= 0) for h in horizons):
        raise BCWTValidationError("positive integer horizons required")
    if len(set(horizons)) != len(horizons):
        raise BCWTValidationError("duplicate horizons forbidden")
    pack = {
        "schema": "ovc-bcwt-consequence-measurement/v0_1",
        "consequence_pack_id": "PENDING_HASH",
        "version": "0.1",
        "source_binding": deepcopy(source_binding),
        "price_side_policy": "SOURCE_BOUND_SINGLE_SIDE",
        "path_clock": str(source_binding["clock"]),
        "anchor_specs": ["FIRST_VALID_KNOWLEDGE_ANCHOR"],
        "fixed_horizons_observed_bars": list(horizons),
        "measurement_specs": list(MEASUREMENTS),
        "structural_consequence_specs": [],
        "censoring_rules": ["FIRST_TRUE_SOURCE_BREAK", "RELEASE_END"],
        "gap_rules": ["NO_CROSS_SEGMENT_BRIDGE", "NO_SYNTHETIC_BAR_FILL"],
        "missingness_rules": ["NO_ZERO_FALSE_DEFAULT", "EXPLICIT_NOT_EVALUABLE"],
        "prohibited_semantics": [
            "TRADE_ENTRY",
            "POSITION_SIZING",
            "EXPECTED_RETURN",
            "PROBABILITY",
            "SETUP_QUALITY",
            "OUTCOME_INFORMED_B_RELABELLING",
            "HORIZON_WINNER_SELECTION",
        ],
        "created_before_payload_access": True,
        "authority_effect": "NONE",
        "scientific_effect": "NONE",
        "fixture_only": source_binding.get("role") == "MECHANICAL_ASSURANCE",
    }
    pack["consequence_pack_id"] = logical_id("consequence_pack", pack)
    return pack


def make_join_manifest(
    *,
    reference_id: str,
    origin_set_hash: str,
    consequence_pack_id: str,
    source_binding: dict[str, Any],
) -> dict[str, Any]:
    if source_binding.get("role") not in R2_ALLOWED_SOURCE_ROLES:
        raise PermissionError("BCWT-R2 source role is not mechanical/consumed-reference")
    manifest = {
        "schema": "ovc-bcwt-outcome-join-manifest/v0_1",
        "execution_role": "MECHANICAL_REFERENCE_ONLY",
        "candidate_generation_id_or_none": None,
        "candidate_population_binding_or_none": None,
        "candidate_occurrence_set_hash_or_none": None,
        "candidate_evaluation_admission_id_or_none": None,
        "mechanical_origin_set_hash": origin_set_hash,
        "origin_contract_id": "OVC-BCWT-B-TO-C-ORIGIN-CONTRACT-0.1",
        "reference_id": reference_id,
        "consequence_pack_id": consequence_pack_id,
        "source_release_ref": deepcopy(source_binding),
        "instrument": str(source_binding["instrument"]),
        "side": str(source_binding["side"]),
        "clock": str(source_binding["clock"]),
        "anchor_spec_id": "FIRST_VALID_KNOWLEDGE_ANCHOR",
        "censoring_policy_id": "BCWT-R2-MECHANICAL-CENSORING-v0.1",
        "authority_effect": "NONE",
        "scientific_effect": "NONE",
    }
    manifest["logical_id"] = logical_id("join", manifest)
    return manifest


def _future_bars(
    origin: dict[str, Any], bars: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]], bool]:
    segment = origin["segment_id"]
    cutoff = int(origin["origin_cutoff_fvt_ms"])
    anchor_candidates = [
        bar
        for bar in bars
        if bar["segment_id"] == segment and int(bar["close_ms"]) == cutoff
    ]
    if len(anchor_candidates) != 1:
        raise BCWTValidationError("exact same-segment anchor bar not found")
    anchor = anchor_candidates[0]
    later = [bar for bar in bars if int(bar["close_ms"]) > cutoff]
    same_segment: list[dict[str, Any]] = []
    gap_seen = False
    for bar in later:
        if bar["segment_id"] != segment:
            gap_seen = True
            break
        same_segment.append(bar)
    return anchor, same_segment, gap_seen


def _measure(
    anchor: dict[str, Any], future: list[dict[str, Any]], measurement: str
) -> tuple[Any, str]:
    anchor_close = int(anchor["close_ticks"])
    closes = [anchor_close] + [int(bar["close_ticks"]) for bar in future]
    highs = [int(bar["high_ticks"]) for bar in future]
    lows = [int(bar["low_ticks"]) for bar in future]
    signed = closes[-1] - anchor_close
    gross = sum(abs(after - before) for before, after in zip(closes, closes[1:]))
    if measurement == "SIGNED_DISPLACEMENT_TICKS":
        return signed, "VALUE"
    if measurement == "ABSOLUTE_DISPLACEMENT_TICKS":
        return abs(signed), "VALUE"
    if measurement == "MAX_UP_EXCURSION_TICKS":
        return max(highs) - anchor_close, "VALUE"
    if measurement == "MAX_DOWN_EXCURSION_TICKS":
        return anchor_close - min(lows), "VALUE"
    if measurement == "OBSERVED_RANGE_TICKS":
        return max([anchor_close] + highs) - min([anchor_close] + lows), "VALUE"
    if measurement == "GROSS_CLOSE_TRAVEL_TICKS":
        return gross, "VALUE"
    if measurement == "SIGNED_EFFICIENCY":
        if gross == 0:
            return None, "FLAT_PATH"
        return signed / gross, "VALUE"
    if measurement == "REVERSAL_RATE":
        changes = [after - before for before, after in zip(closes, closes[1:]) if after - before != 0]
        if len(changes) < 2:
            return None, "INSUFFICIENT_SIGN_PAIRS"
        reversals = sum((left > 0) != (right > 0) for left, right in zip(changes, changes[1:]))
        return reversals / (len(changes) - 1), "VALUE"
    raise BCWTValidationError(f"unknown measurement: {measurement}")


def compile_ledger(
    *,
    origins: list[dict[str, Any]],
    bars: list[dict[str, Any]],
    pack: dict[str, Any],
    join: dict[str, Any],
) -> dict[str, Any]:
    if join.get("execution_role") != "MECHANICAL_REFERENCE_ONLY":
        raise PermissionError("BCWT-R2 only permits mechanical reference execution")
    if any(
        join.get(key) is not None
        for key in (
            "candidate_generation_id_or_none",
            "candidate_population_binding_or_none",
            "candidate_occurrence_set_hash_or_none",
            "candidate_evaluation_admission_id_or_none",
        )
    ):
        raise PermissionError("BCWT-R2 join cannot carry scientific candidate/admission refs")
    records: list[dict[str, Any]] = []
    for origin in origins:
        assert_r2_origin(origin)
        anchor, same_segment_future, gap_seen = _future_bars(origin, bars)
        for horizon in pack["fixed_horizons_observed_bars"]:
            if len(same_segment_future) >= horizon:
                window = same_segment_future[:horizon]
                base_status = "OBSERVED"
            else:
                window = []
                base_status = "CENSORED_GAP" if gap_seen else "CENSORED_RELEASE_END"
            for measurement in pack["measurement_specs"]:
                status = base_status
                value = None
                measurement_state = base_status
                if base_status == "OBSERVED":
                    value, measurement_state = _measure(anchor, window, measurement)
                    if measurement == "REVERSAL_RATE" and measurement_state == "INSUFFICIENT_SIGN_PAIRS":
                        status = "NOT_EVALUABLE"
                record = {
                    "schema": "ovc-bcwt-outcome-record/v0_1",
                    "origin_id": origin["logical_id"],
                    "observer_state_id": origin["observer_state_id"],
                    "consequence_pack_id": pack["consequence_pack_id"],
                    "join_manifest_id": join["logical_id"],
                    "anchor_spec_id": "FIRST_VALID_KNOWLEDGE_ANCHOR",
                    "horizon_observed_bars": horizon,
                    "measurement_spec_id": measurement,
                    "terminal_status": status,
                    "measurement_state": measurement_state,
                    "value": value,
                    "authority_effect": "NONE",
                    "scientific_effect": "NONE",
                }
                if status not in TERMINAL_STATUSES:
                    raise BCWTValidationError(f"unknown terminal status: {status}")
                record["logical_id"] = logical_id("outcome", record)
                records.append(record)
    expected = (
        len(origins)
        * len(pack["fixed_horizons_observed_bars"])
        * len(pack["measurement_specs"])
    )
    if len(records) != expected:
        raise BCWTValidationError("complete denominator failure")
    keys = {
        (row["origin_id"], row["horizon_observed_bars"], row["measurement_spec_id"])
        for row in records
    }
    if len(keys) != expected:
        raise BCWTValidationError("duplicate/missing ledger keys")
    ledger = {
        "schema": "ovc-bcwt-outcome-ledger/v0_1",
        "join_manifest_id": join["logical_id"],
        "consequence_pack_id": pack["consequence_pack_id"],
        "expected_rows": expected,
        "actual_rows": len(records),
        "terminal_status_counts": {
            status: sum(row["terminal_status"] == status for row in records)
            for status in sorted(TERMINAL_STATUSES)
        },
        "records": records,
        "authority_effect": "NONE",
        "scientific_effect": "NONE",
    }
    ledger["logical_id"] = logical_id("ledger", ledger)
    return ledger


def replay_digest(
    origins: list[dict[str, Any]],
    pack: dict[str, Any],
    join: dict[str, Any],
    ledger: dict[str, Any],
) -> str:
    return canonical_sha256({"origins": origins, "pack": pack, "join": join, "ledger": ledger})


def make_run_receipt(
    *, reference_id: str, origins: list[dict[str, Any]], pack: dict[str, Any], join: dict[str, Any], ledger: dict[str, Any]
) -> dict[str, Any]:
    receipt = {
        "schema": "ovc-bcwt-mechanical-run-receipt/v0_1",
        "run_receipt_id": "PENDING_HASH",
        "execution_role": "MECHANICAL_REFERENCE_ONLY",
        "reference_id": reference_id,
        "consequence_pack_id": pack["consequence_pack_id"],
        "join_manifest_id": join["logical_id"],
        "origin_count": len(origins),
        "expected_rows": ledger["expected_rows"],
        "actual_rows": ledger["actual_rows"],
        "terminal_status_counts": deepcopy(ledger["terminal_status_counts"]),
        "replay_digest": replay_digest(origins, pack, join, ledger),
        "authority_effect": "NONE",
        "scientific_effect": "NONE",
    }
    material = deepcopy(receipt)
    material["run_receipt_id"] = "PENDING_HASH"
    receipt["run_receipt_id"] = f"bcwt:run_receipt:{canonical_sha256(material)}"
    return receipt
