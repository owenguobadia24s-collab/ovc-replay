"""Denominator-explicit synthetic assurance metrics for C2E v0.2."""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping

from .serialization import sha256_hex


class AssuranceMetricError(ValueError):
    pass


def exact_rate(numerator: int, denominator: int) -> dict[str, Any]:
    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise AssuranceMetricError("INVALID_NUMERATOR_DENOMINATOR")
    return {
        "numerator": numerator,
        "denominator": denominator,
        "exact_rate": None if denominator == 0 else f"{Fraction(numerator, denominator).numerator}/{Fraction(numerator, denominator).denominator}",
    }


def build_conflict_metrics(
    *, ambiguous_candidate_sets: int, evaluated_candidate_sets: int,
    conflict_resolutions: int, resolved_boundary_transactions: int,
    conflicted_episodes: int, emitted_episodes: int,
    peer_owner_collisions: int, peer_ownership_frames: int,
    compound_invalidated: int, compound_candidates: int,
    not_evaluable_rules: int, applicable_rule_evaluations: int,
) -> dict[str, Any]:
    return {
        "ambiguous_boundary_rate": exact_rate(ambiguous_candidate_sets, evaluated_candidate_sets),
        "explicit_conflict_rate": exact_rate(conflict_resolutions, resolved_boundary_transactions),
        "conflicted_episode_rate": exact_rate(conflicted_episodes, emitted_episodes),
        "peer_owner_collision_rate": exact_rate(peer_owner_collisions, peer_ownership_frames),
        "compound_invalidated_rate": exact_rate(compound_invalidated, compound_candidates),
        "not_evaluable_boundary_rate": exact_rate(not_evaluable_rules, applicable_rule_evaluations),
    }


def build_conflict_metric_receipt(*, run_id: str, boundary_pack_id: str, metrics: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "c2e_conflict_metric_receipt/v0_1",
        "run_id": str(run_id),
        "boundary_pack_id": str(boundary_pack_id),
        "metrics": dict(metrics),
        "interpretation": "DESCRIPTIVE_DIAGNOSTIC_ONLY",
        "selection_threshold": None,
        "authority_effect": "NONE",
    }
    payload["logical_sha256"] = sha256_hex(payload)
    return payload
