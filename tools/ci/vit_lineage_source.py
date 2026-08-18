from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import json
import os
import re
from typing import Any, Mapping
import urllib.error
import urllib.request

LINEAGE_BLOB_MARKER = re.compile(r"(?im)^VIT-Lineage-Blob:\s*([0-9a-f]{40})\s*$")
LINEAGE_B64_MARKER = re.compile(r"(?im)^VIT-Lineage-B64:\s*([A-Za-z0-9_\-=]+)\s*$")


@dataclass(frozen=True)
class ResolvedLineageSource:
    record: Mapping[str, Any]
    source: str
    immutable_ref: str
    content_sha256: str


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _decode_json_bytes(raw: bytes, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"{label}_INVALID_JSON:{exc}") from exc
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label}_INVALID_OBJECT")
    return value


def _repo_from_env() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not repo or "/" not in repo:
        raise RuntimeError("VIT_LINEAGE_REPOSITORY_CONTEXT_MISSING")
    return repo


def _fetch_git_blob(blob_sha: str) -> bytes:
    repo = _repo_from_env()
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ovc-vit-lineage-source/1",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/git/blobs/{blob_sha}",
        headers=headers,
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"VIT_LINEAGE_BLOB_FETCH_FAILED:{exc}") from exc
    if not isinstance(value, Mapping):
        raise RuntimeError("VIT_LINEAGE_BLOB_PAYLOAD_INVALID")
    observed_sha = str(value.get("sha", "")).strip()
    if observed_sha != blob_sha:
        raise RuntimeError("VIT_LINEAGE_BLOB_SHA_MISMATCH")
    if str(value.get("encoding", "")).strip() != "base64":
        raise RuntimeError("VIT_LINEAGE_BLOB_ENCODING_UNSUPPORTED")
    try:
        return base64.b64decode(str(value.get("content", "")).encode("ascii"), validate=False)
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError("VIT_LINEAGE_BLOB_CONTENT_INVALID") from exc


def _decode_legacy(token: str) -> bytes:
    token += "=" * ((4 - len(token) % 4) % 4)
    try:
        return base64.urlsafe_b64decode(token.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError(f"VIT_LINEAGE_INVALID_ENCODING:{exc}") from exc


def resolve_lineage_source(
    body: str,
    *,
    require: bool = True,
    fetch_blob: callable | None = None,
) -> ResolvedLineageSource | None:
    blob_match = LINEAGE_BLOB_MARKER.search(body)
    b64_match = LINEAGE_B64_MARKER.search(body)
    if blob_match and b64_match:
        raise RuntimeError("VIT_LINEAGE_MULTIPLE_SOURCES")
    if not blob_match and not b64_match:
        if require:
            raise RuntimeError(
                "VIT_LINEAGE_REQUIRED: add `VIT-Lineage-Blob: <git-blob-sha>` "
                "or legacy `VIT-Lineage-B64: <urlsafe-base64-canonical-lineage-json>` to the PR body"
            )
        return None

    if blob_match:
        blob_sha = blob_match.group(1)
        raw = (fetch_blob or _fetch_git_blob)(blob_sha)
        record = _decode_json_bytes(raw, "VIT_LINEAGE_BLOB")
        canonical = _canonical_json_bytes(record)
        if raw != canonical:
            raise RuntimeError("VIT_LINEAGE_BLOB_NOT_CANONICAL_JSON")
        return ResolvedLineageSource(
            record=record,
            source="IMMUTABLE_GIT_BLOB",
            immutable_ref=blob_sha,
            content_sha256=hashlib.sha256(raw).hexdigest(),
        )

    raw = _decode_legacy(b64_match.group(1))
    record = _decode_json_bytes(raw, "VIT_LINEAGE")
    return ResolvedLineageSource(
        record=record,
        source="LEGACY_INLINE_B64",
        immutable_ref=hashlib.sha256(raw).hexdigest(),
        content_sha256=hashlib.sha256(raw).hexdigest(),
    )
