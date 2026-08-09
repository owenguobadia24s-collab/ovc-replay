from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .models import CheckpointRecord
from .planner import CanonicalPlan
from .serialization import logical_sha256


class CheckpointError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


@dataclass(frozen=True)
class StageCompletion:
    stage_id: str
    stage_spec_hash: str
    output_logical_hash: str
    content_hash: str
    attempt_id: str
    status: str = "COMPLETE"

    def __post_init__(self) -> None:
        if self.status != "COMPLETE":
            raise CheckpointError("IROF_CHECKPOINT_INCOMPLETE_AS_COMPLETE", self.stage_id)
        for name in ("stage_id", "stage_spec_hash", "output_logical_hash", "content_hash", "attempt_id"):
            if not str(getattr(self, name)).strip():
                raise CheckpointError("IROF_CHECKPOINT_COMPLETION_FIELD_REQUIRED", name)

    def semantic_dict(self) -> dict[str, str]:
        return {
            "stage_id": self.stage_id,
            "stage_spec_hash": self.stage_spec_hash,
            "output_logical_hash": self.output_logical_hash,
            "content_hash": self.content_hash,
            "status": self.status,
        }


@dataclass(frozen=True)
class OpaqueSubstageCheckpoint:
    checkpoint_id: str
    semantic_run_id: str
    stage_id: str
    owner_checkpoint_schema: str
    opaque_ref: str
    content_hash: str
    attempt_id: str
    status: str = "COMPLETE"

    def __post_init__(self) -> None:
        if self.status != "COMPLETE":
            raise CheckpointError("IROF_OPAQUE_CHECKPOINT_NOT_COMPLETE", self.checkpoint_id)
        for name in (
            "checkpoint_id", "semantic_run_id", "stage_id", "owner_checkpoint_schema",
            "opaque_ref", "content_hash", "attempt_id",
        ):
            if not str(getattr(self, name)).strip():
                raise CheckpointError("IROF_OPAQUE_CHECKPOINT_FIELD_REQUIRED", name)

    def to_checkpoint_record(self) -> CheckpointRecord:
        return CheckpointRecord(
            checkpoint_id=self.checkpoint_id,
            semantic_run_id=self.semantic_run_id,
            stage_id=self.stage_id,
            level="OPAQUE_SUBSTAGE",
            content_hash=self.content_hash,
            status="COMPLETE",
            owner_checkpoint_schema=self.owner_checkpoint_schema,
            opaque_ref=self.opaque_ref,
            attempt_id=self.attempt_id,
        )


@dataclass(frozen=True)
class RunCheckpointManifest:
    semantic_run_id: str
    completions: tuple[StageCompletion, ...]
    opaque_substage_checkpoints: tuple[OpaqueSubstageCheckpoint, ...] = ()
    manifest_version: str = "0.1"

    def __post_init__(self) -> None:
        if not self.semantic_run_id.strip():
            raise CheckpointError("IROF_CHECKPOINT_RUN_ID_REQUIRED", "semantic_run_id")
        stage_ids = tuple(item.stage_id for item in self.completions)
        if len(stage_ids) != len(set(stage_ids)):
            raise CheckpointError("IROF_DUPLICATE_STAGE_COMPLETION", ",".join(stage_ids))
        checkpoint_ids = tuple(item.checkpoint_id for item in self.opaque_substage_checkpoints)
        if len(checkpoint_ids) != len(set(checkpoint_ids)):
            raise CheckpointError("IROF_DUPLICATE_OPAQUE_CHECKPOINT", ",".join(checkpoint_ids))
        if any(item.semantic_run_id != self.semantic_run_id for item in self.opaque_substage_checkpoints):
            raise CheckpointError("IROF_CHECKPOINT_RUN_ID_MISMATCH", self.semantic_run_id)

    def semantic_dict(self) -> dict[str, object]:
        return {
            "manifest_version": self.manifest_version,
            "semantic_run_id": self.semantic_run_id,
            "completions": [item.semantic_dict() for item in sorted(self.completions, key=lambda x: x.stage_id)],
            "opaque_substage_checkpoints": [
                {
                    "checkpoint_id": item.checkpoint_id,
                    "stage_id": item.stage_id,
                    "owner_checkpoint_schema": item.owner_checkpoint_schema,
                    "opaque_ref": item.opaque_ref,
                    "content_hash": item.content_hash,
                    "status": item.status,
                }
                for item in sorted(self.opaque_substage_checkpoints, key=lambda x: x.checkpoint_id)
            ],
        }

    @property
    def logical_hash(self) -> str:
        return logical_sha256(self.semantic_dict())


