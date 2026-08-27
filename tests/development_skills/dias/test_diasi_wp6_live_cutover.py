import json
from pathlib import Path

import pytest

from ovc.development.skills.dias_cutover import (
    ACTIVE_GENERATION,
    DiasCutoverError,
    SELECTED_CLASS,
    SUCCESSOR_WRITER,
    validate_live_registry,
    writer_accepts,
)
from tools.ci.vit_qualification_owner import validate_exact_selected_class


ROOT = Path(__file__).resolve().parents[3]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_successor_route_has_no_retired_authority_and_uses_advanced_fence() -> None:
    registry = load(ROOT / "registries/development/skills/VIT_SELECTED_CLASS_ROUTE_v0_1.json")
    state = validate_live_registry(registry)
    assert state.route_generation == state.writer_generation == ACTIVE_GENERATION == 3
    assert "old_route" not in registry and "incumbent_writer" not in registry
    assert registry["non_selected_classes"] == "SCOPED_NOT_RETIRED_UNCHANGED"


def test_every_pre_removal_generation_is_stale_or_unauthorised() -> None:
    for generation in (1, 2):
        with pytest.raises(DiasCutoverError, match="STALE_WRITER_FENCE"):
            writer_accepts(writer=SUCCESSOR_WRITER, generation=generation, packet_class=SELECTED_CLASS)
    with pytest.raises(DiasCutoverError, match="WRITER_NOT_AUTHORISED"):
        writer_accepts(writer="PES", generation=ACTIVE_GENERATION, packet_class=SELECTED_CLASS)
    assert writer_accepts(writer=SUCCESSOR_WRITER, generation=ACTIVE_GENERATION, packet_class=SELECTED_CLASS)


def test_selected_class_derivation_remains_receipt_path_bound() -> None:
    import hashlib
    lineage = {
        "schema": "ovc-vit-payload-lineage/v2",
        "status": "PAYLOAD_ADMITTED",
        "programme_id": "OVC-DIAS-CONFORMANCE-v0.1",
        "packet_id": "DIASI-WP7B-POST-REMOVAL",
        "route_class": "VIT_MANDATORY",
        "pip": {
            "schema_version": "packet-integration-payload/v0.1",
            "programme_id": "OVC-DIAS-CONFORMANCE-v0.1",
            "packet_id": "DIASI-WP7B-POST-REMOVAL",
            "logical_changes": [{"op": "ADD", "path": "docs/releases/development-skills-v0-3/dias/POST_REMOVAL_RECEIPT.json", "blob_sha": "a" * 40, "mode": "100644"}],
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
        "docs/releases/development-skills-v0-3/dias/POST_REMOVAL_RECEIPT.json",
    )
