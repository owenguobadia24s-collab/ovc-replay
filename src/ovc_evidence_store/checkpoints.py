from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .content_addressed import canonical_json_bytes
from .manifest import EvidenceStoreError


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


@dataclass(frozen=True)
class CheckpointReceipt:
    namespace: str
    sequence: int
    checkpoint_id: str
    checkpoint_sha256: str
    parent_checkpoint_sha256: str | None


class AppendOnlyCheckpointStore:
    """Programme-neutral immutable checkpoint lineage store.

    Scientific programmes own checkpoint meaning and payload schemas.  This
    class owns only immutable sequencing, parent-hash lineage and deterministic
    serialization of the supplied payload.
    """

    def __init__(self, root: Path, *, namespace: str) -> None:
        self.root = Path(root)
        self.namespace = str(namespace).strip().strip("/")
        if not self.namespace or ".." in Path(self.namespace).parts:
            raise EvidenceStoreError("checkpoint namespace must be a non-empty relative path")

    @property
    def checkpoint_root(self) -> Path:
        return self.root / "checkpoints" / self.namespace

    def _path(self, sequence: int) -> Path:
        if int(sequence) <= 0:
            raise EvidenceStoreError("checkpoint sequence must be positive")
        return self.checkpoint_root / f"{int(sequence):08d}.json"

    def latest(self) -> dict[str, Any] | None:
        files = sorted(self.checkpoint_root.glob("*.json")) if self.checkpoint_root.exists() else []
        if not files:
            return None
        return json.loads(files[-1].read_bytes())

    def commit(
        self,
        *,
        sequence: int,
        checkpoint_id: str,
        payload: Mapping[str, Any],
    ) -> CheckpointReceipt:
        seq = int(sequence)
        previous = self.latest()
        expected = 1 if previous is None else int(previous["sequence"]) + 1
        if seq != expected:
            raise EvidenceStoreError(f"CHECKPOINT_SEQUENCE_MISMATCH expected={expected} observed={seq}")
        parent_sha = None if previous is None else str(previous["checkpoint_sha256"])
        body = {
            "schema": "ovc-append-only-checkpoint/v1",
            "namespace": self.namespace,
            "sequence": seq,
            "checkpoint_id": str(checkpoint_id),
            "parent_checkpoint_sha256": parent_sha,
            "payload": dict(payload),
        }
        body_sha = sha256(canonical_json_bytes(body)).hexdigest()
        record = dict(body)
        record["checkpoint_sha256"] = body_sha
        raw = canonical_json_bytes(record) + b"\n"
        path = self._path(seq)
        if path.exists():
            if path.read_bytes() != raw:
                raise EvidenceStoreError(f"CHECKPOINT_HISTORY_REWRITE:{seq}")
        else:
            _atomic_write(path, raw)
        self.verify(seq)
        return CheckpointReceipt(
            namespace=self.namespace,
            sequence=seq,
            checkpoint_id=str(checkpoint_id),
            checkpoint_sha256=body_sha,
            parent_checkpoint_sha256=parent_sha,
        )

    def verify(self, sequence: int) -> dict[str, Any]:
        path = self._path(sequence)
        if not path.exists():
            raise EvidenceStoreError(f"CHECKPOINT_MISSING:{sequence}")
        record = json.loads(path.read_bytes())
        stored = str(record.pop("checkpoint_sha256"))
        observed = sha256(canonical_json_bytes(record)).hexdigest()
        if stored != observed:
            raise EvidenceStoreError(f"CHECKPOINT_HASH_MISMATCH:{sequence}")
        if record.get("namespace") != self.namespace or int(record.get("sequence", -1)) != int(sequence):
            raise EvidenceStoreError(f"CHECKPOINT_BINDING_MISMATCH:{sequence}")
        if int(sequence) > 1:
            parent_path = self._path(int(sequence) - 1)
            if not parent_path.exists():
                raise EvidenceStoreError(f"CHECKPOINT_PARENT_MISSING:{sequence}")
            parent = json.loads(parent_path.read_bytes())
            if record.get("parent_checkpoint_sha256") != parent.get("checkpoint_sha256"):
                raise EvidenceStoreError(f"CHECKPOINT_PARENT_HASH_MISMATCH:{sequence}")
        return record
