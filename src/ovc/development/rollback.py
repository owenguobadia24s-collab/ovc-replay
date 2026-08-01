"""Non-destructive rollback records for development-tooling changes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .identity import canonical_sha256, normalize_relative_path


@dataclass(frozen=True)
class RollbackRecord:
    programme_id: str
    packet_id: str
    target_commit: str
    method: str
    preserved_artifacts: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    rationale: str

    def __post_init__(self) -> None:
        if self.method not in {"REVERT_COMMIT", "DISABLE_PROFILE", "RESTORE_SELECTOR_REFERENCE_ONLY"}:
            raise ValueError("unsupported rollback method")
        if not self.preserved_artifacts or not self.prohibited_actions or not self.rationale:
            raise ValueError("rollback preservation, prohibitions and rationale are required")
        for path in self.preserved_artifacts:
            normalize_relative_path(path)
        forbidden = {"DELETE_HISTORY", "FORCE_PUSH", "REWRITE_ACCEPTED_ARTIFACT"}
        if not forbidden.issubset(set(self.prohibited_actions)):
            raise ValueError("rollback must prohibit destructive history and artifact changes")

    @property
    def rollback_id(self) -> str:
        return canonical_sha256(asdict(self), role="ROLLBACK_RECORD")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["rollback_id"] = self.rollback_id
        return result
