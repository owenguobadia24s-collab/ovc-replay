from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from ovc.development.identity import canonical_sha256, normalize_relative_path


_RESERVED_TOKENS = {
    "TRUSTED_PROMOTION",
    "PACKET_EXECUTOR_TRUSTED_PROMOTION",
    "ORCH_1_ASSISTED_WRITE",
    "GIT_MERGE_CAPABILITY_TRUSTED_PROMOTION",
    "ORCH_2_AUTOMATIC_INTEGRATION",
    "SELECTOR_ACTIVATION",
    "ACTIVE_DISCOVERY",
    "ACTIVE_DEVELOPMENT",
    "ACTIVE_VALIDATION",
    "SCIENTIFIC_PROMOTION",
    "CANONICAL_PUBLICATION",
    "R2_PUBLICATION",
    "VALIDATION",
    "PROBABILITY",
    "RISK",
    "EXPOSURE",
    "TRADING",
    "EXECUTION",
}


def _receipt(
    *,
    skill: str,
    disposition: str,
    reason_codes: Sequence[str],
    output: Mapping[str, Any],
    correct_refusal: bool = False,
) -> dict[str, Any]:
    logical = {
        "skill": skill,
        "execution_mode": "SHADOW",
        "disposition": disposition,
        "reason_codes": sorted(set(reason_codes)),
        "output": dict(output),
        "correct_refusal": bool(correct_refusal),
    }
    return {
        "schema": "ovc-dsai-governance-shadow-execution/v1",
        **logical,
        "evaluation_status": "PASS",
        "authority_effect": "NONE",
        "controlling": False,
        "writes_performed": [],
        "tool_broker_used": False,
        "receipt_id": canonical_sha256(logical, role="DSAI_GOVERNANCE_SHADOW_EXECUTION"),
    }


def shadow_preflight(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    required = ("repository_sha", "plan_id", "packet_id")
    missing = [field for field in required if not str(snapshot.get(field, "")).strip()]
    reasons: list[str] = []
    if missing:
        reasons.append("MISSING_REQUIRED_PREFLIGHT_IDENTITY")
    if snapshot.get("source_precedence_resolved") is not True:
        reasons.append("SOURCE_PRECEDENCE_UNRESOLVED")
    if snapshot.get("scope_status") not in {"IN_SCOPE", "BOUNDED"}:
        reasons.append("SCOPE_NOT_CONFIRMED")
    if snapshot.get("prerequisites_complete") is not True:
        reasons.append("PREREQUISITE_INCOMPLETE")
    disposition = "PASS" if not reasons else "BLOCK"
    return _receipt(
        skill="ovc-preflight",
        disposition=disposition,
        reason_codes=reasons or ["PREFLIGHT_READ_ONLY_PASS"],
        output={
            "repository_sha": snapshot.get("repository_sha"),
            "plan_id": snapshot.get("plan_id"),
            "packet_id": snapshot.get("packet_id"),
            "missing_fields": missing,
        },
        correct_refusal=disposition == "BLOCK",
    )


def shadow_authority_resolver(
    *,
    recorded_authority: Mapping[str, Any],
    requested_delta: str,
    operator_reserved: Iterable[str] = (),
) -> dict[str, Any]:
    requested = str(requested_delta).strip() or "NONE"
    reserved = {str(value) for value in operator_reserved} | _RESERVED_TOKENS
    is_reserved = requested in reserved
    disposition = "BLOCK" if is_reserved else "PASS"
    return _receipt(
        skill="ovc-authority-resolver",
        disposition=disposition,
        reason_codes=["OPERATOR_REQUIRED_RESERVED_DELTA"] if is_reserved else ["AUTHORITY_RESOLVED_NO_GRANT"],
        output={
            "recorded_authority": dict(recorded_authority),
            "requested_delta": requested,
            "reserved": is_reserved,
            "authority_granted": False,
        },
        correct_refusal=is_reserved,
    )


def shadow_scope_guard(
    *,
    requested_paths: Iterable[str],
    allowed_prefixes: Iterable[str],
    ambiguous: bool = False,
) -> dict[str, Any]:
    normalized_prefixes = tuple(sorted({normalize_relative_path(value).rstrip("/") for value in allowed_prefixes}))
    paths = tuple(sorted({normalize_relative_path(value) for value in requested_paths}))
    violations = [
        path
        for path in paths
        if not any(path == prefix or path.startswith(prefix + "/") for prefix in normalized_prefixes)
    ]
    reasons: list[str] = []
    if ambiguous:
        reasons.append("SCOPE_AMBIGUOUS_FAIL_CLOSED")
    if violations:
        reasons.append("SCOPE_EXPANSION_DENIED")
    disposition = "PASS" if not reasons else "BLOCK"
    return _receipt(
        skill="ovc-scope-guard",
        disposition=disposition,
        reason_codes=reasons or ["SCOPE_BOUNDED"],
        output={"requested_paths": list(paths), "allowed_prefixes": list(normalized_prefixes), "violations": violations},
        correct_refusal=disposition == "BLOCK",
    )


def shadow_prerequisite_resolver(
    *,
    required: Iterable[str],
    observed: Mapping[str, str],
    accepted_states: Iterable[str] = ("APPROVED", "COMPLETED", "PASS"),
) -> dict[str, Any]:
    accepted = set(str(value) for value in accepted_states)
    requirements = tuple(sorted(set(str(value) for value in required)))
    missing = [value for value in requirements if value not in observed]
    unsatisfied = [
        {"prerequisite": value, "state": observed[value]}
        for value in requirements
        if value in observed and observed[value] not in accepted
    ]
    disposition = "PASS" if not missing and not unsatisfied else "BLOCK"
    reasons = []
    if missing:
        reasons.append("MISSING_PREREQUISITE")
    if unsatisfied:
        reasons.append("PREREQUISITE_NOT_SATISFIED")
    return _receipt(
        skill="ovc-prerequisite-resolver",
        disposition=disposition,
        reason_codes=reasons or ["PREREQUISITES_SATISFIED"],
        output={"required": list(requirements), "missing": missing, "unsatisfied": unsatisfied},
        correct_refusal=disposition == "BLOCK",
    )
