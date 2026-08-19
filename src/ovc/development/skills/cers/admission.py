from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


_ADMISSION_REQUIRED_FIELDS = frozenset(
    {
        "schema",
        "admission_id",
        "status",
        "programme_id",
        "current_state_root",
        "governing_plan_id",
        "governing_plan_version",
        "owner_authority_source",
        "eligible_authority_classes",
        "eligible_packet_classes",
        "allowed_side_effect_classes",
        "executor_binding_id",
        "write_domain_rule",
        "semantic_owner_rule",
        "operator_boundary_policy",
        "explicit_prohibitions",
        "admission_authority_source",
        "revocation_behavior",
        "authority_effect",
    }
)


def canonical_record_sha256(record: Mapping[str, Any]) -> str:
    payload = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_inactive_admission_registry(
    registry: Mapping[str, Any],
    *,
    programme_roots: Mapping[str, str],
) -> tuple[str, ...]:
    """Return deterministic fail-closed registry defects.

    WP4 only materialises an inactive registry.  This validator deliberately does
    not activate admissions or infer authority from repository presence.
    """

    defects: list[str] = []
    if registry.get("status") != "INACTIVE_PREACTIVATION":
        defects.append("PROGRAMME_ADMISSION_NOT_INACTIVE")
    if registry.get("future_programme_auto_admission") is not False:
        defects.append("FUTURE_PROGRAMME_AUTO_ADMISSION_NOT_FALSE")
    if registry.get("unknown_or_absent_programme") != "DENY":
        defects.append("UNKNOWN_PROGRAMME_NOT_DENIED")
    if registry.get("authority_effect") != "NONE":
        defects.append("REGISTRY_AUTHORITY_EFFECT_NOT_NONE")

    entries = registry.get("entries")
    if not isinstance(entries, list):
        return tuple(defects + ["ADMISSION_ENTRIES_NOT_LIST"])
    hashes = {
        str(row.get("admission_id")): str(row.get("canonical_sha256"))
        for row in registry.get("entry_hashes", ())
        if isinstance(row, Mapping)
    }
    admitted_programmes: set[str] = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            defects.append("ADMISSION_ENTRY_NOT_OBJECT")
            continue
        missing = sorted(_ADMISSION_REQUIRED_FIELDS - set(entry))
        if missing:
            defects.append("ADMISSION_FIELDS_MISSING:" + ",".join(missing))
            continue
        admission_id = str(entry["admission_id"])
        programme_id = str(entry["programme_id"])
        if programme_id in admitted_programmes:
            defects.append(f"DUPLICATE_PROGRAMME_ADMISSION:{programme_id}")
        admitted_programmes.add(programme_id)
        if entry.get("status") != "INACTIVE_PREACTIVATION":
            defects.append(f"ADMISSION_NOT_INACTIVE:{admission_id}")
        if entry.get("authority_effect") != "NONE":
            defects.append(f"ADMISSION_AUTHORITY_EFFECT_NOT_NONE:{admission_id}")
        if entry.get("current_state_root") != programme_roots.get(programme_id):
            defects.append(f"PROGRAMME_ROOT_MISMATCH:{admission_id}")
        if hashes.get(admission_id) != canonical_record_sha256(entry):
            defects.append(f"ADMISSION_HASH_MISMATCH:{admission_id}")

    excluded_programmes = {
        str(row.get("programme_id"))
        for row in registry.get("exclusions", ())
        if isinstance(row, Mapping)
    }
    known_programmes = set(programme_roots)
    if admitted_programmes & excluded_programmes:
        defects.append("PROGRAMME_BOTH_ADMITTED_AND_EXCLUDED")
    if admitted_programmes | excluded_programmes != known_programmes:
        defects.append("PROGRAMME_ROOT_CENSUS_NOT_EXHAUSTIVE")
    return tuple(defects)
