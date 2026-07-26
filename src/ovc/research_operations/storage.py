from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from .canonical import canonical_json_bytes, canonical_sha256
from .lifecycle import freeze_record, supersede_record, verify_frozen_record


class AppendOnlyViolationError(FileExistsError):
    pass


RECORD_DIRECTORIES = {
    "DATA_RELEASE_REF": "releases",
    "RESEARCH_SESSION": "sessions",
    "OBSERVATION_SNAPSHOT": "observations",
    "CLAIM_RECORD": "claims",
    "REALIZATION_SNAPSHOT": "realizations",
    "EVIDENCE_ITEM": "evidence",
    "CASE_BUNDLE": "cases",
    "INCIDENT_RECORD": "incidents",
    "DECISION_RECORD": "decisions",
    "AUDIT_EVENT": "audit",
}


def _safe_name(identifier: str) -> str:
    return identifier.replace(":", "__").replace("/", "_") + ".json"


def _exclusive_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise AppendOnlyViolationError(f"append-only target already exists: {path}") from exc
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_replace(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


class DraftStore:
    """Mutable, derived draft state under var/. Drafts never gain authority."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def create(self, record: dict[str, Any]) -> str:
        draft_id = f"draft:{str(record['record_type']).lower()}:{canonical_sha256(record)}"
        path = self.root / _safe_name(draft_id)
        wrapper = {"draft_id": draft_id, "record": deepcopy(record)}
        _exclusive_write(path, canonical_json_bytes(wrapper))
        return draft_id

    def read(self, draft_id: str) -> dict[str, Any]:
        path = self.root / _safe_name(draft_id)
        return json.loads(path.read_text(encoding="utf-8"))["record"]

    def replace(self, draft_id: str, record: dict[str, Any]) -> None:
        path = self.root / _safe_name(draft_id)
        if not path.exists():
            raise FileNotFoundError(path)
        wrapper = {"draft_id": draft_id, "record": deepcopy(record)}
        _atomic_replace(path, canonical_json_bytes(wrapper))

    def iter_drafts(self) -> Iterable[tuple[str, dict[str, Any]]]:
        if not self.root.exists():
            return []
        result: list[tuple[str, dict[str, Any]]] = []
        for path in sorted(self.root.glob("*.json")):
            wrapper = json.loads(path.read_text(encoding="utf-8"))
            result.append((wrapper["draft_id"], wrapper["record"]))
        return result


class FrozenRecordStore:
    """Append-only store for canonical frozen records."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _path(self, record_type: str, record_id: str) -> Path:
        try:
            directory = RECORD_DIRECTORIES[record_type]
        except KeyError as exc:
            raise ValueError(f"unknown record type: {record_type}") from exc
        return self.root / directory / _safe_name(record_id)

    def write(self, record: dict[str, Any]) -> Path:
        verify_frozen_record(record)
        path = self._path(str(record["record_type"]), str(record["record_id"]))
        _exclusive_write(path, canonical_json_bytes(record))
        return path

    def read(self, record_id: str) -> dict[str, Any]:
        for directory in RECORD_DIRECTORIES.values():
            path = self.root / directory / _safe_name(record_id)
            if path.exists():
                record = json.loads(path.read_text(encoding="utf-8"))
                verify_frozen_record(record)
                return record
        raise FileNotFoundError(record_id)

    def iter_records(self, record_type: str | None = None) -> list[dict[str, Any]]:
        directories = [RECORD_DIRECTORIES[record_type]] if record_type else sorted(set(RECORD_DIRECTORIES.values()))
        records: list[dict[str, Any]] = []
        for directory in directories:
            path = self.root / directory
            if not path.exists():
                continue
            for item in sorted(path.glob("*.json")):
                record = json.loads(item.read_text(encoding="utf-8"))
                verify_frozen_record(record)
                records.append(record)
        return sorted(records, key=lambda record: record["record_id"])


class ResearchWriteService:
    """Governed write boundary. Every public mutation emits a frozen AuditEvent."""

    def __init__(self, *, drafts: DraftStore, records: FrozenRecordStore, operator_id: str):
        self.drafts = drafts
        self.records = records
        self.operator_id = operator_id

    @staticmethod
    def base_record(
        *,
        record_type: str,
        created_at: str,
        cutoff: str,
        operator_id: str,
        source_release_refs: list[dict[str, Any]],
        payload: dict[str, Any],
        artifact_refs: list[dict[str, Any]] | None = None,
        model_refs: list[dict[str, Any]] | None = None,
        missingness: list[dict[str, Any]] | None = None,
        lineage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "record_type": record_type,
            "schema_version": "0.1",
            "lifecycle_state": "DRAFT",
            "created_at": created_at,
            "frozen_at": None,
            "operator_id": operator_id,
            "admissible_cutoff": cutoff,
            "source_release_refs": deepcopy(source_release_refs),
            "artifact_refs": deepcopy(artifact_refs or []),
            "model_refs": deepcopy(model_refs or []),
            "missingness": deepcopy(missingness or []),
            "lineage": deepcopy(lineage or {"parent": [], "derived_from": [], "supersedes": None, "adjudicates": []}),
            "authority_state": "DRAFT",
            "reproducibility_state": "REPRODUCIBLE",
            "payload": deepcopy(payload),
            "content_sha256": None,
        }

    @staticmethod
    def release_ref(release_id: str, cutoff: str) -> dict[str, Any]:
        ref: dict[str, Any] = {"release_id": release_id, "first_valid_time": cutoff}
        if release_id == "OPT-A.GBPUSD.VALIDATION.2025.v2":
            ref.update({"validation_access_state": "LOCKED_UNCONSUMED", "payload_access": "DENIED"})
        return ref

    def _audit(self, *, action: str, object_id: str, result: str, trace_ref: str, at: str, source_refs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        draft = self.base_record(
            record_type="AUDIT_EVENT",
            created_at=at,
            cutoff=at,
            operator_id=self.operator_id,
            source_release_refs=source_refs or [],
            payload={"actor": self.operator_id, "action": action, "object_id": object_id, "result": result, "trace_ref": trace_ref},
            lineage={"parent": [], "derived_from": [object_id], "supersedes": None, "adjudicates": []},
        )
        frozen = freeze_record(draft, frozen_at=at)
        self.records.write(frozen)
        return frozen

    def emit_audit(self, *, action: str, object_id: str, result: str, trace_ref: str, at: str, source_refs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return self._audit(action=action, object_id=object_id, result=result, trace_ref=trace_ref, at=at, source_refs=source_refs)

    def create_draft(self, record: dict[str, Any], *, at: str, action: str) -> str:
        draft_id = self.drafts.create(record)
        self._audit(action=action, object_id=draft_id, result="PASS", trace_ref=f"draft:{draft_id}", at=at, source_refs=record.get("source_release_refs", []))
        return draft_id

    def update_draft(self, draft_id: str, record: dict[str, Any], *, at: str, action: str) -> None:
        self.drafts.replace(draft_id, record)
        self._audit(action=action, object_id=draft_id, result="PASS", trace_ref=f"draft:{draft_id}", at=at, source_refs=record.get("source_release_refs", []))

    def freeze_draft(self, draft_id: str, *, frozen_at: str, action: str) -> dict[str, Any]:
        draft = self.drafts.read(draft_id)
        frozen = freeze_record(draft, frozen_at=frozen_at)
        path = self.records.write(frozen)
        self._audit(action=action, object_id=frozen["record_id"], result="PASS", trace_ref=path.relative_to(self.records.root).as_posix(), at=frozen_at, source_refs=frozen.get("source_release_refs", []))
        return frozen

    def freeze_new(self, draft: dict[str, Any], *, frozen_at: str, action: str) -> dict[str, Any]:
        frozen = freeze_record(draft, frozen_at=frozen_at)
        path = self.records.write(frozen)
        self._audit(action=action, object_id=frozen["record_id"], result="PASS", trace_ref=path.relative_to(self.records.root).as_posix(), at=frozen_at, source_refs=frozen.get("source_release_refs", []))
        return frozen

    def supersede(self, original_id: str, replacement: dict[str, Any], *, frozen_at: str) -> dict[str, Any]:
        original = self.records.read(original_id)
        predecessor, successor = supersede_record(original, replacement, frozen_at=frozen_at)
        if predecessor != original:
            raise RuntimeError("predecessor bytes changed during supersession")
        path = self.records.write(successor)
        self._audit(action="research.supersede", object_id=successor["record_id"], result="PASS", trace_ref=path.relative_to(self.records.root).as_posix(), at=frozen_at, source_refs=successor.get("source_release_refs", []))
        return successor