@dataclass(frozen=True)
class ResumePlan:
    semantic_run_id: str
    prior_attempt_ids: tuple[str, ...]
    new_attempt_id: str
    reusable_completed_stage_ids: tuple[str, ...]
    rerun_stage_ids: tuple[str, ...]
    quarantined_stage_ids: tuple[str, ...]
    quarantined_checkpoint_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]

    @property
    def restart_count(self) -> int:
        return len(set(self.prior_attempt_ids))


class CheckpointLedger:
    def __init__(self, semantic_run_id: str) -> None:
        if not semantic_run_id.strip():
            raise CheckpointError("IROF_CHECKPOINT_RUN_ID_REQUIRED", "semantic_run_id")
        self.semantic_run_id = semantic_run_id
        self._completions: dict[str, StageCompletion] = {}
        self._opaque: dict[str, OpaqueSubstageCheckpoint] = {}
        self._quarantined_stages: dict[str, str] = {}
        self._quarantined_checkpoints: dict[str, str] = {}

    def register_completion(self, completion: StageCompletion) -> None:
        if completion.stage_id in self._quarantined_stages:
            raise CheckpointError("IROF_CHECKPOINT_STAGE_QUARANTINED", completion.stage_id)
        existing = self._completions.get(completion.stage_id)
        if existing is not None and existing.semantic_dict() != completion.semantic_dict():
            self._completions.pop(completion.stage_id, None)
            self._quarantined_stages[completion.stage_id] = "IROF_CHECKPOINT_COMPLETION_HASH_CONFLICT"
            raise CheckpointError("IROF_CHECKPOINT_COMPLETION_HASH_CONFLICT", completion.stage_id)
        self._completions[completion.stage_id] = completion

    def register_opaque(self, checkpoint: OpaqueSubstageCheckpoint) -> None:
        if checkpoint.semantic_run_id != self.semantic_run_id:
            raise CheckpointError("IROF_CHECKPOINT_RUN_ID_MISMATCH", checkpoint.checkpoint_id)
        existing = self._opaque.get(checkpoint.checkpoint_id)
        if existing is not None and (
            existing.content_hash != checkpoint.content_hash
            or existing.opaque_ref != checkpoint.opaque_ref
            or existing.owner_checkpoint_schema != checkpoint.owner_checkpoint_schema
        ):
            self._opaque.pop(checkpoint.checkpoint_id, None)
            self._quarantined_checkpoints[checkpoint.checkpoint_id] = "IROF_OPAQUE_CHECKPOINT_HASH_CONFLICT"
            raise CheckpointError("IROF_OPAQUE_CHECKPOINT_HASH_CONFLICT", checkpoint.checkpoint_id)
        self._opaque[checkpoint.checkpoint_id] = checkpoint

    def verify_stage(
        self,
        stage_id: str,
        *,
        expected_stage_spec_hash: str,
        observed_content_hash: str | None = None,
    ) -> bool:
        completion = self._completions.get(stage_id)
        if completion is None:
            return False
        if completion.stage_spec_hash != expected_stage_spec_hash:
            return False
        if observed_content_hash is not None and completion.content_hash != observed_content_hash:
            self._completions.pop(stage_id, None)
            self._quarantined_stages[stage_id] = "IROF_CHECKPOINT_CONTENT_CORRUPTION"
            return False
        return True

    def verify_opaque(self, checkpoint_id: str, *, observed_content_hash: str | None = None) -> bool:
        checkpoint = self._opaque.get(checkpoint_id)
        if checkpoint is None:
            return False
        if observed_content_hash is not None and checkpoint.content_hash != observed_content_hash:
            self._opaque.pop(checkpoint_id, None)
            self._quarantined_checkpoints[checkpoint_id] = "IROF_OPAQUE_CHECKPOINT_CONTENT_CORRUPTION"
            return False
        return True

    def manifest(self) -> RunCheckpointManifest:
        return RunCheckpointManifest(
            semantic_run_id=self.semantic_run_id,
            completions=tuple(self._completions.values()),
            opaque_substage_checkpoints=tuple(self._opaque.values()),
        )

    @property
    def quarantined_stages(self) -> Mapping[str, str]:
        return dict(self._quarantined_stages)

    @property
    def quarantined_checkpoints(self) -> Mapping[str, str]:
        return dict(self._quarantined_checkpoints)


