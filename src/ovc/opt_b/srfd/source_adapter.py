from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping, Sequence

from ovc.opt_b.market_grammar.episode_ledger import C2LedgerInput

from .serialization import logical_sha256, stable_id

AXES = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY")
AXIS_KEYS = frozenset({"status", "value", "reason_code", "measurement"})
AXIS_STATUSES = frozenset({"EVALUATED", "NOT_EVALUATED", "NOT_EVALUABLE", "CENSORED", "CONFLICT", "QUARANTINED"})
NON_EVALUATED_PRECEDENCE = ("QUARANTINED", "CONFLICT", "CENSORED", "NOT_EVALUABLE", "NOT_EVALUATED")
SIDES = frozenset({"BID", "ASK"})
CLOCKS = frozenset({"15M", "2H_A_L"})
FORBIDDEN_KEYS = frozenset({
    "outcome", "outcomes", "future_return", "return_label", "mfe", "mae", "probability",
    "edge", "risk", "exposure", "trade", "trade_label", "order", "execution",
    "family_id", "cluster_id", "medoid_id", "variant_id", "sensitivity_pack_id",
    "grammar_id", "parse_id", "semantic_label",
})
C2_ALLOWED_KEYS = frozenset({
    "active_c2_model_release_id", "axes", "c1_manifest_id", "c1_release_id", "c2_state_id",
    "clock", "container_ids", "continuity", "eligibility_class", "evaluation_scope_id",
    "first_valid_time", "level_ids", "live_prospective_append", "operation_mode",
    "opt_a_manifest_id", "opt_a_release_id", "parameter_pack_id", "parent_c1_record_id",
    "parent_opt_a_bar_id", "persistence", "relation_set_id", "release_membership", "role",
    "side", "source_slice_id", "target_eligible",
})
C2_REQUIRED_KEYS = frozenset({
    "active_c2_model_release_id", "axes", "c1_manifest_id", "c1_release_id", "c2_state_id",
    "clock", "container_ids", "continuity", "eligibility_class", "evaluation_scope_id",
    "first_valid_time", "level_ids", "operation_mode", "opt_a_manifest_id", "opt_a_release_id",
    "parameter_pack_id", "parent_c1_record_id", "parent_opt_a_bar_id", "persistence",
    "relation_set_id", "release_membership", "role", "side", "source_slice_id", "target_eligible",
})


