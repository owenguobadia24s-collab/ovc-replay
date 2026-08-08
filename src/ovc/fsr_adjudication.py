"""Post-freeze hidden-construction adjudication for FSR v0.1.

This is the only FSR module authorised to open the hidden construction ledger.
It receives an already-completed full-stack result, never reruns a stage with oracle
information, and never feeds an intended label, boundary or expected answer upstream.
Construction intent is used only as a coverage oracle after deterministic outputs are
frozen.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Sequence

from .opt_b.srfd.fsr_adapter import _representation_sets
from .research_operations.canonical import canonical_sha256

PROGRAMME_ID = "OVC-FULL-STACK-SYNTHETIC-FRESH-DISCOVERY-REHEARSAL-v0.1"
HIDDEN_LEDGER_REL = Path("fixtures/full_stack_synthetic_fresh_discovery/v0_1/hidden/HIDDEN_CONSTRUCTION_LEDGER.json")
DAY = datetime(2023, 6, 5, tzinfo=timezone.utc)


def _time(value: str) -> datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(text).astimezone(timezone.utc)


def _clock(text: str) -> datetime:
    hour, minute = map(int, text.split(":"))
    if hour == 24:
        return DAY + timedelta(days=1)
    return DAY.replace(hour=hour, minute=minute)


def _axis(snapshot: Mapping[str, Any], axis: str) -> Mapping[str, Any]:
    return next(item for item in snapshot["formula_outputs"] if item["axis"] == axis)


def _motion(snapshot: Mapping[str, Any]) -> float:
    value = _axis(snapshot, "MOTION").get("facts", {}).get("price_delta")
    return 0.0 if value is None else float(value)


def _container_width(snapshot: Mapping[str, Any]) -> float:
    item = next(
        value
        for value in snapshot["containers"]
        if value.get("family") == "TRAILING_RANGE_SNAPSHOT" and value.get("kind") == "MEASUREMENT"
    )
    return float(item["width"])


def _sign(value: float, epsilon: float = 1e-12) -> int:
    if value > epsilon:
        return 1
    if value < -epsilon:
        return -1
    return 0


def _continuity_reset_times(c2: Mapping[str, Any]) -> set[str]:
    resets: set[str] = set()
    for side in ("BID", "ASK"):
        prior_segment = None
        for snapshot in sorted(
            (item for item in c2["snapshots"] if item["side"] == side),
            key=lambda item: str(item["as_of_time"]),
        ):
            segment = str(snapshot["continuity_segment_id"])
            if prior_segment is not None and segment != prior_segment:
                resets.add(str(snapshot["as_of_time"]))
            prior_segment = segment
    return resets


def _residual_snapshot_ids(result: Mapping[str, Any]) -> set[str]:
    representations, _ = _representation_sets(result["c2"], result["c2e"])
    r4 = {str(item["representation_id"]): item for item in representations["R4"]}
    residual_representation_ids = {
        str(rep_id)
        for catalog in result["srfd"]["family_benchmark"]["catalogs"]
        for rep_id in catalog["residual_ids"]
    }
    snapshots: set[str] = set()
    for rep_id in residual_representation_ids:
        representation = r4.get(rep_id)
        if representation:
            snapshots.update(map(str, representation.get("source_record_ids", [])))
    return snapshots


def _segment_metrics(
    segment: Mapping[str, Any],
    *,
    c2: Mapping[str, Any],
    c2e: Mapping[str, Any],
    residual_snapshot_ids: set[str],
    reset_times: set[str],
) -> dict[str, Any]:
    start = _clock(str(segment["interval"][0]))
    end = _clock(str(segment["interval"][1]))
    snapshots = [item for item in c2["snapshots"] if start < _time(str(item["as_of_time"])) <= end]
    motions = [_motion(item) for item in snapshots]
    widths = [_container_width(item) for item in snapshots]
    signs = [_sign(value) for value in motions if _sign(value) != 0]
    alternations = sum(left != right for left, right in zip(signs, signs[1:]))
    noncomputable = Counter(
        str(output["axis"])
        for snapshot in snapshots
        for output in snapshot["formula_outputs"]
        if output["computability"] != "COMPUTABLE"
    )
    episodes = [
        episode
        for ledger in c2e["ledgers"]
        for episode in ledger["episodes"]
        if _time(str(episode["end_first_valid_time"])) > start
        and _time(str(episode["start_first_valid_time"])) <= end
    ]
    statuses = Counter(str(episode["status"]) for episode in episodes)
    ids = {str(item["snapshot_id"]) for item in snapshots}
    return {
        "segment_id": segment["id"],
        "interval": segment["interval"],
        "snapshot_count": len(snapshots),
        "signed_motion_sum": sum(motions),
        "mean_abs_motion": mean(map(abs, motions)) if motions else 0.0,
        "positive_motion_count": sum(value > 0 for value in motions),
        "negative_motion_count": sum(value < 0 for value in motions),
        "zero_motion_count": sum(value == 0 for value in motions),
        "motion_alternation_count": alternations,
        "mean_measurement_container_width": mean(widths) if widths else 0.0,
        "container_width_first": widths[0] if widths else None,
        "container_width_last": widths[-1] if widths else None,
        "transition_count": sum(len(item.get("transition_records", [])) for item in snapshots),
        "crossing_detector_count": sum(len(item.get("detectors", {}).get("crossing", [])) for item in snapshots),
        "touch_detector_count": sum(len(item.get("detectors", {}).get("touch", [])) for item in snapshots),
        "continuity_reset_count": sum(start < _time(value) <= end for value in reset_times),
        "noncomputable_axis_counts": dict(sorted(noncomputable.items())),
        "episode_status_counts": dict(sorted(statuses.items())),
        "srfd_residual_snapshot_count": len(ids & residual_snapshot_ids),
        "snapshot_ids": sorted(ids),
    }


def _baseline(metrics: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    nonempty = [item for item in metrics if int(item["snapshot_count"]) > 0]
    return {
        "mean_abs_motion": mean(float(item["mean_abs_motion"]) for item in nonempty) if nonempty else 0.0,
        "mean_container_width": mean(float(item["mean_measurement_container_width"]) for item in nonempty) if nonempty else 0.0,
    }


def _cross_intent(intent: str) -> dict[str, Any] | None:
    if intent == "repeated_but_non_identical_sequences":
        return {
            "intent": intent,
            "testability": "CROSS_POPULATION",
            "status": "STRUCTURAL_SIGNAL_PRESENT",
            "evidence": ["SRFD executed multiple representation and family methods with correspondence/disagreement evidence; no semantic family promotion occurred."],
        }
    if intent == "nested_multi_horizon_structure_candidate":
        return {
            "intent": intent,
            "testability": "PARTIAL",
            "status": "PARTIAL_ALIGNMENT",
            "evidence": ["Revised C2 exercised 15M local evidence plus fixed 2H parent context; standalone higher-scale structural-parent episodes were unavailable."],
        }
    if intent == "persistent_object_survival_candidate":
        return {
            "intent": intent,
            "testability": "NOT_TESTABLE_AT_REACHED_LAYER",
            "status": "NOT_TESTABLE",
            "evidence": ["Forward C2P persistent structural objects are not implemented at the pinned baseline."],
        }
    return None


def _intent_disposition(intent: str, metric: Mapping[str, Any], baseline: Mapping[str, float]) -> dict[str, Any]:
    cross = _cross_intent(intent)
    if cross is not None:
        return cross

    n = max(1, int(metric["snapshot_count"]))
    positive = int(metric["positive_motion_count"])
    negative = int(metric["negative_motion_count"])
    alternation = int(metric["motion_alternation_count"])
    motion = float(metric["mean_abs_motion"])
    width0 = metric["container_width_first"]
    width1 = metric["container_width_last"]
    crossings = int(metric["crossing_detector_count"])
    touches = int(metric["touch_detector_count"])
    statuses = metric["episode_status_counts"]
    residual = int(metric["srfd_residual_snapshot_count"])
    noncomputable = sum(metric["noncomputable_axis_counts"].values())
    evidence: list[str] = []
    status = "PARTIAL_ALIGNMENT"

    if intent == "clean_level_crossing":
        status = "STRUCTURAL_SIGNAL_PRESENT" if crossings else "NO_ALIGNMENT_OBSERVED"
        evidence.append(f"crossing_detector_count={crossings}")
    elif intent in {"repeated_level_interaction", "failed_crossing_like_price_behaviour"}:
        count = crossings + touches
        status = "STRUCTURAL_SIGNAL_PRESENT" if count else "NO_ALIGNMENT_OBSERVED"
        evidence.append(f"crossing_plus_touch_count={count}")
    elif intent == "controlled_gap":
        count = int(metric["continuity_reset_count"])
        status = "STRUCTURAL_SIGNAL_PRESENT" if count else "NO_ALIGNMENT_OBSERVED"
        evidence.append(f"continuity_reset_count={count}")
    elif intent in {"directional_expansion", "impulsive_displacement", "continuation"}:
        consistency = max(positive, negative) / n
        status = "STRUCTURAL_SIGNAL_PRESENT" if consistency >= 0.60 and motion >= baseline["mean_abs_motion"] else "PARTIAL_ALIGNMENT"
        evidence.extend([f"directional_consistency={consistency:.3f}", f"mean_abs_motion={motion:.8f}"])
    elif intent in {"pullback_retracement", "reversal"}:
        dominance = max(positive, negative) / n
        status = "STRUCTURAL_SIGNAL_PRESENT" if dominance >= 0.50 else "PARTIAL_ALIGNMENT"
        evidence.extend([f"positive={positive};negative={negative}", f"directional_dominance={dominance:.3f}"])
    elif intent in {"alternating_rotational_behaviour", "range_construction", "swing_formation"}:
        status = "STRUCTURAL_SIGNAL_PRESENT" if alternation >= 2 else "PARTIAL_ALIGNMENT"
        evidence.extend([f"motion_alternation_count={alternation}", f"transition_count={metric['transition_count']}"])
    elif intent == "compression":
        narrowing = width0 is not None and width1 is not None and float(width1) < float(width0)
        status = "STRUCTURAL_SIGNAL_PRESENT" if narrowing or motion < baseline["mean_abs_motion"] else "PARTIAL_ALIGNMENT"
        evidence.extend([f"width_first={width0}", f"width_last={width1}", f"mean_abs_motion={motion:.8f}"])
    elif intent == "quiet_low_range_persistence":
        status = "STRUCTURAL_SIGNAL_PRESENT" if motion < baseline["mean_abs_motion"] else "PARTIAL_ALIGNMENT"
        evidence.extend([f"mean_abs_motion={motion:.8f}", f"global_mean_abs_motion={baseline['mean_abs_motion']:.8f}"])
    elif intent == "volatility_state_change":
        changed = motion > baseline["mean_abs_motion"] or (width0 is not None and width1 is not None and float(width0) != float(width1))
        status = "STRUCTURAL_SIGNAL_PRESENT" if changed else "PARTIAL_ALIGNMENT"
        evidence.extend([f"mean_abs_motion={motion:.8f}", f"width_first={width0};width_last={width1}"])
    elif intent == "ambiguous_development":
        mixed = positive > 0 and negative > 0
        status = "STRUCTURAL_SIGNAL_PRESENT" if mixed or noncomputable else "PARTIAL_ALIGNMENT"
        evidence.extend([f"positive={positive};negative={negative}", f"noncomputable_axis_evaluations={noncomputable}"])
    elif intent == "superficially_similar_but_structurally_different":
        return {
            "intent": intent,
            "testability": "CROSS_SEGMENT_COMPARISON_REQUIRED",
            "status": "PARTIAL_ALIGNMENT",
            "evidence": ["Segment-level structural diagnostics are retained for comparison; no semantic similarity oracle was exposed to SRFD."],
        }
    elif intent == "censored_development":
        count = int(statuses.get("OPEN_AT_CUTOFF", 0)) + int(statuses.get("CENSORED", 0))
        status = "STRUCTURAL_SIGNAL_PRESENT" if count else "NO_ALIGNMENT_OBSERVED"
        evidence.append(f"open_or_censored_episode_overlap_count={count}")
    elif intent == "residual_outlier_candidate":
        status = "STRUCTURAL_SIGNAL_PRESENT" if residual else "PARTIAL_ALIGNMENT"
        evidence.append(f"srfd_residual_snapshot_count={residual}")
    else:
        return {
            "intent": intent,
            "testability": "UNREGISTERED_PROXY",
            "status": "NOT_TESTABLE",
            "evidence": ["No deterministic adjudication proxy was registered for this construction intent."],
        }
    return {"intent": intent, "testability": "DIRECT_OR_PROXY_STRUCTURAL", "status": status, "evidence": evidence}


def adjudicate_hidden_construction(*, repo_root: Path, frozen_result: Mapping[str, Any]) -> dict[str, Any]:
    before = copy.deepcopy(frozen_result["run_manifest"])
    if before.get("hidden_construction_consumed") is not False:
        raise ValueError("PIPELINE_ALREADY_CONSUMED_HIDDEN_CONSTRUCTION")

    hidden_path = repo_root / HIDDEN_LEDGER_REL
    hidden_bytes = hidden_path.read_bytes()
    hidden = json.loads(hidden_bytes)
    if hidden.get("pipeline_consumable") is not False:
        raise ValueError("HIDDEN_LEDGER_PIPELINE_FIREWALL_NOT_EXPLICIT")

    residuals = _residual_snapshot_ids(frozen_result)
    resets = _continuity_reset_times(frozen_result["c2"])
    metrics = [
        _segment_metrics(
            segment,
            c2=frozen_result["c2"],
            c2e=frozen_result["c2e"],
            residual_snapshot_ids=residuals,
            reset_times=resets,
        )
        for segment in hidden["segments"]
    ]
    baseline = _baseline(metrics)
    metrics_by_id = {item["segment_id"]: item for item in metrics}
    comparisons: list[dict[str, Any]] = []
    for segment in hidden["segments"]:
        for intent in segment["intent"]:
            comparisons.append(
                {"segment_id": segment["id"], **_intent_disposition(intent, metrics_by_id[segment["id"]], baseline)}
            )
    for intent in hidden.get("cross_segment_intents", []):
        comparisons.append({"segment_id": "CROSS_SEGMENT", **_intent_disposition(intent, {}, baseline)})

    pipeline_unchanged = before == frozen_result["run_manifest"]
    statuses = Counter(item["status"] for item in comparisons)
    body = {
        "schema": "ovc-fsr-hidden-construction-adjudication/v1",
        "programme_id": PROGRAMME_ID,
        "fixture_id": before["fixture_id"],
        "pipeline_run_manifest_sha256": before["logical_sha256"],
        "hidden_construction_ledger_sha256": hashlib.sha256(hidden_bytes).hexdigest(),
        "oracle_access_phase": "FSR-WP11_POST_FREEZE_ONLY",
        "pipeline_unchanged_after_oracle_read": pipeline_unchanged,
        "segment_metrics": metrics,
        "global_baseline": baseline,
        "comparisons": comparisons,
        "comparison_status_counts": dict(sorted(statuses.items())),
        "interpretation": {
            "architecture_fidelity": "PASS" if pipeline_unchanged else "FAIL",
            "detection_fidelity": "MIXED_STRUCTURAL_ALIGNMENT_EXPECTED_NO_SEMANTIC_ORACLE",
            "method_failure_conclusion": "NONE_AUTOMATIC",
            "representation_failure_conclusion": "NONE_AUTOMATIC",
            "architecture_failure_conclusion": "NONE" if pipeline_unchanged else "ORACLE_CONTAMINATION",
            "note": "Construction intent is a coverage oracle, not market truth. Proxy alignment cannot promote labels, families, methods or grammar semantics.",
        },
        "authority": {
            "market_evidence": False,
            "canonical": False,
            "promotable": False,
            "selector_mutation": "NONE",
            "publication": "NONE",
            "validation_consumption": "DENIED",
            "probability_risk_exposure_execution": "NONE",
        },
    }
    body["logical_sha256"] = canonical_sha256(body)
    return body
