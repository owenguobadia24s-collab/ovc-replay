from __future__ import annotations

import ast
import hashlib
import itertools
import json
from pathlib import Path

import pytest

from ovc.research_operations.rrscg import d10_reference_core, d9_reference_core
from ovc.research_operations.rrscg.d10 import (
    D10_ALGORITHM_ID,
    D10_CAPABILITY_STATE,
    D10_CLAIM_CAP,
    D10_PACKAGE_SHA256,
    D10_RELEASE_BINDING_SHA256,
    D10_RELEASE_BUNDLE_SHA256,
    D10ReducerBindingError,
    reduce_d9_state,
)
from ovc.research_operations.rrscg.d9 import D9StateRecord, build_observer_state
from ovc.research_operations.rrscg.kernel import (
    PRIMARY_CONSTRAINT_VIEWS,
    PRIMARY_TARGET_PACK,
    ConstraintViewEvidence,
    compose_constraint_event,
)

ROOT = Path(__file__).resolve().parents[3]
ORACLE = ROOT / "tests/fixtures/research_operations/rrscg/RRSCG_D10_EXACT_REDUCER_ORACLE_v0_1.json"


def _load_oracle():
    return json.loads(ORACLE.read_text(encoding="utf-8"))


def _state(rows, event_id="D10-EVENT"):
    derived = [d9_reference_core._derive_view(row, 2, 2) for row in rows]
    parent_q, parent_tier = d10_reference_core._select_reducer(
        derived, d10_reference_core._D9_CONTROL_HIERARCHY
    )
    payload = d9_reference_core._build_state(
        "RRSCG_D9_REPOSITORY_NATIVE_v1",
        rows,
        2,
        2,
        {
            "selected_frontier_target_ids": parent_q,
            "relation_resolved": bool(parent_q),
            "selected_resolution_tier": None if parent_tier == "NONE" else parent_tier,
            "full_consensus_state": "TEST_CONTROL",
        },
    )
    return D9StateRecord(event_id, "D10-SYNTH", "SEG-D10", payload)


def _rows(support_bits, target_bits):
    return [
        {
            "view_id": view_id,
            "source_evaluable": True,
            "comparable": True,
            "antecedent_support_count": 2 if support else 0,
            "relation_support_records": ([{"target_id": "T", "support_count": 2}] if target else []),
        }
        for view_id, support, target in zip(PRIMARY_CONSTRAINT_VIEWS, support_bits, target_bits)
    ]


def test_exact_source_and_release_identities_are_pinned():
    oracle = _load_oracle()
    assert D10_ALGORITHM_ID == oracle["algorithm_id"]
    assert D10_PACKAGE_SHA256 == oracle["source_archive"]["sha256"]
    assert D10_RELEASE_BUNDLE_SHA256 == oracle["release_bundle"]["sha256"]
    assert D10_RELEASE_BINDING_SHA256 == oracle["release_bundle"]["release_binding_sha256"]
    assert oracle["source_archive"]["internal_sha256sum_entries_verified"] == 64
    assert oracle["release_bundle"]["standalone_equals_nested_release_bytes"] is True
    assert oracle["bound_source_hashes"]["immutable_parent_r2_sha256"] == (
        "5426cd9340c93a2aff0f5c8f3093f9db876647d1790aaa82da3e444a4f3029b5"
    )


def test_exact_reducer_function_source_segment_is_unchanged():
    oracle = _load_oracle()
    source = Path(d10_reference_core.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_select_reducer")
    segment = ast.get_source_segment(source, node)
    assert hashlib.sha256(segment.encode()).hexdigest() == (
        oracle["reference_function_source_sha256"]["_select_reducer"]
    )


def test_repository_reducer_matches_exact_reference_for_all_1024_boolean_cases():
    count = 0
    for bits in itertools.product((False, True), repeat=10):
        support_bits = bits[:5]
        target_bits = bits[5:]
        state = _state(_rows(support_bits, target_bits), event_id=f"CASE-{count:04d}")
        expected_q, expected_tier = d10_reference_core._select_reducer(
            state.state_shape_payload["view_evidence_records"],
            d10_reference_core._D10_SUCCESSOR_HIERARCHY,
        )
        actual = reduce_d9_state(state)
        assert list(actual.selected_frontier) == expected_q
        assert actual.selected_resolution_tier == expected_tier
        assert actual.relation_resolved is bool(expected_q)
        count += 1
    assert count == 1024


def test_d10_changes_only_d9_minimal_to_c_last_family_subset():
    memberships = {
        "C_LAST_EXACT": ("T1",),
        "C_LAST_HI": ("T1",),
        "C_LAST_MID": ("T1", "T2"),
        "CARRIER_BAG_HI": ("T2",),
        "CARRIER_BAG_MID": ("T2",),
    }
    rows = [
        {
            "view_id": view_id,
            "source_evaluable": True,
            "comparable": True,
            "antecedent_support_count": 2,
            "relation_support_records": [
                {"target_id": target, "support_count": 2} for target in memberships[view_id]
            ],
        }
        for view_id in PRIMARY_CONSTRAINT_VIEWS
    ]
    d9_state = _state(rows)
    assert d9_state.state_shape_payload["resolution_tier"] == "MINIMAL_CONSTRAINT"
    assert d9_state.state_shape_payload["Q"]["target_ids"] == ["T1", "T2"]
    d10 = reduce_d9_state(d9_state)
    assert d10.selected_resolution_tier == "C_LAST_FAMILY_CONSENSUS"
    assert d10.selected_frontier == ("T1",)
    assert set(d10.selected_frontier) < set(d9_state.state_shape_payload["Q"]["target_ids"])


def test_d9_control_is_unchanged_outside_the_frozen_delta():
    cases = [
        _rows((True,) * 5, (True,) * 5),
        _rows((False, True, True, False, True), (False, True, True, False, True)),
        _rows((False, False, True, False, False), (False, False, True, False, False)),
        _rows((False,) * 5, (False,) * 5),
    ]
    for index, rows in enumerate(cases):
        d9_state = _state(rows, event_id=f"CONTROL-{index}")
        d10 = reduce_d9_state(d9_state)
        assert list(d10.selected_frontier) == d9_state.state_shape_payload["Q"]["target_ids"]
        assert d10.selected_resolution_tier == (d9_state.state_shape_payload["resolution_tier"] or "NONE")


def test_forged_parent_d9_control_fails_closed():
    state = _state(_rows((True,) * 5, (True,) * 5))
    forged_payload = dict(state.state_shape_payload)
    forged_payload["Q"] = {"status": "EVALUABLE", "target_ids": ["FORGED"]}
    forged = D9StateRecord(
        event_id=state.event_id,
        source_generation_id=state.source_generation_id,
        stream_segment_id=state.stream_segment_id,
        state_shape_payload=forged_payload,
    )
    with pytest.raises(D10ReducerBindingError, match="IMMUTABLE_PARENT_R2_CONTROL_MISMATCH"):
        reduce_d9_state(forged)


def test_capability_remains_inactive_and_descriptive_only():
    assert D10_CAPABILITY_STATE == "INACTIVE"
    assert D10_CLAIM_CAP == "DESCRIPTIVE_DEVELOPMENT_ONLY"
    source = Path(__import__("ovc.research_operations.rrscg.d10", fromlist=["x"]).__file__).read_text()
    forbidden = ("probability", "risk", "exposure", "trading", "execution")
    assert all(f"def {name}" not in source.lower() for name in forbidden)
