from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import pytest

from ovc.development.skills.dias import DiasContractError
from ovc.development.identity import canonical_sha256
from ovc.development.skills.dias_packet import (
    ApplyPrecondition,
    DependencyFrontier,
    ImmutablePacketIntegrationPayload,
    LogicalChange,
    PacketReadyRecord,
    assess_applicability,
    classify_assurance,
    reconstruct_pip,
)


SHA64_A = "a" * 64
SHA64_B = "b" * 64
SHA64_C = "c" * 64
TREE = "d" * 40


def ready_and_pip() -> tuple[PacketReadyRecord, ImmutablePacketIntegrationPayload]:
    frontier = DependencyFrontier(tokens=("OWNER_STATE:vit-v19",), owner_fact_ids=(SHA64_A,))
    ready = PacketReadyRecord(
        programme_id="OVC-DIAS-CONFORMANCE-v0.1",
        packet_id="DIASI-WP2-VERTICAL-SLICE",
        authority_envelope_id=SHA64_A,
        source_tree=TREE,
        logical_changes=(LogicalChange("ADD", "records/result.json", SHA64_B),),
        preconditions=(ApplyPrecondition("records/result.json", "PATH_ABSENT", None),),
        dependency_frontier_id=frontier.frontier_id,
        test_dependency_manifest_id=SHA64_C,
    )
    pip = ImmutablePacketIntegrationPayload.from_ready(
        ready,
        assurance_class="AA2",
        completion_transition={"status": "COMPLETED", "next_packet": "DIASI-WP3"},
    )
    return ready, pip


def test_ready_record_and_pip_are_deterministic_and_immutable() -> None:
    ready, pip = ready_and_pip()
    again_ready, again_pip = ready_and_pip()
    assert ready.ready_id == again_ready.ready_id
    assert pip.pip_id == again_pip.pip_id
    assert pip.packet_ready_id == ready.ready_id
    with pytest.raises(Exception):
        pip.packet_id = "MUTATED"  # type: ignore[misc]


@pytest.mark.parametrize("event", ["MAIN_MOVED", "PROVIDER_RERUN", "LEASE_LOST", "RULESET_DRIFT", "PROCESS_RESTART"])
def test_ordinary_movement_does_not_semantically_reopen(event: str) -> None:
    _, pip = ready_and_pip()
    observed = {}
    assessment = assess_applicability(pip, events=[event], observed_preconditions=observed)
    assert assessment.status == "PLACEMENT_RECOMPUTE_ONLY"
    assert assessment.semantic_reopen is False
    assert assessment.placement_recompute_required is True


@pytest.mark.parametrize("event", ["PACKET_DEFECT", "MEANING_BEARING_OWNER_CONFLICT", "FAILED_APPLY_PRECONDITION"])
def test_only_exact_semantic_events_reopen(event: str) -> None:
    _, pip = ready_and_pip()
    assessment = assess_applicability(pip, events=[event], observed_preconditions={})
    assert assessment.status == "SEMANTIC_REOPEN_REQUIRED"
    assert assessment.semantic_reopen is True


def test_apply_precondition_failure_reopens_even_on_ordinary_movement() -> None:
    frontier = DependencyFrontier(tokens=("MAIN:abc",), owner_fact_ids=(SHA64_A,))
    ready = PacketReadyRecord(
        programme_id="P",
        packet_id="DIASI-WP2",
        authority_envelope_id=SHA64_A,
        source_tree=TREE,
        logical_changes=(LogicalChange("MODIFY", "a.json", SHA64_B),),
        preconditions=(ApplyPrecondition("a.json", "BLOB_EQUALS", "expected"),),
        dependency_frontier_id=frontier.frontier_id,
        test_dependency_manifest_id=SHA64_C,
    )
    pip = ImmutablePacketIntegrationPayload.from_ready(ready, assurance_class="AA1", completion_transition={"status": "COMPLETED"})
    assessment = assess_applicability(pip, events=["MAIN_MOVED"], observed_preconditions={"a.json": "different"})
    assert assessment.semantic_reopen is True
    assert assessment.reasons == ("FAILED_APPLY_PRECONDITION", "a.json")


def test_unknown_event_blocks_without_manufacturing_development_reopen() -> None:
    _, pip = ready_and_pip()
    assessment = assess_applicability(pip, events=["ALIEN_EVENT"], observed_preconditions={})
    assert assessment.status == "BLOCKED_CROSS_BOUNDARY_UNKNOWN"
    assert assessment.semantic_reopen is False


def test_fresh_process_reconstruction_preserves_pip_identity() -> None:
    _, pip = ready_and_pip()
    decoded = json.loads(json.dumps(asdict(pip), sort_keys=True))
    reconstructed = reconstruct_pip(decoded)
    assert reconstructed == pip
    assert reconstructed.pip_id == pip.pip_id


def test_assurance_classification_is_closed_and_deterministic() -> None:
    assert classify_assurance(["OWNER_FACT:x"]) == "AA2"
    assert classify_assurance(["MAIN:x"]) == "AA1"
    assert classify_assurance(["MAIN:x", "TREE:y"]) == "AA3"
    assert classify_assurance(["CREDENTIAL_REF:logical-name"]) == "CROSS_BOUNDARY_UNKNOWN"
    with pytest.raises(DiasContractError):
        classify_assurance(["MAGIC:x"])


def test_vertical_slice_has_no_live_write_or_external_runtime() -> None:
    ready, pip = ready_and_pip()
    assessment = assess_applicability(pip, events=["PROCESS_RESTART", "MAIN_MOVED"], observed_preconditions={})
    assert ready.status == "PACKET_READY"
    assert assessment.semantic_reopen is False
    assert assessment.status == "PLACEMENT_RECOMPUTE_ONLY"


def test_wp2_court_records_bind_vit_identities_and_reserved_boundary() -> None:
    root = Path(__file__).resolve().parents[3]
    wp2 = root / "docs/programmes/dias-v0-1/wp2"
    authority = json.loads((wp2 / "DIASI_WP2_VIT_AUTHORITY_MANIFEST.json").read_text(encoding="utf-8"))
    frontier = json.loads((wp2 / "DIASI_WP2_VIT_DEPENDENCY_FRONTIER.json").read_text(encoding="utf-8"))
    assert canonical_sha256(authority["payload"]) == authority["logical_id"]
    assert canonical_sha256(frontier["payload"]) == frontier["logical_id"]
    state = json.loads((root / "registries/implementation/dias_v0_1/DIASI_CURRENT_v0_3.json").read_text(encoding="utf-8"))
    assert state["next_packet"] == "DIASI-WP3"
    assert state["next_reserved_operator_gate"] == "DIASI-G-DGS-CUTOVER-DRAIN"
    assert state["live_cutover"] is False
