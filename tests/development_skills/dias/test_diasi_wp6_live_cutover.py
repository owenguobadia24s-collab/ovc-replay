import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from ovc.development.skills.dias_cutover import (
    CUTOVER_PHRASE,
    DiasCutoverError,
    InFlightItem,
    SELECTED_CLASS,
    SUCCESSOR_WRITER,
    freeze_selected_intake,
    initial_state,
    transfer_route_and_writer,
    validate_live_registry,
    writer_accepts,
)
from tools.ci.vit_qualification_owner import validate_exact_selected_class


ROOT = Path(__file__).resolve().parents[3]
WP6 = ROOT / "docs/programmes/dias-v0-1/wp6"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_id(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def test_atomic_empty_drain_advances_both_fences_and_disables_old_route() -> None:
    frozen = freeze_selected_intake(initial_state(), packet_class=SELECTED_CLASS)
    active = transfer_route_and_writer(frozen, disposed_items=(), operator_phrase=CUTOVER_PHRASE)
    assert active.route_generation == active.writer_generation == 2
    assert active.qualification_writer == SUCCESSOR_WRITER
    assert active.old_route == "DISABLED_RETAINED"
    assert active.parallel_physical_writer is False


def test_unknown_or_cross_scope_in_flight_fails_closed() -> None:
    frozen = freeze_selected_intake(initial_state(), packet_class=SELECTED_CLASS)
    with pytest.raises(DiasCutoverError, match="SCOPE_ESCAPE"):
        transfer_route_and_writer(
            frozen,
            disposed_items=(InFlightItem("x", "OTHER", 1, "COMPLETE_OLD"),),
            operator_phrase=CUTOVER_PHRASE,
        )
    with pytest.raises(DiasCutoverError, match="QUARANTINED"):
        transfer_route_and_writer(
            frozen,
            disposed_items=(InFlightItem("x", SELECTED_CLASS, 1, "QUARANTINE_BLOCK"),),
            operator_phrase=CUTOVER_PHRASE,
        )


def test_stale_or_dual_writer_is_rejected() -> None:
    with pytest.raises(DiasCutoverError, match="STALE_WRITER_FENCE"):
        writer_accepts(writer=SUCCESSOR_WRITER, generation=1, packet_class=SELECTED_CLASS)
    with pytest.raises(DiasCutoverError, match="WRITER_NOT_AUTHORISED"):
        writer_accepts(writer="PES", generation=2, packet_class=SELECTED_CLASS)
    assert writer_accepts(writer=SUCCESSOR_WRITER, generation=2, packet_class=SELECTED_CLASS)


def test_live_registry_is_exact_and_global_cers_unchanged() -> None:
    registry = load(ROOT / "registries/development/skills/VIT_SELECTED_CLASS_ROUTE_v0_1.json")
    state = validate_live_registry(registry)
    assert state.selected_class == SELECTED_CLASS
    assert registry["global_intake_freeze"] is False
    assert registry["non_selected_classes"] == "SCOPED_NOT_RETIRED_UNCHANGED"
    assert registry["removal_authority"].startswith("DENIED")
    with pytest.raises(DiasCutoverError, match="STATE_DRIFT"):
        validate_live_registry({**registry, "route_generation": 3})


def test_selected_class_is_derived_from_receipt_paths_not_label() -> None:
    lineage = {
        "schema": "ovc-vit-payload-lineage/v2",
        "status": "PAYLOAD_ADMITTED",
        "programme_id": "OVC-DIAS-CONFORMANCE-v0.1",
        "packet_id": "DIASI-WP6-LIVE-PILOT",
        "route_class": "VIT_MANDATORY",
        "pip": {
            "schema_version": "packet-integration-payload/v0.1",
            "programme_id": "OVC-DIAS-CONFORMANCE-v0.1",
            "packet_id": "DIASI-WP6-LIVE-PILOT",
            "logical_changes": [{"op": "ADD", "path": "docs/releases/development-skills-v0-3/dias/EXACT_RECEIPT.json", "blob_sha": "a" * 40, "mode": "100644"}],
            "authority_manifest_id": "b" * 64,
            "dependency_frontier_id": "c" * 64,
            "completion_transition": {"status": "COMPLETED"},
        },
        "pip_id": "PENDING",
        "binding_policy": "LATE_PHYSICAL_PLACEMENT",
        "routing": {"controller": "DSAI_VIT_PHYSICAL_CONTROLLER", "physical_gateway": "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY", "route_class": "VIT_MANDATORY"},
    }
    lineage["pip_id"] = hashlib.sha256(json.dumps(lineage["pip"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert validate_exact_selected_class(root=ROOT, lineage_record=lineage) == (
        "docs/releases/development-skills-v0-3/dias/EXACT_RECEIPT.json",
    )
    bad = json.loads(json.dumps(lineage))
    bad["pip"]["logical_changes"][0]["path"] = "src/ovc/unsafe.py"
    bad["pip_id"] = hashlib.sha256(json.dumps(bad["pip"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    with pytest.raises(RuntimeError, match="NOT_EXACT_SELECTED_CLASS"):
        validate_exact_selected_class(root=ROOT, lineage_record=bad)


def test_wp6_artifacts_bind_canonical_ids_and_pending_live_pilot() -> None:
    for name in (
        "DIASI_WP6_LIVE_PILOT_AUTHORITY_MANIFEST.json",
        "DIASI_WP6_LIVE_PILOT_DEPENDENCY_FRONTIER.json",
        "DIASI_WP6_VIT_AUTHORITY_MANIFEST.json",
        "DIASI_WP6_VIT_DEPENDENCY_FRONTIER.json",
    ):
        binding = load(WP6 / name)
        assert binding["logical_id"] == canonical_id(binding["payload"])
    drain = load(WP6 / "DIASI_WP6_IN_FLIGHT_DRAIN_RECORD.json")
    assert drain["counts"]["unknown"] == drain["counts"]["undispositioned"] == 0
    state = load(ROOT / "registries/implementation/dias_v0_1/DIASI_CURRENT_v0_9.json")
    assert state["next_packet"] == "DIASI-WP6-LIVE-PILOT"
    assert state["retirement"] is False and state["proof_substitution"] is False
