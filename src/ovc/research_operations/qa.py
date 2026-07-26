from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterable

from .canonical import canonical_sha256


QA_STATUSES = {"PASS", "WARN", "BLOCK", "QUARANTINE", "NOT_EVALUATED"}


@dataclass(frozen=True)
class QAAssertion:
    check_id: str
    target_id: str
    status: str
    severity: str
    detail: str
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_refs"] = list(self.evidence_refs)
        return value


@dataclass(frozen=True)
class QARun:
    schema: str
    target_id: str
    source_commit: str
    assertions: tuple[QAAssertion, ...]
    disposition: str
    logical_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "target_id": self.target_id,
            "source_commit": self.source_commit,
            "assertions": [item.to_dict() for item in self.assertions],
            "disposition": self.disposition,
            "logical_sha256": self.logical_sha256,
        }


Check = Callable[[dict[str, Any]], QAAssertion]


class QARunner:
    """Run registered checks without mutating their target or source artifacts."""

    def __init__(self, checks: Iterable[Check]):
        self.checks = tuple(checks)

    def run(self, target: dict[str, Any], *, target_id: str, source_commit: str) -> QARun:
        before = canonical_sha256(target)
        assertions = tuple(sorted((check(target) for check in self.checks), key=lambda item: item.check_id))
        after = canonical_sha256(target)
        if before != after:
            raise RuntimeError("QA checks mutated their target")
        for assertion in assertions:
            if assertion.status not in QA_STATUSES:
                raise ValueError(f"invalid QA status: {assertion.status}")
        statuses = {item.status for item in assertions}
        disposition = "BLOCK" if "BLOCK" in statuses else "QUARANTINE" if "QUARANTINE" in statuses else "WARN" if "WARN" in statuses else "PASS"
        logical = {
            "target_id": target_id,
            "source_commit": source_commit,
            "assertions": [item.to_dict() for item in assertions],
            "disposition": disposition,
        }
        return QARun(
            schema="ovc-research-operations-qa-run/v0.1",
            target_id=target_id,
            source_commit=source_commit,
            assertions=assertions,
            disposition=disposition,
            logical_sha256=canonical_sha256(logical),
        )


def required_fields_check(check_id: str, fields: Iterable[str], *, severity: str = "BLOCK") -> Check:
    required = tuple(fields)

    def check(target: dict[str, Any]) -> QAAssertion:
        missing = tuple(field for field in required if target.get(field) in (None, "", []))
        return QAAssertion(
            check_id=check_id,
            target_id=str(target.get("record_id") or target.get("artifact_id") or "UNRESOLVED"),
            status="PASS" if not missing else "BLOCK",
            severity=severity,
            detail="all required fields present" if not missing else f"missing: {','.join(missing)}",
        )

    return check
