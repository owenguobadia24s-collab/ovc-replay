from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any, Iterable, Mapping

from .canonical import canonical_bytes
from .ledger import CanonicalEventLedger
from .projection import projection_digest, rebuild_snapshots


class CheckpointIntegrityError(ValueError):
    pass


def _hash(payload: Any) -> str:
    return sha256(canonical_bytes(payload)).hexdigest()


def build_checkpoint(
    ledger: CanonicalEventLedger,
    *,
    open_tracklet_ids: Iterable[str] = (),
    assertion_ids: Iterable[str] = (),
    index_digest: str | None = None,
) -> dict[str, Any]:
    ledger.verify_integrity()
    snapshots = tuple(rebuild_snapshots(ledger))
    body = {
        "schema": "c2p-checkpoint/v0.2",
        "ledger_seal": dict(ledger.seal()),
        "ledger_digest": ledger.global_digest(),
        "projection_digest": projection_digest(snapshots),
        "open_tracklet_ids": sorted(set(open_tracklet_ids)),
        "assertion_ids": sorted(set(assertion_ids)),
        "index_digest": index_digest,
        "events": [dict(event) for event in ledger.all_events()],
    }
    return {"checkpoint_id": _hash(body), **body}


def checkpoint_bytes(checkpoint: Mapping[str, Any]) -> bytes:
    validate_checkpoint(checkpoint)
    return canonical_bytes(dict(checkpoint))


def validate_checkpoint(checkpoint: Mapping[str, Any]) -> bool:
    if checkpoint.get("schema") != "c2p-checkpoint/v0.2":
        raise CheckpointIntegrityError("C2P_CHECKPOINT_SCHEMA_INVALID")
    checkpoint_id = checkpoint.get("checkpoint_id")
    body = {key: deepcopy(value) for key, value in checkpoint.items() if key != "checkpoint_id"}
    if checkpoint_id != _hash(body):
        raise CheckpointIntegrityError("C2P_CHECKPOINT_HASH_MISMATCH")
    return True


def restore_checkpoint(checkpoint: Mapping[str, Any]) -> CanonicalEventLedger:
    validate_checkpoint(checkpoint)
    events = checkpoint.get("events")
    if not isinstance(events, list):
        raise CheckpointIntegrityError("C2P_CHECKPOINT_EVENTS_INVALID")
    ledger = CanonicalEventLedger.from_events(events)
    if ledger.global_digest() != checkpoint.get("ledger_digest"):
        raise CheckpointIntegrityError("C2P_CHECKPOINT_LEDGER_DIGEST_MISMATCH")
    if canonical_bytes(dict(ledger.seal())) != canonical_bytes(dict(checkpoint.get("ledger_seal", {}))):
        raise CheckpointIntegrityError("C2P_CHECKPOINT_FRONTIER_MISMATCH")
    snapshots = tuple(rebuild_snapshots(ledger))
    if projection_digest(snapshots) != checkpoint.get("projection_digest"):
        raise CheckpointIntegrityError("C2P_CHECKPOINT_PROJECTION_DIGEST_MISMATCH")
    return ledger
