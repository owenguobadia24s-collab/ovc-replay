from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class MigrationError(ValueError):
    """Raised when a source-faithful programme migration cannot be reproduced."""


_NATIVE_GENESIS_FIELDS = (
    "programme_class",
    "constitutional_parent",
    "programme_parents",
    "purpose",
    "scope",
    "creation_triggers",
    "scope_audit_ref",
    "authority_envelope_ref",
    "governing_sources",
    "provenance",
)

_STATE_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "status": ("programme_status", "status"),
    "current_packet": ("current_packet",),
    "current_gate": ("current_gate",),
    "operator_decision_required": ("operator_decision_required",),
    "operator_decision_id": ("operator_decision_id",),
    "baseline_commit": ("baseline_commit", "plan_baseline_commit"),
    "branch": ("branch",),
    "candidate_commit": ("candidate_commit", "tested_candidate_commit", "final_head_commit"),
    "merge_commit": ("merge_commit", "terminal_merge_commit"),
    "authority": ("authority",),
    "blockers": ("blockers",),
    "next_action": ("next_action", "exact_work_after_decision"),
}

_TERMINAL_STATUSES = {"COMPLETED", "SUPERSEDED", "HISTORICAL", "RETIRED", "QUARANTINED"}
_STATE_FILENAME_RE = re.compile(r"(?:PROGRAMME|PROGRAM)[_-]?STATE", re.IGNORECASE)
_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9._-]+")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def logical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise MigrationError(f"source path escapes repository root: {path}") from exc


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MigrationError(f"cannot load JSON source {path}") from exc
    if not isinstance(value, dict):
        raise MigrationError(f"programme source must be a JSON object: {path}")
    return value


def discover_programme_state_paths(
    root: Path | str,
    *,
    include_roots: Sequence[str] = ("registries",),
    exclude_paths: Iterable[str] = (),
) -> list[Path]:
    repository_root = Path(root)
    excluded = {Path(item).as_posix() for item in exclude_paths}
    discovered: list[Path] = []
    for include_root in include_roots:
        base = repository_root / include_root
        if not base.exists():
            continue
        for path in base.rglob("*.json"):
            relative = _relative_path(repository_root, path)
            if relative in excluded or not _STATE_FILENAME_RE.search(path.name):
                continue
            try:
                document = _load_json_object(path)
            except MigrationError:
                continue
            if isinstance(document.get("programme_id"), str) and document["programme_id"]:
                discovered.append(path)
    return sorted(discovered, key=lambda path: _relative_path(repository_root, path))


def _first_present(document: Mapping[str, Any], aliases: Sequence[str]) -> tuple[str | None, Any]:
    for alias in aliases:
        if alias in document:
            return alias, deepcopy(document[alias])
    return None, None


def _migration_deadline(status: Any) -> str:
    status_value = str(status or "UNKNOWN").upper()
    if status_value in _TERMINAL_STATUSES:
        return "BEFORE_REACTIVATION_OR_SUPERSESSION"
    return "BEFORE_NEXT_AUTHORITY_CHANGING_GATE_OR_PROGRAMME_BOUNDARY"


def build_migration_record(root: Path | str, path: Path | str) -> dict[str, Any]:
    repository_root = Path(root)
    source_path = Path(path)
    if not source_path.is_absolute():
        source_path = repository_root / source_path
    if not source_path.is_file():
        raise MigrationError(f"migration source does not exist: {source_path}")

    document = _load_json_object(source_path)
    programme_id = document.get("programme_id")
    if not isinstance(programme_id, str) or not programme_id:
        raise MigrationError(f"migration source has no programme_id: {source_path}")

    relative = _relative_path(repository_root, source_path)
    source_hash = file_sha256(source_path)
    preserved_values: dict[str, Any] = {
        "programme_id": programme_id,
        "plan_id": deepcopy(document.get("plan_id")),
        "plan_version": deepcopy(document.get("plan_version")),
        "source_schema": deepcopy(document.get("schema")),
    }
    source_field_map: dict[str, str] = {}
    for target, aliases in _STATE_FIELD_ALIASES.items():
        source_field, value = _first_present(document, aliases)
        if source_field is not None:
            preserved_values[target] = value
            source_field_map[target] = source_field

    present_fields = sorted(key for key, value in preserved_values.items() if value is not None)
    missing_descriptive_fields = sorted(
        field
        for field in ("plan_id", "plan_version", "status", "authority", "blockers", "next_action")
        if preserved_values.get(field) is None
    )
    unresolved_native_fields = sorted(field for field in _NATIVE_GENESIS_FIELDS if field not in document)

    confidence = "HIGH"
    if missing_descriptive_fields:
        confidence = "MEDIUM"
    if preserved_values.get("status") is None or preserved_values.get("authority") is None:
        confidence = "LOW"

    safe_programme_id = _SAFE_ID_RE.sub("_", programme_id)
    migration_id = f"PGMIG.{safe_programme_id}.{source_hash[:16]}"
    return {
        "record_type": "MIGRATION_RECORD",
        "schema_version": "0.1",
        "migration_id": migration_id,
        "programme_id": programme_id,
        "source": {
            "path": relative,
            "sha256": source_hash,
            "format": "JSON",
            "schema": deepcopy(document.get("schema")),
            "precedence": 3,
            "authority_role": "AUTHORITATIVE_PROGRAMME_STATE",
        },
        "import_status": "PROVISIONAL_NON_CANONICAL",
        "authority_effect": "NONE",
        "confidence": confidence,
        "source_coverage": {
            "present_fields": present_fields,
            "missing_descriptive_fields": missing_descriptive_fields,
            "source_field_map": source_field_map,
        },
        "preserved_values": preserved_values,
        "inferred_fields": [],
        "unresolved_fields": unresolved_native_fields,
        "conflicting_fields": [],
        "native_governance_deadline": _migration_deadline(preserved_values.get("status")),
        "migration_uncertainty": {
            "required": True,
            "banner": "MIGRATION_UNCERTAINTY",
            "reason": "NON_NATIVE_GENESIS_IMPORT",
            "removal_condition": "ACCEPTED_NATIVE_GENESIS_AT_A_LATER_AUTHORITY_CHANGING_GATE",
        },
        "rollback": "Discard this derived record and rebuild it from the preserved source path and SHA-256; never rewrite the source programme state.",
    }


