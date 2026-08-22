from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.shared_systems.envelopes import (
    AdapterDescriptor, CompatibilityContract, DependencyDescriptor, EvidenceEntry,
    EvidenceFrontier, InterfaceBinding, LineageEdgeEnvelope, OwnerExtensionRegistry,
    SharedEnvelopeError, StatePlaneValue, StateVector,
    research_operations_legacy_state,
)

ROOT = Path(__file__).resolve().parents[2]


def registry() -> OwnerExtensionRegistry:
    raw = json.loads((ROOT / "registries/shared_systems/envelopes/OWNER_EXTENSION_REGISTRY_v0_1.json").read_text(encoding="utf-8"))
    return OwnerExtensionRegistry(raw["entries"])


def test_state_planes_are_orthogonal_and_do_not_imply_authority() -> None:
    vector = StateVector((
        StatePlaneValue("LIFECYCLE", "RO", "FROZEN"),
        StatePlaneValue("AVAILABILITY", "RO", "AVAILABLE"),
    ))
    assert vector.authority("RO") == "UNKNOWN"
    assert vector.value("LIFECYCLE", "RO").owner_state == "FROZEN"


def test_ro_frozen_legacy_correction_preserves_record_state_not_authority() -> None:
    vector = research_operations_legacy_state(lifecycle_state="FROZEN", authority_state="FROZEN")
    assert vector.value("LIFECYCLE", "RESEARCH_OPERATIONS").owner_state == "FROZEN"
    assert vector.authority("RESEARCH_OPERATIONS") == "UNKNOWN"


def test_duplicate_and_authorising_state_planes_fail_closed() -> None:
    state = StatePlaneValue("LIFECYCLE", "RO", "FROZEN")
    with pytest.raises(SharedEnvelopeError, match="AMBIGUOUS"):
        StateVector((state, state))
    with pytest.raises(SharedEnvelopeError, match="AUTHORITY_EFFECT_FORBIDDEN"):
        StatePlaneValue("LIFECYCLE", "RO", "FROZEN", authority_effect="GRANT")


def test_evidence_cutoff_and_latest_required_fvt_are_enforced() -> None:
    entry = EvidenceEntry("E1", "D1", "2026-08-01T11:00:00Z", "GEN.1")
    frontier = EvidenceFrontier("F1", "0.1", "ESL", "2026-08-01T12:00:00Z", "D.v1", (entry,), (), "2026-08-01T11:00:00Z", ("GEN.1",))
    assert frontier.evidence_entries == (entry,)
    with pytest.raises(SharedEnvelopeError, match="AFTER_CUTOFF"):
        EvidenceFrontier("F2", "0.1", "ESL", "2026-08-01T10:00:00Z", "D.v1", (entry,), (), None, ("GEN.1",))
    with pytest.raises(SharedEnvelopeError, match="UNBOUND"):
        EvidenceFrontier("F3", "0.1", "ESL", "2026-08-01T12:00:00Z", "D.v1", (entry,), (), "2026-08-01T10:00:00Z", ("GEN.1",))


def test_present_missing_conflict_fails_closed() -> None:
    entry = EvidenceEntry("E1", "D1", "2026-08-01T11:00:00Z", "GEN.1")
    with pytest.raises(SharedEnvelopeError, match="PRESENT_MISSING_CONFLICT"):
        EvidenceFrontier("F", "0.1", "ESL", "2026-08-01T12:00:00Z", "D.v1", (entry,), ("E1",), None, ("GEN.1",))


def test_missingness_affects_only_declared_surface() -> None:
    dep = DependencyDescriptor("D.OPTIONAL", "OPTIONAL", "ALLOWED", "detail", "EVALUATOR", "OPTIONAL_MISSING", "ESL", ("detail_panel",))
    assert dep.missing_disposition() == {"status":"MISSING_OPTIONAL", "affected_surfaces":("detail_panel",), "reason_code":"OPTIONAL_MISSING"}
    forbidden = DependencyDescriptor("D.VALIDATION", "CONDITIONAL", "FORBIDDEN", "protected", "EVALUATOR", "ACCESS_DENIED", "VALIDATION", ("validation_panel",))
    assert forbidden.missing_disposition()["status"] == "FORBIDDEN"


def test_owner_predicates_are_closed_and_global_parent_is_forbidden() -> None:
    edge = LineageEdgeEnvelope("E", "GENEALOGY", "ESL", "EPISODE_SPLIT_FROM", "OLD", "NEW", "ESL.v1", "LINEAGE_PREDICATE")
    edge.validate(registry())
    with pytest.raises(SharedEnvelopeError, match="GLOBAL_PARENT"):
        LineageEdgeEnvelope("E", "GENEALOGY", "ESL", "PARENT", "OLD", "NEW", "ESL.v1", "LINEAGE_PREDICATE").validate(registry())
    with pytest.raises(SharedEnvelopeError, match="OWNER_EXTENSION_UNKNOWN"):
        LineageEdgeEnvelope("E", "GENEALOGY", "UNKNOWN", "SPLIT", "OLD", "NEW", "X", "LINEAGE_PREDICATE").validate(registry())


def test_adapter_maps_only_source_fields_and_declares_every_loss() -> None:
    adapter = AdapterDescriptor("A1", "ESL", "ESL.CONTRACT.v1", "CONSUMER.CONTRACT.v1", (("old_name", "new_name"),), ("legacy_note",))
    assert adapter.adapt({"old_name": 7, "legacy_note": "x"}) == {"new_name": 7}
    with pytest.raises(SharedEnvelopeError, match="UNDECLARED_LOSS"):
        adapter.adapt({"old_name": 7, "hidden": 8, "legacy_note": "x"})
    with pytest.raises(SharedEnvelopeError, match="FABRICATION"):
        AdapterDescriptor("A2", "ESL", "ESL.v1", "C.v1", (), (), ("invent_default",))


def test_interface_requires_exact_compatibility_and_matching_adapter() -> None:
    compatibility = CompatibilityContract("C1", "ESL.CONTRACT.v1", "CONSUMER.CONTRACT.v1", "LOSSY_ADAPTER_ALLOWED", "episode", ("EXACT_FIELDS",), ("legacy_note",))
    adapter = AdapterDescriptor("A1", "ESL", "ESL.CONTRACT.v1", "CONSUMER.CONTRACT.v1", (("old_name", "new_name"),), ("legacy_note",))
    binding = InterfaceBinding("I1", "ESL", "CONSUMER", "ESL.CONTRACT.v1", "CONSUMER.CONTRACT.v1", ("schema.v1",), ("profile.v1",), ("producer=1",), "INPUT", "C1", "A1")
    binding.validate(compatibility, adapter)
    with pytest.raises(SharedEnvelopeError, match="LATEST"):
        InterfaceBinding("I2", "ESL", "C", "ESL.latest", "C.v1", ("s",), ("p",), ("g",), "INPUT", "C1")
