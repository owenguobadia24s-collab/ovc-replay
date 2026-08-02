from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

FORMULA_REGISTRY_ID = "C1.FORMULAS.v0.1"
PRICE_INCREMENT = Decimal("0.00001")
CLOCK_SECONDS = {"15M": 900, "2H_A_L": 7200}
EXPECTED_PARENT_COUNTS = {"15M": 15, "2H_A_L": 120}


class SourceC1AuditError(ValueError):
    """Raised when source/C1 audit evidence violates a frozen invariant."""


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise SourceC1AuditError("TIMESTAMP_NOT_TIMEZONE_AWARE")
    return parsed.astimezone(timezone.utc)


def canonical_hash(value: Any, *, ensure_ascii: bool = True) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=ensure_ascii,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise SourceC1AuditError(f"JSONL_RECORD_NOT_OBJECT:{path}:{line_number}")
            records.append(value)
    return records


def _render(value: Decimal) -> str:
    if value == 0:
        return "0"
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def bar_logical_dict(bar: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "bar_id": bar["bar_id"],
        "clock": bar["clock"],
        "side": bar["side"],
        "start_utc": bar["start_utc"],
        "end_utc": bar["end_utc"],
        "open": bar["open"],
        "high": bar["high"],
        "low": bar["low"],
        "close": bar["close"],
        "volume": bar["volume"],
        "parent_source_object_ids": list(bar["parent_source_object_ids"]),
        "quality_state": bar["quality_state"],
    }


def source_bar_id(bar: Mapping[str, Any]) -> str:
    return f"rps-price:{canonical_hash(bar_logical_dict(bar))}"


def recompute_c1(
    record: Mapping[str, Any],
    prior: Mapping[str, Any] | None,
) -> tuple[dict[str, str | None], dict[str, str], dict[str, str]]:
    with localcontext() as context:
        context.prec = 34
        prices = record["prices"]
        o = Decimal(str(prices["open"]))
        h = Decimal(str(prices["high"]))
        l = Decimal(str(prices["low"]))
        c = Decimal(str(prices["close"]))
        range_abs = h - l
        body = c - o
        upper = h - max(o, c)
        lower = min(o, c) - l
        values: dict[str, str | None] = {
            "range_abs": _render(range_abs),
            "range_ticks": _render(range_abs / PRICE_INCREMENT),
            "body_signed": _render(body),
            "body_abs": _render(abs(body)),
            "body_utilisation": _render(abs(body) / range_abs) if range_abs else None,
            "upper_wick_abs": _render(upper),
            "lower_wick_abs": _render(lower),
            "upper_wick_share": _render(upper / range_abs) if range_abs else None,
            "lower_wick_share": _render(lower / range_abs) if range_abs else None,
            "wick_balance": _render((upper - lower) / range_abs) if range_abs else None,
            "open_location": _render((o - l) / range_abs) if range_abs else None,
            "close_location": _render((c - l) / range_abs) if range_abs else None,
            "signed_efficiency": _render(body / range_abs) if range_abs else None,
            "true_range_abs": None,
            "true_range_ticks": None,
            "close_change": None,
            "open_gap": None,
        }
        nulls: dict[str, str] = {}
        if not range_abs:
            for field in (
                "body_utilisation",
                "upper_wick_share",
                "lower_wick_share",
                "wick_balance",
                "open_location",
                "close_location",
                "signed_efficiency",
            ):
                nulls[field] = "ZERO_RANGE"
        if prior is None:
            for field in ("true_range_abs", "true_range_ticks", "close_change", "open_gap"):
                nulls[field] = "NO_PRIOR_BAR"
        else:
            prior_close = Decimal(str(prior["prices"]["close"]))
            true_range = max(range_abs, abs(h - prior_close), abs(l - prior_close))
            values["true_range_abs"] = _render(true_range)
            values["true_range_ticks"] = _render(true_range / PRICE_INCREMENT)
            values["close_change"] = _render(c - prior_close)
            values["open_gap"] = _render(o - prior_close)
        categorical = {"direction": "UP" if body > 0 else "DOWN" if body < 0 else "FLAT"}
        return values, categorical, nulls


def expected_c1_record_id(record: Mapping[str, Any]) -> str:
    identity = {
        "source_bar_id": record["source_bar_id"],
        "release_id": record["opt_a_release_id"],
        "manifest_id": record["opt_a_manifest_id"],
        "clock_id": record["clock"],
        "price_side": record["side"],
        "formula_registry_id": record["formula_registry_id"],
        "measurements": record["measurements"],
        "categorical": record["categorical"],
        "null_reasons": record["null_reasons"],
    }
    return f"c1:{canonical_hash(identity, ensure_ascii=False)}"


