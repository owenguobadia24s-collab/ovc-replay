"""ASOCS audit-source qualification and literal-source parser.

This module is intentionally source-facing only.  It never creates OPT-A releases,
assigns BID/ASK, maps source timestamps to a timezone, or admits the audit period
into an OVC research role.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import csv
import hashlib
from pathlib import Path
from typing import Iterator, Mapping, Sequence, TextIO

EXPECTED_HEADER: tuple[str, ...] = (
    "Date",
    "Time",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
)
DATE_TIME_FORMAT = "%Y%m%d %H:%M:%S"
CLAIM_CLASS_EXACT = "EXACT_ACTIVE_STACK_OBSERVATIONAL_COHERENCE"
CLAIM_CLASS_MORPHOLOGY = "ASOCS_SINGLE_STREAM_MORPHOLOGY_COHERENCE"
EXACT_INTERFACE_NOT_EVALUABLE = "NOT_EVALUABLE_EXACT_ACTIVE_INTERFACE"
AUDIT_ROLE = "ASOCS_AUDIT_OUT_OF_ROLE_H1_2026"
UNRESOLVED_SIDE = "UNRESOLVED_SINGLE_STREAM"
UNRESOLVED_TIMEZONE = "SOURCE_TIMEZONE_UNRESOLVED"


class ASOCSSourceQualificationError(ValueError):
    """Fail-closed source qualification failure."""


@dataclass(frozen=True)
class ASOCSRow:
    row_number: int
    literal_date: str
    literal_time: str
    source_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @property
    def literal_timestamp(self) -> str:
        return f"{self.literal_date} {self.literal_time}"


@dataclass(frozen=True)
class ASOCSSourceGap:
    previous_literal_timestamp: str
    next_literal_timestamp: str
    delta_minutes: int
    state: str = "OBSERVED_SOURCE_GAP"


@dataclass(frozen=True)
class SourceProvenanceAssessment:
    provider_label: str
    provider_status: str
    provider_evidence: tuple[str, ...]
    price_side: str
    price_side_status: str
    timestamp_timezone: str
    timestamp_timezone_status: str
    session_metadata: str
    role: str = AUDIT_ROLE
    active_provider: bool = False
    selector_eligible: bool = False
    ec1_eligible: bool = False


@dataclass(frozen=True)
class ClaimClassDecision:
    claim_class: str
    exact_active_interface_authorized: bool
    reason_codes: tuple[str, ...]
    active_provider: bool = False
    canonical: bool = False
    publication: bool = False


@dataclass(frozen=True)
class ASOCSSourceManifest:
    schema: str
    source_logical_name: str
    sha256: str
    byte_size: int
    row_count: int
    header: tuple[str, ...]
    instrument: str
    native_grain: str
    first_literal_timestamp: str
    last_literal_timestamp: str
    target_row_count: int
    target_first_literal_timestamp: str
    target_last_literal_timestamp: str
    pre_context_row_count: int
    post_context_row_count: int
    duplicate_timestamp_count: int
    non_monotonic_timestamp_count: int
    missing_cell_count: int
    parse_error_count: int
    ohlc_envelope_error_count: int
    numeric_domain_error_count: int
    adjacent_gap_count_target: int
    shortest_target_gap_minutes: int | None
    longest_target_gap_minutes: int | None
    month_target_counts: Mapping[str, int]
    source_bytes_mutated: bool = False
    authority_class: str = "ASOCS_AUDIT_ONLY"

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["header"] = list(self.header)
        value["month_target_counts"] = dict(self.month_target_counts)
        return value


@dataclass(frozen=True)
class SourceQualificationResult:
    manifest: ASOCSSourceManifest
    provenance: SourceProvenanceAssessment
    claim_class: ClaimClassDecision


def parse_literal_timestamp(date_text: str, time_text: str) -> datetime:
    """Parse the exact source Date+Time fields without timezone conversion."""
    if len(date_text) != 8 or not date_text.isascii() or not date_text.isdigit():
        raise ASOCSSourceQualificationError(f"INVALID_DATE_LITERAL:{date_text!r}")
    if len(time_text) != 8 or time_text[2] != ":" or time_text[5] != ":":
        raise ASOCSSourceQualificationError(f"INVALID_TIME_LITERAL:{time_text!r}")
    try:
        parsed = datetime.strptime(f"{date_text} {time_text}", DATE_TIME_FORMAT)
    except ValueError as exc:
        raise ASOCSSourceQualificationError(
            f"INVALID_TIMESTAMP_LITERAL:{date_text} {time_text}"
        ) from exc
    if parsed.tzinfo is not None:
        raise AssertionError("literal source parser must remain timezone-naive")
    return parsed


def parse_decimal(text: str, field: str) -> Decimal:
    """Locale-independent exact decimal parser; comma/localized forms are rejected."""
    if not text or "," in text or text.strip() != text:
        raise ASOCSSourceQualificationError(f"INVALID_DECIMAL_LITERAL:{field}:{text!r}")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ASOCSSourceQualificationError(
            f"INVALID_DECIMAL_LITERAL:{field}:{text!r}"
        ) from exc
    if not value.is_finite():
        raise ASOCSSourceQualificationError(f"NONFINITE_DECIMAL:{field}:{text!r}")
    return value


def parse_row(values: Sequence[str], row_number: int) -> ASOCSRow:
    if len(values) != len(EXPECTED_HEADER):
        raise ASOCSSourceQualificationError(
            f"COLUMN_COUNT_MISMATCH:row={row_number}:got={len(values)}"
        )
    if any(value == "" for value in values):
        raise ASOCSSourceQualificationError(f"MISSING_CELL:row={row_number}")
    date_text, time_text, o_text, h_text, l_text, c_text, v_text = values
    source_time = parse_literal_timestamp(date_text, time_text)
    o = parse_decimal(o_text, "Open")
    h = parse_decimal(h_text, "High")
    l = parse_decimal(l_text, "Low")
    c = parse_decimal(c_text, "Close")
    v = parse_decimal(v_text, "Volume")
    if min(o, h, l, c) <= 0 or v < 0:
        raise ASOCSSourceQualificationError(f"NUMERIC_DOMAIN_ERROR:row={row_number}")
    if l > h or not (l <= o <= h) or not (l <= c <= h):
        raise ASOCSSourceQualificationError(f"OHLC_ENVELOPE_ERROR:row={row_number}")
    return ASOCSRow(row_number, date_text, time_text, source_time, o, h, l, c, v)


def iter_source_rows(handle: TextIO) -> Iterator[ASOCSRow]:
    reader = csv.reader(handle, dialect="excel", strict=True)
    try:
        header = tuple(next(reader))
    except StopIteration as exc:
        raise ASOCSSourceQualificationError("EMPTY_SOURCE") from exc
    if header != EXPECTED_HEADER:
        raise ASOCSSourceQualificationError(
            f"HEADER_MISMATCH:expected={EXPECTED_HEADER!r}:got={header!r}"
        )
    for row_number, values in enumerate(reader, start=2):
        yield parse_row(values, row_number)


def default_provenance() -> SourceProvenanceAssessment:
    """Freeze only what the supplied artifact/design actually supports."""
    return SourceProvenanceAssessment(
        provider_label="DARWINEX",
        provider_status="DECLARED",
        provider_evidence=(
            "source logical filename contains darwinex",
            "ratified ASOCS design identifies provider label as Darwinex from supplied artifact identity",
        ),
        price_side=UNRESOLVED_SIDE,
        price_side_status="UNRESOLVED",
        timestamp_timezone=UNRESOLVED_TIMEZONE,
        timestamp_timezone_status="UNRESOLVED",
        session_metadata="NONE_SUPPLIED",
    )


def decide_claim_class(provenance: SourceProvenanceAssessment) -> ClaimClassDecision:
    exact = (
        provenance.price_side in {"BID", "ASK"}
        and provenance.price_side_status == "DECLARED"
        and provenance.timestamp_timezone_status == "DECLARED"
        and provenance.timestamp_timezone != UNRESOLVED_TIMEZONE
    )
    if exact:
        return ClaimClassDecision(CLAIM_CLASS_EXACT, True, ("EXACT_SIDE_AND_CLOCK_PROVENANCE",))
    reasons: list[str] = []
    if provenance.price_side == UNRESOLVED_SIDE:
        reasons.append("PRICE_SIDE_UNRESOLVED")
    if provenance.timestamp_timezone_status != "DECLARED":
        reasons.append("TIMESTAMP_TIMEZONE_NOT_EXACTLY_DECLARED")
    return ClaimClassDecision(CLAIM_CLASS_MORPHOLOGY, False, tuple(reasons))


def qualify_source(
    path: str | Path,
    *,
    expected_sha256: str,
    expected_byte_size: int | None = None,
    expected_row_count: int | None = None,
    expected_logical_name: str | None = None,
    target_start: datetime = datetime(2026, 1, 1),
    target_end: datetime = datetime(2026, 7, 1),
) -> SourceQualificationResult:
    source_path = Path(path)
    raw = source_path.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != expected_sha256:
        raise ASOCSSourceQualificationError(
            f"SOURCE_HASH_MISMATCH:expected={expected_sha256}:actual={actual_sha}"
        )
    if expected_byte_size is not None and len(raw) != expected_byte_size:
        raise ASOCSSourceQualificationError(
            f"SOURCE_BYTE_SIZE_MISMATCH:expected={expected_byte_size}:actual={len(raw)}"
        )
    try:
        raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ASOCSSourceQualificationError("SOURCE_NOT_STRICT_UTF8") from exc

    row_count = 0
    first_row: ASOCSRow | None = None
    last_row: ASOCSRow | None = None
    previous: ASOCSRow | None = None
    seen: set[datetime] = set()
    duplicate_count = 0
    non_monotonic_count = 0
    target_count = 0
    pre_count = 0
    post_count = 0
    target_first: ASOCSRow | None = None
    target_last: ASOCSRow | None = None
    target_gap_deltas: list[int] = []
    target_previous: ASOCSRow | None = None
    month_counts: dict[str, int] = {}

    with source_path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        for row in iter_source_rows(handle):
            row_count += 1
            if first_row is None:
                first_row = row
            last_row = row
            if row.source_time in seen:
                duplicate_count += 1
            seen.add(row.source_time)
            if previous is not None and row.source_time <= previous.source_time:
                non_monotonic_count += 1
            previous = row

            if row.source_time < target_start:
                pre_count += 1
            elif row.source_time >= target_end:
                post_count += 1
            else:
                target_count += 1
                if target_first is None:
                    target_first = row
                target_last = row
                month = row.source_time.strftime("%Y-%m")
                month_counts[month] = month_counts.get(month, 0) + 1
                if target_previous is not None:
                    delta = int((row.source_time - target_previous.source_time).total_seconds() // 60)
                    if delta > 1:
                        target_gap_deltas.append(delta)
                target_previous = row

    if first_row is None or last_row is None:
        raise ASOCSSourceQualificationError("SOURCE_HAS_NO_DATA_ROWS")
    if expected_row_count is not None and row_count != expected_row_count:
        raise ASOCSSourceQualificationError(
            f"SOURCE_ROW_COUNT_MISMATCH:expected={expected_row_count}:actual={row_count}"
        )
    if duplicate_count:
        raise ASOCSSourceQualificationError(f"DUPLICATE_TIMESTAMPS:{duplicate_count}")
    if non_monotonic_count:
        raise ASOCSSourceQualificationError(f"NON_MONOTONIC_TIMESTAMPS:{non_monotonic_count}")
    if target_first is None or target_last is None:
        raise ASOCSSourceQualificationError("TARGET_HAS_NO_ROWS")

    manifest = ASOCSSourceManifest(
        schema="ovc-asocs-source-manifest/v0_1",
        source_logical_name=expected_logical_name or source_path.name,
        sha256=actual_sha,
        byte_size=len(raw),
        row_count=row_count,
        header=EXPECTED_HEADER,
        instrument="GBPUSD",
        native_grain="M1",
        first_literal_timestamp=first_row.literal_timestamp,
        last_literal_timestamp=last_row.literal_timestamp,
        target_row_count=target_count,
        target_first_literal_timestamp=target_first.literal_timestamp,
        target_last_literal_timestamp=target_last.literal_timestamp,
        pre_context_row_count=pre_count,
        post_context_row_count=post_count,
        duplicate_timestamp_count=duplicate_count,
        non_monotonic_timestamp_count=non_monotonic_count,
        missing_cell_count=0,
        parse_error_count=0,
        ohlc_envelope_error_count=0,
        numeric_domain_error_count=0,
        adjacent_gap_count_target=len(target_gap_deltas),
        shortest_target_gap_minutes=min(target_gap_deltas) if target_gap_deltas else None,
        longest_target_gap_minutes=max(target_gap_deltas) if target_gap_deltas else None,
        month_target_counts=dict(sorted(month_counts.items())),
    )
    provenance = default_provenance()
    return SourceQualificationResult(manifest, provenance, decide_claim_class(provenance))


def exact_interface_evaluability_matrix() -> list[dict[str, object]]:
    """Fail-closed WP1 matrix. Morphology compatibility is not granted here.

    The active C1 contract requires an exact active OPT-A release, clock and price
    side. Because the supplied audit stream has neither an active release identity
    nor exact side/timezone provenance, every downstream exact active-interface
    construct is blocked transitively. WP4 may separately prove a non-authoritative
    morphology-compatible adapter under the downgraded claim class.
    """
    constructs = (
        "C1_ARITHMETIC_PRIMITIVES",
        "C2_OBSERVATION",
        "C2_HORIZON",
        "C2_LEVEL",
        "C2_CONTAINER",
        "C2_RELATION",
        "C2_FORMULA",
        "C2_TRANSITION",
        "C2_PARENT_CONTEXT",
        "C2_COMPUTABILITY",
        "C2E_EPISODE",
        "C2E_PHASE",
        "OCCURRENCE_CONTEXT_ATTACHMENT",
    )
    rows: list[dict[str, object]] = []
    for construct in constructs:
        rows.append(
            {
                "construct": construct,
                "exact_active_interface": EXACT_INTERFACE_NOT_EVALUABLE,
                "reason_codes": [
                    "NO_ACTIVE_OPT_A_RELEASE_IDENTITY_FOR_AUDIT_SOURCE",
                    "PRICE_SIDE_UNRESOLVED",
                    "TIMESTAMP_TIMEZONE_UNRESOLVED",
                ],
                "morphology_route": "TO_BE_PROVEN_OR_FAIL_CLOSED_IN_ASOCSI_WP4",
                "authority_effect": "NONE",
            }
        )
    return rows
