from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.p2cti.identity import (
    entry_id,
    generation_id,
    logical_id,
    series_id,
    source_frontier_id,
)
from ovc.research_operations.p2cti.sources import OwnerSourceReference, require_reference_only
from ovc.research_operations.p2cti.state import TheoryStatePlanes, infer_authority_from_state

ROOT = Path(__file__).resolve().parents[3]


def test_identity_is_deterministic_and_physical_provenance_is_excluded():
    series = series_id()
    entry_a = entry_id(
        series=series,
        subject_id="TH-TEST-001",
        subject_class="IN_HOUSE_THEORY_RECORD",
        owner_object_id="ro:p2:theory:" + "a" * 64,
        owner_semantic_generation="0.1",
    )
    entry_b = entry_id(
        series=series,
        subject_id="TH-TEST-001",
        subject_class="IN_HOUSE_THEORY_RECORD",
        owner_object_id="ro:p2:theory:" + "a" * 64,
        owner_semantic_generation="0.1",
    )
    assert entry_a == entry_b
    assert entry_a.startswith("p2cti:entry:")

    with pytest.raises(ValueError, match="physical provenance"):
        logical_id("entry", {"subject_id": "TH-TEST-001", "pr_number": 1020})


def test_generation_membership_is_order_independent_but_duplicates_fail():
    series = series_id()
    frontier = source_frontier_id([
        {"owner_programme": "A", "source_ref": "a", "semantic_generation": "1", "source_sha256": "1" * 64},
        {"owner_programme": "B", "source_ref": "b", "semantic_generation": "1", "source_sha256": "2" * 64},
    ])
    a = "p2cti:entry:" + "a" * 64
    b = "p2cti:entry:" + "b" * 64
    assert generation_id(series=series, generation_ordinal=0, member_entry_ids=[a, b], source_frontier=frontier) == generation_id(
        series=series, generation_ordinal=0, member_entry_ids=[b, a], source_frontier=frontier
    )
    with pytest.raises(ValueError, match="unique"):
        generation_id(series=series, generation_ordinal=0, member_entry_ids=[a, a], source_frontier=frontier)


def test_owner_adapter_is_reference_only():
    ref = OwnerSourceReference(
        owner_programme="RESEARCH_OPERATIONS_DMRP_PATH2",
        object_type="THEORY_RECORD",
        object_id="ro:p2:theory:" + "a" * 64,
        semantic_generation="0.1",
        source_path="records/research_operations/path2/example.json",
        content_sha256="b" * 64,
        authority_refs=("authority:example",),
    )
    payload = {"source_object_ref": ref.as_reference(), "subject_id": "TH-TEST-001"}
    require_reference_only(payload)
    assert payload["source_object_ref"]["scientific_payload_copied"] is False
    assert "scientific_payload" not in payload

    with pytest.raises(ValueError, match="owner scientific payload"):
        require_reference_only({**payload, "proposition": "copied owner science"})


def test_state_planes_are_orthogonal_and_do_not_infer_authority():
    state = TheoryStatePlanes(
        theory_lifecycle="FROZEN",
        evidence="UNTESTED",
        p2_frontier="P2-5",
        formalisation="PREREGISTRATION",
        candidate_relation="NONE",
        currentness="CURRENT_WITH_LIMITATION",
        authority_refs=("authority:path2",),
    )
    assert state.as_dict()["evidence"] == "UNTESTED"
    assert state.as_dict()["candidate_relation"] == "NONE"
    with pytest.raises(RuntimeError, match="forbids authority inference"):
        infer_authority_from_state(state)


def test_registries_contain_required_non_transitivity_and_reason_codes():
    state_registry = json.loads((ROOT / "registries/research_operations/p2cti/P2CTI_STATE_PLANE_REGISTRY_v0_1.json").read_text())
    reason_registry = json.loads((ROOT / "registries/research_operations/p2cti/P2CTI_REASON_CODE_REGISTRY_v0_1.json").read_text())
    assert "OWNER_AUTHORITY_NE_P2CTI_AUTHORITY" in state_registry["non_transitivity"]
    codes = {item["code"] for item in reason_registry["reason_codes"]}
    assert {
        "BOOTSTRAP_SOURCE_CENSUS_FAIL",
        "STATE_OWNER_CONFLICT",
        "CURRENTNESS_UNRESOLVED",
        "RELATION_CONFLICT",
        "DUPLICATE_AMBIGUITY",
        "MODE_LEAK",
        "PROTECTED_SOURCE_LEAK",
        "REFERENCE_DIVERGENCE",
        "REBUILD_DIVERGENCE",
        "CAPACITY_EXCEEDED",
        "DESIGN_CONTRADICTION",
        "AUTHORITY_AMBIGUITY",
    } <= codes
