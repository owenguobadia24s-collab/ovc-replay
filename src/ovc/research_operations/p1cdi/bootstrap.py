from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import re
from typing import Any

from ovc.research_operations.canonical import canonical_sha256


_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DMRP_CLASSES = frozenset(
    {"DMRP_CONFORMANT", "LEGACY_PRE_DMRP_DISCOVERY", "NOT_APPLICABLE", "UNRESOLVED"}
)
_CURRENTNESS = frozenset({"CURRENT", "HISTORICAL", "STALE", "UNRESOLVED", "CONFLICT"})
_TERMINAL_DISPOSITIONS = frozenset(
    {
        "MIGRATED",
        "EXACT_DUPLICATE",
        "NOT_APPLICABLE",
        "SOURCE_UNAVAILABLE",
        "VISIBILITY_BLOCKED",
        "SOURCE_INVALID",
        "QUARANTINED",
    }
)
_SUBJECT_FIELDS = frozenset(
    {
        "subject_id",
        "owner",
        "source_locator",
        "source_sha256",
        "source_generation",
        "dmrp_conformance_class",
        "visibility_state",
        "currentness_state",
        "migration_disposition",
    }
)
_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p1cdi/bootstrap_source_registry.json"
)


class BootstrapCensusError(ValueError):
    """Raised when exact WP3 census or reconciliation invariants fail."""


def _load_registry() -> tuple[dict[str, str], tuple[str, ...], str, str, str]:
    registry = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    if registry.get("schema") != "p1cdi-bootstrap-source-registry/v0.1":
        raise RuntimeError("P1CDI bootstrap source registry schema mismatch")
    if registry.get("status") != "CLOSED" or registry.get("authority_effect") != "NONE":
        raise RuntimeError("P1CDI bootstrap source registry must be closed and non-authorising")
    if registry.get("silent_omission") != "FORBIDDEN":
        raise RuntimeError("P1CDI bootstrap census must forbid silent omission")
    if registry.get("summary_reconstruction") != "FORBIDDEN":
        raise RuntimeError("P1CDI bootstrap census must forbid summary reconstruction")

    roots = registry.get("source_roots")
    families = registry.get("source_families")
    if not isinstance(roots, list) or not roots or not isinstance(families, list) or not families:
        raise RuntimeError("P1CDI bootstrap source registry is incomplete")
    source_roots: list[str] = []
    for root in roots:
        if not isinstance(root, Mapping) or set(root) != {"path", "role", "recursive"}:
            raise RuntimeError("invalid P1CDI bootstrap source root")
        if type(root["path"]) is not str or not root["path"] or root["recursive"] is not True:
            raise RuntimeError("P1CDI bootstrap source roots must be explicit recursive paths")
        source_roots.append(root["path"])

    owners: dict[str, str] = {}
    for family in families:
        if not isinstance(family, Mapping) or set(family) != {
            "family",
            "owner",
            "object_types",
            "migration_rule",
        }:
            raise RuntimeError("invalid P1CDI bootstrap source family")
        object_types = family["object_types"]
        owner = family["owner"]
        if type(owner) is not str or not owner or not isinstance(object_types, list) or not object_types:
            raise RuntimeError("P1CDI bootstrap source family is incomplete")
        for object_type in object_types:
            if type(object_type) is not str or not object_type or object_type in owners:
                raise RuntimeError(f"duplicate or invalid bootstrap object type: {object_type!r}")
            owners[object_type] = owner
    return (
        owners,
        tuple(sorted(source_roots)),
        registry["missing_visibility"],
        registry["missing_currentness"],
        registry["missing_dmrp_conformance"],
    )


(
    _OBJECT_OWNERS,
    BOOTSTRAP_SOURCE_ROOTS,
    _MISSING_VISIBILITY,
    _MISSING_CURRENTNESS,
    _MISSING_DMRP,
) = _load_registry()
BOOTSTRAP_OBJECT_TYPES = tuple(sorted(_OBJECT_OWNERS))