class SourceAdapterError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _hex64(value: object, field: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise SourceAdapterError("QA_SCHEMA_FAILURE", f"{field} must be lowercase SHA-256 hex")
    return text


def _text(value: object, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise SourceAdapterError("QA_SCHEMA_FAILURE", f"{field} must be non-empty")
    return text


def _utc(value: object, field: str) -> str:
    text = _text(value, field)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise SourceAdapterError("TIME_PARENT_NOT_FIRST_VALID", f"invalid UTC time for {field}") from exc
    if parsed.tzinfo is None:
        raise SourceAdapterError("TIME_PARENT_NOT_FIRST_VALID", f"timezone required for {field}")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _dt(value: object, field: str) -> datetime:
    return datetime.fromisoformat(_utc(value, field).replace("Z", "+00:00"))


def _forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise SourceAdapterError("AUTH_SCOPE_EXPANSION", f"forbidden field {path}.{key}")
            _forbidden(child, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _forbidden(child, f"{path}[{index}]")


@dataclass(frozen=True)
class C2SourceBinding:
    source_release_id: str
    source_commit: str
    source_slice_id: str
    source_manifest_sha256: str
    output_manifest_sha256: str
    active_c2_model_release_id: str
    benchmark_start_inclusive_utc: str
    benchmark_end_exclusive_utc: str
    context_start_utc: str
    context_end_exclusive_utc: str
    instrument: str = "GBPUSD"
    operation_mode: str = "TIME_GATED_REPLAY"
    role: str = "DISCOVERY"

    def __post_init__(self) -> None:
        for field in ("source_release_id", "source_commit", "source_slice_id", "active_c2_model_release_id"):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        object.__setattr__(self, "source_manifest_sha256", _hex64(self.source_manifest_sha256, "source_manifest_sha256"))
        object.__setattr__(self, "output_manifest_sha256", _hex64(self.output_manifest_sha256, "output_manifest_sha256"))
        object.__setattr__(self, "instrument", _text(self.instrument, "instrument").upper())
        object.__setattr__(self, "operation_mode", _text(self.operation_mode, "operation_mode"))
        object.__setattr__(self, "role", _text(self.role, "role"))
        for field in (
            "benchmark_start_inclusive_utc", "benchmark_end_exclusive_utc",
            "context_start_utc", "context_end_exclusive_utc",
        ):
            object.__setattr__(self, field, _utc(getattr(self, field), field))
        start = _dt(self.benchmark_start_inclusive_utc, "benchmark_start_inclusive_utc")
        end = _dt(self.benchmark_end_exclusive_utc, "benchmark_end_exclusive_utc")
        context_start = _dt(self.context_start_utc, "context_start_utc")
        context_end = _dt(self.context_end_exclusive_utc, "context_end_exclusive_utc")
        if not context_start <= start < end <= context_end:
            raise SourceAdapterError("QA_SCHEMA_FAILURE", "benchmark window must be inside context window")

    @property
    def logical_hash(self) -> str:
        return logical_sha256(self.to_dict())

    def to_dict(self) -> dict[str, str]:
        return {
            "source_release_id": self.source_release_id,
            "source_commit": self.source_commit,
            "source_slice_id": self.source_slice_id,
            "source_manifest_sha256": self.source_manifest_sha256,
            "output_manifest_sha256": self.output_manifest_sha256,
            "active_c2_model_release_id": self.active_c2_model_release_id,
            "benchmark_start_inclusive_utc": self.benchmark_start_inclusive_utc,
            "benchmark_end_exclusive_utc": self.benchmark_end_exclusive_utc,
            "context_start_utc": self.context_start_utc,
            "context_end_exclusive_utc": self.context_end_exclusive_utc,
            "instrument": self.instrument,
            "operation_mode": self.operation_mode,
            "role": self.role,
        }


def _classify_open_time(open_time: object, binding: C2SourceBinding) -> str:
    current = _dt(open_time, "open_time")
    context_start = _dt(binding.context_start_utc, "context_start_utc")
    context_end = _dt(binding.context_end_exclusive_utc, "context_end_exclusive_utc")
    target_start = _dt(binding.benchmark_start_inclusive_utc, "benchmark_start_inclusive_utc")
    target_end = _dt(binding.benchmark_end_exclusive_utc, "benchmark_end_exclusive_utc")
    if current < context_start or current >= context_end:
        return "OUTSIDE_CONTEXT"
    if current < target_start:
        return "CONTEXT_PRE_TARGET"
    if current < target_end:
        return "TARGET_JUNE"
    return "CONTEXT_POST_TARGET"


def build_c1_parent_index(rows: Iterable[Mapping[str, Any]], binding: C2SourceBinding) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    required = {
        "c1_record_id", "first_valid_time", "open_time", "close_time", "clock", "side",
        "source_slice_id", "source_manifest_sha256", "eligibility_class", "target_eligible",
        "operation_mode", "role",
    }
    for source in rows:
        row = dict(source)
        _forbidden(row)
        missing = sorted(required - set(row))
        if missing:
            raise SourceAdapterError("QA_SCHEMA_FAILURE", "C1 missing fields:" + ",".join(missing))
        record_id = _text(row["c1_record_id"], "c1_record_id")
        if record_id in index:
            raise SourceAdapterError("QA_SCHEMA_FAILURE", f"duplicate C1 record:{record_id}")
        if _text(row["source_slice_id"], "source_slice_id") != binding.source_slice_id:
            raise SourceAdapterError("AVAIL_SOURCE_UNAVAILABLE", "C1 source slice mismatch")
        if _hex64(row["source_manifest_sha256"], "source_manifest_sha256") != binding.source_manifest_sha256:
            raise SourceAdapterError("AVAIL_SOURCE_UNAVAILABLE", "C1 source manifest mismatch")
        if _text(row["operation_mode"], "operation_mode") != binding.operation_mode or _text(row["role"], "role") != binding.role:
            raise SourceAdapterError("AUTH_SCOPE_EXPANSION", "C1 operation mode/role mismatch")
        clock = _text(row["clock"], "clock")
        side = _text(row["side"], "side").upper()
        if clock not in CLOCKS or side not in SIDES:
            raise SourceAdapterError("COMP_CLOCK_INCOMPATIBLE", "C1 clock/side outside frozen source")
        classification = _classify_open_time(row["open_time"], binding)
        expected_target = classification == "TARGET_JUNE"
        if classification == "OUTSIDE_CONTEXT":
            raise SourceAdapterError("AVAIL_SOURCE_UNAVAILABLE", "C1 open_time outside frozen context")
        if str(row["eligibility_class"]) != classification or bool(row["target_eligible"]) != expected_target:
            raise SourceAdapterError("QA_NON_REPRODUCIBLE", f"C1 target classification mismatch:{record_id}")
        first_valid = _utc(row["first_valid_time"], "first_valid_time")
        close_time = _utc(row["close_time"], "close_time")
        if first_valid != close_time:
            raise SourceAdapterError("TIME_PARENT_NOT_FIRST_VALID", f"C1 FVT/close mismatch:{record_id}")
        normalized = dict(row)
        normalized.update({
            "c1_record_id": record_id,
            "first_valid_time": first_valid,
            "open_time": _utc(row["open_time"], "open_time"),
            "close_time": close_time,
            "clock": clock,
            "side": side,
            "independent_eligibility_class": classification,
            "independent_target_eligible": expected_target,
        })
        index[record_id] = normalized
    return index


def _axis(name: str, raw: object) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise SourceAdapterError("REP_REQUIRED_DIMENSION_MISSING", f"axis {name} must be an object")
    keys = set(raw)
    unknown = sorted(keys - AXIS_KEYS)
    missing = sorted({"status", "value"} - keys)
    if unknown:
        raise SourceAdapterError("QA_SCHEMA_FAILURE", f"unknown axis fields {name}:" + ",".join(unknown))
    if missing:
        raise SourceAdapterError("REP_REQUIRED_DIMENSION_MISSING", f"missing axis fields {name}:" + ",".join(missing))
    status = _text(raw["status"], f"axes.{name}.status").upper()
    if status not in AXIS_STATUSES:
        raise SourceAdapterError("QA_SCHEMA_FAILURE", f"unsupported axis status {name}:{status}")
    value = raw.get("value")
    if value is not None:
        value = _text(value, f"axes.{name}.value")
    reason = raw.get("reason_code")
    if reason is not None:
        reason = _text(reason, f"axes.{name}.reason_code")
    measurement = raw.get("measurement")
    if measurement is not None:
        measurement = _text(measurement, f"axes.{name}.measurement")
    if status == "EVALUATED" and reason is not None:
        raise SourceAdapterError("QA_SCHEMA_FAILURE", f"evaluated axis cannot carry reason:{name}")
    if status != "EVALUATED" and reason is None:
        raise SourceAdapterError("REP_REQUIRED_DIMENSION_MISSING", f"non-evaluated axis requires reason:{name}")
    return {"status": status, "value": value, "reason_code": reason, "measurement": measurement}


def _axes(raw: object) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, Mapping):
        raise SourceAdapterError("REP_REQUIRED_DIMENSION_MISSING", "axes object required")
    keys = set(raw)
    if keys != set(AXES):
        missing = sorted(set(AXES) - keys)
        unknown = sorted(keys - set(AXES))
        detail = []
        if missing:
            detail.append("missing=" + ",".join(missing))
        if unknown:
            detail.append("unknown=" + ",".join(unknown))
        code = "REP_REQUIRED_DIMENSION_MISSING" if missing and not unknown else "QA_SCHEMA_FAILURE"
        raise SourceAdapterError(code, "axis set mismatch:" + ";".join(detail))
    return {name: _axis(name, raw[name]) for name in AXES}


def _computability(axes: Mapping[str, Mapping[str, Any]]) -> tuple[str, str | None]:
    for status in NON_EVALUATED_PRECEDENCE:
        if any(str(axes[name]["status"]) == status for name in AXES):
            reasons = [
                f"{name}:{axes[name]['status']}:{axes[name].get('reason_code') or 'UNSPECIFIED'}"
                for name in AXES if axes[name]["status"] != "EVALUATED"
            ]
            return status, "|".join(reasons)
    return "EVALUABLE", None


def adapt_c2_state(
    source: Mapping[str, Any],
    binding: C2SourceBinding,
    *,
    c1_parent_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    row = dict(source)
    _forbidden(row)
    unknown = sorted(set(row) - C2_ALLOWED_KEYS)
    missing = sorted(C2_REQUIRED_KEYS - set(row))
    if unknown:
        raise SourceAdapterError("QA_SCHEMA_FAILURE", "unknown C2 fields:" + ",".join(unknown))
    if missing:
        raise SourceAdapterError("QA_SCHEMA_FAILURE", "C2 missing fields:" + ",".join(missing))
    record_id = _text(row["c2_state_id"], "c2_state_id")
    if _text(row["active_c2_model_release_id"], "active_c2_model_release_id") != binding.active_c2_model_release_id:
        raise SourceAdapterError("AVAIL_SOURCE_UNAVAILABLE", "active C2 model release mismatch")
    if _text(row["source_slice_id"], "source_slice_id") != binding.source_slice_id:
        raise SourceAdapterError("AVAIL_SOURCE_UNAVAILABLE", "C2 source slice mismatch")
    if _text(row["operation_mode"], "operation_mode") != binding.operation_mode or _text(row["role"], "role") != binding.role:
        raise SourceAdapterError("AUTH_SCOPE_EXPANSION", "C2 operation mode/role mismatch")
    if bool(row["release_membership"]):
        raise SourceAdapterError("AUTH_SCOPE_EXPANSION", "C2 source cannot be a release member")
    if str(row.get("live_prospective_append", "DENIED")) != "DENIED":
        raise SourceAdapterError("AUTH_SCOPE_EXPANSION", "live prospective append must remain denied")
    parent_id = _text(row["parent_c1_record_id"], "parent_c1_record_id")
    parent = c1_parent_index.get(parent_id)
    if parent is None:
        raise SourceAdapterError("AVAIL_REQUIRED_PARENT_MISSING", f"missing C1 parent:{parent_id}")
    clock = _text(row["clock"], "clock")
    side = _text(row["side"], "side").upper()
    if clock != parent["clock"] or side != parent["side"]:
        raise SourceAdapterError("COMP_CLOCK_INCOMPATIBLE", f"C2/C1 clock or side mismatch:{record_id}")
    first_valid_time = _utc(row["first_valid_time"], "first_valid_time")
    if first_valid_time != parent["first_valid_time"]:
        raise SourceAdapterError("TIME_PARENT_NOT_FIRST_VALID", f"C2/C1 FVT mismatch:{record_id}")
    eligibility = str(parent["independent_eligibility_class"])
    target = bool(parent["independent_target_eligible"])
    if str(row["eligibility_class"]) != eligibility or bool(row["target_eligible"]) != target:
        raise SourceAdapterError("QA_NON_REPRODUCIBLE", f"C2 target classification mismatch:{record_id}")
    axes = _axes(row["axes"])
    computability_status, reason = _computability(axes)
    scope_id = _text(row["evaluation_scope_id"], "evaluation_scope_id")
    native = {
        "axes": axes,
        "level_ids": sorted(str(item) for item in row["level_ids"]),
        "container_ids": sorted(str(item) for item in row["container_ids"]),
        "relation_set_id": _text(row["relation_set_id"], "relation_set_id"),
        "persistence": dict(row["persistence"]) if isinstance(row["persistence"], Mapping) else row["persistence"],
        "continuity": _text(row["continuity"], "continuity"),
        "parameter_pack_id": _text(row["parameter_pack_id"], "parameter_pack_id"),
    }
    lineage = {
        "source_release_id": binding.source_release_id,
        "source_commit": binding.source_commit,
        "source_slice_id": binding.source_slice_id,
        "source_manifest_sha256": binding.source_manifest_sha256,
        "output_manifest_sha256": binding.output_manifest_sha256,
        "active_c2_model_release_id": binding.active_c2_model_release_id,
        "c1_record_id": parent_id,
        "c1_release_id": _text(row["c1_release_id"], "c1_release_id"),
        "c1_manifest_id": _text(row["c1_manifest_id"], "c1_manifest_id"),
        "opt_a_release_id": _text(row["opt_a_release_id"], "opt_a_release_id"),
        "opt_a_manifest_id": _text(row["opt_a_manifest_id"], "opt_a_manifest_id"),
        "parent_opt_a_bar_id": _text(row["parent_opt_a_bar_id"], "parent_opt_a_bar_id"),
    }
    source_hash = logical_sha256(row)
    return {
        "record_id": record_id,
        "first_valid_time": first_valid_time,
        "instrument": binding.instrument,
        "side": side,
        "clock": clock,
        "units": "MIXED_TYPED_C2",
        "representation_schema": f"C2_TYPED_AXES:{binding.active_c2_model_release_id}:{scope_id}",
        "source_quality": "ACCEPTED_FROZEN_C2",
        "evaluation_scope_id": scope_id,
        "eligibility_class": eligibility,
        "target_eligible": target,
        "computability_status": computability_status,
        "not_evaluable_reason": reason,
        "native_c2": native,
        "source_lineage": lineage,
        "source_logical_sha256": source_hash,
        "adapter_semantics": "SCHEMA_PRESERVING_NO_REPRESENTATION_FIELD_SELECTION",
    }


def adapt_c2_to_c2e_input(adapted: Mapping[str, Any]) -> C2LedgerInput:
    native = adapted.get("native_c2")
    lineage = adapted.get("source_lineage")
    if not isinstance(native, Mapping) or not isinstance(lineage, Mapping):
        raise SourceAdapterError("QA_SCHEMA_FAILURE", "adapted C2 source namespaces required")
    axes = native.get("axes")
    if not isinstance(axes, Mapping):
        raise SourceAdapterError("REP_REQUIRED_DIMENSION_MISSING", "adapted axes required")
    computability = str(adapted.get("computability_status"))
    ledger_status = "EVALUABLE" if computability == "EVALUABLE" else computability
    reset_reason = "C2_SCOPE_RESET" if str(native.get("continuity", "")) == "RESET" else None
    state_key = "C2.STATE." + logical_sha256({"axes": axes, "scope": adapted.get("evaluation_scope_id")})
    return C2LedgerInput.from_mapping({
        "record_id": adapted["record_id"],
        "source_release_id": lineage["source_release_id"],
        "instrument_id": adapted["instrument"],
        "side": adapted["side"],
        "scope_id": adapted["evaluation_scope_id"],
        "clock_id": adapted["clock"],
        "first_valid_time": adapted["first_valid_time"],
        "state_key": state_key,
        "transition_kind": "NONE",
        "parent_record_id": None,
        "computability_status": ledger_status,
        "not_evaluable_reason": adapted.get("not_evaluable_reason"),
        "reset_reason": reset_reason,
        "source_sha256": adapted["source_logical_sha256"],
    })


def bind_source_population(
    c2_rows: Iterable[Mapping[str, Any]],
    c1_rows: Iterable[Mapping[str, Any]],
    binding: C2SourceBinding,
) -> dict[str, Any]:
    parent_index = build_c1_parent_index(c1_rows, binding)
    eligible: list[str] = []
    context: list[str] = []
    exclusions: list[dict[str, str]] = []
    computability: dict[str, int] = {}
    seen: set[str] = set()
    source_hashes: list[str] = []
    for source in c2_rows:
        raw_id = str(source.get("c2_state_id", "")).strip()
        if raw_id and raw_id in seen:
            raise SourceAdapterError("QA_SCHEMA_FAILURE", f"duplicate C2 state:{raw_id}")
        try:
            adapted = adapt_c2_state(source, binding, c1_parent_index=parent_index)
        except SourceAdapterError as exc:
            target_hint = bool(source.get("target_eligible"))
            if exc.reason_code == "REP_REQUIRED_DIMENSION_MISSING" and target_hint and raw_id:
                exclusions.append({"record_id": raw_id, "reason_code": exc.reason_code, "detail": exc.detail})
                seen.add(raw_id)
                continue
            raise
        record_id = str(adapted["record_id"])
        if record_id in seen:
            raise SourceAdapterError("QA_SCHEMA_FAILURE", f"duplicate C2 state:{record_id}")
        seen.add(record_id)
        source_hashes.append(str(adapted["source_logical_sha256"]))
        if adapted["target_eligible"]:
            eligible.append(record_id)
            status = str(adapted["computability_status"])
            computability[status] = computability.get(status, 0) + 1
        else:
            context.append(record_id)
    eligible.sort()
    context.sort()
    exclusions.sort(key=lambda item: (item["record_id"], item["reason_code"], item["detail"]))
    eligible_hash = sha256(_canonical_json(eligible)).hexdigest()
    exclusion_hash = sha256(_canonical_json(exclusions)).hexdigest()
    population_identity = {
        "source_binding_hash": binding.logical_hash,
        "eligible_record_ids_sha256": eligible_hash,
        "exclusion_ledger_sha256": exclusion_hash,
        "benchmark_window": [binding.benchmark_start_inclusive_utc, binding.benchmark_end_exclusive_utc],
    }
    return {
        "population_id": stable_id("SRFD.POP.", population_identity),
        "source_binding_sha256": binding.logical_hash,
        "source_record_count": len(seen),
        "eligible_record_count": len(eligible),
        "eligible_record_ids": eligible,
        "eligible_record_ids_sha256": eligible_hash,
        "context_record_count": len(context),
        "context_record_ids_sha256": sha256(_canonical_json(context)).hexdigest(),
        "exclusion_count": len(exclusions),
        "exclusions": exclusions,
        "exclusion_ledger_sha256": exclusion_hash,
        "computability_counts_within_eligible_population": {key: computability[key] for key in sorted(computability)},
        "source_record_hashes_sha256": sha256(_canonical_json(sorted(source_hashes))).hexdigest(),
        "missingness_policy": "RETAIN_IN_POPULATION_DEFER_TO_FROZEN_REPRESENTATION_COMPUTABILITY",
        "authority_state": "READ_ONLY_BINDING_CANDIDATE_NO_RUN_AUTHORITY",
    }
