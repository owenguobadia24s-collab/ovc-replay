from __future__ import annotations

import hashlib
import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

FAMILIES = (
    "ResearchCoverageItem",
    "ResearchRequirementProfile",
    "ResearchCapabilityFrontier",
    "ResearchCoverageAssessment",
    "CapabilityNeedAssessment",
    "RCCRBootstrapManifest",
    "RCCRRefreshTrigger",
)
ID_FIELDS = {
    "ResearchCoverageItem": "coverage_item_generation_id",
    "ResearchRequirementProfile": "requirement_profile_id",
    "ResearchCapabilityFrontier": "capability_frontier_id",
    "ResearchCoverageAssessment": "coverage_assessment_id",
    "CapabilityNeedAssessment": "capability_need_assessment_id",
    "RCCRBootstrapManifest": "bootstrap_id",
    "RCCRRefreshTrigger": "trigger_id",
}
FORBIDDEN_EMBED_KEYS = {
    "raw_payload", "payload_bytes", "binary_payload", "secret", "token", "password",
    "local_path", "absolute_path", "filesystem_path",
}
MAX_CANONICAL_BYTES = 262_144


class RCCRValidationError(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f"{code}: {detail}")


class RCCRAppendOnlyCollision(FileExistsError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _identity_material(family: str, record: dict[str, Any]) -> dict[str, Any]:
    material = deepcopy(record)
    material.pop(ID_FIELDS[family], None)
    return material


def logical_identity(family: str, record: dict[str, Any]) -> str:
    if family not in FAMILIES:
        raise RCCRValidationError("UNKNOWN_FAMILY", family)
    digest = hashlib.sha256(canonical_json_bytes(_identity_material(family, record))).hexdigest()
    return f"rccr:{family}:{digest}"


def _schema_path(family: str) -> Path:
    root = Path(__file__).resolve().parents[4]
    return root / "schemas" / "research_operations" / "rccr" / "v0_1" / f"{family}.schema.json"


def _types_match(value: Any, expected: str | list[str]) -> bool:
    options = [expected] if isinstance(expected, str) else expected
    checks = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "null": lambda v: v is None,
        "boolean": lambda v: isinstance(v, bool),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    }
    return any(checks[t](value) for t in options)


def _validate_schema(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    if "type" in schema and not _types_match(value, schema["type"]):
        raise RCCRValidationError("SCHEMA_TYPE", path)
    if "const" in schema and value != schema["const"]:
        raise RCCRValidationError("SCHEMA_CONST", path)
    if "enum" in schema and value not in schema["enum"]:
        raise RCCRValidationError("UNKNOWN_MANDATORY_ENUM", f"{path}={value}")
    if isinstance(value, str):
        if schema.get("minLength") and len(value) < int(schema["minLength"]):
            raise RCCRValidationError("SCHEMA_MIN_LENGTH", path)
        if schema.get("pattern") and not re.match(schema["pattern"], value):
            raise RCCRValidationError("SCHEMA_PATTERN", path)
    if isinstance(value, dict):
        required = set(schema.get("required", []))
        missing = required - set(value)
        if missing:
            raise RCCRValidationError("SCHEMA_REQUIRED", f"{path}:{','.join(sorted(missing))}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = set(value) - set(props)
            if unknown:
                raise RCCRValidationError("SCHEMA_CLOSED", f"{path}:{','.join(sorted(unknown))}")
        for key, item in value.items():
            if key in props:
                _validate_schema(item, props[key], f"{path}.{key}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            _validate_schema(item, schema["items"], f"{path}[{index}]")


def _check_leakage(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in FORBIDDEN_EMBED_KEYS:
                raise RCCRValidationError("PAYLOAD_OR_PATH_LEAKAGE", f"{path}.{key}")
            _check_leakage(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _check_leakage(item, f"{path}[{index}]")
    elif isinstance(value, str):
        low = value.lower()
        if value.startswith(("/", "\\")) or "\\" in value or re.match(r"^[a-zA-Z]:[/\\]", value):
            raise RCCRValidationError("ABSOLUTE_PATH_LEAKAGE", path)
        if "/../" in f"/{value}/" or low.startswith("../"):
            raise RCCRValidationError("PATH_TRAVERSAL", path)


def validate_canonical_object(family: str, record: dict[str, Any], *, require_identity: bool = True) -> None:
    if family not in FAMILIES:
        raise RCCRValidationError("UNKNOWN_FAMILY", family)
    schema = json.loads(_schema_path(family).read_text(encoding="utf-8"))
    _validate_schema(record, schema)
    if record.get("authority_effect") != "NONE":
        raise RCCRValidationError("AUTHORITY_EFFECT_DENIED", str(record.get("authority_effect")))
    _check_leakage(record)
    if len(canonical_json_bytes(record)) > MAX_CANONICAL_BYTES:
        raise RCCRValidationError("CANONICAL_OBJECT_TOO_LARGE", str(len(canonical_json_bytes(record))))
    if require_identity:
        expected = logical_identity(family, record)
        if record.get(ID_FIELDS[family]) != expected:
            raise RCCRValidationError("IDENTITY_MISMATCH", f"expected {expected}")


class RCCRAppendOnlyStore:
    def __init__(self, root: str | Path, *, audit_callback: Callable[[dict[str, Any]], None] | None = None):
        self.root = Path(root)
        self.audit_callback = audit_callback

    def _record_path(self, family: str, record_id: str) -> Path:
        safe = record_id.replace(":", "__") + ".json"
        return self.root / family / safe

    @staticmethod
    def _exclusive_write(path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError as exc:
            raise RCCRAppendOnlyCollision(f"append-only target exists: {path}") from exc
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.write(b"\n")
            handle.flush()
            os.fsync(handle.fileno())

    def write(self, family: str, record: dict[str, Any]) -> Path:
        validate_canonical_object(family, record)
        record_id = str(record[ID_FIELDS[family]])
        path = self._record_path(family, record_id)
        self._exclusive_write(path, canonical_json_bytes(record))
        event = {"event":"RCCR_CANONICAL_APPEND","family":family,"record_id":record_id,"authority_effect":"NONE"}
        audit_path = self.root / "audit" / (hashlib.sha256(canonical_json_bytes(event)).hexdigest() + ".json")
        self._exclusive_write(audit_path, canonical_json_bytes(event))
        if self.audit_callback:
            self.audit_callback(deepcopy(event))
        return path

    def supersede(self, family: str, predecessor: dict[str, Any], successor: dict[str, Any], *, supersession_field: str) -> Path:
        validate_canonical_object(family, predecessor)
        expected_predecessor = predecessor[ID_FIELDS[family]]
        if successor.get(supersession_field) != expected_predecessor:
            raise RCCRValidationError("SUPERSESSION_LINEAGE_REQUIRED", supersession_field)
        return self.write(family, successor)
