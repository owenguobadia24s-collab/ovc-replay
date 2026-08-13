"""Diagnostic-only development latency tracing.

Measures observable execution around already-authorized OVC/DSAI operations.
It grants no authority, uses overlap-safe interval accounting, and never infers
model reasoning time without explicit measured platform telemetry.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import subprocess
import time
from typing import Any, Callable, Iterator, Mapping, Sequence

from ovc.development.identity import canonical_sha256

EVIDENCE_CLASSES = frozenset({"MEASURED", "DERIVED", "INFERRED", "UNAVAILABLE"})
ACTIVITY_CLASSES = frozenset({"ACTIVE", "WAIT", "OVERLAP"})
LATENCY_CATEGORIES = (
    "MODEL_REASONING", "REPOSITORY_INSPECTION", "CONNECTOR_TOOL_LATENCY",
    "LOCAL_EXECUTION", "LOCAL_TEST_ASSURANCE", "REMOTE_CI_QUEUE",
    "REMOTE_CI_EXECUTION", "POLLING_WAIT", "REMEDIATION_RETRY",
    "EVIDENCE_COLLECTION", "OPERATOR_GATE_WAIT", "FINAL_SYNTHESIS", "OTHER",
)
DIAGNOSTIC_RECEIPT_CLASS = "TEMPORARY_DIAGNOSTIC_OBSERVABILITY"
DIAGNOSTIC_AUTHORITY_EFFECT = "NONE"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include an explicit timezone")
    return parsed.astimezone(timezone.utc)


def _duration_ms(started_at: str, completed_at: str) -> int:
    milliseconds = int(round((_parse_utc(completed_at) - _parse_utc(started_at)).total_seconds() * 1000))
    if milliseconds < 0:
        raise ValueError("completed_at precedes started_at")
    return milliseconds


def _epoch_ms(value: str) -> int:
    return int(round(_parse_utc(value).timestamp() * 1000))


def _union_ms(intervals: Sequence[tuple[int, int]]) -> int:
    ordered = sorted((start, end) for start, end in intervals if end >= start)
    if not ordered:
        return 0
    total = 0
    current_start, current_end = ordered[0]
    for start, end in ordered[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            total += current_end - current_start
            current_start, current_end = start, end
    return total + current_end - current_start


def _ratio(numerator_ms: int | None, denominator_ms: int | None) -> float | None:
    if numerator_ms is None or denominator_ms is None or denominator_ms <= 0:
        return None
    return round(numerator_ms / denominator_ms, 6)


class DevelopmentTrace:
    """Append-only in-memory trace for one development run."""

    def __init__(
        self, *, run_id: str, programme_id: str | None = None, packet_id: str | None = None,
        started_at_utc: str | None = None, clock_ns: Callable[[], int] = time.perf_counter_ns,
        utc_now: Callable[[], str] = _utc_now, allow_model_reasoning_telemetry: bool = False,
    ) -> None:
        if not str(run_id):
            raise ValueError("run_id is required")
        self.run_id = str(run_id)
        self.programme_id = str(programme_id) if programme_id else None
        self.packet_id = str(packet_id) if packet_id else None
        self._clock_ns = clock_ns
        self._utc_now = utc_now
        self._allow_model_reasoning_telemetry = bool(allow_model_reasoning_telemetry)
        self.started_at_utc = started_at_utc or utc_now()
        _parse_utc(self.started_at_utc)
        self._wall_start_ns = int(clock_ns())
        self._events: list[dict[str, Any]] = []
        self._open: dict[str, dict[str, Any]] = {}
        self._sequence = 0

    @property
    def events(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(event) for event in self._events)

    def _validate(self, category: str, activity_class: str, evidence_class: str, metadata: Mapping[str, Any] | None) -> None:
        if category not in LATENCY_CATEGORIES:
            raise ValueError(f"unsupported latency category {category}")
        if activity_class not in ACTIVITY_CLASSES:
            raise ValueError(f"unsupported activity class {activity_class}")
        if evidence_class not in EVIDENCE_CLASSES:
            raise ValueError(f"unsupported evidence class {evidence_class}")
        if category == "MODEL_REASONING":
            telemetry = str((metadata or {}).get("telemetry_source", ""))
            if not (self._allow_model_reasoning_telemetry and evidence_class == "MEASURED" and telemetry.startswith("PLATFORM_TELEMETRY")):
                raise ValueError("MODEL_REASONING requires explicit measured platform telemetry")

    def start_span(self, *, category: str, operation: str, source: str, activity_class: str = "ACTIVE",
                   evidence_class: str = "MEASURED", evidence_ref: str | None = None,
                   overlap_group: str | None = None, metadata: Mapping[str, Any] | None = None) -> str:
        self._validate(category, activity_class, evidence_class, metadata)
        self._sequence += 1
        token = f"{self.run_id}:{self._sequence:06d}"
        self._open[token] = {
            "category": category, "operation": str(operation), "activity_class": activity_class,
            "source": str(source), "evidence_class": evidence_class,
            "evidence_ref": str(evidence_ref) if evidence_ref else None,
            "overlap_group": str(overlap_group) if overlap_group else None,
            "metadata": dict(metadata or {}), "started_at_utc": self._utc_now(),
            "started_ns": int(self._clock_ns()),
        }
        return token

    def finish_span(self, token: str, *, outcome: str = "PASS", evidence_ref: str | None = None,
                    metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if token not in self._open:
            raise ValueError(f"unknown or already-finished span {token}")
        opened = self._open.pop(token)
        completed_at_utc = self._utc_now()
        duration_ms = max(0, int(round((int(self._clock_ns()) - int(opened["started_ns"])) / 1_000_000)))
        logical = {
            "run_id": self.run_id, "sequence": int(token.rsplit(":", 1)[1]),
            "category": opened["category"], "operation": opened["operation"],
            "activity_class": opened["activity_class"], "source": opened["source"],
            "evidence_class": opened["evidence_class"],
            "evidence_ref": str(evidence_ref) if evidence_ref else opened["evidence_ref"],
            "overlap_group": opened["overlap_group"], "started_at_utc": opened["started_at_utc"],
            "completed_at_utc": completed_at_utc, "duration_ms": duration_ms,
            "outcome": str(outcome), "metadata": {**opened["metadata"], **dict(metadata or {})},
        }
        event = {"schema": "ovc-development-observability-event/v1", **logical, "authority_effect": "NONE",
                 "record_id": canonical_sha256(logical, role="OVC_DEVELOPMENT_OBSERVABILITY_EVENT")}
        self._events.append(event)
        return dict(event)

    @contextmanager
    def span(self, **kwargs: Any) -> Iterator[str]:
        token = self.start_span(**kwargs)
        try:
            yield token
        except BaseException as exc:
            self.finish_span(token, outcome="FAIL", metadata={"exception_type": type(exc).__name__})
            raise
        else:
            self.finish_span(token)

    def measure_call(self, func: Callable[..., Any], *args: Any, category: str, operation: str, source: str,
                     activity_class: str = "ACTIVE", evidence_ref: str | None = None,
                     overlap_group: str | None = None, metadata: Mapping[str, Any] | None = None, **kwargs: Any) -> Any:
        with self.span(category=category, operation=operation, source=source, activity_class=activity_class,
                       evidence_ref=evidence_ref, overlap_group=overlap_group, metadata=metadata):
            return func(*args, **kwargs)

    def record_external_interval(self, *, category: str, operation: str, started_at_utc: str,
                                 completed_at_utc: str, activity_class: str, source: str,
                                 evidence_class: str = "MEASURED", evidence_ref: str | None = None,
                                 overlap_group: str | None = None, outcome: str = "PASS",
                                 metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
        self._validate(category, activity_class, evidence_class, metadata)
        _parse_utc(started_at_utc); _parse_utc(completed_at_utc)
        self._sequence += 1
        logical = {
            "run_id": self.run_id, "sequence": self._sequence, "category": category,
            "operation": str(operation), "activity_class": activity_class, "source": str(source),
            "evidence_class": evidence_class, "evidence_ref": str(evidence_ref) if evidence_ref else None,
            "overlap_group": str(overlap_group) if overlap_group else None,
            "started_at_utc": str(started_at_utc), "completed_at_utc": str(completed_at_utc),
            "duration_ms": _duration_ms(started_at_utc, completed_at_utc), "outcome": str(outcome),
            "metadata": dict(metadata or {}),
        }
        event = {"schema": "ovc-development-observability-event/v1", **logical, "authority_effect": "NONE",
                 "record_id": canonical_sha256(logical, role="OVC_DEVELOPMENT_OBSERVABILITY_EVENT")}
        self._events.append(event)
        return dict(event)

    def finish_run(self, *, completed_at_utc: str | None = None) -> dict[str, Any]:
        if self._open:
            raise RuntimeError("cannot finish run with open spans")
        finished_at = completed_at_utc or self._utc_now()
        _parse_utc(finished_at)
        monotonic_wall_ms = max(0, int(round((int(self._clock_ns()) - self._wall_start_ns) / 1_000_000)))
        utc_wall_ms = _duration_ms(self.started_at_utc, finished_at)
        wall_ms = utc_wall_ms if completed_at_utc is not None else monotonic_wall_ms
        return summarize_trace(run_id=self.run_id, programme_id=self.programme_id, packet_id=self.packet_id,
                               started_at_utc=self.started_at_utc, completed_at_utc=finished_at,
                               total_wall_ms=wall_ms, events=self._events)


def summarize_trace(*, run_id: str, programme_id: str | None, packet_id: str | None,
                    started_at_utc: str, completed_at_utc: str, total_wall_ms: int,
                    events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    all_intervals: list[tuple[int, int]] = []
    by_category = {category: [] for category in LATENCY_CATEGORIES}
    by_activity = {activity: [] for activity in ACTIVITY_CLASSES}
    counts = {category: 0 for category in LATENCY_CATEGORIES}
    for event in events:
        interval = (_epoch_ms(str(event["started_at_utc"])), _epoch_ms(str(event["completed_at_utc"])))
        all_intervals.append(interval)
        category, activity = str(event["category"]), str(event["activity_class"])
        by_category[category].append(interval); by_activity[activity].append(interval); counts[category] += 1
    total = max(0, int(total_wall_ms))
    observed = _union_ms(all_intervals)
    if total:
        observed = min(observed, total)
    category_ms = {category: _union_ms(value) for category, value in by_category.items()}
    active_ms, wait_ms = _union_ms(by_activity["ACTIVE"]), _union_ms(by_activity["WAIT"])
    verification_ms = _union_ms(by_category["LOCAL_TEST_ASSURANCE"] + by_category["REMOTE_CI_QUEUE"] + by_category["REMOTE_CI_EXECUTION"])
    poll_ms = _union_ms(by_category["POLLING_WAIT"] + by_category["OPERATOR_GATE_WAIT"])
    remediation_ms = _union_ms(by_category["REMEDIATION_RETRY"])
    decomposition = {category: {"duration_ms": category_ms[category] if counts[category] else None,
                                "evidence_class": "MEASURED" if counts[category] else "UNAVAILABLE",
                                "event_count": counts[category]} for category in LATENCY_CATEGORIES}
    if not counts["MODEL_REASONING"]:
        decomposition["MODEL_REASONING"] = {"duration_ms": None, "evidence_class": "UNAVAILABLE", "event_count": 0,
                                             "reason": "NO_EXPLICIT_PLATFORM_MODEL_TELEMETRY"}
    logical = {
        "run_id": str(run_id), "programme_id": str(programme_id) if programme_id else None,
        "packet_id": str(packet_id) if packet_id else None, "started_at_utc": str(started_at_utc),
        "completed_at_utc": str(completed_at_utc), "total_wall_ms": total,
        "observed_union_ms": observed, "unobserved_wall_ms": max(0, total - observed),
        "latency_decomposition": decomposition,
        "throughput": {
            "active_execution_ms": active_ms, "external_wait_ms": wait_ms,
            "known_idle_or_poll_ms": poll_ms, "verification_ms": verification_ms,
            "remediation_ms": remediation_ms, "active_execution_ratio": _ratio(active_ms, total),
            "external_wait_ratio": _ratio(wait_ms, total), "verification_ratio": _ratio(verification_ms, total),
            "remediation_ratio": _ratio(remediation_ms, total),
        },
        "overlap_accounting": "INTERVAL_UNION_NO_DOUBLE_COUNT",
        "model_reasoning_policy": "UNAVAILABLE_UNLESS_EXPLICIT_MEASURED_PLATFORM_TELEMETRY",
        "event_count": len(events),
    }
    return {"schema": "ovc-development-observability-trace-summary/v1", **logical, "authority_effect": "NONE",
            "record_id": canonical_sha256(logical, role="OVC_DEVELOPMENT_OBSERVABILITY_TRACE_SUMMARY")}


def observe_subprocess(trace: DevelopmentTrace, command: Sequence[str], *, category: str = "LOCAL_EXECUTION",
                       operation: str | None = None, activity_class: str = "ACTIVE", source: str = "LOCAL_SUBPROCESS",
                       evidence_ref: str | None = None,
                       runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
                       **run_kwargs: Any) -> subprocess.CompletedProcess[Any]:
    """Measure an already-authorized subprocess call without granting permission."""
    command_list = [str(value) for value in command]
    if not command_list:
        raise ValueError("command is required")
    token = trace.start_span(category=category, operation=operation or command_list[0], activity_class=activity_class,
                             source=source, evidence_ref=evidence_ref, metadata={"argv": command_list})
    try:
        result = runner(command_list, **run_kwargs)
    except BaseException as exc:
        trace.finish_span(token, outcome="FAIL", metadata={"exception_type": type(exc).__name__})
        raise
    returncode = int(getattr(result, "returncode", 0))
    trace.finish_span(token, outcome="PASS" if returncode == 0 else "FAIL", metadata={"returncode": returncode})
    return result


def ingest_github_workflow_jobs(trace: DevelopmentTrace, *, workflow_run: Mapping[str, Any],
                                jobs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Ingest GitHub Actions queue/execution intervals from already-fetched payloads."""
    recorded: list[dict[str, Any]] = []
    run_id = workflow_run.get("id")
    for job in jobs:
        job_id, name = job.get("id"), str(job.get("name", "github-job"))
        created, started, completed = job.get("created_at"), job.get("started_at"), job.get("completed_at")
        evidence_ref = f"github-run:{run_id}/job:{job_id}"
        if created and started and _duration_ms(str(created), str(started)) > 0:
            recorded.append(trace.record_external_interval(category="REMOTE_CI_QUEUE", operation=f"{name}:queue",
                started_at_utc=str(created), completed_at_utc=str(started), activity_class="WAIT",
                source="GITHUB_ACTIONS", evidence_ref=evidence_ref, overlap_group=f"github-run:{run_id}",
                metadata={"workflow_name": workflow_run.get("name"), "job_name": name}))
        if started and completed:
            recorded.append(trace.record_external_interval(category="REMOTE_CI_EXECUTION", operation=name,
                started_at_utc=str(started), completed_at_utc=str(completed), activity_class="WAIT",
                source="GITHUB_ACTIONS", evidence_ref=evidence_ref, overlap_group=f"github-run:{run_id}",
                outcome=str(job.get("conclusion") or job.get("status") or "UNKNOWN").upper(),
                metadata={"workflow_name": workflow_run.get("name"), "job_name": name}))
    return recorded
