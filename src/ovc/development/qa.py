"""Reusable QA assertions with fail-closed aggregation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .identity import canonical_sha256


VALID_STATUSES = {"PASS", "WARN", "BLOCK", "QUARANTINE", "NOT_EVALUABLE"}
_BLOCKING = {"BLOCK", "QUARANTINE", "NOT_EVALUABLE"}


@dataclass(frozen=True)
class QAAssertion:
    check_id: str
    target: str
    status: str
    severity: str
    evidence: tuple[str, ...]
    timestamp: str
    code_hash: str
    config_hash: str
    input_hash: str
    issue_links: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.check_id or not self.target:
            raise ValueError("check_id and target are required")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"invalid QA status: {self.status}")
        if not self.evidence:
            raise ValueError("QA evidence is required")
        for value in (self.code_hash, self.config_hash, self.input_hash):
            if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
                raise ValueError("QA hashes must be lowercase SHA-256")

    @property
    def assertion_id(self) -> str:
        return canonical_sha256(asdict(self), role="QA_ASSERTION")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["assertion_id"] = self.assertion_id
        return result


def aggregate_assertions(assertions: Iterable[QAAssertion]) -> dict[str, Any]:
    rows = sorted(assertions, key=lambda row: (row.check_id, row.target, row.assertion_id))
    if not rows:
        return {
            "status": "NOT_EVALUABLE",
            "reason": "NO_ASSERTIONS",
            "assertion_count": 0,
            "assertions": [],
        }
    statuses = {row.status for row in rows}
    if "QUARANTINE" in statuses:
        status = "QUARANTINE"
    elif "BLOCK" in statuses:
        status = "BLOCK"
    elif "NOT_EVALUABLE" in statuses:
        status = "NOT_EVALUABLE"
    elif "WARN" in statuses:
        status = "WARN"
    else:
        status = "PASS"
    payload = [row.to_dict() for row in rows]
    return {
        "status": status,
        "blocking": any(row.status in _BLOCKING for row in rows),
        "assertion_count": len(rows),
        "assertions": payload,
        "logical_hash": canonical_sha256(payload, role="QA_ASSERTION_SET"),
    }
