from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

from . import source_adapter as legacy
from .serialization import logical_sha256, stable_id

ADAPTER_ID = "SRFDI-SOURCE-ADAPTER-v0.2"
EVALUATED_REASON_POLICY = "PRESERVE_OPTIONAL_DESCRIPTIVE_REASON_CODE"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _axis(name: str, raw: object) -> dict[str, Any]:
    """Schema-preserving v0.2 axis reader.

    Accepted frozen June C2 records may carry a descriptive reason_code on an
    EVALUATED axis (notably QUALITY=DEGRADED/CENSORED).  The WP2C contract
    requires preservation of status, value, reason and measurement and does
    not define the presence of such a reason as non-computability.  v0.2
    therefore preserves it rather than rewriting or rejecting it.
    """
    if not isinstance(raw, Mapping):
        raise legacy.SourceAdapterError("REP_REQUIRED_DIMENSION_MISSING", f"axis {name} must be an object")
    keys = set(raw)
    unknown = sorted(keys - legacy.AXIS_KEYS)
    missing = sorted({"status", "value"} - keys)
    if unknown:
        raise legacy.SourceAdapterError("QA_SCHEMA_FAILURE", f"unknown axis fields {name}:" + ",".join(unknown))
    if missing:
        raise legacy.SourceAdapterError("REP_REQUIRED_DIMENSION_MISSING", f"missing axis fields {name}:" + ",".join(missing))
    status = legacy._text(raw["status"], f"axes.{name}.status").upper()
    if status not in legacy.AXIS_STATUSES:
        raise legacy.SourceAdapterError("QA_SCHEMA_FAILURE", f"unsupported axis status {name}:{status}")
    value = raw.get("value")
    if value is not None:
        value = legacy._text(value, f"axes.{name}.value")
    reason = raw.get("reason_code")
    if reason is not None:
        reason = legacy._text(reason, f"axes.{name}.reason_code")
    measurement = raw.get("measurement")
    if measurement is not None:
        measurement = legacy._text(measurement, f"axes.{name}.measurement")
    if status != "EVALUATED" and reason is None:
        raise legacy.SourceAdapterError("REP_REQUIRED_DIMENSION_MISSING", f"non-evaluated axis requires reason:{name}")
    return {"status": status, "value": value, "reason_code": reason, "measurement": measurement}


def _axes(raw: object) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, Mapping):
        raise legacy.SourceAdapterError("REP_REQUIRED_DIMENSION_MISSING", "axes object required")
    keys = set(raw)
    if keys != set(legacy.AXES):
        missing = sorted(set(legacy.AXES) - keys)
        unknown = sorted(keys - set(legacy.AXES))
        detail: list[str] = []
        if missing:
            detail.append("missing=" + ",".join(missing))
        if unknown:
            detail.append("unknown=" + ",".join(unknown))
        code = "REP_REQUIRED_DIMENSION_MISSING" if missing and not unknown else "QA_SCHEMA_FAILURE"
        raise legacy.SourceAdapterError(code, "axis set mismatch:" + ";".join(detail))
    return {name: _axis(name, raw[name]) for name in legacy.AXES}


