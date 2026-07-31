from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Iterable, Mapping, Sequence

ALLOWED_TRIGGER_CLASSIFICATIONS = {
    "BOUNDARY_ZONE_ENTRY",
    "BREACH_ACTIVE",
    "LONG_PERSISTENCE",
    "REPEATED_SWITCHING",
    "NO_TRIGGER",
    "INSUFFICIENT_EVIDENCE",
}
ALLOWED_STRUCTURAL_VERDICTS = {"SUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE"}
ALLOWED_REVIEW_DISPOSITIONS = {
    "WORKFLOW_ACCEPTED",
    "DEFER_PILOT_OBJECT",
    "REJECT_PILOT_OBJECT",
}


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp must use UTC Z notation")
    return datetime.fromisoformat(value[:-1] + "+00:00")


def candidate_occupied_state_ids(candidates: Iterable[Mapping[str, Any]]) -> set[str]:
    occupied: set[str] = set()
    for candidate in candidates:
        state_ids = candidate.get("source_c2_record_ids")
        if not isinstance(state_ids, list) or not all(isinstance(item, str) and item for item in state_ids):
            raise ValueError("candidate source_c2_record_ids must be a non-empty string list")
        occupied.update(state_ids)
    return occupied


def quality_sequence(rows: Sequence[Mapping[str, Any]]) -> tuple[Any, ...]:
    return tuple(((row.get("axes") or {}).get("QUALITY") or {}).get("value") for row in rows)


def contiguous_windows(
    rows: Sequence[Mapping[str, Any]],
    length: int,
    *,
    excluded_state_ids: set[str],
    used_state_ids: set[str] | None = None,
) -> list[list[Mapping[str, Any]]]:
    if length < 1:
        raise ValueError("length must be positive")
    used = used_state_ids or set()
    ordered = sorted(rows, key=lambda row: (parse_utc(str(row["first_valid_time"])), str(row["c2_state_id"])))
    windows: list[list[Mapping[str, Any]]] = []
    for index in range(0, len(ordered) - length + 1):
        window = ordered[index : index + length]
        ids = [str(row["c2_state_id"]) for row in window]
        if len(set(ids)) != len(ids):
            continue
        if any(item in excluded_state_ids or item in used for item in ids):
            continue
        times = [parse_utc(str(row["first_valid_time"])) for row in window]
        if any(times[pos + 1] - times[pos] != timedelta(minutes=15) for pos in range(len(times) - 1)):
            continue
        windows.append(window)
    return windows


def select_matched_control(
    promoted_candidate: Mapping[str, Any],
    promoted_rows: Sequence[Mapping[str, Any]],
    stream_rows: Sequence[Mapping[str, Any]],
    *,
    occupied_state_ids: set[str],
    used_state_ids: set[str],
) -> dict[str, Any]:
    candidate_id = str(promoted_candidate["window_id"])
    length = int(promoted_candidate["duration_records"])
    target_quality = quality_sequence(promoted_rows)
    target_start = parse_utc(str(promoted_candidate["trigger_first_valid_at"]))
    eligible = contiguous_windows(
        stream_rows,
        length,
        excluded_state_ids=occupied_state_ids,
        used_state_ids=used_state_ids,
    )
    if not eligible:
        raise ValueError(f"no eligible matched control for {candidate_id}")

    scored: list[tuple[int, int, str, list[Mapping[str, Any]]]] = []
    for window in eligible:
        ids = [str(row["c2_state_id"]) for row in window]
        mismatch = sum(left != right for left, right in zip(quality_sequence(window), target_quality))
        distance = int(abs((parse_utc(str(window[0]["first_valid_time"])) - target_start).total_seconds()))
        tie_break = hashlib.sha256((candidate_id + "|" + "|".join(ids)).encode("utf-8")).hexdigest()
        scored.append((mismatch, distance, tie_break, window))
    mismatch, distance, tie_break, selected = min(scored, key=lambda item: item[:3])
    selected_ids = [str(row["c2_state_id"]) for row in selected]
    used_state_ids.update(selected_ids)
    return {
        "control_id": "PDCTRL-MATCHED-" + hashlib.sha256(
            (candidate_id + "|" + "|".join(selected_ids)).encode("utf-8")
        ).hexdigest()[:24],
        "control_class": "MATCHED_NONCANDIDATE_WINDOW",
        "matched_candidate_window_id": candidate_id,
        "source_c2_record_ids": selected_ids,
        "quality_sequence": list(quality_sequence(selected)),
        "selection_score": {
            "quality_mismatch_count": mismatch,
            "absolute_start_distance_seconds": distance,
            "tie_break_sha256": tie_break,
        },
    }


