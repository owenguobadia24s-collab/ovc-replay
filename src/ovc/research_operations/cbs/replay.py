from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .identity import CBSContractError, canonical_id, seal_object


def logical_output_hash(outputs: Sequence[Mapping[str, Any]]) -> str:
    rows = sorted((dict(row) for row in outputs), key=lambda row: canonical_id(row))
    return canonical_id({"logical_outputs": rows})


def build_replay_receipt(*, fresh_outputs: Sequence[Mapping[str, Any]], restart_outputs: Sequence[Mapping[str, Any]],
                         worker_order_outputs: Sequence[Mapping[str, Any]], hash_seed_outputs: Sequence[Mapping[str, Any]],
                         checkpoint_ids: Sequence[str]) -> dict[str, Any]:
    hashes = {
        "fresh": logical_output_hash(fresh_outputs), "restart": logical_output_hash(restart_outputs),
        "worker_order": logical_output_hash(worker_order_outputs), "hash_seed": logical_output_hash(hash_seed_outputs),
    }
    if len(set(hashes.values())) != 1:
        reason = "CHECKPOINT_DIVERGENCE" if hashes["fresh"] != hashes["restart"] else "REPLAY_NONDETERMINISTIC"
        raise CBSContractError(reason)
    return seal_object(
        {"schema": "ovc-cbs-replay-restart-receipt/v0.1", "logical_output_hash": hashes["fresh"],
         "path_hashes": hashes, "checkpoint_ids": list(checkpoint_ids), "fresh_restart_equal": True,
         "cross_process_hash_seed_worker_order_equal": True}, id_field="replay_receipt_id"
    )
