from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import PipelineProfile, StageSpec


class RegistryError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


@dataclass(frozen=True)
class RegistrySnapshot:
    stage_specs: tuple[StageSpec, ...]
    profiles: tuple[PipelineProfile, ...]

    def stage_by_id(self) -> dict[str, StageSpec]:
        return {item.stage_id: item for item in self.stage_specs}

    def profile_by_id(self) -> dict[str, PipelineProfile]:
        return {item.profile_id: item for item in self.profiles}


def _assert_unique(values: Iterable[str], *, kind: str) -> None:
    items = tuple(values)
    if len(items) != len(set(items)):
        raise RegistryError(f"IROF_DUPLICATE_{kind.upper()}_ID", f"duplicate {kind} identity")


def build_registry_snapshot(*, stage_specs: Iterable[StageSpec], profiles: Iterable[PipelineProfile]) -> RegistrySnapshot:
    stages = tuple(sorted(stage_specs, key=lambda item: item.stage_id))
    profile_values = tuple(sorted(profiles, key=lambda item: item.profile_id))
    _assert_unique((item.stage_id for item in stages), kind="stage")
    _assert_unique((item.profile_id for item in profile_values), kind="profile")
    stage_ids = {item.stage_id for item in stages}
    for profile in profile_values:
        missing = sorted(set(profile.included_stage_ids) - stage_ids)
        if missing:
            raise RegistryError("IROF_PROFILE_UNKNOWN_STAGE", f"{profile.profile_id}:{','.join(missing)}")
    return RegistrySnapshot(stages, profile_values)
