from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from ovc.development.skills.async_assurance import (
    AssuranceCompletionSignal,
    AssuranceFuture,
    apply_completion_signal,
)

GITHUB_PROVIDER_ADAPTER_ID = "GITHUB_ACTIONS_READ_ONLY_v1"
TERMINAL_STATUS = "completed"


@dataclass(frozen=True)
class GitHubAssuranceObservation:
    repository: str
    candidate_commit: str
    workflow_name: str
    run_id: str
    check_name: str
    status: str
    conclusion: str | None
    observed_at: str
    provider_adapter_id: str = GITHUB_PROVIDER_ADAPTER_ID

    def __post_init__(self) -> None:
        for value in (
            self.repository, self.candidate_commit, self.workflow_name,
            self.run_id, self.check_name, self.status, self.observed_at,
        ):
            if not value:
                raise ValueError("GitHub observation exact binding fields are required")
        if self.provider_adapter_id != GITHUB_PROVIDER_ADAPTER_ID:
            raise ValueError("unrecognized GitHub provider adapter")

    @property
    def observation_key(self) -> tuple[str, ...]:
        return (
            self.repository,
            self.candidate_commit,
            self.workflow_name,
            self.run_id,
            self.check_name,
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "schema": "ovc-dsai3v-github-assurance-observation/v1",
            **asdict(self),
            "authority_effect": "NONE",
        }


def provider_capabilities() -> dict[str, Any]:
    return {
        "provider_adapter_id": GITHUB_PROVIDER_ADAPTER_ID,
        "read_only": True,
        "repository_write": False,
        "merge": False,
        "force_push": False,
        "irreversible_side_effects": [],
        "authority_effect": "NONE",
    }


def normalize_github_observation(raw: Mapping[str, Any]) -> GitHubAssuranceObservation:
    return GitHubAssuranceObservation(
        repository=str(raw.get("repository") or ""),
        candidate_commit=str(raw.get("candidate_commit") or raw.get("head_sha") or ""),
        workflow_name=str(raw.get("workflow_name") or ""),
        run_id=str(raw.get("run_id") or ""),
        check_name=str(raw.get("check_name") or raw.get("job_name") or ""),
        status=str(raw.get("status") or ""),
        conclusion=None if raw.get("conclusion") is None else str(raw.get("conclusion")),
        observed_at=str(raw.get("observed_at") or ""),
    )


def signal_from_observation(
    future: AssuranceFuture,
    observation: GitHubAssuranceObservation,
) -> AssuranceCompletionSignal | None:
    if observation.status.lower() != TERMINAL_STATUS or observation.conclusion is None:
        return None
    if (
        observation.provider_adapter_id != future.provider_adapter_id
        or observation.candidate_commit != future.candidate_commit
        or observation.workflow_name != future.workflow_name
        or observation.run_id != future.run_id
        or observation.check_name != future.check_name
    ):
        return None
    return AssuranceCompletionSignal(
        future_id=future.future_id,
        provider_adapter_id=observation.provider_adapter_id,
        repository=observation.repository,
        candidate_commit=observation.candidate_commit,
        workflow_name=observation.workflow_name,
        run_id=observation.run_id,
        check_name=observation.check_name,
        conclusion=observation.conclusion,
        observed_at=observation.observed_at,
    )


def reconcile_github_future(
    future: AssuranceFuture,
    observations: Sequence[GitHubAssuranceObservation],
) -> AssuranceFuture:
    exact = [
        row for row in observations
        if row.provider_adapter_id == future.provider_adapter_id
        and row.candidate_commit == future.candidate_commit
        and row.workflow_name == future.workflow_name
        and row.run_id == future.run_id
        and row.check_name == future.check_name
    ]
    terminal = [
        row for row in exact
        if row.status.lower() == TERMINAL_STATUS and row.conclusion is not None
    ]
    if not terminal:
        return future
    conclusions = {str(row.conclusion).upper() for row in terminal}
    if len(conclusions) != 1:
        raise ValueError("GITHUB_ASSURANCE_TERMINAL_CONFLICT")
    current = future
    for selected in sorted(
        terminal,
        key=lambda row: (row.observed_at, row.check_name, row.conclusion or ""),
    ):
        signal = signal_from_observation(current, selected)
        assert signal is not None
        current = apply_completion_signal(current, signal)
    return current
