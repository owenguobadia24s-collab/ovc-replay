from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
from typing import Iterable, Sequence

HARNESS_IDENTITY_VERSION = "ovc-aa0-assurance-harness/v1"
DEFAULT_PATHSPECS: tuple[str, ...] = (
    ".github/workflows/tests.yml",
    "pyproject.toml",
    "requirements-console-vnext.txt",
    "registries/implementation/ci_performance/CIPR_POST_PYT_PYTEST_SHARD_CANONICAL_POLICY_v0_1.json",
    "tools/ci/aa0_harness_identity.py",
    "tools/ci/pytest_unittest_parity.py",
    "tools/ci/pytest_shard_shadow.py",
    "tools/ci/pytest_shard_canonical.py",
    "tests/**",
)


class HarnessIdentityError(ValueError):
    """Raised when the AA0 assurance harness cannot receive a stable identity."""


def _git(root: Path, args: Sequence[str]) -> bytes:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip()
        raise HarnessIdentityError(f"git command failed: {detail}") from exc
    return proc.stdout


def _tracked_matches(root: Path, pathspec: str) -> tuple[str, ...]:
    raw = _git(root, ["ls-files", "-z", "--", pathspec])
    matches = tuple(sorted(item for item in raw.decode("utf-8").split("\0") if item))
    if not matches:
        raise HarnessIdentityError(f"AA0_HARNESS_REQUIRED_INPUT_MISSING:{pathspec}")
    return matches


def tracked_harness_files(
    root: str | Path,
    pathspecs: Iterable[str] = DEFAULT_PATHSPECS,
) -> tuple[str, ...]:
    repo = Path(root).resolve()
    if not (repo / ".git").exists():
        raise HarnessIdentityError("AA0_HARNESS_GIT_ROOT_REQUIRED")
    resolved: set[str] = set()
    for pathspec in tuple(pathspecs):
        if not pathspec or pathspec.startswith("/") or ".." in Path(pathspec).parts:
            raise HarnessIdentityError(f"AA0_HARNESS_PATHSPEC_INVALID:{pathspec}")
        resolved.update(_tracked_matches(repo, pathspec))
    files = tuple(sorted(resolved))
    for relative in files:
        path = repo / relative
        if not path.is_file():
            raise HarnessIdentityError(f"AA0_HARNESS_TRACKED_INPUT_NOT_FILE:{relative}")
    return files


def compute_harness_identity(
    root: str | Path,
    pathspecs: Iterable[str] = DEFAULT_PATHSPECS,
) -> str:
    """Hash the tracked AA0 assurance harness once, independent of Git placement.

    Identity depends only on the versioned path inventory and file bytes. Commit SHA,
    branch name, physical-main SHA/tree, VIT generation and filesystem metadata are
    deliberately excluded.
    """
    repo = Path(root).resolve()
    files = tracked_harness_files(repo, pathspecs)
    digest = hashlib.sha256()
    digest.update(HARNESS_IDENTITY_VERSION.encode("utf-8") + b"\0")
    for relative in files:
        encoded_path = relative.encode("utf-8")
        content = (repo / relative).read_bytes()
        content_digest = hashlib.sha256(content).digest()
        digest.update(len(encoded_path).to_bytes(4, "big"))
        digest.update(encoded_path)
        digest.update(content_digest)
    return digest.hexdigest()


def main() -> int:
    root = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
    identity = compute_harness_identity(root)
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as handle:
            handle.write(f"harness_hash={identity}\n")
    print(f"OVC_AA0_HARNESS_IDENTITY={identity}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
