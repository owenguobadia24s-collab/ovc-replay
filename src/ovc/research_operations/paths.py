from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .config import ResearchOperationsConfig


class PathPolicyError(ValueError):
    pass


class UnsafePathError(PathPolicyError):
    pass


@dataclass(frozen=True)
class ApprovedRoot:
    alias: str
    path: Path
    read_only: bool
    required: bool


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


class ApprovedPathRegistry:
    def __init__(self, roots: Iterable[ApprovedRoot]):
        self._roots = {root.alias: root for root in roots}
        if len(self._roots) != len(list(roots)):
            raise PathPolicyError("duplicate root alias")

    @classmethod
    def from_json(cls, registry_path: str | Path, config: ResearchOperationsConfig) -> "ApprovedPathRegistry":
        data = json.loads(Path(registry_path).read_text(encoding="utf-8"))
        values = config.template_values()
        roots: list[ApprovedRoot] = []
        for item in data.get("roots", []):
            template = str(item["path_template"])
            resolved: Path | None = None
            for key, value in values.items():
                token = "${" + key + "}"
                if template == token:
                    resolved = value
                    break
                if template.startswith(token + "/"):
                    if value is not None:
                        resolved = value / template[len(token) + 1 :]
                    break
            required = bool(item.get("required", True))
            if resolved is None:
                if required:
                    raise PathPolicyError(f"unresolved required path template: {template}")
                continue
            roots.append(
                ApprovedRoot(
                    alias=str(item["alias"]),
                    path=resolved.resolve(strict=False),
                    read_only=bool(item.get("read_only", True)),
                    required=required,
                )
            )
        return cls(roots)

    def aliases(self) -> tuple[str, ...]:
        return tuple(sorted(self._roots))

    def root(self, alias: str) -> ApprovedRoot:
        try:
            return self._roots[alias]
        except KeyError as exc:
            raise PathPolicyError(f"unapproved root alias: {alias}") from exc

    def resolve(
        self,
        alias: str,
        relative_path: str | Path = ".",
        *,
        for_write: bool = False,
        must_exist: bool = False,
    ) -> Path:
        root = self.root(alias)
        rel = Path(relative_path)
        if rel.is_absolute() or any(part == ".." for part in rel.parts):
            raise UnsafePathError(f"path traversal or absolute path denied: {relative_path}")
        if for_write and root.read_only:
            raise PathPolicyError(f"write denied for read-only root: {alias}")
        candidate = (root.path / rel).resolve(strict=False)
        if not _is_within(candidate, root.path):
            raise UnsafePathError(f"path escapes approved root: {relative_path}")
        self._reject_symlink_components(root.path, candidate)
        if must_exist and not candidate.exists():
            raise FileNotFoundError(candidate)
        return candidate

    @staticmethod
    def _reject_symlink_components(root: Path, candidate: Path) -> None:
        current = root
        if current.exists() and current.is_symlink():
            raise UnsafePathError(f"approved root is a symlink: {root}")
        try:
            rel = candidate.relative_to(root)
        except ValueError as exc:
            raise UnsafePathError(f"candidate is outside root: {candidate}") from exc
        for part in rel.parts:
            current = current / part
            if current.exists() and current.is_symlink():
                raise UnsafePathError(f"symlink denied: {current}")

    def safe_files(self, alias: str) -> list[Path]:
        root = self.root(alias)
        if not root.path.exists():
            if root.required:
                raise FileNotFoundError(root.path)
            return []
        files: list[Path] = []
        for path in sorted(root.path.rglob("*"), key=lambda item: item.as_posix()):
            if path.is_symlink():
                raise UnsafePathError(f"symlink denied: {path}")
            if path.is_file():
                self.resolve(alias, path.relative_to(root.path), must_exist=True)
                files.append(path)
        return files

    def portable_location(self, alias: str, path: Path) -> dict[str, str]:
        root = self.root(alias)
        resolved = path.resolve(strict=False)
        if not _is_within(resolved, root.path):
            raise UnsafePathError(f"path outside approved root: {path}")
        return {"root_alias": alias, "relative_path": resolved.relative_to(root.path).as_posix()}
