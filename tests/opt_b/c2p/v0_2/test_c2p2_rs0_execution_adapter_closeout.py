from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ovc.opt_b.c2p_v0_2.rs0_execution import (
    RS0ExecutionError, checkpoint_identity, iter_verified_rows, validate_locator,
)

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def test_exact_locator_and_read_only_causal_row(tmp_path: Path) -> None:
    stream=tmp_path/"c2.jsonl"
    row={
        "schema":"ovc-c2p2-rs0-source-row/v1",
        "source_role":"C2_VNEXT",
        "instrument":"GBPUSD","side":"BID","clock":"15M",
        "first_valid_time":"2021-01-01T00:15:00Z",
        "evaluation_cutoff":"2021-01-01T00:15:00Z",
        "source_record_id":"c2-1",
        "structural_role_id":"LEVEL",
        "geometry_kind_id":"POINT",
        "geometry_signature":{"price":"1.23450"},
        "relation_topology":[],
    }
    stream.write_text(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    locator={
        "schema":"ovc-c2p2-rs0-source-locator/v1",
        "instrument":"GBPUSD","sides":["BID","ASK"],"clocks":["15M","2H_A_L"],
        "interval":"[2021-01-01T00:00:00Z,2024-01-01T00:00:00Z)",
        "sources":[{"role":"C2_VNEXT","relative_path":"c2.jsonl","sha256":_sha(stream),"size_bytes":stream.stat().st_size,"row_count":1}],
    }
    verified=validate_locator(locator,tmp_path)
    assert verified[0].role=="C2_VNEXT"
    assert list(iter_verified_rows(stream,expected_role="C2_VNEXT"))==[row]

def test_locator_fails_closed_on_byte_change(tmp_path: Path) -> None:
    stream=tmp_path/"c2.jsonl"
    stream.write_text("{}\n",encoding="utf-8")
    locator={
        "schema":"ovc-c2p2-rs0-source-locator/v1",
        "instrument":"GBPUSD","sides":["BID","ASK"],"clocks":["15M","2H_A_L"],
        "interval":"[2021-01-01T00:00:00Z,2024-01-01T00:00:00Z)",
        "sources":[{"role":"C2_VNEXT","relative_path":"c2.jsonl","sha256":"0"*64,"size_bytes":stream.stat().st_size,"row_count":1}],
    }
    with pytest.raises(RS0ExecutionError, match="SHA256_MISMATCH"):
        validate_locator(locator,tmp_path)

def test_forbidden_outcome_fields_are_rejected(tmp_path: Path) -> None:
    stream=tmp_path/"c2.jsonl"
    row={
        "schema":"ovc-c2p2-rs0-source-row/v1","source_role":"C2_VNEXT",
        "instrument":"GBPUSD","side":"ASK","clock":"2H_A_L",
        "first_valid_time":"2021-01-01T02:00:00Z","evaluation_cutoff":"2021-01-01T02:00:00Z",
        "outcome":1,
    }
    stream.write_text(json.dumps(row)+"\n",encoding="utf-8")
    with pytest.raises(RS0ExecutionError, match="FORBIDDEN_SOURCE_FIELD"):
        list(iter_verified_rows(stream,expected_role="C2_VNEXT"))

def test_checkpoint_identity_is_candidate_set_and_progress_bound() -> None:
    a=checkpoint_identity(locator_sha256="a"*64,candidate_ids=["C","A","B"],completed_rows=256)
    b=checkpoint_identity(locator_sha256="a"*64,candidate_ids=["A","B","C"],completed_rows=256)
    c=checkpoint_identity(locator_sha256="a"*64,candidate_ids=["A","B","C"],completed_rows=257)
    assert a==b
    assert a!=c
