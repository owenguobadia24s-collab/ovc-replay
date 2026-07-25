from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

from .manifest import EvidenceStoreError


EXTERNAL_ROOT_ENV = "OVC_EXTERNAL_ARTIFACT_ROOT"


def _is_relative_to(path: Path, other: Path) -> bool:
    try:
        path.relative_to(other)
    except ValueError:
        return False
    return True


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor) if path.anchor else Path()
    for part in path.parts[1:] if path.anchor else path.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise EvidenceStoreError(
                f"external artifact root may not traverse a symbolic link: {current}"
            )


def resolve_external_root(
    *,
    repository_root: Path,
    environ: Mapping[str, str] | None = None,
    create: bool = False,
) -> Path:
    """Resolve and validate the operator-local evidence root.

    The absolute path is read from the process environment and is never written
    to repository configuration by this function.
    """

    values = os.environ if environ is None else environ
    raw = values.get(EXTERNAL_ROOT_ENV, "").strip()
    if not raw:
        raise EvidenceStoreError(f"{EXTERNAL_ROOT_ENV} is not set")

    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        raise EvidenceStoreError(f"{EXTERNAL_ROOT_ENV} must be an absolute path")

    _reject_symlink_components(candidate)
    root = candidate.resolve(strict=False)
    repository = repository_root.resolve(strict=True)

    if root == repository or _is_relative_to(root, repository) or _is_relative_to(repository, root):
        raise EvidenceStoreError(
            "external artifact root and repository root must be disjoint directories"
        )

    if create:
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise EvidenceStoreError(f"cannot create external artifact root {root}: {exc}") from exc

    if not root.exists():
        raise EvidenceStoreError(f"external artifact root does not exist: {root}")
    if root.is_symlink() or not root.is_dir():
        raise EvidenceStoreError(f"external artifact root is not a regular directory: {root}")
    return root