def _require_string(value: object, field: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if type(value) is not str or not value:
        raise BootstrapCensusError(f"{field} must be a non-empty string")
    return value


def _json_pointer_part(value: object) -> str:
    return str(value).replace("~", "~0").replace("/", "~1")


def _walk_json(value: object, pointer: str = "") -> list[tuple[str, Mapping[str, Any]]]:
    found: list[tuple[str, Mapping[str, Any]]] = []
    if isinstance(value, Mapping):
        markers = [value.get(name) for name in ("record_type", "object_type")]
        recognized = [marker for marker in markers if type(marker) is str and marker in _OBJECT_OWNERS]
        if recognized:
            if len(set(recognized)) != 1:
                raise BootstrapCensusError(f"conflicting source object types at {pointer or '/'}")
            found.append((pointer or "/", value))
        for key in sorted(value, key=str):
            found.extend(_walk_json(value[key], f"{pointer}/{_json_pointer_part(key)}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_walk_json(item, f"{pointer}/{index}"))
    return found


def _source_object_type(source: Mapping[str, Any]) -> str:
    markers = [source.get(name) for name in ("record_type", "object_type")]
    recognized = [marker for marker in markers if type(marker) is str and marker in _OBJECT_OWNERS]
    if len(set(recognized)) != 1:
        raise BootstrapCensusError("source object must have one exact registered type")
    return recognized[0]


def _source_generation(source: Mapping[str, Any]) -> str | None:
    values = [
        source[name]
        for name in ("source_generation", "generation_id", "cycle_generation_id")
        if name in source and type(source[name]) is str and source[name]
    ]
    unique = sorted(set(values))
    return unique[0] if len(unique) == 1 else None


def _closed_or_default(value: object, allowed: frozenset[str], default: str) -> str:
    return value if type(value) is str and value in allowed else default


def _subject_from_source(*, locator: str, source: Mapping[str, Any]) -> dict[str, Any]:
    object_type = _source_object_type(source)
    source_sha256 = canonical_sha256(source)
    subject_key = {"source_locator": locator, "source_sha256": source_sha256}
    return {
        "subject_id": f"p1cdi:bootstrap-source:{canonical_sha256(subject_key)}",
        "owner": _OBJECT_OWNERS[object_type],
        "source_locator": locator,
        "source_sha256": source_sha256,
        "source_generation": _source_generation(source),
        "dmrp_conformance_class": _closed_or_default(
            source.get("dmrp_conformance_class"), _DMRP_CLASSES, _MISSING_DMRP
        ),
        "visibility_state": _closed_or_default(
            source.get("visibility_state"),
            frozenset({"PATH1_FULL", "PATH1_SAFE", "CROSS_MODE_POST_FREEZE", "OPERATOR_RESTRICTED", "PROTECTED"}),
            _MISSING_VISIBILITY,
        ),
        "currentness_state": _closed_or_default(
            source.get("currentness_state"), _CURRENTNESS, _MISSING_CURRENTNESS
        ),
        "migration_disposition": "PENDING",
    }


def scan_repository_source_subjects(repository_root: Path) -> list[dict[str, Any]]:
    """Scan only exact closed owner-record roots; fixtures/types are never source records."""

    repository_root = repository_root.resolve()
    subjects: list[dict[str, Any]] = []
    for relative_root in BOOTSTRAP_SOURCE_ROOTS:
        source_root = (repository_root / relative_root).resolve()
        try:
            source_root.relative_to(repository_root)
        except ValueError as exc:
            raise BootstrapCensusError("bootstrap source root escapes repository") from exc
        if not source_root.is_dir():
            raise BootstrapCensusError(f"required bootstrap source root is unavailable: {relative_root}")
        for path in sorted(source_root.rglob("*.json")):
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise BootstrapCensusError(f"unreadable bootstrap owner record: {path}") from exc
            relative = path.relative_to(repository_root).as_posix()
            for pointer, source in _walk_json(document):
                subjects.append(
                    _subject_from_source(locator=f"{relative}#{pointer}", source=source)
                )
    subjects.sort(key=lambda item: (item["source_locator"], item["source_sha256"]))
    subject_ids = [item["subject_id"] for item in subjects]
    locators = [item["source_locator"] for item in subjects]
    if len(subject_ids) != len(set(subject_ids)) or len(locators) != len(set(locators)):
        raise BootstrapCensusError("bootstrap source subjects are not uniquely addressable")
    return subjects


def freeze_source_census(
    *, census_id: str, as_of_commit: str, subjects: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    _require_string(census_id, "census_id")
    if type(as_of_commit) is not str or not _COMMIT.fullmatch(as_of_commit):
        raise BootstrapCensusError("as_of_commit must be a lowercase Git commit")
    normalized = [_normalize_subject(subject, disposition="PENDING") for subject in subjects]
    normalized.sort(key=lambda item: (item["source_locator"], item["source_sha256"]))
    _assert_unique_subjects(normalized)
    return {
        "record_type": "P1CDIBootstrapSourceCensusManifest",
        "schema_version": "0.1",
        "census_id": census_id,
        "as_of_commit": as_of_commit,
        "subjects": normalized,
        "expected_subject_count": len(normalized),
        "silent_omission": "FORBIDDEN",
        "reconstruction_from_summary": "FORBIDDEN",
        "authority_effect": "NONE",
    }


def reconcile_source_census(
    *, manifest_id: str, census: Mapping[str, Any], subjects: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    _require_string(manifest_id, "manifest_id")
    if census.get("record_type") != "P1CDIBootstrapSourceCensusManifest":
        raise BootstrapCensusError("a frozen P1CDI source census is required")
    census_subjects_raw = census.get("subjects")
    if not isinstance(census_subjects_raw, list):
        raise BootstrapCensusError("census subjects must be an array")
    census_subjects = [_normalize_subject(item, disposition="PENDING") for item in census_subjects_raw]
    if census.get("expected_subject_count") != len(census_subjects):
        raise BootstrapCensusError("census expected count does not bind subjects")
    _assert_unique_subjects(census_subjects)

    reconciled = [_normalize_subject(item) for item in subjects]
    reconciled.sort(key=lambda item: (item["source_locator"], item["source_sha256"]))
    _assert_unique_subjects(reconciled)
    census_by_id = {item["subject_id"]: item for item in census_subjects}
    reconciled_by_id = {item["subject_id"]: item for item in reconciled}
    if set(census_by_id) != set(reconciled_by_id):
        raise BootstrapCensusError("every and only frozen census subject must reconcile")
    for subject_id, frozen in census_by_id.items():
        result = reconciled_by_id[subject_id]
        for field in sorted(_SUBJECT_FIELDS - {"migration_disposition"}):
            if result[field] != frozen[field]:
                raise BootstrapCensusError(
                    f"reconciliation mutated frozen source field {field}: {subject_id}"
                )
        if result["migration_disposition"] not in _TERMINAL_DISPOSITIONS:
            raise BootstrapCensusError(f"subject is not terminally reconciled: {subject_id}")
    census_ref = _require_string(census.get("census_id"), "census_id")
    return {
        "record_type": "BootstrapSourceCompletenessManifest",
        "schema_version": "0.1",
        "manifest_id": manifest_id,
        "census_ref": census_ref,
        "subjects": reconciled,
        "expected_subject_count": len(census_subjects),
        "reconciled_subject_count": len(reconciled),
        "complete": True,
        "authority_effect": "NONE",
    }


def build_historical_membership_events(
    *,
    completeness: Mapping[str, Any],
    generation_by_subject: Mapping[str, str],
    effective_time: str,
) -> list[dict[str, Any]]:
    """Create historical-only lifecycle events; WP3 never auto-activates or publishes current."""

    if completeness.get("record_type") != "BootstrapSourceCompletenessManifest":
        raise BootstrapCensusError("a bootstrap completeness manifest is required")
    if completeness.get("complete") is not True:
        raise BootstrapCensusError("incomplete bootstrap cannot create membership")
    _require_string(effective_time, "effective_time")
    subjects = completeness.get("subjects")
    if not isinstance(subjects, list):
        raise BootstrapCensusError("completeness subjects must be an array")
    migrated = [item for item in subjects if item.get("migration_disposition") == "MIGRATED"]
    migrated_ids = {item["subject_id"] for item in migrated}
    if set(generation_by_subject) != migrated_ids:
        raise BootstrapCensusError("historical generation bindings must exactly cover migrated subjects")
    events: list[dict[str, Any]] = []
    for subject in sorted(migrated, key=lambda item: item["subject_id"]):
        subject_id = subject["subject_id"]
        generation_id = _require_string(generation_by_subject[subject_id], "generation_id")
        event_key = {"subject_id": subject_id, "generation_id": generation_id}
        events.append(
            {
                "record_type": "P1DistinctionLifecycleEvent",
                "schema_version": "0.1",
                "event_id": f"p1cdi:bootstrap-historical:{canonical_sha256(event_key)}",
                "generation_id": generation_id,
                "activity_state": "HISTORICAL",
                "effective_time": effective_time,
                "source_scientific_disposition_ref": None,
                "authority_effect": "NONE",
            }
        )
    return events


def _normalize_subject(
    subject: Mapping[str, Any], *, disposition: str | None = None
) -> dict[str, Any]:
    if not isinstance(subject, Mapping) or set(subject) != _SUBJECT_FIELDS:
        raise BootstrapCensusError("bootstrap subject must use the exact closed field set")
    normalized = dict(subject)
    for field in ("subject_id", "owner", "visibility_state", "currentness_state", "migration_disposition"):
        _require_string(normalized[field], field)
    _require_string(normalized["source_locator"], "source_locator", nullable=True)
    source_sha256 = normalized["source_sha256"]
    if source_sha256 is not None and (type(source_sha256) is not str or not _SHA256.fullmatch(source_sha256)):
        raise BootstrapCensusError("source_sha256 must be null or lowercase SHA-256")
    _require_string(normalized["source_generation"], "source_generation", nullable=True)
    if normalized["dmrp_conformance_class"] not in _DMRP_CLASSES:
        raise BootstrapCensusError("invalid DMRP conformance class")
    if normalized["currentness_state"] not in _CURRENTNESS:
        raise BootstrapCensusError("invalid source currentness state")
    if disposition is not None and normalized["migration_disposition"] != disposition:
        raise BootstrapCensusError(f"migration_disposition must be {disposition}")
    return normalized


def _assert_unique_subjects(subjects: Sequence[Mapping[str, Any]]) -> None:
    ids = [item["subject_id"] for item in subjects]
    locators = [item["source_locator"] for item in subjects]
    if len(ids) != len(set(ids)) or len(locators) != len(set(locators)):
        raise BootstrapCensusError("bootstrap subject IDs and locators must be unique")
