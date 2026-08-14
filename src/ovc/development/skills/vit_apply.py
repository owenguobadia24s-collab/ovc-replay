from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence
import hashlib
import os
import subprocess
import tempfile

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_core import AuthorizedMainWriter, PacketIntegrationPayload, VitContractError

REFERENCE_APPLY_PROFILE = "INTEGRATION_APPLY_PROFILE_REFERENCE_v0_1"

@dataclass(frozen=True)
class CompositionFailure:
    reason_code: str
    path: str | None = None
    detail: str | None = None

@dataclass(frozen=True)
class CompositionReceipt:
    predecessor_tree: str
    payload_id: str
    apply_profile: str
    result_tree: str | None
    changed_paths: tuple[str, ...]
    failures: tuple[CompositionFailure, ...]

    @property
    def receipt_id(self) -> str:
        return canonical_sha256(asdict(self))

    @property
    def disposition(self) -> str:
        if self.failures:
            return "COMPOSITION_FAILED"
        if self.result_tree == self.predecessor_tree:
            return "NO_REPOSITORY_DELTA"
        return "COMPOSED"

@dataclass(frozen=True)
class AuthorizedExternalMainAdvanceReceipt:
    writer_identity: str
    authority_source: str
    predecessor_commit: str
    predecessor_tree: str
    result_commit: str
    result_tree: str
    operation_class: str
    related_refs: tuple[str, ...] = ()
    issued_at: str = ""
    integrity: str = ""

    @property
    def advance_receipt_id(self) -> str:
        return canonical_sha256(asdict(self))


def _safe_path(path: str) -> str:
    p = PurePosixPath(path)
    if not path or p.is_absolute() or ".." in p.parts or path.startswith(".git/") or path == ".git":
        raise VitContractError("INPUT_PRECONDITION_MISMATCH")
    return p.as_posix()


def _run_git(repo: Path, args: Sequence[str], *, env: Mapping[str, str] | None = None) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(os.environ, **(dict(env or {}))))
    return proc.stdout.strip()


def tree_content_diagnostic_fingerprint(repo: str | Path, treeish: str) -> str:
    repo = Path(repo)
    raw = subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", "-z", treeish], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
    return hashlib.sha256(raw).hexdigest()


def apply_payload_reference(repo: str | Path, predecessor_tree: str, payload: PacketIntegrationPayload) -> CompositionReceipt:
    repo = Path(repo)
    failures: list[CompositionFailure] = []
    changed: list[str] = []
    seen: set[str] = set()
    with tempfile.TemporaryDirectory() as td:
        index = str(Path(td) / "index")
        env = {"GIT_INDEX_FILE": index}
        try:
            _run_git(repo, ["read-tree", predecessor_tree], env=env)
        except subprocess.CalledProcessError as exc:
            return CompositionReceipt(predecessor_tree, payload.payload_id, REFERENCE_APPLY_PROFILE, None, (), (CompositionFailure("INPUT_PRECONDITION_MISMATCH", detail=str(exc)),))
        for change in payload.logical_changes:
            try:
                path = _safe_path(str(change.get("path", "")))
            except VitContractError:
                failures.append(CompositionFailure("INPUT_PRECONDITION_MISMATCH", str(change.get("path", "")), "unsafe path"))
                continue
            if path in seen:
                failures.append(CompositionFailure("CONTENT_CONFLICT", path, "duplicate path mutation"))
                continue
            seen.add(path)
            op = change.get("op")
            if op == "DELETE":
                try:
                    _run_git(repo, ["update-index", "--force-remove", "--", path], env=env)
                except subprocess.CalledProcessError as exc:
                    failures.append(CompositionFailure("INPUT_PRECONDITION_MISMATCH", path, str(exc)))
                    continue
                changed.append(path)
            elif op in {"ADD", "MODIFY"}:
                blob_sha = str(change.get("blob_sha", ""))
                mode = str(change.get("mode", "100644"))
                if not blob_sha or mode not in {"100644", "100755", "120000", "160000"}:
                    failures.append(CompositionFailure("INPUT_PRECONDITION_MISMATCH", path, "missing blob or invalid mode"))
                    continue
                try:
                    _run_git(repo, ["cat-file", "-e", f"{blob_sha}^{{blob}}"] if mode != "160000" else ["cat-file", "-e", f"{blob_sha}^{{commit}}"])
                    _run_git(repo, ["update-index", "--add", "--cacheinfo", mode, blob_sha, path], env=env)
                except subprocess.CalledProcessError as exc:
                    failures.append(CompositionFailure("INPUT_PRECONDITION_MISMATCH", path, str(exc)))
                    continue
                changed.append(path)
            else:
                failures.append(CompositionFailure("INPUT_PRECONDITION_MISMATCH", path, "unknown op"))
        if failures:
            return CompositionReceipt(predecessor_tree, payload.payload_id, REFERENCE_APPLY_PROFILE, None, tuple(sorted(changed)), tuple(failures))
        result = _run_git(repo, ["write-tree"], env=env)
        return CompositionReceipt(predecessor_tree, payload.payload_id, REFERENCE_APPLY_PROFILE, result, tuple(sorted(changed)), ())


def validate_external_main_advance(receipt: AuthorizedExternalMainAdvanceReceipt, writers: Sequence[AuthorizedMainWriter], current_commit: str, current_tree: str) -> str:
    matches = [w for w in writers if w.writer_identity == receipt.writer_identity and w.active]
    if len(matches) != 1:
        return "REPOSITORY_INTEGRITY_INCIDENT"
    writer = matches[0]
    if receipt.operation_class not in writer.operation_classes:
        return "REPOSITORY_INTEGRITY_INCIDENT"
    if receipt.authority_source not in writer.authority_sources:
        return "REPOSITORY_INTEGRITY_INCIDENT"
    if receipt.predecessor_commit != current_commit or receipt.predecessor_tree != current_tree:
        return "REPOSITORY_INTEGRITY_INCIDENT"
    if not receipt.result_commit or not receipt.result_tree or not receipt.integrity:
        return "REPOSITORY_INTEGRITY_INCIDENT"
    return "EXTERNAL_MAIN_REANCHOR"
