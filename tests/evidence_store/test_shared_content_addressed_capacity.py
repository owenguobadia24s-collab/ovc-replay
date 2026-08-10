from __future__ import annotations

from hashlib import sha256
import json

import pytest

from ovc_evidence_store import CapacityEnvelope, ContentAddressedArtifactStore, EvidenceStoreError, project_storage_bytes


def test_content_addressed_store_round_trip_is_deterministic(tmp_path):
    store = ContentAddressedArtifactStore(
        tmp_path,
        namespace="test/run-1",
        max_external_bytes=10_000_000,
        chunk_bytes=8,
        compression_level=6,
    )
    raw = b'{"alpha":1,"beta":[1,2,3],"pad":"abcdefghijklmnopqrstuvwxyz"}'
    logical = sha256(b"logical-science-output").hexdigest()
    context = {"programme_id": "P", "run_id": "R", "binding": "B"}
    first = store.commit_bytes(unit_id="u/1", raw_output=raw, logical_output_sha256=logical, context=context)
    size_after_first = store.total_bytes()
    second = store.commit_bytes(unit_id="u/1", raw_output=raw, logical_output_sha256=logical, context=context)
    assert first == second
    assert store.total_bytes() == size_after_first
    assert store.load_bytes("u/1", expected_context=context) == raw
    store.verify_receipt(first, expected_context=context)


def test_content_addressed_store_fails_closed_on_capacity(tmp_path):
    store = ContentAddressedArtifactStore(
        tmp_path,
        namespace="test/capacity",
        max_external_bytes=64,
        chunk_bytes=16,
    )
    with pytest.raises(EvidenceStoreError, match="CAPACITY_EXTERNAL_BYTES_EXCEEDED"):
        store.commit_bytes(
            unit_id="u/large",
            raw_output=b"x" * 1024,
            logical_output_sha256="0" * 64,
            context={"run": "r"},
        )


def test_context_is_part_of_manifest_binding(tmp_path):
    store = ContentAddressedArtifactStore(
        tmp_path,
        namespace="test/context",
        max_external_bytes=1_000_000,
    )
    receipt = store.commit_bytes(
        unit_id="u",
        raw_output=b"{}",
        logical_output_sha256="a" * 64,
        context={"science": "S1"},
    )
    with pytest.raises(EvidenceStoreError, match="ARTIFACT_CONTEXT_MISMATCH"):
        store.verify_receipt(receipt, expected_context={"science": "S2"})


def test_evidence_derived_capacity_projection_and_tier_assertion():
    worksheet = project_storage_bytes(
        completed_bytes=10_620_989_538,
        completed_units=1626,
        total_units=2020,
        remaining_unit_bounds=[3_030_958_176],
        reserve_fraction=0.30,
    )
    assert worksheet["linear_full_projection_bytes"] == 13_194_587_249
    assert worksheet["conservative_full_bound_bytes"] == 13_651_947_714
    assert worksheet["minimum_with_reserve_bytes"] == 17_747_532_029
    envelope = CapacityEnvelope(
        envelope_id="SRFD.T1.v1",
        tier="T1",
        max_external_bytes=24 * 1024**3,
    )
    envelope.assert_external_bytes(worksheet["minimum_with_reserve_bytes"])
    with pytest.raises(EvidenceStoreError, match="CAPACITY_EXTERNAL_BYTES_EXCEEDED"):
        envelope.assert_external_bytes(24 * 1024**3 + 1)
