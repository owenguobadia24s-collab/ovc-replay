from __future__ import annotations

import json

import pytest

from ovc_evidence_store import AppendOnlyCheckpointStore, EvidenceStoreError


def test_append_only_checkpoint_lineage(tmp_path):
    store = AppendOnlyCheckpointStore(tmp_path, namespace="programme/run")
    first = store.commit(sequence=1, checkpoint_id="C1", payload={"completed": ["u1"]})
    second = store.commit(sequence=2, checkpoint_id="C2", payload={"completed": ["u1", "u2"]})
    assert second.parent_checkpoint_sha256 == first.checkpoint_sha256
    assert store.verify(1)["checkpoint_id"] == "C1"
    assert store.verify(2)["checkpoint_id"] == "C2"


def test_checkpoint_sequence_cannot_be_relabelled_or_skipped(tmp_path):
    store = AppendOnlyCheckpointStore(tmp_path, namespace="programme/run")
    store.commit(sequence=1, checkpoint_id="C1", payload={"source": "v0.9"})
    with pytest.raises(EvidenceStoreError, match="CHECKPOINT_SEQUENCE_MISMATCH"):
        store.commit(sequence=3, checkpoint_id="C3", payload={})
    with pytest.raises(EvidenceStoreError, match="CHECKPOINT_SEQUENCE_MISMATCH"):
        store.commit(sequence=1, checkpoint_id="RELABELLED", payload={"source": "v1.0"})


def test_checkpoint_parent_hash_tamper_is_detected(tmp_path):
    store = AppendOnlyCheckpointStore(tmp_path, namespace="programme/run")
    store.commit(sequence=1, checkpoint_id="C1", payload={"completed": ["u1"]})
    store.commit(sequence=2, checkpoint_id="C2", payload={"completed": ["u1", "u2"]})
    path = store.checkpoint_root / "00000001.json"
    record = json.loads(path.read_text())
    record["checkpoint_sha256"] = "0" * 64
    path.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    with pytest.raises(EvidenceStoreError, match="CHECKPOINT_PARENT_HASH_MISMATCH"):
        store.verify(2)