def audit_stream(
    bars: Sequence[Mapping[str, Any]],
    c1_records: Sequence[Mapping[str, Any]],
    *,
    clock: str,
    side: str,
) -> dict[str, Any]:
    if clock not in CLOCK_SECONDS:
        raise SourceC1AuditError(f"UNKNOWN_CLOCK:{clock}")
    errors: Counter[str] = Counter()
    expected_seconds = CLOCK_SECONDS[clock]
    expected_parents = EXPECTED_PARENT_COUNTS[clock]
    bar_ids: set[str] = set()
    bar_by_id: dict[str, Mapping[str, Any]] = {}
    previous_start: datetime | None = None
    complete_ids: set[str] = set()
    counts: Counter[str] = Counter()
    parent_histogram: Counter[int] = Counter()

    for bar in bars:
        bar_id = str(bar.get("bar_id"))
        if bar_id in bar_ids:
            errors["duplicate_bar_id"] += 1
        bar_ids.add(bar_id)
        bar_by_id[bar_id] = bar
        if bar.get("clock") != clock:
            errors["bar_clock"] += 1
        if bar.get("side") != side:
            errors["bar_side"] += 1
        start = parse_utc(str(bar["start_utc"]))
        end = parse_utc(str(bar["end_utc"]))
        if int((end - start).total_seconds()) != expected_seconds:
            errors["bar_duration"] += 1
        if previous_start is not None and start <= previous_start:
            errors["bar_non_monotonic"] += 1
        previous_start = start
        parent_count = len(bar.get("parent_source_object_ids", []))
        parent_histogram[parent_count] += 1
        quality = bar.get("quality_state")
        counts["bars_total"] += 1
        if bar.get("target_eligible") is True:
            counts["target_total"] += 1
        if quality == "COMPLETE":
            complete_ids.add(bar_id)
            counts["bars_complete"] += 1
            if bar.get("target_eligible") is True:
                counts["target_complete"] += 1
            if parent_count != expected_parents:
                errors["complete_parent_count"] += 1
            if any(bar.get(field) is None for field in ("open", "high", "low", "close", "volume")):
                errors["complete_null_ohlcv"] += 1
        elif quality == "QUARANTINED_INCOMPLETE_PARENT_SET":
            counts["bars_incomplete"] += 1
            if bar.get("target_eligible") is True:
                counts["target_incomplete"] += 1
            if parent_count >= expected_parents:
                errors["incomplete_parent_count"] += 1
            if any(bar.get(field) is not None for field in ("open", "high", "low", "close", "volume")):
                errors["incomplete_nonnull_ohlcv"] += 1
        else:
            errors["unknown_quality_state"] += 1

    c1_ids: set[str] = set()
    used_parent_ids: set[str] = set()
    prior: Mapping[str, Any] | None = None
    for record in c1_records:
        counts["c1_total"] += 1
        if record.get("target_eligible") is True:
            counts["c1_target"] += 1
        record_id = str(record.get("c1_record_id"))
        if record_id in c1_ids:
            errors["duplicate_c1_id"] += 1
        c1_ids.add(record_id)
        parent_id = str(record.get("source_path", "")).split("/")[-1]
        parent = bar_by_id.get(parent_id)
        if parent is None:
            errors["source_path_missing"] += 1
            prior = record
            continue
        if parent_id in used_parent_ids:
            errors["duplicate_c1_parent"] += 1
        used_parent_ids.add(parent_id)
        if parent.get("quality_state") != "COMPLETE":
            errors["c1_from_incomplete"] += 1
        if record.get("clock") != clock:
            errors["c1_clock"] += 1
        if record.get("side") != side:
            errors["c1_side"] += 1
        if record.get("open_time") != parent.get("start_utc") or record.get("close_time") != parent.get("end_utc"):
            errors["time_lineage"] += 1
        expected_prices = {field: parent.get(field) for field in ("open", "high", "low", "close")}
        if record.get("prices") != expected_prices:
            errors["price_lineage"] += 1
        if record.get("parent_m1_bar_ids") != parent.get("parent_source_object_ids"):
            errors["parent_m1_lineage"] += 1
        if record.get("source_bar_id") != source_bar_id(parent):
            errors["source_bar_identity"] += 1
        lawful_prior = prior if prior is not None and prior.get("close_time") == record.get("open_time") else None
        measurements, categorical, null_reasons = recompute_c1(record, lawful_prior)
        if record.get("measurements") != measurements:
            errors["formula_values"] += 1
        if record.get("categorical") != categorical:
            errors["categorical"] += 1
        if record.get("null_reasons") != null_reasons:
            errors["null_reasons"] += 1
        if record.get("formula_registry_id") != FORMULA_REGISTRY_ID:
            errors["formula_registry_id"] += 1
        if record_id != expected_c1_record_id(record):
            errors["c1_record_identity"] += 1
        prior = record

    missing = complete_ids - used_parent_ids
    extra = used_parent_ids - complete_ids
    if missing:
        errors["c1_complete_bijection_missing"] += len(missing)
    if extra:
        errors["c1_complete_bijection_extra"] += len(extra)

    return {
        "clock": clock,
        "side": side,
        "counts": dict(counts),
        "parent_count_histogram": {str(key): value for key, value in sorted(parent_histogram.items())},
        "mismatches": dict(errors),
        "result": "PASS" if not errors else "FAIL",
    }


