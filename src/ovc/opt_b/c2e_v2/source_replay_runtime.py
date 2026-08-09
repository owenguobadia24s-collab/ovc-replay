"""Canonical C2E2-WP6 runtime over the source-replay projection helpers.

The earlier source_replay module owns deterministic source loading/projection and
artifact writing.  This module is the only WP6 execution entrypoint.  It binds
rule-scoped dependency rows to the reverse-dependency firewall, consumes the
v2 stable-signature evaluator correctly, and drives the frozen lifecycle.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from . import source_replay as base
from .candidate import build_candidate
from .empirical_boundary_rules import evaluate_boundary_predicates as evaluate_legacy_predicates
from .empirical_boundary_rules_v2 import evaluate_boundary_predicates_v2
from .lifecycle import EpisodeEngine
from .resolver import resolve_candidates


def _dependencies(
    bundle: Mapping[str, Any],
    profiles: Mapping[str, Mapping[str, Any]],
    context: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Build only lawful upstream dependency rows.

    FDI/C2G/C2.5/C3 and other downstream names MUST NOT be inserted as
    dependency-result rows merely to say they are absent: the handoff firewall
    correctly rejects those namespaces.  Their absence is enforced by the
    firewall and the boundary pack's PROHIBITED declarations.
    """
    fixed = context.get("fixed_parent_observation_link", {})
    parent_status = (
        "AVAILABLE"
        if fixed.get("computability") == "COMPUTABLE" and fixed.get("parent_observation_id")
        else "NOT_COMPUTABLE"
    )
    all_computable = all(
        profiles[profile_id].get("computability") == "COMPUTABLE"
        for ids in bundle["profile_output_ids"].values()
        for profile_id in ids
    )
    return sorted(
        [
            {
                "dependency_id": "DEP.CONTINUITY",
                "role": "REQUIRED",
                "status": "AVAILABLE",
                "source_record_ids": [str(bundle["observation_id"])],
                "reason_codes": [],
            },
            {
                "dependency_id": "DEP.SOURCE_RELEASE",
                "role": "REQUIRED",
                "status": "AVAILABLE",
                "source_record_ids": [],
                "reason_codes": [],
            },
            {
                "dependency_id": "DEP.STRUCTURAL",
                "role": "REQUIRED",
                "status": "AVAILABLE",
                "source_record_ids": sorted(
                    profile_id
                    for ids in bundle["profile_output_ids"].values()
                    for profile_id in ids
                ),
                "reason_codes": [] if all_computable else ["TECHNICAL_PARTIAL_COMPUTABILITY"],
            },
            {
                "dependency_id": "DEP.PARENT_CONTEXT",
                "role": "OPTIONAL",
                "status": parent_status,
                "source_record_ids": [str(bundle["context_bundle_id"])],
                "reason_codes": sorted(str(item) for item in fixed.get("reason_codes", [])),
            },
        ],
        key=lambda row: row["dependency_id"],
    )


# build_frame resolves this module-global helper at call time.  Binding the
# firewall-safe implementation here keeps projection code single-sourced while
# making source_replay_runtime the canonical execution entrypoint.
base._dependencies = _dependencies


def _rule(pack: Mapping[str, Any], rule_id: str) -> dict[str, Any]:
    for rule in pack["rules"]:
        if rule["boundary_rule_id"] == rule_id:
            return dict(rule)
    raise base.SourceReplayError(f"BOUNDARY_RULE_MISSING:{rule_id}")


def _source_ids(frame: Mapping[str, Any]) -> list[str]:
    structural = frame["structural"]
    return sorted(
        structural["location_record_ids"]
        + structural["motion_record_ids"]
        + structural["organisation_record_ids"]
        + structural["interaction_record_ids"]
    )


