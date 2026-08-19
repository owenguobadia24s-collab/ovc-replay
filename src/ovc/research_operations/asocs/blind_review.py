"""ASOCS WP7 blind-review infrastructure prebuild.

Infrastructure only: no human record is created, no G5 freeze occurs, and no reviewer
session begins. Blind and reveal resources are structurally separated.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

BLIND_RESOURCE_ROOT = "external/asocs/g1/blind"
REVEAL_RESOURCE_ROOT = "external/asocs/g1/reveal"

BLIND_INDEX_ALLOWED_KEYS = frozenset({
    "case_id", "navigation_window", "source_native_visual_ref"
})
BLIND_INDEX_FORBIDDEN_KEYS = frozenset({
    "construct", "stratum", "stratum_memberships", "machine_state",
    "machine_disposition", "c1", "c2", "c2e", "occurrence_context",
    "prior_disagreement_rate", "cross_case_result", "hidden_repeat",
    "outcome", "failure_attribution",
})

PROHIBITED_PROMPT_TERMS = (
    "c1", "c2", "c2e", "level", "container", "relation", "transition",
    "parent context", "computability", "episode", "phase", "occurrencecontext",
    "support", "resistance", "breakout", "rejection", "same level",
)


class ASOCSBlindFirewallError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def validate_blind_index(entry: Mapping[str, Any]) -> dict[str, Any]:
    keys = set(entry)
    leaked = sorted(keys.intersection(BLIND_INDEX_FORBIDDEN_KEYS))
    if leaked:
        raise ASOCSBlindFirewallError("BLIND_METADATA_LEAK:" + ",".join(leaked))
    extras = sorted(keys - BLIND_INDEX_ALLOWED_KEYS)
    if extras:
        raise ASOCSBlindFirewallError("BLIND_FIELD_NOT_ALLOWED:" + ",".join(extras))
    missing = sorted(BLIND_INDEX_ALLOWED_KEYS - keys)
    if missing:
        raise ASOCSBlindFirewallError("BLIND_FIELD_MISSING:" + ",".join(missing))
    return dict(entry)


def lint_neutral_prompt(text: str) -> list[str]:
    normalized = text.casefold()
    hits: list[str] = []
    for term in PROHIBITED_PROMPT_TERMS:
        if re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", normalized):
            hits.append(term)
    return hits


def require_neutral_prompt(text: str) -> str:
    hits = lint_neutral_prompt(text)
    if hits:
        raise ASOCSBlindFirewallError("PROHIBITED_OVC_VOCABULARY:" + ",".join(hits))
    return text


def freeze_blind_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["protocol_label"] = "WITHIN_SINGLE_REVIEWER_PROTOCOL"
    payload["frozen_before_reveal"] = True
    digest = hashlib.sha256(_canonical(payload)).hexdigest()
    return {**payload, "blind_record_sha256": digest}


def successor_annotation(frozen_record: Mapping[str, Any], annotation: Mapping[str, Any]) -> dict[str, Any]:
    if not frozen_record.get("frozen_before_reveal"):
        raise ASOCSBlindFirewallError("BASE_RECORD_NOT_FROZEN")
    return {
        "schema": "ovc-asocs-blind-successor-annotation/v0_1",
        "predecessor_blind_record_sha256": str(frozen_record["blind_record_sha256"]),
        "annotation": dict(annotation),
        "mutates_predecessor": False,
    }
