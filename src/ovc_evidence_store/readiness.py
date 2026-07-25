from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any, Callable

from .lifecycle import build_workspace_inventory, load_publication_approval
from .manifest import EvidenceStoreError, load_manifest, remote_keys, verify_local


Runner = Callable[..., subprocess.CompletedProcess[bytes]]
_PROHIBITED_NAMES = {
    ".env",
    ".ds_store",
    "credentials",
    "credentials.json",
    "id_rsa",
    "id_ed25519",
}
_PROHIBITED_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".tmp", ".swp"}


def _run(
    arguments: list[str],
    *,
    runner: Runner,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[bytes] | None:
    try:
        return runner(
            arguments,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return None


def _contains_symlink(root: Path) -> bool:
    try:
        return any(path.is_symlink() for path in root.rglob("*"))
    except OSError:
        return True


def _prohibited_files(root: Path) -> list[str]:
    prohibited: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        name = path.name.casefold()
        if (
            name in _PROHIBITED_NAMES
            or path.suffix.casefold() in _PROHIBITED_SUFFIXES
            or "__pycache__" in path.parts
            or ".git" in path.parts
        ):
            prohibited.append(path.relative_to(root).as_posix())
    return sorted(prohibited)


def _remote_is_configured(remote: str, runner: Runner) -> bool | None:
    result = _run(["rclone", "listremotes"], runner=runner)
    if result is None or result.returncode != 0:
        return None
    names = {
        line.decode("utf-8", errors="replace").strip().removesuffix(":")
        for line in result.stdout.splitlines()
        if line.strip()
    }
    return remote in names


def _remote_collision_status(
    *,
    remote: str,
    keys: list[str],
    runner: Runner,
) -> str:
    not_found_markers = (
        "not found",
        "object not found",
        "directory not found",
        "doesn't exist",
        "does not exist",
    )
    for key in keys:
        result = _run(
            [
                "rclone",
                "lsjson",
                "--stat",
                "--s3-no-check-bucket",
                f"{remote}:{key}",
            ],
            runner=runner,
        )
        if result is None:
            return "NOT_EVALUABLE"
        if result.returncode == 0:
            return "BLOCK"
        error = result.stderr.decode("utf-8", errors="replace").casefold()
        if not any(marker in error for marker in not_found_markers):
            return "NOT_EVALUABLE"
    return "PASS"


def publication_readiness(
    *,
    release_root: Path,
    manifest_path: Path,
    approval_path: Path,
    repository_root: Path,
    remote: str | None = None,
    bucket_lock_visible: bool | None = None,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    """Evaluate publication readiness without mutating local or remote state."""

    checks: dict[str, str] = {
        "release_root": "BLOCK",
        "inventory": "BLOCK",
        "local_hashes": "BLOCK",
        "manifest_schema": "BLOCK",
        "prohibited_files": "BLOCK",
        "symlinks": "BLOCK",
        "duplicate_remote_keys": "BLOCK",
        "source_commit": "BLOCK",
        "git_worktree": "BLOCK",
        "publication_approval": "BLOCK",
        "rclone_remote": "NOT_EVALUABLE",
        "canonical_collision": "NOT_EVALUABLE",
        "bucket_lock_visibility": "NOT_EVALUABLE",
    }
    details: dict[str, Any] = {}
    manifest: dict[str, Any] | None = None

    if release_root.is_dir() and not release_root.is_symlink():
        checks["release_root"] = "PASS"
    else:
        details["release_root"] = "missing or unsafe release directory"

    if checks["release_root"] == "PASS":
        if _contains_symlink(release_root):
            details["symlinks"] = "one or more symbolic links are present"
        else:
            checks["symlinks"] = "PASS"
        prohibited = _prohibited_files(release_root)
        if prohibited:
            details["prohibited_files"] = prohibited
        else:
            checks["prohibited_files"] = "PASS"

    try:
        manifest = load_manifest(manifest_path)
        checks["manifest_schema"] = "PASS"
    except EvidenceStoreError as exc:
        details["manifest_schema"] = str(exc)

    if manifest is not None and checks["release_root"] == "PASS":
        try:
            verify_local(manifest, release_root)
            checks["local_hashes"] = "PASS"
        except EvidenceStoreError as exc:
            details["local_hashes"] = str(exc)

        try:
            actual = build_workspace_inventory(release_root, "readiness-release")["files"]
            if actual == manifest["files"]:
                checks["inventory"] = "PASS"
            else:
                details["inventory"] = "release root contains missing or unmanifested files"
        except EvidenceStoreError as exc:
            details["inventory"] = str(exc)

        manifest_key, file_keys = remote_keys(manifest)
        all_keys = [manifest_key, *file_keys.values()]
        if len(all_keys) == len(set(all_keys)):
            checks["duplicate_remote_keys"] = "PASS"
        else:
            details["duplicate_remote_keys"] = "manifest resolves to duplicate remote keys"

        try:
            load_publication_approval(
                approval_path,
                manifest=manifest,
                manifest_path=manifest_path,
            )
            checks["publication_approval"] = "PASS"
        except EvidenceStoreError as exc:
            details["publication_approval"] = str(exc)

        head = _run(["git", "rev-parse", "HEAD"], runner=runner, cwd=repository_root)
        if head is None or head.returncode != 0:
            details["source_commit"] = "Git HEAD is not evaluable"
        else:
            current = head.stdout.decode("ascii", errors="replace").strip()
            if current == manifest["repository_commit"]:
                checks["source_commit"] = "PASS"
            else:
                details["source_commit"] = {
                    "expected": manifest["repository_commit"],
                    "actual": current,
                }

        status = _run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            runner=runner,
            cwd=repository_root,
        )
        if status is None or status.returncode != 0:
            details["git_worktree"] = "Git worktree state is not evaluable"
        elif status.stdout.strip():
            details["git_worktree"] = status.stdout.decode("utf-8", errors="replace").splitlines()
        else:
            checks["git_worktree"] = "PASS"

        if remote:
            configured = _remote_is_configured(remote, runner)
            if configured is True:
                checks["rclone_remote"] = "PASS"
                checks["canonical_collision"] = _remote_collision_status(
                    remote=remote,
                    keys=all_keys,
                    runner=runner,
                )
                if checks["canonical_collision"] != "PASS":
                    details["canonical_collision"] = (
                        "one or more exact keys already exist"
                        if checks["canonical_collision"] == "BLOCK"
                        else "remote key absence could not be established"
                    )
            elif configured is False:
                details["rclone_remote"] = f"rclone remote is not configured: {remote}"
            else:
                details["rclone_remote"] = "rclone configuration is not evaluable"
        else:
            details["rclone_remote"] = "no remote requested"
            details["canonical_collision"] = "remote collision check not requested"

    if bucket_lock_visible is True:
        checks["bucket_lock_visibility"] = "PASS"
    elif bucket_lock_visible is False:
        checks["bucket_lock_visibility"] = "WARN"
        details["bucket_lock_visibility"] = "canonical lock was reported as not visible"
    else:
        details["bucket_lock_visibility"] = "bucket lock visibility not supplied"

    values = set(checks.values())
    if "BLOCK" in values:
        overall = "BLOCKED"
    elif "NOT_EVALUABLE" in values:
        overall = "NOT_EVALUABLE"
    else:
        overall = "READY"

    return {
        "schema": "ovc-evidence-publication-readiness/v1",
        "overall_status": overall,
        "checks": checks,
        "details": details,
        "side_effects_performed": False,
    }
