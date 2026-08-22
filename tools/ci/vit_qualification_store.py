from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Callable, Mapping
import urllib.error
import urllib.parse
import urllib.request

from ovc.development.skills.vit_routing import validate_vit_lineage_record

LEDGER_BRANCH = "ovc/vit-qualification-ledger-v1"
LEDGER_ROOT = ".ovc/vit-qualifications"
ENVELOPE_SCHEMA = "ovc-vit-qualification-envelope/v0.1"
POINTER_SCHEMA = "ovc-vit-qualification-head-pointer/v0.1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ResolvedQualificationEnvelope:
    record: Mapping[str, Any]
    qualification_id: str
    candidate_head_sha: str
    candidate_head_tree: str
    pip_id: str
    authority_manifest_id: str
    dependency_frontier_id: str


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _decode_canonical_json(raw: bytes, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"{label}_INVALID_JSON:{exc}") from exc
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label}_INVALID_OBJECT")
    if raw != _canonical_json_bytes(value):
        raise RuntimeError(f"{label}_NOT_CANONICAL_JSON")
    return value


def _git_tree(root: Path, commit: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"{commit}^{{tree}}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "VIT_QUALIFICATION_HEAD_TREE_RESOLUTION_FAILED")
    tree = proc.stdout.strip()
    if not SHA40.fullmatch(tree):
        raise RuntimeError("VIT_QUALIFICATION_HEAD_TREE_INVALID")
    return tree


def build_qualification_envelope(
    *,
    root: Path,
    head_sha: str,
    lineage_record: Mapping[str, Any],
) -> Mapping[str, Any]:
    if not SHA40.fullmatch(head_sha):
        raise RuntimeError("VIT_QUALIFICATION_HEAD_SHA_INVALID")
    lineage = validate_vit_lineage_record(lineage_record)
    if not lineage.late_binding:
        raise RuntimeError("VIT_QUALIFICATION_REQUIRES_LATE_BINDING_LINEAGE")
    pip = lineage_record.get("pip")
    if not isinstance(pip, Mapping):
        raise RuntimeError("VIT_QUALIFICATION_PIP_INVALID")
    authority = str(pip.get("authority_manifest_id", "")).strip()
    frontier = str(pip.get("dependency_frontier_id", "")).strip()
    if not SHA64.fullmatch(authority) or not SHA64.fullmatch(frontier):
        raise RuntimeError("VIT_QUALIFICATION_FRONTIER_INVALID")
    payload = {
        "schema_version": ENVELOPE_SCHEMA,
        "candidate_head_sha": head_sha,
        "candidate_head_tree": _git_tree(root, head_sha),
        "pip_id": lineage.pip_id,
        "authority_manifest_id": authority,
        "dependency_frontier_id": frontier,
        "lineage": dict(lineage_record),
    }
    return {**payload, "qualification_id": _canonical_sha256(payload)}


def validate_qualification_envelope(
    envelope: Mapping[str, Any],
    *,
    expected_head_sha: str | None = None,
    expected_head_tree: str | None = None,
) -> ResolvedQualificationEnvelope:
    if str(envelope.get("schema_version", "")) != ENVELOPE_SCHEMA:
        raise RuntimeError("VIT_QUALIFICATION_SCHEMA_INVALID")
    qualification_id = str(envelope.get("qualification_id", "")).strip()
    if not SHA64.fullmatch(qualification_id):
        raise RuntimeError("VIT_QUALIFICATION_ID_INVALID")
    identity_payload = {key: value for key, value in envelope.items() if key != "qualification_id"}
    if _canonical_sha256(identity_payload) != qualification_id:
        raise RuntimeError("VIT_QUALIFICATION_ID_MISMATCH")

    head_sha = str(envelope.get("candidate_head_sha", "")).strip()
    head_tree = str(envelope.get("candidate_head_tree", "")).strip()
    if not SHA40.fullmatch(head_sha) or not SHA40.fullmatch(head_tree):
        raise RuntimeError("VIT_QUALIFICATION_HEAD_IDENTITY_INVALID")
    if expected_head_sha is not None and head_sha != expected_head_sha:
        raise RuntimeError("VIT_QUALIFICATION_HEAD_SHA_MISMATCH")
    if expected_head_tree is not None and head_tree != expected_head_tree:
        raise RuntimeError("VIT_QUALIFICATION_HEAD_TREE_MISMATCH")

    record = envelope.get("lineage")
    if not isinstance(record, Mapping):
        raise RuntimeError("VIT_QUALIFICATION_LINEAGE_INVALID")
    lineage = validate_vit_lineage_record(record)
    if not lineage.late_binding:
        raise RuntimeError("VIT_QUALIFICATION_REQUIRES_LATE_BINDING_LINEAGE")
    pip = record.get("pip")
    if not isinstance(pip, Mapping):
        raise RuntimeError("VIT_QUALIFICATION_PIP_INVALID")
    authority = str(pip.get("authority_manifest_id", "")).strip()
    frontier = str(pip.get("dependency_frontier_id", "")).strip()
    if lineage.pip_id != str(envelope.get("pip_id", "")):
        raise RuntimeError("VIT_QUALIFICATION_PIP_ID_MISMATCH")
    if authority != str(envelope.get("authority_manifest_id", "")):
        raise RuntimeError("VIT_QUALIFICATION_AUTHORITY_ID_MISMATCH")
    if frontier != str(envelope.get("dependency_frontier_id", "")):
        raise RuntimeError("VIT_QUALIFICATION_FRONTIER_ID_MISMATCH")
    if not SHA64.fullmatch(authority) or not SHA64.fullmatch(frontier):
        raise RuntimeError("VIT_QUALIFICATION_FRONTIER_INVALID")

    return ResolvedQualificationEnvelope(
        record=dict(record),
        qualification_id=qualification_id,
        candidate_head_sha=head_sha,
        candidate_head_tree=head_tree,
        pip_id=lineage.pip_id,
        authority_manifest_id=authority,
        dependency_frontier_id=frontier,
    )


def _repo_from_env() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not repo or "/" not in repo:
        raise RuntimeError("VIT_QUALIFICATION_REPOSITORY_CONTEXT_MISSING")
    return repo


def _headers(*, write: bool = False) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ovc-vit-qualification-ledger/1",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif write:
        raise RuntimeError("VIT_QUALIFICATION_WRITE_TOKEN_MISSING")
    return headers


def _contents_url(path: str) -> str:
    owner, repo = _repo_from_env().split("/", 1)
    encoded = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
    query = urllib.parse.urlencode({"ref": LEDGER_BRANCH})
    return f"https://api.github.com/repos/{owner}/{repo}/contents/{encoded}?{query}"


def _fetch_ledger_file(path: str) -> tuple[bytes, str] | None:
    request = urllib.request.Request(_contents_url(path), headers=_headers(), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            value = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise RuntimeError(f"VIT_QUALIFICATION_LEDGER_FETCH_FAILED:{exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"VIT_QUALIFICATION_LEDGER_FETCH_FAILED:{exc}") from exc
    if not isinstance(value, Mapping) or str(value.get("encoding", "")) != "base64":
        raise RuntimeError("VIT_QUALIFICATION_LEDGER_PAYLOAD_INVALID")
    try:
        raw = base64.b64decode(str(value.get("content", "")).encode("ascii"), validate=False)
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError("VIT_QUALIFICATION_LEDGER_CONTENT_INVALID") from exc
    return raw, str(value.get("sha", ""))


def _pointer_path(head_sha: str) -> str:
    return f"{LEDGER_ROOT}/heads/{head_sha}.json"


def _envelope_path(qualification_id: str) -> str:
    return f"{LEDGER_ROOT}/envelopes/{qualification_id}.json"


def resolve_qualification_envelope(
    *,
    root: Path,
    head_sha: str,
    fetch_file: Callable[[str], bytes | None] | None = None,
) -> ResolvedQualificationEnvelope | None:
    if not SHA40.fullmatch(head_sha):
        raise RuntimeError("VIT_QUALIFICATION_HEAD_SHA_INVALID")
    local_tree = _git_tree(root, head_sha)

    def read(path: str) -> bytes | None:
        if fetch_file is not None:
            return fetch_file(path)
        fetched = _fetch_ledger_file(path)
        return None if fetched is None else fetched[0]

    pointer_raw = read(_pointer_path(head_sha))
    if pointer_raw is None:
        return None
    pointer = _decode_canonical_json(pointer_raw, "VIT_QUALIFICATION_POINTER")
    if str(pointer.get("schema_version", "")) != POINTER_SCHEMA:
        raise RuntimeError("VIT_QUALIFICATION_POINTER_SCHEMA_INVALID")
    if str(pointer.get("candidate_head_sha", "")) != head_sha:
        raise RuntimeError("VIT_QUALIFICATION_POINTER_HEAD_MISMATCH")
    qualification_id = str(pointer.get("qualification_id", "")).strip()
    if not SHA64.fullmatch(qualification_id):
        raise RuntimeError("VIT_QUALIFICATION_POINTER_ID_INVALID")

    envelope_raw = read(_envelope_path(qualification_id))
    if envelope_raw is None:
        raise RuntimeError("VIT_QUALIFICATION_ENVELOPE_MISSING")
    envelope = _decode_canonical_json(envelope_raw, "VIT_QUALIFICATION_ENVELOPE")
    resolved = validate_qualification_envelope(
        envelope,
        expected_head_sha=head_sha,
        expected_head_tree=local_tree,
    )
    if resolved.qualification_id != qualification_id:
        raise RuntimeError("VIT_QUALIFICATION_POINTER_ENVELOPE_MISMATCH")
    return resolved


def _put_ledger_file(path: str, raw: bytes, *, message: str, existing_sha: str | None = None) -> Mapping[str, Any]:
    url = _contents_url(path).split("?", 1)[0]
    body: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(raw).decode("ascii"),
        "branch": LEDGER_BRANCH,
    }
    if existing_sha:
        body["sha"] = existing_sha
    request = urllib.request.Request(
        url,
        data=json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        headers={**_headers(write=True), "Content-Type": "application/json"},
        method="PUT",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            value = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"VIT_QUALIFICATION_LEDGER_WRITE_FAILED:{exc.code}:{detail}") from exc
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"VIT_QUALIFICATION_LEDGER_WRITE_FAILED:{exc}") from exc
    if not isinstance(value, Mapping):
        raise RuntimeError("VIT_QUALIFICATION_LEDGER_WRITE_RESPONSE_INVALID")
    return value


def publish_qualification_envelope(
    envelope: Mapping[str, Any],
    *,
    replace_head_binding: bool = False,
) -> str:
    resolved = validate_qualification_envelope(envelope)
    envelope_raw = _canonical_json_bytes(envelope)
    envelope_path = _envelope_path(resolved.qualification_id)
    existing_envelope = _fetch_ledger_file(envelope_path)
    if existing_envelope is None:
        _put_ledger_file(
            envelope_path,
            envelope_raw,
            message=f"VIT qualification envelope {resolved.qualification_id}",
        )
    elif existing_envelope[0] != envelope_raw:
        raise RuntimeError("VIT_QUALIFICATION_CONTENT_ADDRESS_COLLISION")

    pointer = {
        "schema_version": POINTER_SCHEMA,
        "candidate_head_sha": resolved.candidate_head_sha,
        "qualification_id": resolved.qualification_id,
    }
    pointer_raw = _canonical_json_bytes(pointer)
    pointer_path = _pointer_path(resolved.candidate_head_sha)
    existing_pointer = _fetch_ledger_file(pointer_path)
    if existing_pointer is not None:
        current = _decode_canonical_json(existing_pointer[0], "VIT_QUALIFICATION_POINTER")
        current_id = str(current.get("qualification_id", ""))
        if current_id == resolved.qualification_id:
            return resolved.qualification_id
        if not replace_head_binding:
            raise RuntimeError(f"VIT_QUALIFICATION_HEAD_ALREADY_BOUND:{current_id}")
        pointer_sha = existing_pointer[1]
    else:
        pointer_sha = None

    _put_ledger_file(
        pointer_path,
        pointer_raw,
        existing_sha=pointer_sha,
        message=f"VIT qualification bind {resolved.candidate_head_sha} -> {resolved.qualification_id}",
    )
    return resolved.qualification_id
