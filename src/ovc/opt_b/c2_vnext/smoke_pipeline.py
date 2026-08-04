"""Canonical synthetic end-to-end topology smoke for C2AR-WP5.5."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from .containers import (
    build_container_graph,
    build_swing_envelope,
    build_trailing_range_container,
    evaluate_role_projection,
    shadow_pairing_policies,
)
from .horizons import HorizonDefinition, evaluate_horizon
from .levels import (
    baseline_pivot_policies,
    build_confirmed_pivot_level,
    build_swing_graph,
    build_trailing_range_snapshot,
    detect_pivot_candidates,
    evaluate_selector,
)
from .observation import build_population, default_gbpusd_calendar
from .relations_vnext import (
    build_relation_set,
    fixed_object_crossing,
    point_probe,
    relate_point_to_container,
    relate_point_to_level,
)

UTC = timezone.utc


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _build_rows(fixture: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    start = datetime.fromisoformat(str(fixture["start"]).replace("Z", "+00:00"))
    interval = int(fixture["interval_minutes"])
    evidence: list[dict[str, Any]] = []
    prices: dict[int, dict[str, Any]] = {}
    for raw in fixture["rows"]:
        index = int(raw["index"])
        interval_start = start + timedelta(minutes=index * interval)
        interval_end = interval_start + timedelta(minutes=interval)
        evidence.append({
            "interval_start": _iso(interval_start),
            "interval_end": _iso(interval_end),
            "side": fixture["side"],
            "source_record_id": f"C2AR.SMOKE.SOURCE.{index:03d}",
            "opt_a_release_id": "OPT-A.C2AR.SMOKE.v1",
            "opt_a_record_id": f"OPT-A.C2AR.SMOKE.{index:03d}",
            "c1_release_id": "C1.C2AR.SMOKE.v1",
            "c1_record_id": f"C1.C2AR.SMOKE.{index:03d}",
            "complete": True,
        })
        prices[index] = {
            "open": float(raw["open"]), "high": float(raw["high"]),
            "low": float(raw["low"]), "close": float(raw["close"]),
        }
    return evidence, prices


def run_canonical_smoke(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Run observation → horizon → level → container → relation deterministically."""
    evidence, price_by_index = _build_rows(fixture)
    population = build_population(
        fixture["start"], fixture["end"], instrument=fixture["instrument"],
        calendar=default_gbpusd_calendar(), evidence_rows=evidence,
        sides=(fixture["side"],), partition_id=fixture["partition_id"],
    )
    observations = copy.deepcopy(population["observations"])
    for index, observation in enumerate(observations):
        observation.update(price_by_index[index])
        observation["content_sha256"] = sha256({k: v for k, v in observation.items() if k != "content_sha256"})

    trailing_definition = HorizonDefinition(
        horizon_id="HORIZON.C2AR.SMOKE.TRAILING.4.v1",
        kind="TRAILING_COUNT", semantic_type="OBSERVATION_COUNT",
        unit="OBSERVATION", grain="15M_C2_OBSERVATION",
        source_basis="C2AR.SMOKE.CANONICAL.v1",
        applicability_scope=("GBPUSD", "BID", "SMOKE"),
        consumer_classes=("C2_MEASUREMENT",), causal_class="CAUSAL_BACKWARD",
        continuity_policy="SAME_CONTINUITY_SEGMENT",
        first_valid_rule="CURRENT_OBSERVATION_FIRST_VALID", version="v1",
        maturity="SHADOW_EXPERIMENT", clock_id="LATTICE.15M.UTC_0000.v1",
        count=4, template=False, benchmark_only=False, canonical=False,
    )
    horizon = evaluate_horizon(
        trailing_definition, observations,
        as_of_observation_id=observations[-1]["observation_id"],
        consumer_class="C2_MEASUREMENT",
    )
    member_ids = set(horizon["member_observation_ids"])
    trailing_observations = [item for item in observations if item["observation_id"] in member_ids]

    policy = baseline_pivot_policies()[0]
    high_candidates = detect_pivot_candidates(observations, policy=policy, polarity="HIGH")
    low_candidates = detect_pivot_candidates(observations, policy=policy, polarity="LOW")
    confirmed_highs = [build_confirmed_pivot_level(item) for item in high_candidates if item["status"] == "UNIQUE_CONFIRMED"]
    confirmed_lows = [build_confirmed_pivot_level(item) for item in low_candidates if item["status"] == "UNIQUE_CONFIRMED"]
    expected_high_index = int(fixture["expected"]["confirmed_high_anchor_index"])
    expected_low_index = int(fixture["expected"]["confirmed_low_anchor_index"])
    high_anchor_id = observations[expected_high_index]["observation_id"]
    low_anchor_id = observations[expected_low_index]["observation_id"]
    swing_high = next(item for item in confirmed_highs if high_anchor_id in item["source_ids"])
    swing_low = next(item for item in confirmed_lows if low_anchor_id in item["source_ids"])
    range_levels = build_trailing_range_snapshot(
        trailing_observations, horizon_id=trailing_definition.horizon_id,
        clock_id="LATTICE.15M.UTC_0000.v1",
    )
    levels = [swing_high, swing_low, *range_levels]
    swing_graph = build_swing_graph([swing_high, swing_low])
    level_projection = evaluate_selector(
        levels, selector_id="SELECTOR.C2.LEVEL.LATEST_FIRST_VALID.r1",
        as_of_time=observations[-1]["first_valid_time"],
    )

    trailing_container = build_trailing_range_container(range_levels)
    pairing, swing_container = build_swing_envelope(
        swing_low, swing_high, policy=shadow_pairing_policies()[0],
    )
    if swing_container is None:
        raise AssertionError(f"synthetic swing envelope unavailable: {pairing}")
    containers = [trailing_container, swing_container]
    container_graph = build_container_graph(containers)
    measurement_projection = evaluate_role_projection(
        containers, projection_id="PROJECTION.C2.CONTAINER.LATEST_FIRST_VALID.r1",
        role="LOCAL_MEASUREMENT", scope_kind="LOCAL",
        as_of_time=observations[-1]["first_valid_time"],
    )
    structural_projection = evaluate_role_projection(
        containers, projection_id="PROJECTION.C2.CONTAINER.LATEST_FIRST_VALID.r1",
        role="LOCAL_STRUCTURAL", scope_kind="LOCAL",
        as_of_time=observations[-1]["first_valid_time"],
    )

    current = observations[-1]
    close_probe = point_probe(
        value=current["close"], source_record_id=current["observation_id"],
        first_valid_time=current["first_valid_time"], probe_label="CLOSE",
    )
    level_relations = [relate_point_to_level(close_probe, item, precision=5) for item in levels]
    container_relations = [relate_point_to_container(close_probe, item, precision=5) for item in containers]
    level_set = build_relation_set(
        scope_type="LOCAL_LEVELS", subject_observation_id=current["observation_id"],
        candidate_object_ids=[item["level_id"] for item in levels] + ["LEVEL.C2AR.SMOKE.EXCLUDED"],
        relations=level_relations,
        exclusions=[{"object_id": "LEVEL.C2AR.SMOKE.EXCLUDED", "reason": "SYNTHETIC_EXPLICIT_EXCLUSION"}],
        as_of_time=current["first_valid_time"],
    )
    container_set = build_relation_set(
        scope_type="LOCAL_MEASUREMENT_CONTAINERS", subject_observation_id=current["observation_id"],
        candidate_object_ids=[item["container_id"] for item in containers],
        relations=container_relations, exclusions=[], as_of_time=current["first_valid_time"],
    )
    crossing = fixed_object_crossing(
        object_id=swing_high["level_id"], object_value=swing_high["value"],
        previous_value=observations[1]["close"], current_value=observations[2]["close"],
        previous_time=observations[1]["first_valid_time"], current_time=observations[2]["first_valid_time"],
        precision=5, evidence_mode="M1_PATH",
        ordered_path=[observations[1]["close"], 1.18, 1.24, observations[2]["close"]],
    )

    stages = {
        "observation": {"population_id": population["population_id"], "count": len(observations), "sha256": sha256(observations)},
        "horizon": {"membership_id": horizon["membership_id"], "status": horizon["status"], "member_count": len(horizon["member_observation_ids"]), "sha256": sha256(horizon)},
        "level": {"level_ids": [item["level_id"] for item in levels], "candidate_status_counts": _status_counts([*high_candidates, *low_candidates]), "selector_result_id": level_projection["selector_result_id"], "sha256": sha256({"levels": levels, "graph": swing_graph, "projection": level_projection})},
        "container": {"container_ids": [item["container_id"] for item in containers], "pairing_evidence_id": pairing["pairing_evidence_id"], "measurement_projection_id": measurement_projection["projection_result_id"], "structural_projection_id": structural_projection["projection_result_id"], "sha256": sha256({"containers": containers, "graph": container_graph, "measurement_projection": measurement_projection, "structural_projection": structural_projection})},
        "relation": {"relation_set_ids": [level_set["relation_set_id"], container_set["relation_set_id"]], "relation_count": len(level_relations) + len(container_relations), "crossing_evidence_id": crossing["crossing_evidence_id"], "sha256": sha256({"level_relations": level_relations, "container_relations": container_relations, "sets": [level_set, container_set], "crossing": crossing})},
    }
    chronology = {
        "all_level_first_valid_by_current": all(item["first_valid_time"] <= current["first_valid_time"] for item in levels),
        "all_container_first_valid_by_current": all(item["first_valid_time"] <= current["first_valid_time"] for item in containers),
        "horizon_has_future_member": any(item > current["first_valid_time"] for item in horizon["member_first_valid_times"]),
    }
    authority = {
        "active_selector": "NONE", "active_parameter": "NONE",
        "formula_threshold": "NONE", "release_publication": "NONE",
        "validation": "NONE", "semantic_promotion": "NONE",
        "probability_risk_exposure_execution": "NONE",
    }
    manifest_body = {
        "schema": "ovc-c2ar-wp5-5-smoke-manifest/v1",
        "fixture_id": fixture["fixture_id"], "instrument": fixture["instrument"],
        "side": fixture["side"], "stages": stages,
        "chronology": chronology,
        "mocked_components": list(fixture["mocked_components"]),
        "ambiguity_and_exclusion": {
            "level_selector_tie_count": len(level_projection["tie_ids"]),
            "level_selector_selected": level_projection["selected_level_id"],
            "explicit_relation_exclusion_count": len(level_set["exclusions"]),
            "censored_candidate_count": sum(1 for item in [*high_candidates, *low_candidates] if item["status"] == "CENSORED_CONFIRMATION"),
        },
        "authority": authority,
        "raw_market_data": False, "r2_write_authority": "NONE",
        "status": "PASS" if chronology["all_level_first_valid_by_current"] and chronology["all_container_first_valid_by_current"] and not chronology["horizon_has_future_member"] else "FAIL",
    }
    return {**manifest_body, "manifest_sha256": sha256(manifest_body)}


def _status_counts(records: list[Mapping[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for record in records:
        status = str(record["status"])
        result[status] = result.get(status, 0) + 1
    return dict(sorted(result.items()))
