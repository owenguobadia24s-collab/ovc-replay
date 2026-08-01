from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

ROUTE_ID = "RESEARCH.C2_SEQUENCE_EVIDENCE"
ROUTE_STATE = "DISABLED_PENDING_RC_G5"
SCHEMA_ID = "ovc-ro4-console-projection/v1"
SCHEMA_PATH = "schemas/research_operations/v0_4/ro4_console_projection_v0_1.schema.json"
SCHEMA_BLOB_SHA = "83bcf57c0374411dfdf02a61483b529b46f333c7"

REQUIRED_BANNERS = (
    "LOCAL READ ONLY — ROUTE DISABLED PENDING RC-G5.",
    "NO ANNOTATION OR WRITE ACTIONS ARE AVAILABLE.",
    "VALIDATION IS LOCKED_UNCONSUMED.",
    "C2 AND PATTERN DISCOVERY AUTHORITY IS UNCHANGED.",
)

ALLOWED_PANEL_CLASSES = frozenset(
    {
        "C2_STATE",
        "C2_TRANSITION",
        "PERSISTENCE_CONFLICT",
        "RO4_SEQUENCE",
        "BOUNDARY_FRICTION_READ_ONLY",
        "PD_TRIGGER_TRACE_ONLY",
        "SIGNATURE_DIVERSITY",
        "SAMPLE_DISCLOSURE",
    }
)

FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "actions",
        "action",
        "forms",
        "form",
        "buttons",
        "button",
        "write",
        "writes",
        "mutation",
        "mutate",
        "activate",
        "promotion",
        "promote",
        "probability",
        "likelihood",
        "confidence",
        "percentage",
        "percent",
        "ratio",
        "heatmap",
        "score",
        "rank",
        "ranking",
        "candidate_quality",
        "recommended_action",
        "synthetic_control",
        "ablated_control",
        "validation_payload",
        "runtime_path",
        "local_path",
        "remote_key",
        "secret",
        "token",
        "credentials",
    }
)
PD_FORBIDDEN_KEYS = frozenset(
    {
        "candidate_id",
        "candidate_ids",
        "candidate",
        "candidates",
        "cluster_id",
        "cluster_ids",
        "novelty",
        "promotion",
        "review_decision",
        "evidence_bridge_write",
    }
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class RO4ProjectionError(ValueError):
    pass


class RO4ProjectionDenied(RO4ProjectionError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    try:
        digest = hashlib.sha1(usedforsecurity=False)
    except TypeError:  # pragma: no cover
        digest = hashlib.sha1()
    digest.update(header)
    digest.update(content)
    return digest.hexdigest()


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key).strip().lower()
            yield from _walk_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _walk_keys(child)


def _guard_payload(payload: Mapping[str, Any], *, panel_class: str) -> None:
    keys = set(_walk_keys(payload))
    forbidden = sorted(keys.intersection(FORBIDDEN_PAYLOAD_KEYS))
    if forbidden:
        raise RO4ProjectionDenied("RO4_PROJECTION_FORBIDDEN_PAYLOAD_KEYS:" + ",".join(forbidden))
    if panel_class == "PD_TRIGGER_TRACE_ONLY":
        pd_forbidden = sorted(keys.intersection(PD_FORBIDDEN_KEYS))
        if pd_forbidden:
            raise RO4ProjectionDenied("RO4_PD_TRACE_EXCEEDS_IDENTITY_AUTHORITY:" + ",".join(pd_forbidden))
    for key in keys:
        if key.endswith("_write") or key.endswith("_mutation"):
            raise RO4ProjectionDenied(f"RO4_PROJECTION_WRITE_CAPABILITY_DENIED:{key}")


def verify_projection_schema_binding(schema_root: str | Path | None = None) -> dict[str, str]:
    root = Path(schema_root) if schema_root is not None else Path(__file__).resolve().parents[4]
    path = root / SCHEMA_PATH
    try:
        raw = path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RO4ProjectionError("RO4_CONSOLE_SCHEMA_UNAVAILABLE") from exc
    if _git_blob_sha(raw) != SCHEMA_BLOB_SHA:
        raise RO4ProjectionError("RO4_CONSOLE_SCHEMA_BLOB_MISMATCH")
    if parsed.get("$id") != SCHEMA_ID:
        raise RO4ProjectionError("RO4_CONSOLE_SCHEMA_ID_MISMATCH")
    if parsed.get("properties", {}).get("route_state", {}).get("const") != ROUTE_STATE:
        raise RO4ProjectionError("RO4_CONSOLE_SCHEMA_ROUTE_STATE_MISMATCH")
    return {"schema_id": SCHEMA_ID, "path": SCHEMA_PATH, "git_blob_sha": SCHEMA_BLOB_SHA}


def count_cell(
    *,
    count: int,
    eligible_denominator: int,
    slice_identity: str,
    excluded_count: int = 0,
    missing_count: int = 0,
) -> dict[str, Any]:
    values = (count, eligible_denominator, excluded_count, missing_count)
    if any(not isinstance(value, int) or value < 0 for value in values):
        raise RO4ProjectionError("RO4_COUNT_CELL_NON_NEGATIVE_INTEGERS_REQUIRED")
    if count > eligible_denominator:
        raise RO4ProjectionError("RO4_COUNT_EXCEEDS_ELIGIBLE_DENOMINATOR")
    if not slice_identity:
        raise RO4ProjectionError("RO4_COUNT_CELL_SLICE_IDENTITY_REQUIRED")
    return {
        "count": count,
        "eligible_denominator": eligible_denominator,
        "excluded_count": excluded_count,
        "missing_count": missing_count,
        "slice_identity": slice_identity,
        "display_text": f"{count} of {eligible_denominator} eligible records",
        "display_style": "COUNT_WITH_VISIBLE_DENOMINATOR",
    }


def _validate_release_refs(source_release_refs: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not source_release_refs:
        raise RO4ProjectionError("RO4_PROJECTION_SOURCE_RELEASE_REQUIRED")
    validated: list[dict[str, Any]] = []
    for ref in source_release_refs:
        required = {
            "release_id",
            "manifest_id",
            "manifest_sha256",
            "role",
            "authority_state",
            "parent_c1_release_id",
            "availability",
        }
        missing = sorted(required - set(ref))
        if missing:
            raise RO4ProjectionError("RO4_RELEASE_REF_MISSING:" + ",".join(missing))
        role = str(ref["role"]).upper()
        if role == "VALIDATION" or "VALIDATION" in str(ref["release_id"]).upper():
            raise RO4ProjectionDenied("RO4_VALIDATION_DENIED_BEFORE_PANEL_RESOLUTION")
        if role not in {"DISCOVERY", "DEVELOPMENT"}:
            raise RO4ProjectionDenied(f"RO4_RELEASE_ROLE_DENIED:{role}")
        if not SHA256_RE.fullmatch(str(ref["manifest_sha256"])):
            raise RO4ProjectionError("RO4_RELEASE_MANIFEST_HASH_INVALID")
        if ref.get("validation_consumption", "LOCKED_UNCONSUMED") != "LOCKED_UNCONSUMED":
            raise RO4ProjectionDenied("RO4_VALIDATION_CONSUMPTION_NOT_LOCKED")
        prohibited = {"payload", "runtime_path", "validation_path"}.intersection(ref)
        if prohibited:
            raise RO4ProjectionDenied("RO4_RELEASE_PAYLOAD_LOCATION_DENIED:" + ",".join(sorted(prohibited)))
        validated.append(dict(ref))
    return validated


def _validate_panels(panels: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not panels:
        raise RO4ProjectionError("RO4_PROJECTION_PANEL_REQUIRED")
    validated: list[dict[str, Any]] = []
    ids: set[str] = set()
    sampled = False
    disclosure = False
    for panel in panels:
        if set(panel) != {"panel_id", "panel_class", "payload"}:
            raise RO4ProjectionError("RO4_PANEL_FIELDS_MUST_BE_EXACT")
        panel_id = str(panel["panel_id"])
        panel_class = str(panel["panel_class"])
        payload = panel["payload"]
        if not panel_id or panel_id in ids:
            raise RO4ProjectionError("RO4_PANEL_ID_MISSING_OR_DUPLICATE")
        ids.add(panel_id)
        if panel_class not in ALLOWED_PANEL_CLASSES:
            raise RO4ProjectionDenied(f"RO4_PANEL_CLASS_DENIED:{panel_class}")
        if not isinstance(payload, Mapping):
            raise RO4ProjectionError("RO4_PANEL_PAYLOAD_OBJECT_REQUIRED")
        _guard_payload(payload, panel_class=panel_class)
        if payload.get("sampled") is True:
            sampled = True
        if panel_class == "SAMPLE_DISCLOSURE":
            disclosure = True
            required = {"sample_manifest_sha256", "sample_count", "population_count", "method", "deterministic", "banner"}
            missing = sorted(required - set(payload))
            if missing:
                raise RO4ProjectionError("RO4_SAMPLE_DISCLOSURE_MISSING:" + ",".join(missing))
            if not SHA256_RE.fullmatch(str(payload["sample_manifest_sha256"])):
                raise RO4ProjectionError("RO4_SAMPLE_MANIFEST_HASH_INVALID")
            if payload["deterministic"] is not True:
                raise RO4ProjectionDenied("RO4_NON_DETERMINISTIC_SAMPLE_DENIED")
            if not isinstance(payload["sample_count"], int) or not isinstance(payload["population_count"], int):
                raise RO4ProjectionError("RO4_SAMPLE_COUNTS_MUST_BE_INTEGERS")
            if payload["sample_count"] < 0 or payload["population_count"] < payload["sample_count"]:
                raise RO4ProjectionError("RO4_SAMPLE_COUNTS_INVALID")
            if "SAMPLED ONLY" not in str(payload["banner"]).upper():
                raise RO4ProjectionDenied("RO4_SAMPLED_ONLY_BANNER_REQUIRED")
        validated.append({"panel_id": panel_id, "panel_class": panel_class, "payload": dict(payload)})
    if sampled and not disclosure:
        raise RO4ProjectionDenied("RO4_SILENT_SAMPLING_DENIED")
    return validated


def build_console_projection(
    *,
    source_commit: str,
    source_release_refs: list[Mapping[str, Any]],
    panels: list[Mapping[str, Any]],
    schema_root: str | Path | None = None,
) -> dict[str, Any]:
    if not COMMIT_RE.fullmatch(source_commit):
        raise RO4ProjectionError("RO4_PROJECTION_SOURCE_COMMIT_INVALID")
    verify_projection_schema_binding(schema_root)
    projection: dict[str, Any] = {
        "projection_id": "PENDING",
        "route_id": ROUTE_ID,
        "route_state": ROUTE_STATE,
        "source_commit": source_commit,
        "source_release_refs": _validate_release_refs(source_release_refs),
        "panels": _validate_panels(panels),
        "authority_banners": list(REQUIRED_BANNERS),
        "writes": "NONE",
        "remote_deployment": "DENIED",
    }
    logical_hash = _sha256({key: value for key, value in projection.items() if key != "projection_id"})
    projection["projection_id"] = f"RO4.CONSOLE.PROJECTION.{logical_hash[:24]}"
    projection["logical_hash"] = _sha256({key: value for key, value in projection.items() if key != "logical_hash"})
    validate_console_projection(projection, schema_root=schema_root)
    return projection


def validate_console_projection(projection: Mapping[str, Any], *, schema_root: str | Path | None = None) -> None:
    verify_projection_schema_binding(schema_root)
    required = {
        "projection_id",
        "route_id",
        "route_state",
        "source_commit",
        "source_release_refs",
        "panels",
        "authority_banners",
        "writes",
        "remote_deployment",
        "logical_hash",
    }
    if set(projection) != required:
        raise RO4ProjectionError("RO4_PROJECTION_FIELDS_MUST_BE_EXACT")
    if projection["route_id"] != ROUTE_ID or projection["route_state"] != ROUTE_STATE:
        raise RO4ProjectionDenied("RO4_ROUTE_MUST_REMAIN_DISABLED_PENDING_RC_G5")
    if projection["writes"] != "NONE" or projection["remote_deployment"] != "DENIED":
        raise RO4ProjectionDenied("RO4_PROJECTION_WRITE_OR_REMOTE_AUTHORITY_DENIED")
    if tuple(projection["authority_banners"]) != REQUIRED_BANNERS:
        raise RO4ProjectionDenied("RO4_PROJECTION_PERMANENT_BANNERS_MISMATCH")
    if not COMMIT_RE.fullmatch(str(projection["source_commit"])):
        raise RO4ProjectionError("RO4_PROJECTION_SOURCE_COMMIT_INVALID")
    _validate_release_refs(list(projection["source_release_refs"]))
    _validate_panels(list(projection["panels"]))
    expected = _sha256({key: value for key, value in projection.items() if key != "logical_hash"})
    if projection["logical_hash"] != expected:
        raise RO4ProjectionError("RO4_PROJECTION_LOGICAL_HASH_MISMATCH")
    if not str(projection["projection_id"]).startswith("RO4.CONSOLE.PROJECTION."):
        raise RO4ProjectionError("RO4_PROJECTION_ID_INVALID")
