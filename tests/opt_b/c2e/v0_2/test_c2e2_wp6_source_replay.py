from __future__ import annotations

import copy

from ovc.opt_b.c2e_v2.candidate import build_candidate
from ovc.opt_b.c2e_v2.lifecycle import EpisodeEngine
from ovc.opt_b.c2e_v2.source_replay import comparison_source, population_identity
from ovc.opt_b.c2e_v2.source_replay_runtime import _dependencies
from ovc.opt_b.c2e_v2.stable_signatures import build_comparison_signatures


def _frame(parent_status: str = "NOT_COMPUTABLE") -> dict:
    return {
        "frame_id": "C2E.FRAME.TEST",
        "chronology": {"first_valid_time": "2026-06-01T00:15:00Z"},
        "evidence": {
            "dependency_results": [
                {"dependency_id": "DEP.CONTINUITY", "role": "REQUIRED", "status": "AVAILABLE", "source_record_ids": [], "reason_codes": []},
                {"dependency_id": "DEP.STRUCTURAL", "role": "REQUIRED", "status": "AVAILABLE", "source_record_ids": [], "reason_codes": []},
                {"dependency_id": "DEP.PARENT_CONTEXT", "role": "OPTIONAL", "status": parent_status, "source_record_ids": [], "reason_codes": ["NO_PARENT"] if parent_status != "AVAILABLE" else []},
            ]
        },
    }


def _rule(rule_id: str, candidate_type: str, action: str, priority: int, required: list[str], optional: list[str]) -> dict:
    return {
        "boundary_rule_id": rule_id,
        "candidate_type": candidate_type,
        "lifecycle_action": action,
        "priority_class": priority,
        "dependencies": {
            "REQUIRED": required,
            "OPTIONAL": optional,
            "WARNING": [],
            "ONE_OF": [],
            "PROHIBITED": ["FDI_C2G", "OUTCOME", "VALIDATION", "C2_5", "C3"],
        },
    }


def test_rule_scoped_parent_dependency_blocks_reparent_but_not_continuation() -> None:
    frame = _frame("NOT_COMPUTABLE")
    reparent = build_candidate(
        _rule("R.REPARENT", "RE_PARENT_CANDIDATE", "RE_PARENT", 4, ["DEP.PARENT_CONTEXT"], []),
        frame,
        matched=True,
        effective_time="2026-06-01T00:15:00Z",
    )
    continuation = build_candidate(
        _rule("R.CONT", "CONTINUATION_CANDIDATE", "CONTINUATION", 7, ["DEP.CONTINUITY", "DEP.STRUCTURAL"], ["DEP.PARENT_CONTEXT"]),
        frame,
        matched=True,
        effective_time="2026-06-01T00:15:00Z",
    )
    assert reparent is not None and reparent["evaluable"] is False
    assert "DEP_REQUIRED_NOT_EVALUABLE:DEP.PARENT_CONTEXT" in reparent["reason_codes"]
    assert continuation is not None and continuation["evaluable"] is True
    assert "DEPENDENCY_WARNING:DEP.PARENT_CONTEXT" in continuation["warning_reason_codes"]


def test_prohibited_dependencies_are_not_required_as_handoff_rows() -> None:
    frame = _frame("AVAILABLE")
    candidate = build_candidate(
        _rule("R.CONT", "CONTINUATION_CANDIDATE", "CONTINUATION", 7, ["DEP.CONTINUITY", "DEP.STRUCTURAL"], ["DEP.PARENT_CONTEXT"]),
        frame,
        matched=True,
        effective_time="2026-06-01T00:15:00Z",
    )
    assert candidate is not None and candidate["evaluable"] is True


def test_reparent_is_upstream_boundary_event_not_c2e_topology() -> None:
    engine = EpisodeEngine("C2E.BOUNDARY.PACK.TEST")
    frame = {
        "frame_id": "C2E.FRAME.TEST",
        "identity": {"scope_id": "LOCAL_15M", "scale_id": "15M", "instrument_id": "GBPUSD", "side": "BID"},
        "source_binding": {"source_release_id": "SOURCE.TEST"},
    }
    genesis = engine.birth(
        frame=frame,
        boundary_rule_id="R.BIRTH",
        candidate_id="C.BIRTH",
        effective_time="2026-06-01T00:15:00Z",
        first_valid_time="2026-06-01T00:15:00Z",
    )
    event = engine.re_parent(
        episode_id=genesis["episode_id"],
        candidate_id="C.REPARENT",
        effective_time="2026-06-01T02:00:00Z",
        first_valid_time="2026-06-01T02:00:00Z",
    )
    assert event["lifecycle_action"] == "RE_PARENT"
    assert engine.topology.edges == []