def select_population_control(
    stream_rows: Sequence[Mapping[str, Any]],
    *,
    side: str,
    scope_id: str,
    occupied_state_ids: set[str],
    used_state_ids: set[str],
    length: int = 4,
) -> dict[str, Any]:
    eligible = contiguous_windows(
        stream_rows,
        length,
        excluded_state_ids=occupied_state_ids,
        used_state_ids=used_state_ids,
    )
    if not eligible:
        raise ValueError(f"no eligible population control for {side}/{scope_id}")
    ranked: list[tuple[str, list[Mapping[str, Any]]]] = []
    for window in eligible:
        ids = [str(row["c2_state_id"]) for row in window]
        rank = hashlib.sha256(("POP|" + side + "|" + scope_id + "|" + "|".join(ids)).encode("utf-8")).hexdigest()
        ranked.append((rank, window))
    rank, selected = min(ranked, key=lambda item: item[0])
    selected_ids = [str(row["c2_state_id"]) for row in selected]
    used_state_ids.update(selected_ids)
    return {
        "control_id": "PDCTRL-POP-" + hashlib.sha256(
            (side + "|" + scope_id + "|" + "|".join(selected_ids)).encode("utf-8")
        ).hexdigest()[:24],
        "control_class": "POPULATION_NONCANDIDATE_WINDOW",
        "matched_candidate_window_id": None,
        "source_c2_record_ids": selected_ids,
        "quality_sequence": list(quality_sequence(selected)),
        "selection_score": {"population_hash_rank_sha256": rank},
    }


