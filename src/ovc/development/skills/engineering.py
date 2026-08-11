from __future__ import annotations

from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256, normalize_relative_path

from .freshness import BaseFreshnessPolicy


_FORBIDDEN_KEYS = {
    "authority_decision", "decision_authority", "grant_authority", "operator_decision",
    "selector_activation", "scientific_promotion", "merge_execute", "force_push", "history_rewrite",
}
_FORBIDDEN_GIT_ACTIONS = {"MERGE", "FORCE_PUSH", "REBASE_HISTORY", "REWRITE_HISTORY", "DELETE_HISTORY"}
_ALLOWED_GIT_ACTIONS = {"CREATE_BRANCH", "STAGE_FILES", "COMMIT", "PUSH", "OPEN_PR", "UPDATE_PR"}


def _walk_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        found = {str(key) for key in value}
        for item in value.values():
            found |= _walk_keys(item)
        return found
    if isinstance(value, (list, tuple)):
        found: set[str] = set()
        for item in value:
            found |= _walk_keys(item)
        return found
    return set()


def build_artifact_proposal(*, kind: str, logical_path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    path = normalize_relative_path(logical_path)
    forbidden = sorted(_walk_keys(payload) & _FORBIDDEN_KEYS)
    if forbidden:
        raise ValueError(f"constructive Skill output contains forbidden authority fields {forbidden}")
    logical = {"kind": str(kind), "logical_path": path, "payload": dict(payload)}
    return {
        "schema": "ovc-dsai-artifact-proposal/v1",
        **logical,
        "proposal_id": canonical_sha256(logical, role="DSAI_ARTIFACT_PROPOSAL"),
        "execution_mode": "DRY_RUN",
        "authority_effect": "NONE",
        "writes_performed": [],
    }


def build_contract_proposal(*, logical_path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return build_artifact_proposal(kind="CONTRACT", logical_path=logical_path, payload=payload)


def build_schema_proposal(*, logical_path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return build_artifact_proposal(kind="SCHEMA", logical_path=logical_path, payload=payload)


def build_fixture_proposal(*, logical_path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return build_artifact_proposal(kind="FIXTURE", logical_path=logical_path, payload=payload)


def build_implementation_proposal(*, logical_path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return build_artifact_proposal(kind="IMPLEMENTATION", logical_path=logical_path, payload=payload)


def git_packet_dry_run(
    *,
    actions: Sequence[str],
    paths: Sequence[str],
    freshness: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_actions = tuple(str(value).upper() for value in actions)
    forbidden = sorted(set(normalized_actions) & _FORBIDDEN_GIT_ACTIONS)
    unknown = sorted(set(normalized_actions) - _ALLOWED_GIT_ACTIONS - _FORBIDDEN_GIT_ACTIONS)
    if forbidden or unknown:
        return {
            "schema": "ovc-dsai-git-packet-dry-run/v1", "status": "BLOCK",
            "reason_codes": (["FORBIDDEN_GIT_ACTION"] if forbidden else []) + (["UNKNOWN_GIT_ACTION"] if unknown else []),
            "forbidden_actions": forbidden, "unknown_actions": unknown, "planned_actions": [],
            "merge_capability": "DISABLED_UNTRUSTED", "force_push": False, "history_rewrite": False,
            "authority_effect": "NONE", "writes_performed": [],
        }
    if freshness.get("status") != "FRESH":
        return {
            "schema": "ovc-dsai-git-packet-dry-run/v1", "status": "BLOCK",
            "reason_codes": ["REPREFLIGHT_REQUIRED"], "forbidden_actions": [], "unknown_actions": [],
            "planned_actions": [], "merge_capability": "DISABLED_UNTRUSTED", "force_push": False,
            "history_rewrite": False, "authority_effect": "NONE", "writes_performed": [],
        }
    normalized_paths = sorted({normalize_relative_path(value) for value in paths})
    return {
        "schema": "ovc-dsai-git-packet-dry-run/v1", "status": "PASS", "reason_codes": ["DRY_RUN_ONLY"],
        "forbidden_actions": [], "unknown_actions": [], "planned_actions": list(normalized_actions),
        "paths": normalized_paths, "merge_capability": "DISABLED_UNTRUSTED", "force_push": False,
        "history_rewrite": False, "authority_effect": "NONE", "writes_performed": [],
    }


def default_freshness_policy() -> BaseFreshnessPolicy:
    return BaseFreshnessPolicy()
