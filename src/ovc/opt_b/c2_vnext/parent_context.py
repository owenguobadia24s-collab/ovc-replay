"""Inactive, noncanonical parent-context resolver for C2 vNext.

CEAR-G8 authorises deterministic SHADOW_FROZEN_READ_ONLY implementation only.
This module cannot activate parent selection, choose thresholds, promote events
or episodes, mutate active C2, publish releases, consume Validation, or exercise
probability, risk, exposure, trading or execution authority.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

UTC = timezone.utc
RESOLVER_ID = "C2.PARENT.CONTEXT.RESOLVER.v1"
PARENT_CLOCK = "2H_A_L"
PARENT_ANCHOR = "UTC_0000"
AUTHORITY = "SHADOW_FROZEN_READ_ONLY"
VALID_PARENT_SLOT_STATUS = "COMPLETE"
VALID_PARENT_OBJECT_STATUS = "VALID"
ROLE_MEASUREMENT = "PARENT_MEASUREMENT"
ROLE_STRUCTURAL = "PARENT_STRUCTURAL"
ROLE_AXIS = "PARENT_AXIS_CONTEXT"
PROHIBITED_KEYS = {
    "probability",
    "risk",
    "exposure",
    "trade",
    "trading",
    "execution",
    "position_size",
    "target",
    "stop",
    "semantic_label",
    "event_promotion",
    "episode_promotion",
    "active_selector",
    "canonical_selector",
}
IDENTITY_FIELDS = (
    "instrument_id",
    "side",
    "release_id",
    "calendar_id",
    "parent_lattice_id",
)


class ParentContextError(ValueError):
    """Raised when the frozen parent-context or authority boundary is violated."""


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise ParentContextError(marker)


def _parse_time(value: str | datetime) -> datetime:
    try:
        result = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ParentContextError("INVALID_TIME") from exc
    _require(result.tzinfo is not None, "TIMEZONE_REQUIRED")
    return result.astimezone(UTC)


def _iso(value: str | datetime) -> str:
    return _parse_time(value).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(prefix: str, value: Any) -> str:
    return f"{prefix}.{hashlib.sha256(_canonical(value)).hexdigest()[:24]}"


def _scan_prohibited(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in PROHIBITED_KEYS:
                raise ParentContextError(f"PROHIBITED_FIELD:{path}.{key}")
            _scan_prohibited(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _scan_prohibited(item, f"{path}[{index}]")


def expected_parent_slot(local_first_valid_time: str | datetime) -> tuple[str, str]:
    """Return the latest expected completed UTC-anchored two-hour slot.

    The returned interval end is always less than or equal to the local
    first-valid time. Equality is intentionally allowed by CEAR-G8.
    """
    local_time = _parse_time(local_first_valid_time)
    boundary_hour = local_time.hour - (local_time.hour % 2)
    end = local_time.replace(hour=boundary_hour, minute=0, second=0, microsecond=0)
    start = end - timedelta(hours=2)
    return _iso(start), _iso(end)


def _base_link(
    *,
    link_kind: str,
    local: Mapping[str, Any],
    expected_start: str,
    expected_end: str,
    candidate_ids: Sequence[str],
    eligible_ids: Sequence[str],
    exclusions: Sequence[Mapping[str, Any]],
    selected_id: str | None,
    selection_reason: str,
    evidence_status: str,
    reason_codes: Sequence[str],
    parent_observation_id: str | None = None,
    parent_object_id: str | None = None,
    parent_definition_hash: str | None = None,
    parent_first_valid_time: str | None = None,
    age_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema": "c2_parent_context_link/vnext-r1",
        "link_kind": link_kind,
        "local_observation_id": str(local["observation_id"]),
        "local_first_valid_time": _iso(local["first_valid_time"]),
        "as_of_time": _iso(local["first_valid_time"]),
        "parent_scope_id": str(local["parent_scope_id"]),
        "parent_clock": PARENT_CLOCK,
        "parent_lattice_id": str(local["parent_lattice_id"]),
        "parent_calendar_id": str(local["calendar_id"]),
        "expected_parent_slot_start": expected_start,
        "expected_parent_slot_end": expected_end,
        "parent_observation_id": parent_observation_id,
        "parent_object_id": parent_object_id,
        "parent_definition_hash": parent_definition_hash,
        "parent_first_valid_time": parent_first_valid_time,
        "instrument_id": str(local["instrument_id"]),
        "side": str(local["side"]),
        "release_id": str(local["release_id"]),
        "evidence_status": evidence_status,
        "computability": "COMPUTABLE" if selected_id is not None else "NOT_COMPUTABLE",
        "reason_codes": sorted({str(item) for item in reason_codes}),
        "resolver_id": RESOLVER_ID,
        "resolver_version": "1",
        "candidate_ids": sorted({str(item) for item in candidate_ids}),
        "eligible_ids": sorted({str(item) for item in eligible_ids}),
        "exclusions": sorted(
            [copy.deepcopy(dict(item)) for item in exclusions],
            key=lambda item: (str(item.get("candidate_id", "")), tuple(item.get("reason_codes", []))),
        ),
        "selected_id": selected_id,
        "selection_reason": selection_reason,
        "fallback_id": None,
        "refresh_status": "NOT_COMPUTABLE" if selected_id is None else "LINKED",
        "previous_link_id": None,
        "age_evidence": copy.deepcopy(dict(age_evidence or {})),
        "source_ids": [],
        "active": False,
        "canonical": False,
        "semantic_authority": "NONE",
        "episode_authority": "NONE",
        "thresholds": [],
        "authority": AUTHORITY,
    }
    body["link_id"] = _digest("C2.PARENT.LINK", body)
    body["content_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    return body


def _validate_local(local: Mapping[str, Any]) -> None:
    required = {
        "observation_id",
        "first_valid_time",
        "instrument_id",
        "side",
        "release_id",
        "calendar_id",
        "parent_lattice_id",
        "parent_scope_id",
    }
    _require(required.issubset(local), "LOCAL_OBSERVATION_FIELDS_REQUIRED")
    _parse_time(local["first_valid_time"])
    for field in required - {"first_valid_time"}:
        _require(bool(str(local[field])), f"LOCAL_{field.upper()}_REQUIRED")


def _identity_reasons(local: Mapping[str, Any], candidate: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    for field in IDENTITY_FIELDS:
        if str(candidate.get(field, "")) != str(local[field]):
            reasons.append(f"{field.upper()}_MISMATCH")
    return reasons


def _age_seconds(later: str | datetime, earlier: str | datetime) -> int:
    seconds = int((_parse_time(later) - _parse_time(earlier)).total_seconds())
    _require(seconds >= 0, "NEGATIVE_AGE_PROHIBITED")
    return seconds


def _slot_inventory(
    local: Mapping[str, Any],
    parent_slots: Sequence[Mapping[str, Any]],
    expected_start: str,
    expected_end: str,
) -> tuple[list[str], list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    candidate_ids: list[str] = []
    expected_candidates: list[Mapping[str, Any]] = []
    exclusions: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for slot in parent_slots:
        _require("observation_id" in slot, "PARENT_OBSERVATION_ID_REQUIRED")
        slot_id = str(slot["observation_id"])
        _require(slot_id not in seen, "DUPLICATE_PARENT_OBSERVATION_ID")
        seen.add(slot_id)
        candidate_ids.append(slot_id)
        _require("interval_start" in slot and "interval_end" in slot, "PARENT_INTERVAL_REQUIRED")
        is_expected = _iso(slot["interval_start"]) == expected_start and _iso(slot["interval_end"]) == expected_end
        if is_expected:
            expected_candidates.append(slot)
        else:
            exclusions.append({"candidate_id": slot_id, "reason_codes": ["NOT_EXPECTED_PARENT_SLOT"]})
    return candidate_ids, expected_candidates, exclusions


def _resolve_fixed_parent(
    local: Mapping[str, Any],
    parent_slots: Sequence[Mapping[str, Any]],
    expected_start: str,
    expected_end: str,
    *,
    eligible_local_observation_count: int,
    registered_closure_count: int,
) -> tuple[dict[str, Any], Mapping[str, Any] | None]:
    candidate_ids, expected_candidates, exclusions = _slot_inventory(
        local, parent_slots, expected_start, expected_end
    )
    if not expected_candidates:
        link = _base_link(
            link_kind="FIXED_PARENT_OBSERVATION_LINK",
            local=local,
            expected_start=expected_start,
            expected_end=expected_end,
            candidate_ids=candidate_ids,
            eligible_ids=[],
            exclusions=exclusions,
            selected_id=None,
            selection_reason="EXPECTED_PARENT_SLOT_MISSING",
            evidence_status="NOT_COMPUTABLE",
            reason_codes=["EXPECTED_PARENT_SLOT_MISSING"],
            age_evidence={
                "elapsed_duration_seconds": None,
                "eligible_local_observation_count": eligible_local_observation_count,
                "parent_slot_count": len(parent_slots),
                "registered_closure_count": registered_closure_count,
                "parent_observation_age_seconds": None,
                "parent_object_age_seconds": None,
                "role_projection_age_seconds": None,
            },
        )
        return link, None
    if len(expected_candidates) > 1:
        conflict_exclusions = exclusions + [
            {"candidate_id": str(slot["observation_id"]), "reason_codes": ["EXPECTED_PARENT_SLOT_CONFLICTED"]}
            for slot in expected_candidates
        ]
        link = _base_link(
            link_kind="FIXED_PARENT_OBSERVATION_LINK",
            local=local,
            expected_start=expected_start,
            expected_end=expected_end,
            candidate_ids=candidate_ids,
            eligible_ids=[],
            exclusions=conflict_exclusions,
            selected_id=None,
            selection_reason="EXPECTED_PARENT_SLOT_CONFLICTED",
            evidence_status="NOT_COMPUTABLE",
            reason_codes=["EXPECTED_PARENT_SLOT_CONFLICTED"],
        )
        return link, None

    slot = expected_candidates[0]
    slot_id = str(slot["observation_id"])
    reasons = _identity_reasons(local, slot)
    status = str(slot.get("status", ""))
    if status != VALID_PARENT_SLOT_STATUS:
        known = {
            "MISSING",
            "INCOMPLETE",
            "GAPPED",
            "CONFLICTED",
            "CLOSURE_UNRESOLVED",
            "CENSORED",
            "NOT_FIRST_VALID",
        }
        reasons.append(f"EXPECTED_PARENT_SLOT_{status}" if status in known else "EXPECTED_PARENT_SLOT_STATUS_INVALID")
    required = {"first_valid_time", "source_id"}
    if not required.issubset(slot):
        reasons.append("PARENT_SLOT_IDENTITY_INCOMPLETE")
    else:
        parent_first_valid = _parse_time(slot["first_valid_time"])
        local_first_valid = _parse_time(local["first_valid_time"])
        if parent_first_valid > local_first_valid:
            reasons.append("PARENT_NOT_FIRST_VALID")
        if _parse_time(slot["interval_end"]) > local_first_valid:
            reasons.append("PARENT_INTERVAL_END_AFTER_LOCAL_FIRST_VALID")
        if not str(slot["source_id"]):
            reasons.append("PARENT_SOURCE_ID_REQUIRED")
    reasons = sorted(set(reasons))
    if reasons:
        exclusions.append({"candidate_id": slot_id, "reason_codes": reasons})
        link = _base_link(
            link_kind="FIXED_PARENT_OBSERVATION_LINK",
            local=local,
            expected_start=expected_start,
            expected_end=expected_end,
            candidate_ids=candidate_ids,
            eligible_ids=[],
            exclusions=exclusions,
            selected_id=None,
            selection_reason=reasons[0],
            evidence_status="NOT_COMPUTABLE",
            reason_codes=reasons,
        )
        return link, None

    age = _age_seconds(local["first_valid_time"], slot["first_valid_time"])
    link = _base_link(
        link_kind="FIXED_PARENT_OBSERVATION_LINK",
        local=local,
        expected_start=expected_start,
        expected_end=expected_end,
        candidate_ids=candidate_ids,
        eligible_ids=[slot_id],
        exclusions=exclusions,
        selected_id=slot_id,
        selection_reason="EXACT_EXPECTED_COMPLETED_PARENT_SLOT",
        evidence_status="LINKED",
        reason_codes=[],
        parent_observation_id=slot_id,
        parent_first_valid_time=_iso(slot["first_valid_time"]),
        age_evidence={
            "elapsed_duration_seconds": age,
            "eligible_local_observation_count": eligible_local_observation_count,
            "parent_slot_count": len(parent_slots),
            "registered_closure_count": registered_closure_count,
            "parent_observation_age_seconds": age,
            "parent_object_age_seconds": None,
            "role_projection_age_seconds": age,
        },
    )
    link["source_ids"] = [str(slot["source_id"])]
    link["content_sha256"] = hashlib.sha256(_canonical({k: v for k, v in link.items() if k != "content_sha256"})).hexdigest()
    return link, slot


def _project_role(
    *,
    local: Mapping[str, Any],
    fixed_parent: Mapping[str, Any] | None,
    parent_objects: Sequence[Mapping[str, Any]],
    role: str,
    depth: int | None,
    expected_start: str,
    expected_end: str,
) -> dict[str, Any]:
    role_candidates = [
        item
        for item in parent_objects
        if str(item.get("role", "")) == role
        and (role != ROLE_STRUCTURAL or item.get("depth") == depth)
    ]
    candidate_ids: list[str] = []
    eligible: list[Mapping[str, Any]] = []
    exclusions: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for item in role_candidates:
        _require("object_id" in item, "PARENT_OBJECT_ID_REQUIRED")
        object_id = str(item["object_id"])
        _require(object_id not in seen, "DUPLICATE_PARENT_OBJECT_ID")
        seen.add(object_id)
        candidate_ids.append(object_id)
        reasons = _identity_reasons(local, item)
        if fixed_parent is None:
            reasons.append("DEPENDENCY_NOT_COMPUTABLE")
        elif str(item.get("parent_observation_id", "")) != str(fixed_parent["observation_id"]):
            reasons.append("PARENT_OBSERVATION_ID_MISMATCH")
        if str(item.get("status", "")) != VALID_PARENT_OBJECT_STATUS:
            reasons.append("PARENT_OBJECT_STATUS_INVALID")
        if not str(item.get("definition_hash", "")):
            reasons.append("PARENT_DEFINITION_HASH_REQUIRED")
        if "first_valid_time" not in item:
            reasons.append("PARENT_OBJECT_FIRST_VALID_REQUIRED")
        else:
            if _parse_time(item["first_valid_time"]) > _parse_time(local["first_valid_time"]):
                reasons.append("PARENT_NOT_FIRST_VALID")
        if reasons:
            exclusions.append({"candidate_id": object_id, "reason_codes": sorted(set(reasons))})
        else:
            eligible.append(item)

    link_kind = {
        ROLE_MEASUREMENT: "PARENT_MEASUREMENT_LINK",
        ROLE_STRUCTURAL: "PARENT_STRUCTURAL_LINK_BY_DEPTH",
        ROLE_AXIS: "PARENT_AXIS_CONTEXT_LINK",
    }[role]
    if fixed_parent is None:
        reason = "DEPENDENCY_NOT_COMPUTABLE"
        selected = None
    elif not eligible:
        reason = "NO_ELIGIBLE_PARENT_OBJECT"
        selected = None
    elif len(eligible) > 1:
        reason = "MULTIPLE_ELIGIBLE_NO_GOVERNED_SELECTION"
        selected = None
        exclusions.extend(
            {"candidate_id": str(item["object_id"]), "reason_codes": [reason]}
            for item in eligible
        )
        eligible = []
    else:
        reason = "EXACTLY_ONE_ELIGIBLE_PARENT_OBJECT"
        selected = eligible[0]

    selected_id = str(selected["object_id"]) if selected else None
    parent_first_valid = _iso(selected["first_valid_time"]) if selected else None
    age = _age_seconds(local["first_valid_time"], selected["first_valid_time"]) if selected else None
    link = _base_link(
        link_kind=link_kind,
        local=local,
        expected_start=expected_start,
        expected_end=expected_end,
        candidate_ids=candidate_ids,
        eligible_ids=[str(item["object_id"]) for item in eligible],
        exclusions=exclusions,
        selected_id=selected_id,
        selection_reason=reason,
        evidence_status="LINKED" if selected else "NOT_COMPUTABLE",
        reason_codes=[] if selected else [reason],
        parent_observation_id=str(fixed_parent["observation_id"]) if fixed_parent else None,
        parent_object_id=selected_id,
        parent_definition_hash=str(selected["definition_hash"]) if selected else None,
        parent_first_valid_time=parent_first_valid,
        age_evidence={
            "elapsed_duration_seconds": age,
            "eligible_local_observation_count": None,
            "parent_slot_count": None,
            "registered_closure_count": None,
            "parent_observation_age_seconds": (
                _age_seconds(local["first_valid_time"], fixed_parent["first_valid_time"])
                if fixed_parent else None
            ),
            "parent_object_age_seconds": age,
            "role_projection_age_seconds": age,
        },
    )
    if role == ROLE_STRUCTURAL:
        link["structural_depth"] = depth
        link["content_sha256"] = hashlib.sha256(_canonical({k: v for k, v in link.items() if k != "content_sha256"})).hexdigest()
    return link


def _higher_order_projection(
    local: Mapping[str, Any],
    higher_order_local_objects: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    candidate_ids: list[str] = []
    eligible_ids: list[str] = []
    exclusions: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    for item in sorted(higher_order_local_objects, key=lambda row: str(row.get("object_id", ""))):
        _require("object_id" in item, "HIGHER_ORDER_LOCAL_OBJECT_ID_REQUIRED")
        object_id = str(item["object_id"])
        candidate_ids.append(object_id)
        reasons: list[str] = []
        if str(item.get("local_clock", "")) != "15M":
            reasons.append("LOCAL_CLOCK_MISMATCH")
        try:
            depth = int(item.get("depth", -1))
        except (TypeError, ValueError):
            depth = -1
        if depth < 1:
            reasons.append("HIGHER_ORDER_DEPTH_REQUIRED")
        if str(item.get("local_observation_id", "")) != str(local["observation_id"]):
            reasons.append("LOCAL_OBSERVATION_ID_MISMATCH")
        if reasons:
            exclusions.append({"candidate_id": object_id, "reason_codes": sorted(set(reasons))})
            continue
        eligible_ids.append(object_id)
        links.append(
            {
                "link_kind": "HIGHER_ORDER_LOCAL_CLOCK_LINK",
                "object_id": object_id,
                "local_clock": "15M",
                "depth": depth,
                "parent_equivalence": False,
                "active": False,
                "canonical": False,
                "authority": AUTHORITY,
            }
        )
    body = {
        "schema": "c2_higher_order_local_projection/vnext-r1",
        "projection_id": "",
        "local_observation_id": str(local["observation_id"]),
        "candidate_ids": sorted(candidate_ids),
        "eligible_ids": sorted(eligible_ids),
        "exclusions": exclusions,
        "links": links,
        "selected_id": None,
        "selection_reason": "INVENTORY_ONLY_NO_PARENT_EQUIVALENCE",
        "fallback_id": None,
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    body["projection_id"] = _digest("C2.LOCAL.HIGHER.ORDER", body)
    return body


def _episode_projection(episode_candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    candidate_ids = sorted(
        str(item.get("episode_id")) for item in episode_candidates if item.get("episode_id")
    )
    return {
        "schema": "c2_episode_context_projection/vnext-r1",
        "link_kind": "HIGHER_SCALE_EPISODE_LINK",
        "candidate_ids": candidate_ids,
        "eligible_ids": [],
        "exclusions": [
            {"candidate_id": item, "reason_codes": ["EPISODE_AUTHORITY_UNAVAILABLE"]}
            for item in candidate_ids
        ],
        "selected_id": None,
        "selection_reason": "EPISODE_AUTHORITY_UNAVAILABLE",
        "fallback_id": None,
        "computability": "NOT_COMPUTABLE",
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
        "episode_authority": "NONE",
    }


def _apply_refresh(current: dict[str, Any], previous: Mapping[str, Any] | None) -> None:
    if previous is None:
        return
    previous_selected = previous.get("selected_id")
    current_selected = current.get("selected_id")
    current["previous_link_id"] = previous.get("link_id")
    if previous_selected == current_selected and current_selected is not None:
        current["refresh_status"] = "UNCHANGED"
    elif previous_selected is None and current_selected is not None:
        current["refresh_status"] = "LINKED"
    elif previous_selected is not None and current_selected is None:
        current["refresh_status"] = "CLEARED"
    elif previous_selected != current_selected and current_selected is not None:
        current["refresh_status"] = "REFRESHED"
    else:
        current["refresh_status"] = "NOT_COMPUTABLE"
    current["content_sha256"] = hashlib.sha256(_canonical({k: v for k, v in current.items() if k != "content_sha256"})).hexdigest()


def resolve_parent_context(
    *,
    local_observation: Mapping[str, Any],
    parent_slots: Sequence[Mapping[str, Any]],
    parent_objects: Sequence[Mapping[str, Any]] = (),
    structural_depths: Sequence[int] = (),
    higher_order_local_objects: Sequence[Mapping[str, Any]] = (),
    episode_candidates: Sequence[Mapping[str, Any]] = (),
    previous_bundle: Mapping[str, Any] | None = None,
    eligible_local_observation_count: int = 0,
    registered_closure_count: int = 0,
    episode_authority: bool = False,
) -> dict[str, Any]:
    """Resolve a typed, fail-closed parent-context bundle.

    The function is deterministic and read-only. It resolves the expected
    fixed slot before testing completeness, never carries an older parent
    forward, and never chooses among unresolved multiple parent objects.
    """
    _scan_prohibited(local_observation)
    _scan_prohibited(parent_slots)
    _scan_prohibited(parent_objects)
    _scan_prohibited(higher_order_local_objects)
    _scan_prohibited(episode_candidates)
    _require(not episode_authority, "EPISODE_AUTHORITY_NOT_AVAILABLE")
    _require(isinstance(eligible_local_observation_count, int) and eligible_local_observation_count >= 0, "ELIGIBLE_LOCAL_COUNT_INVALID")
    _require(isinstance(registered_closure_count, int) and registered_closure_count >= 0, "REGISTERED_CLOSURE_COUNT_INVALID")
    local = copy.deepcopy(dict(local_observation))
    _validate_local(local)
    expected_start, expected_end = expected_parent_slot(local["first_valid_time"])
    fixed_link, fixed_parent = _resolve_fixed_parent(
        local,
        list(parent_slots),
        expected_start,
        expected_end,
        eligible_local_observation_count=eligible_local_observation_count,
        registered_closure_count=registered_closure_count,
    )
    previous_fixed = None
    if previous_bundle is not None:
        previous_fixed = previous_bundle.get("fixed_parent_observation_link")
    _apply_refresh(fixed_link, previous_fixed if isinstance(previous_fixed, Mapping) else None)

    measurement = _project_role(
        local=local,
        fixed_parent=fixed_parent,
        parent_objects=parent_objects,
        role=ROLE_MEASUREMENT,
        depth=None,
        expected_start=expected_start,
        expected_end=expected_end,
    )
    axis = _project_role(
        local=local,
        fixed_parent=fixed_parent,
        parent_objects=parent_objects,
        role=ROLE_AXIS,
        depth=None,
        expected_start=expected_start,
        expected_end=expected_end,
    )
    depths = sorted({int(item) for item in structural_depths} | {
        int(item["depth"])
        for item in parent_objects
        if str(item.get("role", "")) == ROLE_STRUCTURAL and isinstance(item.get("depth"), int)
    })
    structural_links = [
        _project_role(
            local=local,
            fixed_parent=fixed_parent,
            parent_objects=parent_objects,
            role=ROLE_STRUCTURAL,
            depth=depth,
            expected_start=expected_start,
            expected_end=expected_end,
        )
        for depth in depths
    ]
    higher_order = _higher_order_projection(local, higher_order_local_objects)
    episode = _episode_projection(episode_candidates)
    local_frame = {
        "schema": "c2_local_in_parent_frame_profile/vnext-r1",
        "profile_id": "",
        "local_observation_id": str(local["observation_id"]),
        "fixed_parent_observation_id": fixed_link["selected_id"],
        "parent_measurement_object_id": measurement["selected_id"],
        "parent_structural_object_ids": [
            item["selected_id"] for item in structural_links if item["selected_id"] is not None
        ],
        "parent_axis_context_object_id": axis["selected_id"],
        "computability": "COMPUTABLE" if fixed_link["selected_id"] is not None else "NOT_COMPUTABLE",
        "reason_codes": [] if fixed_link["selected_id"] is not None else ["DEPENDENCY_NOT_COMPUTABLE"],
        "interpretation": None,
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    local_frame["profile_id"] = _digest("C2.LOCAL.PARENT.FRAME", local_frame)

    components = {
        "fixed_parent_observation": fixed_link["computability"],
        "parent_measurement": measurement["computability"],
        "parent_axis_context": axis["computability"],
        "parent_structural_by_depth": {
            str(item["structural_depth"]): item["computability"] for item in structural_links
        },
        "higher_order_local_clock": "COMPUTABLE",
        "episode_context": "NOT_COMPUTABLE",
    }
    body: dict[str, Any] = {
        "schema": "c2_parent_context_bundle/vnext-r1",
        "bundle_id": "",
        "resolver_id": RESOLVER_ID,
        "resolver_version": "1",
        "local_observation_id": str(local["observation_id"]),
        "local_first_valid_time": _iso(local["first_valid_time"]),
        "expected_parent_slot_start": expected_start,
        "expected_parent_slot_end": expected_end,
        "fixed_parent_observation_link": fixed_link,
        "parent_measurement_link": measurement,
        "parent_structural_links_by_depth": structural_links,
        "parent_axis_context_link": axis,
        "local_in_parent_frame_profile": local_frame,
        "higher_order_local_clock_projection": higher_order,
        "higher_scale_episode_link": episode,
        "component_computability": components,
        "global_degraded_state": None,
        "universal_staleness_threshold": None,
        "fallback_parent_id": None,
        "active": False,
        "canonical": False,
        "semantic_authority": "NONE",
        "episode_authority": "NONE",
        "consumer_denominator_authority": "NONE",
        "authority": AUTHORITY,
    }
    body["bundle_id"] = _digest("C2.PARENT.BUNDLE", body)
    body["content_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    return body
