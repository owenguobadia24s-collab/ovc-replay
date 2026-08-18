from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

_PROVENANCE_ONLY_KEYS = {
    "branch",
    "branch_name",
    "pr_number",
    "pull_request",
    "worker",
    "worker_id",
    "ci_run",
    "ci_run_id",
    "local_path",
    "cache_key",
    "ui_session",
    "physical_attempt_id",
}

_KIND_PREFIXES = {
    "series",
    "entry",
    "generation",
    "frontier",
    "control",
    "pointer",
    "generation_manifest",
    "bootstrap_manifest",
}


def _reject_physical_provenance(value: Any, path: str = "identity") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in _PROVENANCE_ONLY_KEYS:
                raise ValueError(f"physical provenance key is not identity-bearing: {path}.{key}")
            _reject_physical_provenance(item, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _reject_physical_provenance(item, f"{path}[{index}]")


def logical_id(kind: str, identity_payload: Mapping[str, Any]) -> str:
    """Return a content-addressed P2CTI logical ID.

    Branch/PR/worker/run/cache/UI provenance is deliberately forbidden from the
    identity payload. Owner scientific payloads should be referenced by exact ID
    and semantic generation, not embedded here.
    """

    if kind not in _KIND_PREFIXES:
        raise ValueError(f"unsupported P2CTI identity kind: {kind}")
    _reject_physical_provenance(identity_payload)
    digest = canonical_sha256({"kind": kind, "identity": dict(identity_payload)})
    return f"p2cti:{kind}:{digest}"


def series_id(series_key: str = "PATH2_CONTINUOUS_THEORY_INVENTORY") -> str:
    return logical_id("series", {"series_key": series_key, "schema_version": "0.1"})


def entry_id(
    *,
    series: str,
    subject_id: str,
    subject_class: str,
    owner_object_id: str,
    owner_semantic_generation: str,
) -> str:
    return logical_id(
        "entry",
        {
            "series_id": series,
            "subject_id": subject_id,
            "subject_class": subject_class,
            "owner_object_id": owner_object_id,
            "owner_semantic_generation": owner_semantic_generation,
        },
    )


def generation_id(
    *,
    series: str,
    generation_ordinal: int,
    member_entry_ids: Sequence[str],
    source_frontier: str,
) -> str:
    if generation_ordinal < 0:
        raise ValueError("generation_ordinal must be >= 0")
    members = sorted(set(member_entry_ids))
    if len(members) != len(member_entry_ids):
        raise ValueError("member_entry_ids must be unique")
    return logical_id(
        "generation",
        {
            "series_id": series,
            "generation_ordinal": generation_ordinal,
            "member_entry_ids": members,
            "source_frontier_id": source_frontier,
        },
    )


def source_frontier_id(source_bindings: Sequence[Mapping[str, Any]]) -> str:
    normalized = sorted(
        [dict(binding) for binding in source_bindings],
        key=lambda item: (
            str(item.get("owner_programme", "")),
            str(item.get("source_ref", "")),
            str(item.get("semantic_generation", "")),
            str(item.get("source_sha256", "")),
        ),
    )
    return logical_id("frontier", {"source_bindings": normalized})


def control_record_id(
    *, object_type: str, source_frontier: str, identity_payload: Mapping[str, Any]
) -> str:
    return logical_id(
        "control",
        {
            "object_type": object_type,
            "source_frontier_id": source_frontier,
            "identity_payload": dict(identity_payload),
        },
    )