def adapt_c2_state(
    source: Mapping[str, Any],
    binding: legacy.C2SourceBinding,
    *,
    c1_parent_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    row = dict(source)
    legacy._forbidden(row)
    unknown = sorted(set(row) - legacy.C2_ALLOWED_KEYS)
    missing = sorted(legacy.C2_REQUIRED_KEYS - set(row))
    if unknown:
        raise legacy.SourceAdapterError("QA_SCHEMA_FAILURE", "unknown C2 fields:" + ",".join(unknown))
    if missing:
        raise legacy.SourceAdapterError("QA_SCHEMA_FAILURE", "C2 missing fields:" + ",".join(missing))
    record_id = legacy._text(row["c2_state_id"], "c2_state_id")
    if legacy._text(row["active_c2_model_release_id"], "active_c2_model_release_id") != binding.active_c2_model_release_id:
        raise legacy.SourceAdapterError("AVAIL_SOURCE_UNAVAILABLE", "active C2 model release mismatch")
    if legacy._text(row["source_slice_id"], "source_slice_id") != binding.source_slice_id:
        raise legacy.SourceAdapterError("AVAIL_SOURCE_UNAVAILABLE", "C2 source slice mismatch")
    if legacy._text(row["operation_mode"], "operation_mode") != binding.operation_mode or legacy._text(row["role"], "role") != binding.role:
        raise legacy.SourceAdapterError("AUTH_SCOPE_EXPANSION", "C2 operation mode/role mismatch")
    if bool(row["release_membership"]):
        raise legacy.SourceAdapterError("AUTH_SCOPE_EXPANSION", "C2 source cannot be a release member")
    if str(row.get("live_prospective_append", "DENIED")) != "DENIED":
        raise legacy.SourceAdapterError("AUTH_SCOPE_EXPANSION", "live prospective append must remain denied")

    parent_id = legacy._text(row["parent_c1_record_id"], "parent_c1_record_id")
    parent = c1_parent_index.get(parent_id)
    if parent is None:
        raise legacy.SourceAdapterError("AVAIL_REQUIRED_PARENT_MISSING", f"missing C1 parent:{parent_id}")
    clock = legacy._text(row["clock"], "clock")
    side = legacy._text(row["side"], "side").upper()
    if clock != parent["clock"] or side != parent["side"]:
        raise legacy.SourceAdapterError("COMP_CLOCK_INCOMPATIBLE", f"C2/C1 clock or side mismatch:{record_id}")
    first_valid_time = legacy._utc(row["first_valid_time"], "first_valid_time")
    if first_valid_time != parent["first_valid_time"]:
        raise legacy.SourceAdapterError("TIME_PARENT_NOT_FIRST_VALID", f"C2/C1 FVT mismatch:{record_id}")
    eligibility = str(parent["independent_eligibility_class"])
    target = bool(parent["independent_target_eligible"])
    if str(row["eligibility_class"]) != eligibility or bool(row["target_eligible"]) != target:
        raise legacy.SourceAdapterError("QA_NON_REPRODUCIBLE", f"C2 target classification mismatch:{record_id}")

    axes = _axes(row["axes"])
    computability_status, reason = legacy._computability(axes)
    scope_id = legacy._text(row["evaluation_scope_id"], "evaluation_scope_id")
    native = {
        "axes": axes,
        "level_ids": sorted(str(item) for item in row["level_ids"]),
        "container_ids": sorted(str(item) for item in row["container_ids"]),
        "relation_set_id": legacy._text(row["relation_set_id"], "relation_set_id"),
        "persistence": dict(row["persistence"]) if isinstance(row["persistence"], Mapping) else row["persistence"],
        "continuity": legacy._text(row["continuity"], "continuity"),
        "parameter_pack_id": legacy._text(row["parameter_pack_id"], "parameter_pack_id"),
    }
    lineage = {
        "source_release_id": binding.source_release_id,
        "source_commit": binding.source_commit,
        "source_slice_id": binding.source_slice_id,
        "source_manifest_sha256": binding.source_manifest_sha256,
        "output_manifest_sha256": binding.output_manifest_sha256,
        "active_c2_model_release_id": binding.active_c2_model_release_id,
        "c1_record_id": parent_id,
        "c1_release_id": legacy._text(row["c1_release_id"], "c1_release_id"),
        "c1_manifest_id": legacy._text(row["c1_manifest_id"], "c1_manifest_id"),
        "opt_a_release_id": legacy._text(row["opt_a_release_id"], "opt_a_release_id"),
        "opt_a_manifest_id": legacy._text(row["opt_a_manifest_id"], "opt_a_manifest_id"),
        "parent_opt_a_bar_id": legacy._text(row["parent_opt_a_bar_id"], "parent_opt_a_bar_id"),
    }
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
        "source_logical_sha256": logical_sha256(row),
        "adapter_semantics": "SCHEMA_PRESERVING_NO_REPRESENTATION_FIELD_SELECTION",
        "adapter_id": ADAPTER_ID,
        "evaluated_reason_policy": EVALUATED_REASON_POLICY,
    }


def adapt_c2_to_c2e_input(adapted: Mapping[str, Any]):
    return legacy.adapt_c2_to_c2e_input(adapted)


def bind_source_population(
    c2_rows: Iterable[Mapping[str, Any]],
    c1_rows: Iterable[Mapping[str, Any]],
    binding: legacy.C2SourceBinding,
) -> dict[str, Any]:
    parent_index = legacy.build_c1_parent_index(c1_rows, binding)
    eligible: list[str] = []
    context: list[str] = []
    exclusions: list[dict[str, str]] = []
    computability: dict[str, int] = {}
    seen: set[str] = set()
    source_hashes: list[str] = []
    evaluated_reason_occurrences = 0
    for source in c2_rows:
        raw_id = str(source.get("c2_state_id", "")).strip()
        if raw_id and raw_id in seen:
            raise legacy.SourceAdapterError("QA_SCHEMA_FAILURE", f"duplicate C2 state:{raw_id}")
        try:
            adapted = adapt_c2_state(source, binding, c1_parent_index=parent_index)
        except legacy.SourceAdapterError as exc:
            target_hint = bool(source.get("target_eligible"))
            if exc.reason_code == "REP_REQUIRED_DIMENSION_MISSING" and target_hint and raw_id:
                exclusions.append({"record_id": raw_id, "reason_code": exc.reason_code, "detail": exc.detail})
                seen.add(raw_id)
                continue
            raise
        record_id = str(adapted["record_id"])
        if record_id in seen:
            raise legacy.SourceAdapterError("QA_SCHEMA_FAILURE", f"duplicate C2 state:{record_id}")
        seen.add(record_id)
        source_hashes.append(str(adapted["source_logical_sha256"]))
        axes = adapted["native_c2"]["axes"]
        evaluated_reason_occurrences += sum(
            1 for value in axes.values()
            if value["status"] == "EVALUATED" and value.get("reason_code") is not None
        )
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
        "accepted_evaluated_reason_code_occurrences": evaluated_reason_occurrences,
        "missingness_policy": "RETAIN_IN_POPULATION_DEFER_TO_FROZEN_REPRESENTATION_COMPUTABILITY",
        "authority_state": "READ_ONLY_BINDING_CANDIDATE_NO_RUN_AUTHORITY",
        "adapter_id": ADAPTER_ID,
    }
