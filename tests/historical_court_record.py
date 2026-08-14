"""Read immutable historical repository objects for succession-sensitive tests."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _repository_path(path: str | Path) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        candidate = candidate.resolve().relative_to(ROOT)
    return candidate.as_posix()


def text_at(commit: str, path: str | Path) -> str:
    """Return an exact file blob from a fully fetched historical commit."""
    relative = _repository_path(path)
    return subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout


def json_at(commit: str, path: str | Path) -> Any:
    return json.loads(text_at(commit, path))


def names_at(commit: str, directory: str | Path) -> set[str]:
    """Return direct child names in a historical Git tree."""
    relative = _repository_path(directory)
    treeish = commit if relative == "." else f"{commit}:{relative}"
    output = subprocess.run(
        ["git", "ls-tree", "--name-only", treeish],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout
    return {line for line in output.splitlines() if line}