def validate_response(
    response: Mapping[str, Any],
    *,
    cards_by_id: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    errors: list[str] = []
    blind_id = response.get("blind_id")
    if blind_id not in cards_by_id:
        return [f"unknown blind_id: {blind_id}"]
    card = cards_by_id[str(blind_id)]
    if response.get("card_payload_sha256") != card.get("card_payload_sha256"):
        errors.append(f"{blind_id}: card_payload_sha256 mismatch")
    if response.get("trigger_classification") not in ALLOWED_TRIGGER_CLASSIFICATIONS:
        errors.append(f"{blind_id}: invalid trigger_classification")
    if response.get("structural_description_verdict") not in ALLOWED_STRUCTURAL_VERDICTS:
        errors.append(f"{blind_id}: invalid structural_description_verdict")
    if response.get("review_disposition") not in ALLOWED_REVIEW_DISPOSITIONS:
        errors.append(f"{blind_id}: invalid review_disposition")
    confidence = response.get("confidence")
    if not isinstance(confidence, int) or isinstance(confidence, bool) or not 1 <= confidence <= 5:
        errors.append(f"{blind_id}: confidence must be integer 1..5")
    if not isinstance(response.get("contradictory_fact_codes"), list):
        errors.append(f"{blind_id}: contradictory_fact_codes must be a list")
    if not isinstance(response.get("notes"), str):
        errors.append(f"{blind_id}: notes must be a string")
    return errors


def cohen_kappa(left: Sequence[str], right: Sequence[str]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    labels = sorted(set(left) | set(right))
    observed = sum(a == b for a, b in zip(left, right)) / len(left)
    left_counts = Counter(left)
    right_counts = Counter(right)
    expected = sum((left_counts[label] / len(left)) * (right_counts[label] / len(right)) for label in labels)
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1.0 - expected)


def score_blinded_review(
    review_input: Mapping[str, Any],
    answer_key: Mapping[str, Any],
    completed_response: Mapping[str, Any],
) -> dict[str, Any]:
    cards = review_input.get("cards")
    mappings = answer_key.get("mapping")
    responses = completed_response.get("responses")
    if not isinstance(cards, list) or not isinstance(mappings, list) or not isinstance(responses, list):
        raise ValueError("cards, mapping and responses must be lists")
    cards_by_id = {str(card["blind_id"]): card for card in cards}
    mapping_by_id = {str(item["blind_id"]): item for item in mappings}
    if set(cards_by_id) != set(mapping_by_id):
        raise ValueError("answer-key blind IDs do not match review cards")
    if len(responses) != len(cards_by_id):
        raise ValueError("response count does not match card count")
    response_by_id: dict[str, Mapping[str, Any]] = {}
    errors: list[str] = []
    for response in responses:
        blind_id = str(response.get("blind_id"))
        if blind_id in response_by_id:
            errors.append(f"duplicate response: {blind_id}")
        response_by_id[blind_id] = response
        errors.extend(validate_response(response, cards_by_id=cards_by_id))
    missing = sorted(set(cards_by_id) - set(response_by_id))
    if missing:
        errors.append("missing responses: " + ",".join(missing))
    if errors:
        raise ValueError("; ".join(errors))

    controls = []
    promoted = []
    for blind_id in sorted(cards_by_id):
        expected = mapping_by_id[blind_id]
        response = response_by_id[blind_id]
        pair = {"blind_id": blind_id, "expected": expected, "response": response}
        if expected["object_class"] == "NEGATIVE_CONTROL":
            controls.append(pair)
        elif expected["object_class"] == "PROMOTED_CANDIDATE":
            promoted.append(pair)
        else:
            raise ValueError(f"unsupported object class for {blind_id}")

    control_determinate = [
        pair for pair in controls if pair["response"]["trigger_classification"] != "INSUFFICIENT_EVIDENCE"
    ]
    false_positives = [
        pair for pair in control_determinate if pair["response"]["trigger_classification"] != "NO_TRIGGER"
    ]
    promoted_determinate = [
        pair for pair in promoted if pair["response"]["trigger_classification"] != "INSUFFICIENT_EVIDENCE"
    ]
    detected = [
        pair for pair in promoted_determinate if pair["response"]["trigger_classification"] != "NO_TRIGGER"
    ]
    exact_reason = [
        pair for pair in promoted_determinate
        if pair["response"]["trigger_classification"] == pair["expected"]["expected_trigger_classification"]
    ]
    disposition_pairs = [
        pair for pair in promoted if pair["expected"].get("prior_operator_disposition") is not None
    ]
    prior_dispositions = [str(pair["expected"]["prior_operator_disposition"]) for pair in disposition_pairs]
    repeat_dispositions = [str(pair["response"]["review_disposition"]) for pair in disposition_pairs]
    agreement_count = sum(left == right for left, right in zip(prior_dispositions, repeat_dispositions))
    contradictions = [
        pair for pair in promoted if pair["response"]["structural_description_verdict"] == "CONTRADICTED"
    ]

    metrics = {
        "card_count": len(cards),
        "control_count": len(controls),
        "control_determinate_count": len(control_determinate),
        "control_true_negative_count": len(control_determinate) - len(false_positives),
        "control_false_positive_count": len(false_positives),
        "promoted_count": len(promoted),
        "promoted_determinate_count": len(promoted_determinate),
        "promoted_trigger_detected_count": len(detected),
        "promoted_exact_reason_agreement_count": len(exact_reason),
        "promoted_structural_contradiction_count": len(contradictions),
        "prior_repeat_disposition_agreement_count": agreement_count,
        "prior_repeat_disposition_count": len(disposition_pairs),
        "prior_repeat_disposition_kappa": cohen_kappa(prior_dispositions, repeat_dispositions),
    }
    acceptance = {
        "all_cards_completed": len(responses) == len(cards),
        "at_least_8_determinate_controls": len(control_determinate) >= 8,
        "no_control_false_positives": len(false_positives) == 0,
        "at_least_5_promoted_triggers_detected": len(detected) >= 5,
        "at_least_4_exact_trigger_reasons": len(exact_reason) >= 4,
        "no_promoted_structural_contradictions": len(contradictions) == 0,
        "at_least_4_of_6_disposition_agreement": agreement_count >= 4,
        "disposition_kappa_at_least_0_40": (
            metrics["prior_repeat_disposition_kappa"] is not None
            and metrics["prior_repeat_disposition_kappa"] >= 0.40
        ),
    }
    bounded_pass = all(acceptance.values())
    return {
        "schema": "ovc-pd-june-mdr-corr2-scored-review/v1",
        "review_id": review_input.get("review_id"),
        "metrics": metrics,
        "acceptance": acceptance,
        "bounded_result": (
            "PASS_EXACT_JUNE_CONTROLLED_REPEAT_REVIEW"
            if bounded_pass
            else "DEFER_OR_BLOCK_EXACT_JUNE_CONTROLLED_REPEAT_REVIEW"
        ),
        "general_market_description_reliability": "NOT_ESTABLISHED_SINGLE_GAPPED_JUNE_SLICE",
    }