def build_conflict_ledger(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_programme: dict[str, list[Mapping[str, Any]]] = {}
    for record in records:
        by_programme.setdefault(str(record["programme_id"]), []).append(record)

    findings: list[dict[str, Any]] = []
    for programme_id in sorted(by_programme):
        programme_records = by_programme[programme_id]
        if len(programme_records) > 1:
            fields = ("status", "current_packet", "current_gate", "operator_decision_id", "authority")
            for field in fields:
                values = {
                    canonical_json_bytes(record.get("preserved_values", {}).get(field)).decode("utf-8")
                    for record in programme_records
                }
                if len(values) > 1:
                    findings.append(
                        {
                            "finding_type": "MIGRATION_SOURCE_CONFLICT",
                            "severity": "BLOCK",
                            "programme_id": programme_id,
                            "field": field,
                            "source_paths": sorted(record["source"]["path"] for record in programme_records),
                            "values": sorted(values),
                            "authority_effect": "NONE",
                        }
                    )
        for record in programme_records:
            unresolved = list(record.get("unresolved_fields", ()))
            if unresolved:
                findings.append(
                    {
                        "finding_type": "MIGRATION_UNRESOLVED_FIELDS",
                        "severity": "WARN",
                        "programme_id": programme_id,
                        "source_path": record["source"]["path"],
                        "fields": sorted(unresolved),
                        "authority_effect": "NONE",
                    }
                )
            missing = list(record.get("source_coverage", {}).get("missing_descriptive_fields", ()))
            if missing:
                findings.append(
                    {
                        "finding_type": "MIGRATION_SOURCE_COVERAGE_GAP",
                        "severity": "WARN",
                        "programme_id": programme_id,
                        "source_path": record["source"]["path"],
                        "fields": sorted(missing),
                        "authority_effect": "NONE",
                    }
                )
    return findings


def build_migration_snapshot(
    root: Path | str,
    *,
    include_roots: Sequence[str] = ("registries",),
    exclude_paths: Iterable[str] = (),
    minimum_records: int = 1,
) -> dict[str, Any]:
    repository_root = Path(root)
    paths = discover_programme_state_paths(
        repository_root,
        include_roots=include_roots,
        exclude_paths=exclude_paths,
    )
    records = [build_migration_record(repository_root, path) for path in paths]
    if len(records) < minimum_records:
        raise MigrationError(f"discovered {len(records)} migration records; minimum is {minimum_records}")

    records = sorted(records, key=lambda record: (record["programme_id"], record["source"]["path"]))
    findings = build_conflict_ledger(records)
    blocking = [finding for finding in findings if finding["severity"] == "BLOCK"]
    programme_ids = [record["programme_id"] for record in records]
    snapshot: dict[str, Any] = {
        "schema": "ovc-programme-migration-snapshot/v1",
        "programme_id": "OVC-PG-v0.2",
        "packet_id": "PG-WP4",
        "status": "PASS" if not blocking else "BLOCK",
        "import_status": "PROVISIONAL_NON_CANONICAL",
        "authority_effect": "NONE",
        "migration_uncertainty_required": True,
        "source_roots": list(include_roots),
        "excluded_paths": sorted(Path(item).as_posix() for item in exclude_paths),
        "record_count": len(records),
        "unique_programme_count": len(set(programme_ids)),
        "records": records,
        "conflict_ledger": findings,
        "blocking_conflict_count": len(blocking),
        "canonical_adoption": "DENIED_PENDING_PG_G6",
        "admission_enforcement": "DENIED_PENDING_PG_G6",
        "control_plane_route": "DENIED_PENDING_PG_G6",
        "automatic_upkeep": "DENIED_PENDING_PG_G7",
        "rollback": "Discard and deterministically rebuild this snapshot from programme-owned state; preserve all source bytes and uncertainty findings.",
    }
    snapshot["snapshot_sha256"] = logical_sha256(snapshot)
    return snapshot


def load_migration_source_registry(path: Path | str) -> dict[str, Any]:
    registry = _load_json_object(Path(path))
    if registry.get("schema") != "ovc-programme-migration-source-registry/v1":
        raise MigrationError("unsupported migration source registry schema")
    return registry


def build_snapshot_from_registry(root: Path | str, registry: Mapping[str, Any]) -> dict[str, Any]:
    discovery = registry.get("discovery", {})
    return build_migration_snapshot(
        root,
        include_roots=tuple(discovery.get("include_roots", ("registries",))),
        exclude_paths=tuple(discovery.get("exclude_paths", ())),
        minimum_records=int(discovery.get("minimum_records", 1)),
    )


def write_snapshot(path: Path | str, snapshot: Mapping[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n")
