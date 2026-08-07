from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

from .serialization import canonical_json_bytes, logical_sha256, stable_id

STAGE_ORDER = (
    "population", "representation", "compatibility", "distance", "family",
    "sensitivity", "correspondence", "invariant_core", "stability",
    "failure_attribution", "packet",
)
DENIED_ACTIONS = frozenset({
    "provider_intake", "canonical_r2_publication", "selector_change",
    "c2e_activation", "c2g_activation", "c2p_activation", "c2_5_activation",
    "c3_activation", "validation_consumption", "june_market_benchmark",
    "probability", "risk", "exposure", "trading", "execution",
})


class OrchestrationError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def authority_guard(action: str) -> None:
    if action in DENIED_ACTIONS:
        code = "AUTH_VALIDATION_DENIED" if action == "validation_consumption" else "AUTH_JUNE_NOT_AUTHORISED" if action == "june_market_benchmark" else "AUTH_SCOPE_EXPANSION"
        raise OrchestrationError(code, f"{action} is outside SRFDI fixture-only authority")


def canonicalize_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    values = [dict(item) for item in records]
    if any(not str(item.get("record_id", "")).strip() for item in values):
        raise OrchestrationError("QA_SCHEMA_FAILURE", "record_id required")
    return sorted(values, key=lambda item: str(item["record_id"]))


@dataclass(frozen=True)
class CheckpointReceipt:
    checkpoint_id: str
    completed_stage_index: int
    completed_stage: str
    state: Mapping[str, Any]
    state_logical_hash: str
    stage_receipts: tuple[Mapping[str, Any], ...]
    authority_state: str = "FIXTURE_ONLY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "completed_stage_index": self.completed_stage_index,
            "completed_stage": self.completed_stage,
            "state": dict(self.state),
            "state_logical_hash": self.state_logical_hash,
            "stage_receipts": [dict(item) for item in self.stage_receipts],
            "authority_state": self.authority_state,
        }


def make_checkpoint(index: int, state: Mapping[str, Any], receipts: Sequence[Mapping[str, Any]]) -> CheckpointReceipt:
    if index < 0 or index >= len(STAGE_ORDER):
        raise OrchestrationError("CAP_RESTART_FAILURE", "checkpoint stage outside orchestration")
    state_hash = logical_sha256(state)
    payload = {
        "completed_stage_index": index,
        "completed_stage": STAGE_ORDER[index],
        "state_logical_hash": state_hash,
        "stage_receipts": [dict(item) for item in receipts],
    }
    return CheckpointReceipt(stable_id("SRFD.CHECKPOINT.", payload), index, STAGE_ORDER[index], dict(state), state_hash, tuple(dict(item) for item in receipts))


def verify_checkpoint(checkpoint: CheckpointReceipt) -> None:
    if checkpoint.completed_stage != STAGE_ORDER[checkpoint.completed_stage_index]:
        raise OrchestrationError("CAP_RESTART_FAILURE", "checkpoint stage identity mismatch")
    if logical_sha256(checkpoint.state) != checkpoint.state_logical_hash:
        raise OrchestrationError("CAP_RESTART_FAILURE", "checkpoint state hash mismatch")


def run_pipeline(
    initial_state: Mapping[str, Any],
    stage_functions: Mapping[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]],
    *,
    stop_after: str | None = None,
    checkpoint: CheckpointReceipt | None = None,
) -> dict[str, Any]:
    if set(stage_functions) - set(STAGE_ORDER):
        raise OrchestrationError("QA_SCHEMA_FAILURE", "unknown orchestration stage")
    state = dict(initial_state)
    receipts: list[dict[str, Any]] = []
    start = 0
    if checkpoint is not None:
        verify_checkpoint(checkpoint)
        state = dict(checkpoint.state)
        receipts = [dict(item) for item in checkpoint.stage_receipts]
        start = checkpoint.completed_stage_index + 1
    last_checkpoint: CheckpointReceipt | None = checkpoint
    for index in range(start, len(STAGE_ORDER)):
        stage = STAGE_ORDER[index]
        if stage not in stage_functions:
            continue
        before_hash = logical_sha256(state)
        output = stage_functions[stage](dict(state))
        if not isinstance(output, Mapping):
            raise OrchestrationError("QA_SCHEMA_FAILURE", f"{stage} did not return a mapping")
        state = dict(output)
        receipt_payload = {"stage":stage,"index":index,"input_hash":before_hash,"output_hash":logical_sha256(state)}
        receipts.append({**receipt_payload,"stage_receipt_id":stable_id("SRFD.STAGE.",receipt_payload)})
        last_checkpoint = make_checkpoint(index,state,receipts)
        if stop_after == stage:
            break
    payload = {
        "state": state,
        "state_logical_hash": logical_sha256(state),
        "stage_receipts": receipts,
        "last_checkpoint": last_checkpoint.to_dict() if last_checkpoint else None,
        "authority_state": "FIXTURE_ONLY",
    }
    return {**payload,"run_id":stable_id("SRFD.FIXTURE.RUN.",payload)}


def artifact_reference(*, artifact_id: str, sha256: str, location: str, media_type: str) -> dict[str, str]:
    digest = sha256.lower().strip()
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise OrchestrationError("QA_SCHEMA_FAILURE", "artifact sha256 must be lowercase hex")
    if location.startswith("git://") or location.startswith("repo://"):
        raise OrchestrationError("AUTH_SCOPE_EXPANSION", "bulky/generated artifacts cannot be registered inside Git")
    if not (location.startswith("external://") or location.startswith("r2-readonly://") or location.startswith("memory://")):
        raise OrchestrationError("QA_SCHEMA_FAILURE", "artifact location must use governed external/read-only scheme")
    return {"artifact_id":artifact_id,"sha256":digest,"location":location,"media_type":media_type,"authority_state":"FIXTURE_ONLY"}


def research_operations_event(*, event_type: str, target_id: str, artifact_refs: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    payload = {"event_type":event_type,"target_id":target_id,"artifact_refs":[dict(item) for item in artifact_refs],"authority_effect":"NONE"}
    return {**payload,"event_id":stable_id("SRFD.RO.EVENT.",payload)}


def deterministic_fixture_manifest(catalog: Mapping[str, Any]) -> dict[str, Any]:
    fixtures = catalog.get("fixtures")
    if not isinstance(fixtures, Sequence):
        raise OrchestrationError("QA_SCHEMA_FAILURE", "fixture list required")
    ids = [str(item.get("id")) for item in fixtures if isinstance(item, Mapping)]
    if len(ids) != len(set(ids)):
        raise OrchestrationError("QA_SCHEMA_FAILURE", "duplicate fixture ID")
    payload = {"fixture_ids": sorted(ids), "fixture_count": len(ids), "catalog_hash": logical_sha256(catalog)}
    return {**payload,"manifest_id":stable_id("SRFD.FIXTURES.",payload)}
