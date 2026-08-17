from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Mapping, Sequence

from ovc.research_operations.canonical import canonical_sha256
from .contracts import PRSCContractError

SUPPORT_STATES = frozenset({"SUPPORTED", "NOT_SUPPORTED", "NOT_EVALUABLE", "FAILED"})


def _strings(values: Iterable[object]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def _block_rows(blocks: Mapping[str, Sequence[str]], block_class: str) -> list[dict]:
    rows: list[dict] = []
    for block_id in sorted(blocks):
        bid = str(block_id).strip()
        members = _strings(blocks[block_id])
        if not bid or not members:
            raise PRSCContractError("PRSC_TEMPORAL_BLOCK_INVALID")
        rows.append({"block_id": bid, "block_class": block_class, "unit_ids": list(members)})
    return rows


def build_temporal_challenge_pack(
    *,
    pack_id: str,
    year_blocks: Mapping[str, Sequence[str]],
    fixed_blocks: Mapping[str, Sequence[str]],
) -> dict:
    pid = str(pack_id).strip()
    blocks = _block_rows(year_blocks, "YEAR") + _block_rows(fixed_blocks, "FIXED_BLOCK")
    ids = [row["block_id"] for row in blocks]
    if not pid or not blocks or len(ids) != len(set(ids)):
        raise PRSCContractError("PRSC_TEMPORAL_PACK_INVALID")
    payload = {
        "schema": "ovc-prsc-temporal-challenge-pack/v0.1",
        "pack_id": pid,
        "blocks": sorted(blocks, key=lambda row: (row["block_class"], row["block_id"])),
        "selection_policy": "NO_BEST_BLOCK",
        "post_hoc_applicability_change": False,
        "replication_claim": False,
        "latent_regime_claim": False,
        "causal_claim": False,
        "authority_effect": "NONE",
    }
    payload["semantic_sha256"] = canonical_sha256(payload)
    return payload


def build_temporal_support_profile(*, rows: Sequence[Mapping[str, object]], declared_block_ids: Sequence[str]) -> dict:
    block_ids = _strings(declared_block_ids)
    if not block_ids:
        raise PRSCContractError("PRSC_TEMPORAL_DECLARED_BLOCKS_REQUIRED")
    buckets = {block_id: {state: 0 for state in sorted(SUPPORT_STATES)} for block_id in block_ids}
    for row in rows:
        block_id = str(row.get("block_id", "")).strip()
        state = str(row.get("state", "")).strip().upper()
        if block_id not in buckets or state not in SUPPORT_STATES:
            raise PRSCContractError("PRSC_TEMPORAL_SUPPORT_ROW_INVALID")
        buckets[block_id][state] += 1
    output_blocks: list[dict] = []
    for block_id in block_ids:
        counts = buckets[block_id]
        total = sum(counts.values())
        evaluable = counts["SUPPORTED"] + counts["NOT_SUPPORTED"]
        rate = str((Decimal(counts["SUPPORTED"]) / Decimal(evaluable)).normalize()) if evaluable else None
        output_blocks.append({
            "block_id": block_id,
            "counts": counts,
            "denominator_count": total,
            "evaluable_count": evaluable,
            "support_rate_given_evaluable": rate,
        })
    payload = {
        "schema": "ovc-prsc-temporal-support-profile/v0.1",
        "blocks": output_blocks,
        "total_count": sum(row["denominator_count"] for row in output_blocks),
        "complete_accounting": True,
        "silent_denominator_shrink": False,
        "replication_claim": False,
        "authority_effect": "NONE",
    }
    payload["profile_id"] = canonical_sha256(payload)
    return payload


def leave_one_block_out_support(profile: Mapping[str, object]) -> tuple[dict, ...]:
    blocks = list(profile.get("blocks", []))
    if not blocks:
        raise PRSCContractError("PRSC_TEMPORAL_LOBO_BLOCKS_REQUIRED")
    out: list[dict] = []
    for omitted in blocks:
        remaining = [row for row in blocks if row is not omitted]
        out.append({
            "omitted_block_id": str(omitted["block_id"]),
            "remaining_denominator_count": sum(int(row["denominator_count"]) for row in remaining),
            "remaining_evaluable_count": sum(int(row["evaluable_count"]) for row in remaining),
            "remaining_supported_count": sum(int(row["counts"]["SUPPORTED"]) for row in remaining),
            "diagnostic_effect": "ANNOTATE_ONLY",
        })
    return tuple(out)


def within_discovery_forward_support(profile: Mapping[str, object], *, ordered_block_ids: Sequence[str]) -> tuple[dict, ...]:
    order = tuple(str(value) for value in ordered_block_ids)
    by_id = {str(row["block_id"]): row for row in profile.get("blocks", [])}
    if len(order) < 2 or set(order) != set(by_id):
        raise PRSCContractError("PRSC_FORWARD_SUPPORT_ORDER_INVALID")
    out: list[dict] = []
    for index in range(1, len(order)):
        target_id = order[index]
        target = by_id[target_id]
        out.append({
            "prior_block_ids": list(order[:index]),
            "target_block_id": target_id,
            "target_denominator_count": int(target["denominator_count"]),
            "target_evaluable_count": int(target["evaluable_count"]),
            "target_supported_count": int(target["counts"]["SUPPORTED"]),
            "evidence_class": "WITHIN_DISCOVERY_SUPPORT_DIAGNOSTIC",
            "replication_claim": False,
        })
    return tuple(out)


def build_context_challenge_pack(*, pack_id: str, context_dimensions: Sequence[str]) -> dict:
    pid = str(pack_id).strip()
    dimensions = _strings(context_dimensions)
    if not pid or not dimensions:
        raise PRSCContractError("PRSC_CONTEXT_PACK_INVALID")
    payload = {
        "schema": "ovc-prsc-context-challenge-pack/v0.1",
        "pack_id": pid,
        "context_dimensions": list(dimensions),
        "context_role": "STRATIFIER_ONLY",
        "structural_identity_effect": "NONE",
        "post_hoc_applicability_change": False,
        "causal_claim": False,
        "authority_effect": "NONE",
    }
    payload["semantic_sha256"] = canonical_sha256(payload)
    return payload


def build_temporal_context_stability_matrix(
    *,
    time_block_ids: Sequence[str],
    context_values: Sequence[str],
    rows: Sequence[Mapping[str, object]],
) -> dict:
    times = _strings(time_block_ids)
    contexts = _strings(context_values)
    if not times or not contexts:
        raise PRSCContractError("PRSC_TEMPORAL_CONTEXT_AXES_REQUIRED")
    buckets = {(time_id, context): {state: 0 for state in sorted(SUPPORT_STATES)} for time_id in times for context in contexts}
    for row in rows:
        key = (str(row.get("time_block_id", "")).strip(), str(row.get("context_value", "")).strip())
        state = str(row.get("state", "")).strip().upper()
        if key not in buckets or state not in SUPPORT_STATES:
            raise PRSCContractError("PRSC_TEMPORAL_CONTEXT_ROW_INVALID")
        buckets[key][state] += 1
    cells: list[dict] = []
    for time_id in times:
        for context in contexts:
            counts = buckets[(time_id, context)]
            denominator = sum(counts.values())
            evaluable = counts["SUPPORTED"] + counts["NOT_SUPPORTED"]
            cells.append({
                "time_block_id": time_id,
                "context_value": context,
                "counts": counts,
                "denominator_count": denominator,
                "evaluable_count": evaluable,
            })
    denominator_shapes = {(cell["denominator_count"], cell["evaluable_count"]) for cell in cells}
    support_shapes = {(cell["counts"]["SUPPORTED"], cell["counts"]["NOT_SUPPORTED"]) for cell in cells}
    payload = {
        "schema": "ovc-prsc-temporal-context-stability-matrix/v0.1",
        "time_block_ids": list(times),
        "context_values": list(contexts),
        "cells": cells,
        "cartesian_complete": True,
        "expected_cell_count": len(times) * len(contexts),
        "evaluability_or_composition_drift_detected": len(denominator_shapes) > 1,
        "support_distribution_varies": len(support_shapes) > 1,
        "structural_drift_inferred": False,
        "context_structural_identity_effect": "NONE",
        "post_hoc_applicability_change": False,
        "authority_effect": "NONE",
    }
    payload["matrix_id"] = canonical_sha256(payload)
    return payload
