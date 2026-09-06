from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from ovc.research_operations.rrscg import kernel
from ovc.research_operations.rrscg.d9 import (
    D9BindingError,
    D9_ALGORITHM_ID,
    D9_CAPABILITY_STATE,
    D9_CLAIM_CAP,
    D9_IMPLEMENTATION_SOURCE_SHA256,
    build_observer_motion,
    build_observer_state,
    build_observer_trajectory,
)
from ovc.research_operations.rrscg import d9_reference_core

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests/fixtures/research_operations/rrscg/RRSCG_D9_EXACT_CORE_SOURCE_SHA256_v0_1.json"


def _raw(target: str, support: int = 2):
    return [
        {
            "view_id": view_id,
            "source_evaluable": True,
            "comparable": True,
            "antecedent_support_count": support,
            "relation_support_records": [{"target_id": target, "support_count": 2}],
        }
        for view_id in kernel.PRIMARY_CONSTRAINT_VIEWS
    ]


def _event(event_id: str, target: str, source_generation_id: str = "SYNTH-D9-REPO"):
    views = []
    for row in _raw(target):
        views.append(
            kernel.ConstraintViewEvidence(
                view_id=row["view_id"],
                supported=True,
                antecedent_support=2,
                qualified_frontier_supports=((target, 2),),
                observed_frontier_supports=((target, 2),),
                target_pack_id=kernel.PRIMARY_TARGET_PACK,
                relation_min=2,
                training_frontier_id="frontier",
                source_generation_id=source_generation_id,
            )
        )
    return kernel.compose_constraint_event(
        event_id,
        source_generation_id,
        views,
        kernel.PRIMARY_TARGET_PACK,
        2,
        2,
    )


def test_exact_d9_core_function_source_segments_are_unchanged():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    path = Path(d9_reference_core.__file__)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    found = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in fixture["functions"]:
            found[node.name] = hashlib.sha256(ast.get_source_segment(source, node).encode()).hexdigest()
    assert found == fixture["functions"]


def test_d9_transport_is_inactive_and_descriptive_only():
    assert D9_ALGORITHM_ID == "OVC-EML-GRAMMAR-0003-RRSCG-DYNAMICS-ALGORITHM-0.2-D9"
    assert D9_IMPLEMENTATION_SOURCE_SHA256 == "15c4f3c5bca53e40894c54c8d4cffdca2675a8f62a537efe1b2533efb09bb23a"
    assert D9_CAPABILITY_STATE == "INACTIVE"
    assert D9_CLAIM_CAP == "DESCRIPTIVE_DEVELOPMENT_ONLY"


def test_repository_r2_binds_exact_d9_state_and_motion_mechanics():
    e1 = _event("EV1", "T1")
    e2 = _event("EV2", "T2")
    s1 = build_observer_state(e1, _raw("T1"), stream_segment_id="SEG-A")
    s2 = build_observer_state(e2, _raw("T2"), stream_segment_id="SEG-A")
    assert s1.state_shape_payload["Q"]["target_ids"] == ["T1"]
    assert s2.state_shape_payload["Q"]["target_ids"] == ["T2"]
    motion = build_observer_motion(s1, s2)
    assert motion.motion_shape_payload["q_transition_status"] == "RESOLVED_TO_RESOLVED"
    assert motion.motion_shape_payload["D_Q"]["status"] == "VALUE"
    assert motion.motion_shape_payload["D_Q"]["value"] == {"numerator": 1, "denominator": 1}


def test_d9_adapter_rejects_parent_r2_mismatch():
    event = _event("EV1", "T1")
    bad = _raw("T1")
    bad[0]["relation_support_records"] = [{"target_id": "FORGED", "support_count": 2}]
    with pytest.raises(D9BindingError, match="D9_R2_QUALIFIED_FRONTIER_MISMATCH|D9_R2_RELATION_SUPPORT_MISMATCH"):
        build_observer_state(event, bad, stream_segment_id="SEG-A")


def test_motion_cannot_cross_generation_or_segment():
    a = build_observer_state(_event("A", "T1", "GEN-A"), _raw("T1"), stream_segment_id="SEG-A")
    b = build_observer_state(_event("B", "T1", "GEN-B"), _raw("T1"), stream_segment_id="SEG-A")
    with pytest.raises(D9BindingError, match="CROSS_GENERATION"):
        build_observer_motion(a, b)
    c = build_observer_state(_event("C", "T1", "GEN-A"), _raw("T1"), stream_segment_id="SEG-B")
    with pytest.raises(D9BindingError, match="CROSS_SEGMENT"):
        build_observer_motion(a, c)


def test_trajectory_breaks_motion_at_segment_boundary():
    records = [
        (_event("E1", "T1"), _raw("T1"), "A"),
        (_event("E2", "T1"), _raw("T1"), "A"),
        (_event("E3", "T2"), _raw("T2"), "B"),
    ]
    states, motions = build_observer_trajectory(records)
    assert len(states) == 3
    assert len(motions) == 1
    assert motions[0].predecessor_event_id == "E1"
    assert motions[0].current_event_id == "E2"
