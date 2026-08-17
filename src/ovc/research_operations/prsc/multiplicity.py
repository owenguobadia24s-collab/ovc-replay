from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Mapping, Sequence

from ovc.research_operations.canonical import canonical_sha256
from .contracts import PRSCContractError


LEDGER_STATES = frozenset({"DECLARED", "ATTEMPTED", "FAILED", "POST_HOC"})


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


def build_hypothesis_family_registry(
    *, family_id: str, hypotheses: Sequence[Mapping[str, object]], parent_family_id: str | None = None
) -> dict:
    fid = _text(family_id)
    if not fid or not hypotheses:
        raise PRSCContractError("PRSC_MULTIPLICITY_FAMILY_INVALID")
    normalized: list[dict] = []
    seen: set[str] = set()
    for row in hypotheses:
        hid = _text(row.get("hypothesis_id", ""))
        semantic_key = _text(row.get("semantic_key", ""))
        if not hid or hid in seen or not semantic_key:
            raise PRSCContractError("PRSC_MULTIPLICITY_HYPOTHESIS_INVALID")
        seen.add(hid)
        normalized.append({
            "hypothesis_id": hid,
            "semantic_key": semantic_key,
            "parent_hypothesis_id": _text(row.get("parent_hypothesis_id", "")) or None,
            "status": _text(row.get("status", "DECLARED")).upper(),
        })
    unknown_parents = {
        row["parent_hypothesis_id"] for row in normalized
        if row["parent_hypothesis_id"] is not None and row["parent_hypothesis_id"] not in seen
    }
    if unknown_parents:
        raise PRSCContractError("PRSC_MULTIPLICITY_PARENT_UNKNOWN")
    payload = {
        "schema": "ovc-prsc-scientific-hypothesis-family-registry/v0.1",
        "family_id": fid,
        "parent_family_id": _text(parent_family_id) or None,
        "hypotheses": normalized,
        "declared_hypothesis_count": len(normalized),
        "family_shrink_after_results": False,
        "authority_effect": "NONE",
    }
    payload["semantic_sha256"] = canonical_sha256(payload)
    return payload


def collapse_exact_semantic_duplicates(family_registry: Mapping[str, object]) -> dict:
    groups: dict[str, list[str]] = {}
    for row in family_registry.get("hypotheses", []):
        groups.setdefault(_text(row.get("semantic_key", "")), []).append(_text(row.get("hypothesis_id", "")))
    if "" in groups:
        raise PRSCContractError("PRSC_MULTIPLICITY_HYPOTHESIS_INVALID")
    collapsed = [
        {"inference_hypothesis_id": sorted(ids)[0], "provenance_hypothesis_ids": sorted(ids), "semantic_key": key}
        for key, ids in sorted(groups.items())
    ]
    return {
        "schema": "ovc-prsc-exact-semantic-collapse/v0.1",
        "family_id": family_registry.get("family_id"),
        "groups": collapsed,
        "original_count": sum(len(v) for v in groups.values()),
        "inference_count": len(collapsed),
        "provenance_preserved": True,
        "collapse_rule": "EXACT_SEMANTIC_KEY_ONLY",
        "authority_effect": "NONE",
    }


def build_specification_opportunity_ledger(
    *, family_id: str, configurations: Sequence[Mapping[str, object]]
) -> dict:
    fid = _text(family_id)
    if not fid or not configurations:
        raise PRSCContractError("PRSC_MULTIPLICITY_LEDGER_INVALID")
    rows: list[dict] = []
    seen: set[str] = set()
    for item in configurations:
        cid = _text(item.get("configuration_id", ""))
        state = _text(item.get("state", "")).upper()
        if not cid or cid in seen or state not in LEDGER_STATES:
            raise PRSCContractError("PRSC_MULTIPLICITY_LEDGER_ROW_INVALID")
        seen.add(cid)
        rows.append({
            "configuration_id": cid,
            "state": state,
            "hypothesis_id": _text(item.get("hypothesis_id", "")) or None,
            "reason": _text(item.get("reason", "")) or None,
        })
    counts = {state: sum(row["state"] == state for row in rows) for state in sorted(LEDGER_STATES)}
    payload = {
        "schema": "ovc-prsc-specification-opportunity-ledger/v0.1",
        "family_id": fid,
        "configurations": rows,
        "state_counts": counts,
        "complete_accounting": True,
        "post_hoc_visible": True,
        "authority_effect": "NONE",
    }
    payload["semantic_sha256"] = canonical_sha256(payload)
    return payload


def build_multiplicity_method_pack(*, method_pack_id: str, familywise_alpha: object) -> dict:
    mid = _text(method_pack_id)
    alpha = _decimal(familywise_alpha, "PRSC_MULTIPLICITY_ALPHA_INVALID")
    if not mid or not Decimal("0") < alpha < Decimal("1"):
        raise PRSCContractError("PRSC_MULTIPLICITY_ALPHA_INVALID")
    payload = {
        "schema": "ovc-prsc-multiplicity-method-pack/v0.1",
        "method_pack_id": mid,
        "method": "STEP_DOWN_MAX_STATISTIC",
        "familywise_alpha": format(alpha.normalize(), "f"),
        "shared_reference_draws_required": True,
        "family_redefinition_after_results": "FORBIDDEN",
        "authority_effect": "NONE",
    }
    payload["semantic_sha256"] = canonical_sha256(payload)
    return payload