def run_source_replay(
    materialisation: Mapping[str, Any],
    pack: Mapping[str, Any],
    *,
    source_build_commit: str,
) -> base.ReplayResult:
    engine = EpisodeEngine(str(pack["boundary_pack_id"]))
    frame_index: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []
    blocked_candidates: list[dict[str, Any]] = []
    counters = {
        name: 0
        for name in (
            "birth",
            "continuation",
            "phase_mutation",
            "re_parent",
            "censor_gap",
            "censor_release_end",
            "legacy_disagreements",
            "candidate_not_evaluable",
            "resolver_conflicts",
        )
    }
    by_side = {"ASK": [], "BID": []}
    for bundle in materialisation["bundles"]:
        by_side[str(bundle["side"])].append(bundle)
    for side in by_side:
        by_side[side].sort(key=lambda row: (row["first_valid_time"], row["observation_id"]))

    phase_state: dict[str, tuple[str, list[str]]] = {}
    for side in ("ASK", "BID"):
        previous: dict[str, Any] | None = None
        active_episode_id: str | None = None
        for bundle in by_side[side]:
            frame = base.build_frame(
                bundle,
                predecessor_observation_id=(previous["identity"]["observation_id"] if previous else None),
                observations=materialisation["observations"],
                parent_observations=materialisation["parent_observations"],
                profiles=materialisation["profiles"],
                memberships=materialisation["memberships"],
                contexts=materialisation["contexts"],
                levels=materialisation["levels"],
                containers=materialisation["containers"],
                relation_sets=materialisation["relation_sets"],
                materialisation_manifest=materialisation["manifest"],
                source_build_commit=source_build_commit,
            )
            frame_index.append(
                {
                    "schema": "c2e_input_frame_index/v0_1",
                    "frame_id": frame["frame_id"],
                    "logical_hash": frame["logical_hash"],
                    "lineage_hash": frame["lineage_hash"],
                    "observation_id": frame["identity"]["observation_id"],
                    "side": side,
                    "first_valid_time": frame["chronology"]["first_valid_time"],
                    "continuity_segment_id": frame["chronology"]["continuity_segment_id"],
                    "predecessor_observation_id": frame["chronology"].get("predecessor_observation_id"),
                    "structural_signature_sha256": frame["comparison"]["structural_signature_sha256"],
                    "parent_signature_sha256": frame["comparison"]["parent_signature_sha256"],
                    "context_bundle_id": frame["context"].get("context_resolution_bundle_id"),
                    "source_relation_set_count": sum(
                        1
                        for item in frame["lineage"]["parent_record_ids"]
                        if str(item).startswith("C2.RELATION.SET.")
                    ),
                    "authority": "INACTIVE_NONCANONICAL_SHADOW",
                }
            )

            corrected_evaluation = evaluate_boundary_predicates_v2(frame, previous)
            legacy_evaluation = evaluate_legacy_predicates(frame, previous)
            corrected = corrected_evaluation["matched"]
            legacy = legacy_evaluation["matched"]
            if corrected != legacy:
                counters["legacy_disagreements"] += 1
                disagreements.append(
                    {
                        "schema": "c2e_boundary_disagreement/v0_1",
                        "side": side,
                        "frame_id": frame["frame_id"],
                        "first_valid_time": frame["chronology"]["first_valid_time"],
                        "corrected_matched_rules": corrected_evaluation["matched_rules"],
                        "legacy_matched_rules": legacy_evaluation["matched_rules"],
                        "authority": "COMPARATOR_ONLY",
                    }
                )

            candidates = []
            for rule_id in base.RULE_IDS:
                candidate = build_candidate(
                    _rule(pack, rule_id),
                    frame,
                    matched=bool(corrected[rule_id]),
                    effective_time=frame["chronology"]["first_valid_time"],
                )
                if candidate is not None:
                    if not candidate["evaluable"]:
                        counters["candidate_not_evaluable"] += 1
                        blocked_candidates.append(candidate)
                    candidates.append(candidate)
            resolved = resolve_candidates(pack, candidates)
            if resolved["status"] != "RESOLVED":
                counters["resolver_conflicts"] += 1
                raise base.SourceReplayError(
                    f"BOUNDARY_RESOLUTION_CONFLICT:{side}:{frame['frame_id']}:{resolved['reason_codes']}"
                )

            actions: list[str] = []
            for candidate in resolved["resolved"]:
                action = candidate["lifecycle_action"]
                if action == "CENSOR_GAP":
                    base._require(active_episode_id is not None, "NO_ACTIVE_EPISODE_TO_CENSOR")
                    engine.censor(
                        episode_id=active_episode_id,
                        candidate_id=candidate["candidate_id"],
                        reason="CENSOR_GAP",
                        effective_time=candidate["effective_time"],
                        first_valid_time=candidate["first_valid_time"],
                    )
                    counters["censor_gap"] += 1
                    active_episode_id = None
                elif action == "RE_PARENT":
                    base._require(active_episode_id is not None, "NO_ACTIVE_EPISODE_TO_REPARENT")
                    engine.re_parent(
                        episode_id=active_episode_id,
                        candidate_id=candidate["candidate_id"],
                        effective_time=candidate["effective_time"],
                        first_valid_time=candidate["first_valid_time"],
                        reason_codes=["C2E_UPSTREAM_PARENT_SIGNATURE_CHANGE"],
                    )
                    counters["re_parent"] += 1
                elif action == "PHASE_MUTATION":
                    base._require(active_episode_id is not None, "NO_ACTIVE_EPISODE_TO_PHASE")
                    start_time, source_ids = phase_state[active_episode_id]
                    engine.phase_mutation(
                        episode_id=active_episode_id,
                        candidate_id=candidate["candidate_id"],
                        phase_type="STRUCTURAL_SIGNATURE_INTERVAL",
                        start_time=start_time,
                        end_time=candidate["effective_time"],
                        source_record_ids=source_ids,
                        effective_time=candidate["effective_time"],
                        first_valid_time=candidate["first_valid_time"],
                    )
                    phase_state[active_episode_id] = (candidate["effective_time"], _source_ids(frame))
                    counters["phase_mutation"] += 1
                elif action == "CONTINUATION":
                    base._require(active_episode_id is not None, "NO_ACTIVE_EPISODE_TO_CONTINUE")
                    engine.continue_episode(
                        episode_id=active_episode_id,
                        frame=frame,
                        candidate_id=candidate["candidate_id"],
                        effective_time=candidate["effective_time"],
                        first_valid_time=candidate["first_valid_time"],
                    )
                    counters["continuation"] += 1
                elif action == "BIRTH":
                    genesis = engine.birth(
                        frame=frame,
                        boundary_rule_id=candidate["boundary_rule_id"],
                        candidate_id=candidate["candidate_id"],
                        effective_time=candidate["effective_time"],
                        first_valid_time=candidate["first_valid_time"],
                    )
                    active_episode_id = genesis["episode_id"]
                    phase_state[active_episode_id] = (candidate["effective_time"], _source_ids(frame))
                    counters["birth"] += 1
                else:
                    raise base.SourceReplayError(f"UNSUPPORTED_LIFECYCLE_ACTION:{action}")
                actions.append(action)

            evaluations.append(
                {
                    "schema": "c2e_boundary_evaluation/v0_2",
                    "side": side,
                    "frame_id": frame["frame_id"],
                    "first_valid_time": frame["chronology"]["first_valid_time"],
                    "matched_rules": corrected_evaluation["matched_rules"],
                    "resolved_actions": actions,
                    "blocked_candidate_ids": [candidate["candidate_id"] for candidate in candidates if not candidate["evaluable"]],
                    "authority": "INACTIVE_NONCANONICAL_SHADOW",
                }
            )
            previous = frame

        base._require(previous is not None and active_episode_id is not None, "SIDE_POPULATION_EMPTY_OR_UNOWNED")
        release_evaluation = evaluate_boundary_predicates_v2(previous, previous, release_end=True)
        release = build_candidate(
            _rule(pack, base.RULE_IDS[1]),
            previous,
            matched=bool(release_evaluation["matched"][base.RULE_IDS[1]]),
            effective_time=base.TARGET_END,
            confirmation_time=base.TARGET_END,
        )
        base._require(release is not None and release["evaluable"], "RELEASE_END_CANDIDATE_NOT_EVALUABLE")
        engine.censor(
            episode_id=active_episode_id,
            candidate_id=release["candidate_id"],
            reason="CENSOR_RELEASE_END",
            effective_time=base.TARGET_END,
            first_valid_time=base.TARGET_END,
        )
        counters["censor_release_end"] += 1
        evaluations.append(
            {
                "schema": "c2e_boundary_evaluation/v0_2",
                "side": side,
                "frame_id": previous["frame_id"],
                "first_valid_time": base.TARGET_END,
                "matched_rules": release_evaluation["matched_rules"],
                "resolved_actions": ["CENSOR_RELEASE_END"],
                "blocked_candidate_ids": [],
                "authority": "INACTIVE_NONCANONICAL_SHADOW",
            }
        )

    membership_count = sum(
        1 for record in engine.stream.records if record.get("schema") == "c2e_membership_delta/v0_2"
    )
    base._require(membership_count == 4072, f"MEMBERSHIP_COUNT_RECONCILIATION_FAILED:{membership_count}")
    for episode_id in sorted(engine.genesis):
        engine.stream.append(engine.snapshot(episode_id, as_of_time=base.TARGET_END, first_valid_time=base.TARGET_END))
    base._require(counters["birth"] == len(engine.genesis), "BIRTH_EPISODE_COUNT_MISMATCH")
    base._require(counters["censor_release_end"] == 2, "RELEASE_END_SIDE_COUNT_MISMATCH")
    return base.ReplayResult(
        frame_index=frame_index,
        evaluations=evaluations,
        records=list(engine.stream.records),
        disagreements=disagreements,
        blocked_candidates=blocked_candidates,
        counters=counters,
    )


# Canonical public surface for WP6 callers.
load_materialisation = base.load_materialisation
population_identity = base.population_identity
write_run = base.write_run
sha256_file = base.sha256_file
load_json = base.load_json
