from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence


class UpkeepError(ValueError):
    """Raised when a Programme Genesis upkeep candidate is not lawful."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _parse_time(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise UpkeepError(f"{field} must be a non-empty ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise UpkeepError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise UpkeepError(f"{field} must include an explicit timezone")
    return parsed


def _normalise_source_path(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise UpkeepError("source_ref.path must be non-empty")
    if "\\" in value:
        raise UpkeepError("source_ref.path must use POSIX separators")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise UpkeepError("source_ref.path must be repository-relative and canonical")
    return path.as_posix()


def _forbidden_payload_paths(value: Any, forbidden: set[str], prefix: str = "proposed_payload") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{prefix}.{key_text}"
            if key_text.casefold() in forbidden:
                findings.append(child_path)
            findings.extend(_forbidden_payload_paths(child, forbidden, child_path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            findings.extend(_forbidden_payload_paths(child, forbidden, f"{prefix}[{index}]"))
    return findings


def load_upkeep_registry(path: Path | str) -> dict[str, Any]:
    registry_path = Path(path)
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpkeepError(f"cannot load upkeep registry: {registry_path}") from exc
    if registry.get("schema") != "ovc-programme-genesis-upkeep-candidate-registry/v1":
        raise UpkeepError("unsupported upkeep registry schema")
    return registry


def _candidate_identity_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value)
        for key, value in event.items()
        if key != "candidate_event_id"
    }


def candidate_event_id(event: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(_canonical_bytes(_candidate_identity_payload(event))).hexdigest()
    return f"PG-UPKEEP-{digest[:24]}"


def validate_candidate_event(
    event: Mapping[str, Any],
    registry: Mapping[str, Any],
    *,
    existing_programme_ids: Iterable[str],
) -> dict[str, Any]:
    if event.get("schema") != "ovc-upkeep-candidate-event/v1":
        raise UpkeepError("unsupported candidate event schema")

    allowed_programmes = set(existing_programme_ids)
    programme_id = event.get("programme_id")
    if programme_id not in allowed_programmes:
        raise UpkeepError("candidate must refer to an existing programme identity")

    if event.get("event_type") not in set(registry.get("allowed_event_types", [])):
        raise UpkeepError("candidate event type is not allowlisted")
    if event.get("source_kind") not in set(registry.get("allowed_source_kinds", [])):
        raise UpkeepError("candidate source kind is not allowlisted")

    source_finding_id = event.get("source_finding_id")
    if not isinstance(source_finding_id, str) or not source_finding_id:
        raise UpkeepError("source_finding_id must be non-empty")

    source_ref = event.get("source_ref")
    if not isinstance(source_ref, Mapping):
        raise UpkeepError("source_ref must be an object")
    source_path = _normalise_source_path(source_ref.get("path"))
    source_sha256 = source_ref.get("sha256")
    if not isinstance(source_sha256, str) or len(source_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in source_sha256
    ):
        raise UpkeepError("source_ref.sha256 must be a lowercase SHA-256")

    observed = _parse_time(event.get("observed_at"), "observed_at")
    first_valid = _parse_time(event.get("first_valid_at"), "first_valid_at")
    if first_valid < observed:
        raise UpkeepError("first_valid_at cannot precede observed_at")

    payload = event.get("proposed_payload")
    if not isinstance(payload, Mapping):
        raise UpkeepError("proposed_payload must be an object")
    forbidden = {str(item).casefold() for item in registry.get("forbidden_payload_keys", [])}
    forbidden_paths = _forbidden_payload_paths(payload, forbidden)
    if forbidden_paths:
        raise UpkeepError(f"candidate payload contains forbidden authority fields: {', '.join(sorted(forbidden_paths))}")

    if event.get("status") != registry.get("candidate_status") or event.get("status") != "CANDIDATE_UNAPPROVED":
        raise UpkeepError("candidate status must remain CANDIDATE_UNAPPROVED")
    if event.get("authority_effect") != "NONE" or registry.get("authority_effect") != "NONE":
        raise UpkeepError("candidate authority_effect must remain NONE")

    branch = event.get("target_branch")
    prefix = registry.get("candidate_branch_prefix")
    if not isinstance(branch, str) or not isinstance(prefix, str) or not branch.startswith(prefix):
        raise UpkeepError("candidate target branch is outside the dedicated upkeep prefix")
    if branch in set(registry.get("prohibited_branches", [])):
        raise UpkeepError("candidate target branch is prohibited")

    normalised = deepcopy(dict(event))
    normalised["source_ref"] = {"path": source_path, "sha256": source_sha256}
    expected_id = candidate_event_id(normalised)
    if normalised.get("candidate_event_id") != expected_id:
        raise UpkeepError("candidate_event_id does not match canonical content")
    return normalised


def build_candidate_event(
    *,
    programme_id: str,
    event_type: str,
    source_kind: str,
    source_finding_id: str,
    source_path: str,
    source_sha256: str,
    observed_at: str,
    first_valid_at: str,
    proposed_payload: Mapping[str, Any],
    target_branch: str,
    registry: Mapping[str, Any],
    existing_programme_ids: Iterable[str],
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "schema": "ovc-upkeep-candidate-event/v1",
        "programme_id": programme_id,
        "event_type": event_type,
        "source_kind": source_kind,
        "source_finding_id": source_finding_id,
        "source_ref": {"path": source_path, "sha256": source_sha256},
        "observed_at": observed_at,
        "first_valid_at": first_valid_at,
        "proposed_payload": deepcopy(dict(proposed_payload)),
        "status": "CANDIDATE_UNAPPROVED",
        "authority_effect": "NONE",
        "target_branch": target_branch,
    }
    event["candidate_event_id"] = candidate_event_id(event)
    return validate_candidate_event(event, registry, existing_programme_ids=existing_programme_ids)


def preview_candidate_events(
    findings: Iterable[Mapping[str, Any]],
    *,
    registry: Mapping[str, Any],
    existing_programme_ids: Iterable[str],
    target_branch: str,
) -> list[dict[str, Any]]:
    if registry.get("preview_enabled") is not True:
        raise UpkeepError("candidate preview is disabled")
    ordered = sorted((deepcopy(dict(item)) for item in findings), key=lambda item: str(item.get("source_finding_id", "")))
    maximum = registry.get("max_events_per_run")
    if not isinstance(maximum, int) or maximum < 1:
        raise UpkeepError("registry max_events_per_run is invalid")
    if len(ordered) > maximum:
        raise UpkeepError("candidate preview exceeds max_events_per_run")

    programmes = set(existing_programme_ids)
    candidates = [
        build_candidate_event(
            programme_id=item["programme_id"],
            event_type=item["event_type"],
            source_kind=item["source_kind"],
            source_finding_id=item["source_finding_id"],
            source_path=item["source_ref"]["path"],
            source_sha256=item["source_ref"]["sha256"],
            observed_at=item["observed_at"],
            first_valid_at=item["first_valid_at"],
            proposed_payload=item.get("proposed_payload", {}),
            target_branch=target_branch,
            registry=registry,
            existing_programme_ids=programmes,
        )
        for item in ordered
    ]
    ids = [item["candidate_event_id"] for item in candidates]
    if len(ids) != len(set(ids)):
        raise UpkeepError("duplicate candidate identities in one preview run")
    return candidates


def persist_candidate_event(
    repository_root: Path | str,
    event: Mapping[str, Any],
    *,
    registry: Mapping[str, Any],
    branch_name: str,
    existing_programme_ids: Iterable[str],
) -> Path:
    if registry.get("enabled") is not True:
        raise UpkeepError("automatic upkeep persistence is disabled pending PG-G7")
    decision_id = registry.get("activation_decision_id")
    if not isinstance(decision_id, str) or not decision_id.startswith("PG-G7."):
        raise UpkeepError("accepted PG-G7 activation decision is required")
    if branch_name in set(registry.get("prohibited_branches", [])):
        raise UpkeepError("upkeep persistence cannot target main or another prohibited branch")
    prefix = registry.get("candidate_branch_prefix")
    if not isinstance(prefix, str) or not branch_name.startswith(prefix):
        raise UpkeepError("upkeep persistence requires a dedicated candidate branch")
    if event.get("target_branch") != branch_name:
        raise UpkeepError("event target branch does not match the active branch")

    valid = validate_candidate_event(event, registry, existing_programme_ids=existing_programme_ids)
    root = Path(repository_root).resolve()
    candidate_root = PurePosixPath(str(registry.get("candidate_root", "")))
    if candidate_root.is_absolute() or any(part in {"", ".", ".."} for part in candidate_root.parts):
        raise UpkeepError("candidate_root is not repository-relative and canonical")
    destination = root.joinpath(*candidate_root.parts, f"{valid['candidate_event_id']}.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(valid, handle, sort_keys=True, indent=2, ensure_ascii=False)
            handle.write("\n")
    except FileExistsError as exc:
        raise UpkeepError("candidate event already exists; append-only identity cannot be overwritten") from exc
    return destination