def build_resume_plan(
    *,
    plan: CanonicalPlan,
    semantic_run_id: str,
    completions: Iterable[StageCompletion],
    expected_stage_spec_hashes: Mapping[str, str],
    observed_content_hashes: Mapping[str, str] | None,
    new_attempt_id: str,
    opaque_checkpoints: Iterable[OpaqueSubstageCheckpoint] = (),
    observed_opaque_content_hashes: Mapping[str, str] | None = None,
) -> ResumePlan:
    ledger = CheckpointLedger(semantic_run_id)
    reasons: set[str] = set()
    prior_attempts: set[str] = set()

    for completion in completions:
        prior_attempts.add(completion.attempt_id)
        try:
            ledger.register_completion(completion)
        except CheckpointError as exc:
            reasons.add(exc.reason_code)
    for checkpoint in opaque_checkpoints:
        prior_attempts.add(checkpoint.attempt_id)
        try:
            ledger.register_opaque(checkpoint)
        except CheckpointError as exc:
            reasons.add(exc.reason_code)

    invalid: set[str] = set()
    observed = observed_content_hashes or {}
    for stage_id in plan.ordered_stage_ids:
        expected_spec = expected_stage_spec_hashes.get(stage_id)
        if expected_spec is None:
            invalid.add(stage_id)
            reasons.add("IROF_RESUME_EXPECTED_STAGE_SPEC_MISSING")
            continue
        if not ledger.verify_stage(stage_id, expected_stage_spec_hash=expected_spec, observed_content_hash=observed.get(stage_id)):
            invalid.add(stage_id)
            if stage_id in ledger.quarantined_stages:
                reasons.add(ledger.quarantined_stages[stage_id])

    observed_opaque = observed_opaque_content_hashes or {}
    for checkpoint in opaque_checkpoints:
        if checkpoint.checkpoint_id in observed_opaque and not ledger.verify_opaque(
            checkpoint.checkpoint_id,
            observed_content_hash=observed_opaque[checkpoint.checkpoint_id],
        ):
            reasons.add("IROF_OPAQUE_CHECKPOINT_CONTENT_CORRUPTION")
            invalid.add(checkpoint.stage_id)

    affected: set[str] = set(invalid)
    if invalid:
        affected.update(plan.blocked_descendants(invalid))
    reusable = tuple(stage_id for stage_id in plan.ordered_stage_ids if stage_id not in affected)
    rerun = tuple(stage_id for stage_id in plan.ordered_stage_ids if stage_id in affected)
    return ResumePlan(
        semantic_run_id=semantic_run_id,
        prior_attempt_ids=tuple(sorted(prior_attempts)),
        new_attempt_id=new_attempt_id,
        reusable_completed_stage_ids=reusable,
        rerun_stage_ids=rerun,
        quarantined_stage_ids=tuple(sorted(ledger.quarantined_stages)),
        quarantined_checkpoint_ids=tuple(sorted(ledger.quarantined_checkpoints)),
        reason_codes=tuple(sorted(reasons)),
    )


def assert_fresh_resume_equivalent(fresh_logical_hash: str, repeated_fresh_logical_hash: str, resumed_logical_hash: str) -> None:
    if not fresh_logical_hash or fresh_logical_hash != repeated_fresh_logical_hash or fresh_logical_hash != resumed_logical_hash:
        raise CheckpointError("IROF_RESUME_SCIENTIFIC_HASH_MISMATCH", fresh_logical_hash)