def _source(wrapper: str) -> tuple[dict, dict, dict, dict, dict]:
    level_id = f"L.{wrapper}"
    container_id = f"C.{wrapper}"
    level = {
        "level_id": level_id,
        "horizon_id": "H4",
        "level_type": "HIGH",
        "origin": "TRAILING_RANGE",
        "structural_depth": "NA",
        "value": "1.25000",
    }
    container = {
        "container_id": container_id,
        "horizon_id": "H4",
        "kind": "MEASUREMENT",
        "origin": "TRAILING_RANGE",
        "structural_depth": "NA",
        "pairing_policy_id": "PAIR.RAW",
        "lower_value": "1.24000",
        "upper_value": "1.26000",
        "centre": "1.25000",
        "width": "0.02000",
    }
    location = {
        "axis": "LOCATION", "computability": "COMPUTABLE", "reason_codes": [],
        "semantic_label": None, "selected_object_id": None, "fallback_object_id": None, "numeric_thresholds": [],
        "facts": {"complete_scoped_inventory": True, "exclusions": [], "relations": [{
            "relation_id": f"REL.{wrapper}", "subject_probe_id": f"PROBE.{wrapper}",
            "first_valid_time": "2026-06-01T00:15:00Z", "object_id": level_id, "object_kind": "LEVEL",
            "topology": "BELOW", "mode": "CAUSAL_AS_OF", "source_precision": 5,
            "absolute_distance": "0.00100", "signed_distance": "-0.00100", "equal_at_source_precision": False,
        }]},
    }
    motions = []
    for horizon, delta in (("H4", "0.00010"), ("H8", "0.00020"), ("H16", "0.00030")):
        motions.append({
            "axis": "MOTION", "computability": "COMPUTABLE", "reason_codes": [],
            "semantic_label": None, "selected_object_id": None, "fallback_object_id": None, "numeric_thresholds": [],
            "facts": {"horizon_id": horizon, "membership_status": "COMPLETE", "price_delta": delta, "relation_deltas": [], "member_observation_ids": [f"OBS.{wrapper}"]},
        })
    organisation = {
        "axis": "ORGANISATION", "computability": "COMPUTABLE", "reason_codes": [],
        "semantic_label": None, "selected_object_id": None, "fallback_object_id": None, "numeric_thresholds": [],
        "facts": {"complete_inventory": True, "containers": [{"container_id": container_id}], "container_edges": [], "swing_graph": None},
    }
    interaction = {
        "axis": "INTERACTION", "computability": "COMPUTABLE", "reason_codes": [],
        "semantic_label": None, "selected_object_id": None, "fallback_object_id": None, "numeric_thresholds": [],
        "facts": {"crossings": [], "reference_changes": [], "relation_deltas": []},
    }
    profiles = {f"P.LOC.{wrapper}": location, f"P.ORG.{wrapper}": organisation, f"P.INT.{wrapper}": interaction}
    motion_ids = []
    for index, motion in enumerate(motions):
        key = f"P.M{index}.{wrapper}"; profiles[key] = motion; motion_ids.append(key)
    bundle = {
        "context_bundle_id": f"CTX.{wrapper}",
        "profile_output_ids": {"LOCATION": [f"P.LOC.{wrapper}"], "MOTION": motion_ids, "ORGANISATION": [f"P.ORG.{wrapper}"], "INTERACTION": [f"P.INT.{wrapper}"]},
    }
    contexts = {f"CTX.{wrapper}": {"fixed_parent_observation_link": {"computability": "COMPUTABLE", "parent_observation_id": "PARENT.STABLE", "reason_codes": [], "link_id": f"LINK.{wrapper}"}}}
    return bundle, profiles, contexts, {level_id: level}, {container_id: container}


def test_stable_projection_ignores_wrapper_identity_churn() -> None:
    b1, p1, c1, l1, k1 = _source("A")
    b2, p2, c2, l2, k2 = _source("B")
    s1 = build_comparison_signatures(comparison_source(b1, p1, c1, l1, k1))
    s2 = build_comparison_signatures(comparison_source(b2, p2, c2, l2, k2))
    assert s1["structural_signature_sha256"] == s2["structural_signature_sha256"]
    assert s1["parent_signature_sha256"] == s2["parent_signature_sha256"]


def test_runtime_dependency_rows_are_upstream_only() -> None:
    bundle = {"observation_id": "OBS", "context_bundle_id": "CTX", "profile_output_ids": {"LOCATION": ["L"], "MOTION": ["M1", "M2", "M3"], "ORGANISATION": ["O"], "INTERACTION": ["I"]}}
    profiles = {key: {"computability": "COMPUTABLE"} for key in ("L", "M1", "M2", "M3", "O", "I")}
    context = {"fixed_parent_observation_link": {"computability": "NOT_COMPUTABLE", "parent_observation_id": None, "reason_codes": ["NO_PARENT"]}}
    rows = _dependencies(bundle, profiles, context)
    assert {row["dependency_id"] for row in rows} == {"DEP.CONTINUITY", "DEP.SOURCE_RELEASE", "DEP.STRUCTURAL", "DEP.PARENT_CONTEXT"}
    assert not {"FDI_C2G", "OUTCOME", "VALIDATION", "C2_5", "C3"}.intersection(row["dependency_id"] for row in rows)


def test_population_identity_is_order_invariant() -> None:
    manifest = {"materialisation_id": "MAT"}
    rows = [
        {"observation_id": "B", "side": "BID", "first_valid_time": "2026-06-01T00:30:00Z", "context_bundle_id": "C2", "profile_output_ids": {"LOCATION": ["2"]}},
        {"observation_id": "A", "side": "ASK", "first_valid_time": "2026-06-01T00:15:00Z", "context_bundle_id": "C1", "profile_output_ids": {"LOCATION": ["1"]}},
    ]
    assert population_identity(rows, manifest) == population_identity(list(reversed(copy.deepcopy(rows))), manifest)