def build_shared_family_reference_draws(
    *, family_registry: Mapping[str, object], hypothesis_draws: Mapping[str, Sequence[object]]
) -> dict:
    hypothesis_ids = [_text(row.get("hypothesis_id", "")) for row in family_registry.get("hypotheses", [])]
    if not hypothesis_ids or set(hypothesis_draws) != set(hypothesis_ids):
        raise PRSCContractError("PRSC_MULTIPLICITY_SHARED_DRAWS_INCOMPLETE")
    lengths = {len(hypothesis_draws[hid]) for hid in hypothesis_ids}
    if len(lengths) != 1 or not lengths or next(iter(lengths)) < 1:
        raise PRSCContractError("PRSC_MULTIPLICITY_SHARED_DRAWS_MISALIGNED")
    draw_count = next(iter(lengths))
    draws: list[dict] = []
    for draw_index in range(draw_count):
        stats = {hid: str(_decimal(hypothesis_draws[hid][draw_index], "PRSC_MULTIPLICITY_DRAW_INVALID")) for hid in hypothesis_ids}
        draws.append({"draw_index": draw_index, "statistics": stats})
    payload = {
        "schema": "ovc-prsc-shared-family-reference-draws/v0.1",
        "family_id": family_registry.get("family_id"),
        "hypothesis_ids": hypothesis_ids,
        "draw_count": draw_count,
        "draws": draws,
        "joint_dependence_preserved": True,
        "authority_effect": "NONE",
    }
    payload["semantic_sha256"] = canonical_sha256(payload)
    return payload


def step_down_max_statistic_adjustment(
    *, observed_statistics: Mapping[str, object], shared_reference_draws: Mapping[str, object], method_pack: Mapping[str, object]
) -> dict:
    if method_pack.get("method") != "STEP_DOWN_MAX_STATISTIC":
        raise PRSCContractError("PRSC_MULTIPLICITY_METHOD_UNSUPPORTED")
    hypothesis_ids = list(shared_reference_draws.get("hypothesis_ids", []))
    if set(observed_statistics) != set(hypothesis_ids):
        raise PRSCContractError("PRSC_MULTIPLICITY_OBSERVED_FAMILY_MISMATCH")
    observed = {hid: _decimal(observed_statistics[hid], "PRSC_MULTIPLICITY_OBSERVED_INVALID") for hid in hypothesis_ids}
    ordered = sorted(hypothesis_ids, key=lambda hid: (-observed[hid], hid))
    draws = shared_reference_draws.get("draws", [])
    if not draws:
        raise PRSCContractError("PRSC_MULTIPLICITY_SHARED_DRAWS_INCOMPLETE")
    raw: dict[str, Decimal] = {}
    remaining = list(ordered)
    denominator = Decimal(len(draws) + 1)
    for hid in ordered:
        exceed = 0
        for draw in draws:
            stats = draw.get("statistics", {})
            if set(stats) != set(hypothesis_ids):
                raise PRSCContractError("PRSC_MULTIPLICITY_SHARED_DRAWS_INCOMPLETE")
            reference_max = max(_decimal(stats[rid], "PRSC_MULTIPLICITY_DRAW_INVALID") for rid in remaining)
            if reference_max >= observed[hid]:
                exceed += 1
        raw[hid] = Decimal(exceed + 1) / denominator
        remaining.remove(hid)
    adjusted: dict[str, Decimal] = {}
    running = Decimal("0")
    for hid in ordered:
        running = max(running, raw[hid])
        adjusted[hid] = min(Decimal("1"), running)
    alpha = _decimal(method_pack.get("familywise_alpha"), "PRSC_MULTIPLICITY_ALPHA_INVALID")
    rows = [{
        "hypothesis_id": hid,
        "observed_statistic": str(observed[hid]),
        "raw_stepdown_p": format(raw[hid], "f"),
        "adjusted_p": format(adjusted[hid], "f"),
        "reject_at_declared_alpha": adjusted[hid] <= alpha,
    } for hid in ordered]
    payload = {
        "schema": "ovc-prsc-adjustment-record/v0.1",
        "method_pack_id": method_pack.get("method_pack_id"),
        "family_id": shared_reference_draws.get("family_id"),
        "ordered_hypothesis_ids": ordered,
        "rows": rows,
        "shared_draw_count": len(draws),
        "joint_dependence_preserved": True,
        "authority_effect": "NONE",
    }
    payload["semantic_sha256"] = canonical_sha256(payload)
    return payload


def enforce_review_capacity(*, family_registry: Mapping[str, object], reviewed_hypothesis_ids: Sequence[str], capacity_limit: int) -> dict:
    declared = [_text(row.get("hypothesis_id", "")) for row in family_registry.get("hypotheses", [])]
    reviewed = [_text(v) for v in reviewed_hypothesis_ids]
    if len(set(reviewed)) != len(reviewed) or not set(reviewed).issubset(set(declared)) or capacity_limit < 1:
        raise PRSCContractError("PRSC_REVIEW_CAPACITY_INPUT_INVALID")
    complete = set(reviewed) == set(declared)
    capacity_sufficient = capacity_limit >= len(declared)
    status = "PASS" if complete else "REVIEW_CAPACITY_EXCEEDED"
    return {
        "schema": "ovc-prsc-review-capacity-assessment/v0.1",
        "family_id": family_registry.get("family_id"),
        "declared_count": len(declared),
        "reviewed_count": len(reviewed),
        "capacity_limit": capacity_limit,
        "capacity_sufficient_for_single_batch": capacity_sufficient,
        "status": status,
        "hidden_top_n_allowed": False,
        "required_action": "NONE" if complete else "DETERMINISTIC_BATCH_ALL_OR_DEFER_FAMILY",
        "authority_effect": "NONE",
    }
