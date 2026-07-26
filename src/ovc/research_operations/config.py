from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class ConfigurationError(ValueError):
    pass


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class ResearchOperationsConfig:
    repository_root: Path
    record_root: Path
    runtime_root: Path
    external_artifact_root: Path | None
    operator_id: str

    @classmethod
    def from_environment(
        cls,
        *,
        repository_root: str | Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> "ResearchOperationsConfig":
        source = dict(os.environ if env is None else env)
        repo = _resolved(repository_root or source.get("OVC_REPOSITORY_ROOT") or Path.cwd())
        record_root = _resolved(source.get("OVC_RESEARCH_RECORD_ROOT") or repo / "records" / "research_operations")
        runtime_root = _resolved(source.get("OVC_RESEARCH_RUNTIME_ROOT") or repo / "var" / "research_operations")
        external_raw = source.get("OVC_EXTERNAL_ARTIFACT_ROOT")
        external = _resolved(external_raw) if external_raw else None
        operator_id = source.get("OVC_RESEARCH_OPERATOR_ID", "local-operator").strip()
        if not operator_id:
            raise ConfigurationError("OVC_RESEARCH_OPERATOR_ID must not be empty")
        if external is not None and _is_within(external, repo):
            raise ConfigurationError("OVC_EXTERNAL_ARTIFACT_ROOT must resolve outside the repository")
        return cls(repo, record_root, runtime_root, external, operator_id)

    def template_values(self) -> dict[str, Path | None]:
        return {
            "REPO_ROOT": self.repository_root,
            "RECORD_ROOT": self.record_root,
            "RUNTIME_ROOT": self.runtime_root,
            "EXTERNAL_ROOT": self.external_artifact_root,
        }
