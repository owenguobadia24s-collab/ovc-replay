from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class SynchronisationFinding:
    finding_type: str
    severity: str
    field: str
    source_value: Any
    projection_value: Any
    consequence: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compare_programme_state(
    source_state: Mapping[str, Any],
    projection: Mapping[str, Any],
    *,
    source_commit: str | None = None,
    projection_source_commit: str | None = None,
) -> dict[str, Any]:
    """Compare without repairing; the programme-owned state remains effective."""
    if source_state.get("programme_id") != projection.get("programme_id"):
        raise ValueError("programme_id mismatch")

    findings: list[SynchronisationFinding] = []
    if source_commit and projection_source_commit and source_commit != projection_source_commit:
        findings.append(
            SynchronisationFinding(
                finding_type="STALE_PROJECTION",
                severity="BLOCK",
                field="source_commit",
                source_value=source_commit,
                projection_value=projection_source_commit,
                consequence="Derived portfolio state cannot be treated as current.",
            )
        )

    compared_fields = ("status", "current_packet", "current_gate", "blockers", "next_action")
    for field in compared_fields:
        if field not in source_state:
            continue
        source_value = source_state.get(field)
        projection_value = projection.get(field)
        if source_value != projection_value:
            findings.append(
                SynchronisationFinding(
                    finding_type="STATE_SOURCE_CONFLICT",
                    severity="BLOCK",
                    field=field,
                    source_value=source_value,
                    projection_value=projection_value,
                    consequence="Keep programme-owned source value; expose projection conflict.",
                )
            )

    return {
        "programme_id": source_state["programme_id"],
        "source_state_authoritative": True,
        "effective_state": dict(source_state),
        "derived_projection": dict(projection),
        "status": "PASS" if not findings else "CONFLICT",
        "findings": [finding.to_dict() for finding in findings],
        "repair_performed": False,
        "enforcement_allowed": False,
    }
