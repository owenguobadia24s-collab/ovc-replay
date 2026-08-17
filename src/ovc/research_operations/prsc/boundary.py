from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping, Sequence

from ovc.research_operations.canonical import canonical_sha256

from .contracts import PRSCContractError


FORBIDDEN_BLIND_KEYS = frozenset({
    "c2e_boundary", "c2e_boundary_id", "c2e_episode_id", "canonical_boundary",
    "canonical_boundary_id", "canonical_episode_id", "owner_boundary", "owner_episode",
})


def _text(value: object) -> str:
    return str(value).strip()


def _decimal(value: object, code: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise PRSCContractError(code) from exc
    if not result.is_finite():
        raise PRSCContractError(code)
    return result


def _decimal_text(value: Decimal) -> str:
    if value == value.to_integral():
        return str(value.quantize(Decimal("1")))
    return format(value.normalize(), "f")


def build_tolerance_contract(
    *,
    contract_id: str,
    early_tolerance: object,
    late_tolerance: object,
    position_unit: str,
    uncertainty_policy: str = "DECLARED_INTERVAL_ONLY",
) -> dict:
    cid = _text(contract_id)
    unit = _text(position_unit)
    policy = _text(uncertainty_policy).upper()
    early = _decimal(early_tolerance, "PRSC_BOUNDARY_TOLERANCE_INVALID")
    late = _decimal(late_tolerance, "PRSC_BOUNDARY_TOLERANCE_INVALID")
    if not cid or not unit or early < 0 or late < 0 or policy != "DECLARED_INTERVAL_ONLY":
        raise PRSCContractError("PRSC_BOUNDARY_TOLERANCE_INVALID")
    payload = {
        "schema": "ovc-prsc-tolerance-contract/v0.1",
        "contract_id": cid,
        "position_unit": unit,
        "early_tolerance": _decimal_text(early),
        "late_tolerance": _decimal_text(late),
        "uncertainty_policy": policy,
        "post_hoc_widening": False,
        "authority_effect": "NONE",
    }
    payload["semantic_sha256"] = canonical_sha256(payload)
    return payload


def build_boundary_challenge_pack(
    *,
    pack_id: str,
    canonical_partition_ref: str,
    tolerance_contract_ref: str,
    challengers: Sequence[Mapping[str, object]],
) -> dict:
    pid = _text(pack_id)
    canonical = _text(canonical_partition_ref)
    tolerance = _text(tolerance_contract_ref)
    if not pid or not canonical or not tolerance or not challengers:
        raise PRSCContractError("PRSC_BOUNDARY_PACK_INVALID")
    normalized: list[dict] = []
    seen: set[str] = set()
    for row in challengers:
        challenger_id = _text(row.get("challenger_id", ""))
        method_pack_ref = _text(row.get("method_pack_ref", ""))
        challenger_class = _text(row.get("challenger_class", "")).upper()
        if (
            not challenger_id or challenger_id in seen or not method_pack_ref
            or challenger_class not in {"C2E_INTERNAL_VARIANT", "BLIND_INDEPENDENT_SEGMENTATION"}
        ):
            raise PRSCContractError("PRSC_BOUNDARY_CHALLENGER_INVALID")
        seen.add(challenger_id)
        normalized.append({
            "challenger_id": challenger_id,
            "challenger_class": challenger_class,
            "method_pack_ref": method_pack_ref,
            "canonical_episode_identity_effect": "NONE",
            "owner_authority_effect": "NONE",
        })
    payload = {
        "schema": "ovc-prsc-boundary-challenge-pack/v0.1",
        "pack_id": pid,
        "canonical_partition_ref": canonical,
        "tolerance_contract_ref": tolerance,
        "challengers": normalized,
        "declared_challenger_count": len(normalized),
        "selection_policy": "NO_WINNER",
        "canonical_episode_identity_immutable": True,
        "c2p_c25_c3_authority": "NONE",
        "authority_effect": "NONE",
    }
    payload["semantic_sha256"] = canonical_sha256(payload)
    return payload


def fit_blind_independent_segmentation(
    observations: Sequence[Mapping[str, object]],
    *,
    method_pack_ref: str,
    threshold: object,
    position_key: str = "position",
    value_key: str = "value",
) -> dict:
    method = _text(method_pack_ref)
    limit = _decimal(threshold, "PRSC_BLIND_SEGMENTATION_THRESHOLD_INVALID")
    if not method or limit < 0 or len(observations) < 2:
        raise PRSCContractError("PRSC_BLIND_SEGMENTATION_INPUT_INVALID")
    rows: list[tuple[Decimal, Decimal]] = []
    for row in observations:
        lowered = {str(key).lower() for key in row}
        if lowered & FORBIDDEN_BLIND_KEYS:
            raise PRSCContractError("PRSC_BLIND_SEGMENTATION_OWNER_LABEL_REACHABLE")
        position = _decimal(row.get(position_key), "PRSC_BLIND_SEGMENTATION_POSITION_INVALID")
        value = _decimal(row.get(value_key), "PRSC_BLIND_SEGMENTATION_VALUE_INVALID")
        rows.append((position, value))
    rows.sort(key=lambda item: item[0])
    if len({position for position, _ in rows}) != len(rows):
        raise PRSCContractError("PRSC_BLIND_SEGMENTATION_DUPLICATE_POSITION")
    boundaries: list[dict] = []
    for index in range(1, len(rows)):
        prior_position, prior_value = rows[index - 1]
        position, value = rows[index]
        magnitude = abs(value - prior_value)
        if magnitude >= limit:
            boundary_position = (prior_position + position) / Decimal("2")
            boundaries.append({
                "challenger_boundary_id": f"blind-boundary-{len(boundaries) + 1}",
                "position": _decimal_text(boundary_position),
                "change_magnitude": _decimal_text(magnitude),
            })
    payload = {
        "schema": "ovc-prsc-blind-segmentation-result/v0.1",
        "method_pack_ref": method,
        "threshold": _decimal_text(limit),
        "observation_count": len(rows),
        "boundaries": boundaries,
        "fit_input_contract": "OBSERVATIONS_WITHOUT_C2E_BOUNDARIES_OR_EPISODE_LABELS",
        "canonical_labels_read": False,
        "scientific_authority": "NONE",
        "authority_effect": "NONE",
    }
    payload["result_id"] = canonical_sha256(payload)
    return payload


def _boundary_rows(rows: Sequence[Mapping[str, object]], id_key: str) -> list[tuple[str, Decimal]]:
    output: list[tuple[str, Decimal]] = []
    seen: set[str] = set()
    for row in rows:
        boundary_id = _text(row.get(id_key, ""))
        position = _decimal(row.get("position"), "PRSC_BOUNDARY_POSITION_INVALID")
        if not boundary_id or boundary_id in seen:
            raise PRSCContractError("PRSC_BOUNDARY_ID_INVALID")
        seen.add(boundary_id)
        output.append((boundary_id, position))
    return sorted(output, key=lambda item: (item[1], item[0]))


def _better_alignment(left: tuple, right: tuple) -> tuple:
    left_key = (-left[0], left[1], left[2])
    right_key = (-right[0], right[1], right[2])
    return left if left_key <= right_key else right


def match_boundaries_one_to_one(
    *,
    canonical_boundaries: Sequence[Mapping[str, object]],
    challenger_boundaries: Sequence[Mapping[str, object]],
    tolerance_contract: Mapping[str, object],
) -> dict:
    canonical = _boundary_rows(canonical_boundaries, "canonical_boundary_id")
    challenger = _boundary_rows(challenger_boundaries, "challenger_boundary_id")
    early = _decimal(tolerance_contract.get("early_tolerance"), "PRSC_BOUNDARY_TOLERANCE_INVALID")
    late = _decimal(tolerance_contract.get("late_tolerance"), "PRSC_BOUNDARY_TOLERANCE_INVALID")
    if early < 0 or late < 0:
        raise PRSCContractError("PRSC_BOUNDARY_TOLERANCE_INVALID")

    # Ordered dynamic programming: maximize one-to-one matches, then minimize total
    # absolute displacement, then use pair identity as a deterministic tie-break.
    empty: tuple[int, Decimal, tuple[tuple[str, str, str], ...]] = (0, Decimal("0"), ())
    dp: list[list[tuple[int, Decimal, tuple[tuple[str, str, str], ...]]]] = [
        [empty for _ in range(len(challenger) + 1)] for _ in range(len(canonical) + 1)
    ]
    for i in range(len(canonical) + 1):
        for j in range(len(challenger) + 1):
            if i == 0 and j == 0:
                continue
            candidates: list[tuple[int, Decimal, tuple[tuple[str, str, str], ...]]] = []
            if i:
                candidates.append(dp[i - 1][j])
            if j:
                candidates.append(dp[i][j - 1])
            if i and j:
                canonical_id, canonical_position = canonical[i - 1]
                challenger_id, challenger_position = challenger[j - 1]
                delta = challenger_position - canonical_position
                if -early <= delta <= late:
                    prior = dp[i - 1][j - 1]
                    pair = (canonical_id, challenger_id, _decimal_text(delta))
                    candidates.append((prior[0] + 1, prior[1] + abs(delta), prior[2] + (pair,)))
            best = candidates[0]
            for candidate in candidates[1:]:
                best = _better_alignment(best, candidate)
            dp[i][j] = best

    matched_pairs = dp[-1][-1][2]
    matched_canonical = {pair[0] for pair in matched_pairs}
    matched_challenger = {pair[1] for pair in matched_pairs}
    pair_rows = [
        {
            "canonical_boundary_id": canonical_id,
            "challenger_boundary_id": challenger_id,
            "signed_displacement": delta,
            "direction": "EARLY" if Decimal(delta) < 0 else "LATE" if Decimal(delta) > 0 else "EXACT",
        }
        for canonical_id, challenger_id, delta in matched_pairs
    ]
    payload = {
        "schema": "ovc-prsc-correspondence-ledger/v0.1",
        "tolerance_contract_ref": _text(tolerance_contract.get("semantic_sha256", tolerance_contract.get("contract_id", ""))),
        "matches": pair_rows,
        "unmatched_canonical_boundary_ids": [boundary_id for boundary_id, _ in canonical if boundary_id not in matched_canonical],
        "unmatched_challenger_boundary_ids": [boundary_id for boundary_id, _ in challenger if boundary_id not in matched_challenger],
        "canonical_boundary_count": len(canonical),
        "challenger_boundary_count": len(challenger),
        "matched_count": len(pair_rows),
        "one_to_one": True,
        "directional": True,
        "multiple_confirmation_claim": False,
        "complete_accounting": True,
        "authority_effect": "NONE",
    }
    payload["ledger_id"] = canonical_sha256(payload)
    return payload


def build_boundary_preserving_control(
    *,
    control_id: str,
    source_partition_ref: str,
    boundary_positions: Iterable[object],
    transform_ref: str,
) -> dict:
    cid = _text(control_id)
    source = _text(source_partition_ref)
    transform = _text(transform_ref)
    positions = sorted({_decimal(value, "PRSC_BOUNDARY_CONTROL_POSITION_INVALID") for value in boundary_positions})
    if not cid or not source or not transform or not positions:
        raise PRSCContractError("PRSC_BOUNDARY_CONTROL_INVALID")
    payload = {
        "schema": "ovc-prsc-boundary-preserving-control/v0.1",
        "control_id": cid,
        "source_partition_ref": source,
        "transform_ref": transform,
        "locked_boundary_positions": [_decimal_text(value) for value in positions],
        "boundary_count": len(positions),
        "boundary_positions_immutable": True,
        "selection_effect": "NONE",
        "authority_effect": "NONE",
    }
    payload["semantic_sha256"] = canonical_sha256(payload)
    return payload


def _partition_rows(rows: Sequence[Mapping[str, object]], id_key: str) -> list[dict]:
    output: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        episode_id = _text(row.get(id_key, ""))
        start = _decimal(row.get("start"), "PRSC_EPISODE_INTERVAL_INVALID")
        end = _decimal(row.get("end"), "PRSC_EPISODE_INTERVAL_INVALID")
        morphology = _text(row.get("morphology", "UNDECLARED")).upper()
        if not episode_id or episode_id in seen or end <= start:
            raise PRSCContractError("PRSC_EPISODE_INTERVAL_INVALID")
        seen.add(episode_id)
        output.append({"episode_id": episode_id, "start": start, "end": end, "morphology": morphology})
    output.sort(key=lambda row: (row["start"], row["end"], row["episode_id"]))
    for previous, current in zip(output, output[1:]):
        if current["start"] < previous["end"]:
            raise PRSCContractError("PRSC_EPISODE_PARTITION_OVERLAP")
    return output


def build_episode_partition_correspondence(
    *,
    canonical_episodes: Sequence[Mapping[str, object]],
    challenger_episodes: Sequence[Mapping[str, object]],
) -> dict:
    canonical = _partition_rows(canonical_episodes, "canonical_episode_id")
    challenger = _partition_rows(challenger_episodes, "challenger_episode_id")
    if not canonical or not challenger:
        raise PRSCContractError("PRSC_EPISODE_PARTITION_REQUIRED")
    rows: list[dict] = []
    challenger_use: dict[str, int] = {row["episode_id"]: 0 for row in challenger}
    for source in canonical:
        overlaps: list[tuple[str, Decimal]] = []
        for target in challenger:
            overlap = min(source["end"], target["end"]) - max(source["start"], target["start"])
            if overlap > 0:
                overlaps.append((target["episode_id"], overlap))
                challenger_use[target["episode_id"]] += 1
        if not overlaps:
            state = "UNMATCHED"
        elif len(overlaps) > 1:
            state = "SPLIT"
        else:
            target = next(row for row in challenger if row["episode_id"] == overlaps[0][0])
            if source["start"] == target["start"] and source["end"] == target["end"]:
                state = "EXACT"
            else:
                state = "PARTIAL"
        rows.append({
            "canonical_episode_id": source["episode_id"],
            "challenger_episode_ids": [target_id for target_id, _ in overlaps],
            "overlap_widths": [_decimal_text(width) for _, width in overlaps],
            "state": state,
        })
    for row in rows:
        if len(row["challenger_episode_ids"]) == 1 and challenger_use[row["challenger_episode_ids"][0]] > 1:
            row["state"] = "MERGE"
    payload = {
        "schema": "ovc-prsc-episode-partition-correspondence-record/v0.1",
        "rows": rows,
        "unmatched_challenger_episode_ids": sorted(key for key, count in challenger_use.items() if count == 0),
        "canonical_episode_count": len(canonical),
        "challenger_episode_count": len(challenger),
        "complete_accounting": True,
        "canonical_episode_identity_effect": "NONE",
        "directional": True,
        "authority_effect": "NONE",
    }
    payload["record_id"] = canonical_sha256(payload)
    return payload


def build_c2e_internal_variant_correspondence(
    *,
    canonical_partition_ref: str,
    variant_ref: str,
    canonical_episodes: Sequence[Mapping[str, object]],
    variant_episodes: Sequence[Mapping[str, object]],
) -> dict:
    canonical_ref = _text(canonical_partition_ref)
    internal_ref = _text(variant_ref)
    if not canonical_ref or not internal_ref:
        raise PRSCContractError("PRSC_C2E_INTERNAL_VARIANT_REF_INVALID")
    result = build_episode_partition_correspondence(
        canonical_episodes=canonical_episodes,
        challenger_episodes=variant_episodes,
    )
    result.update({
        "challenger_class": "C2E_INTERNAL_VARIANT",
        "canonical_partition_ref": canonical_ref,
        "variant_ref": internal_ref,
        "canonical_episode_identity_immutable": True,
        "variant_is_owner_truth": False,
    })
    result["record_id"] = canonical_sha256({key: value for key, value in result.items() if key != "record_id"})
    return result


def build_morphology_invariant_core(views: Mapping[str, object]) -> dict:
    if not views:
        raise PRSCContractError("PRSC_MORPHOLOGY_VIEWS_REQUIRED")
    evaluable: list[set[str]] = []
    all_morphologies: set[str] = set()
    accounting: list[dict] = []
    incomplete = False
    for view_id in sorted(views):
        value = views[view_id]
        if isinstance(value, Mapping):
            status = _text(value.get("status", "EVALUABLE")).upper()
            morphologies = {_text(item).upper() for item in value.get("morphologies", ()) if _text(item)}
        else:
            status = "EVALUABLE"
            morphologies = {_text(item).upper() for item in value if _text(item)}
        if status == "EVALUABLE":
            evaluable.append(morphologies)
            all_morphologies.update(morphologies)
        else:
            incomplete = True
        accounting.append({"view_id": str(view_id), "status": status, "morphology_count": len(morphologies)})
    if not evaluable:
        core: set[str] = set()
        state = "NOT_EVALUABLE"
        universal = False
    else:
        core = set.intersection(*evaluable)
        state = "PARTIAL_NOT_UNIVERSAL" if incomplete else "COMPLETE_UNIVERSAL_CORE"
        universal = not incomplete
    payload = {
        "schema": "ovc-prsc-morphology-invariant-core/v0.1",
        "state": state,
        "core": sorted(core),
        "shell": sorted(all_morphologies - core),
        "view_accounting": accounting,
        "universal_claim": universal,
        "canonical_episode_identity_effect": "NONE",
        "selection_effect": "NONE",
        "authority_effect": "NONE",
    }
    payload["invariant_core_id"] = canonical_sha256(payload)
    return payload
