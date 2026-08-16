from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
from typing import Iterable, Mapping, Any

from .core import RCCRValidationError, canonical_json_bytes

ALLOWED_STRATA = {"PATH2_IN_HOUSE", "PATH2_EXTERNAL", "EXTERNAL_FINDING", "ARCHITECTURE_CONTROL"}
ALLOWED_VISIBILITY = {"PRE_FREEZE_VISIBLE", "POST_FREEZE_VISIBLE", "MODE_RESTRICTED"}


@dataclass(frozen=True)
class ScaleoutSource:
    source_id: str
    stratum: str
    object_type: str
    owner: str
    source_ref: str
    source_hash: str
    state: str
    visibility: str
    research_mode: str
    authority_effect: str = "NONE"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def compile_bounded_scaleout(
    candidates: Iterable[Mapping[str, Any]],
    *,
    admitted_ids: Iterable[str],
    owner_authority_frontier: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile one explicit post-pilot source wave.

    Admission is exact-id allowlist only. Owner authority is descriptive input and
    never transfers to RCCR: this compiler does not consume real-source evidence,
    open Validation, activate a capability, or promote science.
    """
    allowed = set(str(v) for v in admitted_ids)
    by_id: dict[str, Mapping[str, Any]] = {}
    for raw in candidates:
        sid = str(raw.get("source_id", ""))
        if not sid:
            raise RCCRValidationError("SOURCE_EXACT_ID_REQUIRED", "scaleout candidate")
        if sid in by_id:
            raise RCCRValidationError("DUPLICATE_SOURCE_ID", sid)
        by_id[sid] = raw

    admitted: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    for sid in sorted(by_id):
        raw = by_id[sid]
        if sid not in allowed:
            excluded.append({"source_id": sid, "reason": "NOT_EXACTLY_ADMITTED"})
            continue
        stratum = str(raw.get("stratum", ""))
        visibility = str(raw.get("visibility", ""))
        if stratum not in ALLOWED_STRATA:
            raise RCCRValidationError("UNADMITTED_SCALEOUT_STRATUM", f"{sid}:{stratum}")
        if visibility not in ALLOWED_VISIBILITY:
            raise RCCRValidationError("VISIBILITY_BINDING_REQUIRED", sid)
        if raw.get("protected") is True or str(raw.get("protection_class", "")).upper() == "VALIDATION":
            raise RCCRValidationError("PROTECTED_SOURCE_DENIED", sid)
        if str(raw.get("authority_effect", "NONE")) != "NONE":
            raise RCCRValidationError("SOURCE_AUTHORITY_EFFECT_FORBIDDEN", sid)
        for key in ("object_type", "owner", "source_ref", "source_hash", "state", "research_mode"):
            if not raw.get(key):
                raise RCCRValidationError("SOURCE_METADATA_INCOMPLETE", f"{sid}:{key}")
        admitted.append(ScaleoutSource(
            source_id=sid,
            stratum=stratum,
            object_type=str(raw["object_type"]),
            owner=str(raw["owner"]),
            source_ref=str(raw["source_ref"]),
            source_hash=str(raw["source_hash"]),
            state=str(raw["state"]),
            visibility=visibility,
            research_mode=str(raw["research_mode"]),
        ).as_dict())

    missing = sorted(allowed - set(by_id))
    if missing:
        raise RCCRValidationError("ADMITTED_SOURCE_NOT_IN_CATALOG", ",".join(missing))

    payload: dict[str, Any] = {
        "schema": "ovc-rccr-bounded-scaleout-manifest/v1",
        "admission_mode": "EXACT_ID_ALLOWLIST_ONLY",
        "interesting_file_discovery": "FORBIDDEN",
        "admitted": admitted,
        "excluded": excluded,
        "pre_post_freeze_visibility_enforced": True,
        "owner_authority_frontier": dict(owner_authority_frontier or {}),
        "rccr_consumption_boundary": {
            "real_source_ec1_consumption": "DENIED_BY_RCCRI_WP6B_SCOPE",
            "path2_real_source_consumption": "DENIED_BY_RCCRI_WP6B_SCOPE",
            "owner_capability_activation": "DENIED",
            "validation_consumption": "DENIED",
        },
        "authority_effect": "NONE",
    }
    payload["manifest_id"] = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return payload