def audit_files(
    bars_path: Path,
    c1_path: Path,
    *,
    clock: str,
    side: str,
    expected_bar_sha256: str | None = None,
    expected_c1_sha256: str | None = None,
) -> dict[str, Any]:
    observed_bar_sha = sha256_file(bars_path)
    observed_c1_sha = sha256_file(c1_path)
    if expected_bar_sha256 is not None and observed_bar_sha != expected_bar_sha256:
        raise SourceC1AuditError(f"BAR_SHA256_MISMATCH:{clock}:{side}")
    if expected_c1_sha256 is not None and observed_c1_sha != expected_c1_sha256:
        raise SourceC1AuditError(f"C1_SHA256_MISMATCH:{clock}:{side}")
    result = audit_stream(read_jsonl(bars_path), read_jsonl(c1_path), clock=clock, side=side)
    result["file_sha256"] = {"bars": observed_bar_sha, "c1": observed_c1_sha}
    return result


def validate_reference(reference: Mapping[str, Any]) -> dict[str, Any]:
    if reference.get("schema") != "ovc-mta-wp2-external-audit-reference/v1":
        raise SourceC1AuditError("REFERENCE_SCHEMA_MISMATCH")
    if reference.get("programme_id") != "OVC-MTA-v0.2" or reference.get("gate_id") != "MTA-G2":
        raise SourceC1AuditError("REFERENCE_IDENTITY_MISMATCH")
    files = reference.get("input_files")
    if not isinstance(files, list) or len(files) != 8:
        raise SourceC1AuditError("REFERENCE_INPUT_FILE_COUNT_MISMATCH")
    keys = {(item.get("role"), item.get("clock"), item.get("side")) for item in files}
    expected = {
        (role, clock, side)
        for role in ("BARS", "C1")
        for clock in ("15M", "2H_A_L")
        for side in ("BID", "ASK")
    }
    if keys != expected:
        raise SourceC1AuditError("REFERENCE_INPUT_FILE_MATRIX_MISMATCH")
    accounting = reference.get("record_accounting")
    if not isinstance(accounting, dict):
        raise SourceC1AuditError("REFERENCE_ACCOUNTING_MISSING")
    if accounting.get("derived_bars_complete") != accounting.get("c1_records_total"):
        raise SourceC1AuditError("REFERENCE_COMPLETE_C1_ACCOUNTING_MISMATCH")
    if accounting.get("unaccounted_derived_records") != 0:
        raise SourceC1AuditError("REFERENCE_UNACCOUNTED_RECORDS")
    if reference.get("qa_recommendation") != "PASS":
        raise SourceC1AuditError("REFERENCE_QA_NOT_PASS")
    if reference.get("validation_consumption") != "DENIED" or reference.get("r2_publication") != "DENIED":
        raise SourceC1AuditError("REFERENCE_AUTHORITY_ESCAPE")
    mismatches = reference.get("mismatch_counts")
    if not isinstance(mismatches, dict) or any(value != 0 for value in mismatches.values()):
        raise SourceC1AuditError("REFERENCE_MISMATCHES_NONZERO")
    return {
        "status": "PASS",
        "audit_id": reference["audit_id"],
        "external_artifact_sha256": reference["external_artifact"]["sha256"],
        "audited_derived_records_total": accounting["audited_derived_records_total"],
        "logical_sha256": canonical_hash(dict(reference)),
    }
