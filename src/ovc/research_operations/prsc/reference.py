from __future__ import annotations

import random
from math import fsum
from typing import Mapping, Sequence

from ovc.research_operations.canonical import canonical_sha256
from .contracts import PRSCContractError


def _manifest_blocks(manifest: Mapping[str, object]) -> dict[str, tuple[str, ...]]:
    blocks = {str(item["block_id"]): tuple(str(v) for v in item["unit_ids"]) for item in manifest.get("blocks", [])}
    if not blocks:
        raise PRSCContractError("PRSC_REFERENCE_BLOCKS_REQUIRED")
    return blocks


def build_reference_method_pack(*, method_pack_id: str, primary_method: str = "DEPENDENCY_PRESERVING_BLOCK_RESAMPLE", secondary_methods: Sequence[str] = ()) -> dict:
    if primary_method != "DEPENDENCY_PRESERVING_BLOCK_RESAMPLE":
        raise PRSCContractError("PRSC_REFERENCE_PRIMARY_MUST_BE_REFERENCE_FIRST_BLOCK_RESAMPLE")
    allowed_secondary = {"HAC_EXPLICIT_ORDERED_SECONDARY"}
    unknown = set(secondary_methods) - allowed_secondary
    if unknown:
        raise PRSCContractError(f"PRSC_REFERENCE_SECONDARY_UNKNOWN:{','.join(sorted(unknown))}")
    payload = {
        "schema": "ovc-prsc-reference-method-pack/v0.1",
        "method_pack_id": method_pack_id,
        "primary_method": primary_method,
        "secondary_methods": list(secondary_methods),
        "universal_n_eff": None,
        "universal_alpha": None,
        "reference_first": True,
        "authority_effect": "NONE",
    }
    payload["semantic_sha256"] = canonical_sha256(payload)
    return payload


def dependency_preserving_block_resample(manifest: Mapping[str, object], *, draws: int, seed: int) -> dict:
    if draws < 1:
        raise PRSCContractError("PRSC_REFERENCE_DRAWS_INVALID")
    blocks = _manifest_blocks(manifest)
    block_ids = tuple(sorted(blocks))
    rng = random.Random(int(seed))
    ensembles: list[dict] = []
    accounting: list[dict] = []
    for draw_index in range(draws):
        sampled_ids = tuple(rng.choice(block_ids) for _ in block_ids)
        sampled_blocks = [{"source_block_id": bid, "unit_ids": list(blocks[bid])} for bid in sampled_ids]
        ensembles.append({"draw_index": draw_index, "sampled_blocks": sampled_blocks})
        accounting.append({"draw_index": draw_index, "state": "GENERATED", "sampled_block_count": len(sampled_blocks), "sampled_unit_count": sum(len(v["unit_ids"]) for v in sampled_blocks)})
    payload = {
        "schema": "ovc-prsc-reference-ensemble-manifest/v0.1",
        "reference_method": "DEPENDENCY_PRESERVING_BLOCK_RESAMPLE",
        "seed": int(seed),
        "requested_draws": draws,
        "generated_draws": draws,
        "rejected_draws": 0,
        "draws": ensembles,
        "accounting": accounting,
        "silent_surrogate_drop": False,
        "authority_effect": "NONE",
    }
    payload["ensemble_id"] = canonical_sha256(payload)
    return payload


def validate_reference_preservation(block_manifest: Mapping[str, object], ensemble_manifest: Mapping[str, object]) -> dict:
    blocks = _manifest_blocks(block_manifest)
    failures: list[dict] = []
    checked = 0
    for draw in ensemble_manifest.get("draws", []):
        for sample in draw.get("sampled_blocks", []):
            checked += 1
            block_id = str(sample.get("source_block_id"))
            units = tuple(str(v) for v in sample.get("unit_ids", []))
            if block_id not in blocks:
                failures.append({"draw_index": draw.get("draw_index"), "reason": "UNKNOWN_SOURCE_BLOCK", "block_id": block_id})
            elif units != blocks[block_id]:
                failures.append({"draw_index": draw.get("draw_index"), "reason": "DEPENDENCE_BLOCK_MUTATED_OR_SPLIT", "block_id": block_id})
    return {"schema": "ovc-prsc-reference-preservation-manifest/v0.1", "status": "PASS" if not failures else "BLOCK", "checked_sampled_blocks": checked, "failures": failures, "block_preservation_required": True, "authority_effect": "NONE"}


def build_negative_space_controls(block_manifest: Mapping[str, object], *, positive_unit_ids: Sequence[str]) -> dict:
    blocks = _manifest_blocks(block_manifest)
    positive = set(map(str, positive_unit_ids))
    eligible: list[str] = []
    ineligible: list[dict] = []
    accounted_units: set[str] = set()
    for block_id in sorted(blocks):
        members = set(blocks[block_id])
        accounted_units.update(members)
        if members & positive:
            ineligible.append({"block_id": block_id, "reason": "SHARES_DEPENDENCE_BLOCK_WITH_POSITIVE"})
        else:
            eligible.append(block_id)
    return {"eligible_negative_control_block_ids": eligible, "ineligible_blocks": ineligible, "accounted_unit_count": len(accounted_units), "positive_unit_ids": sorted(positive), "control_selection_scope": "WHOLE_BLOCK_ONLY", "silent_drop": False}


def hac_ordered_secondary(values: Sequence[float], *, max_lag: int, ordered: bool) -> dict:
    """Explicit-lag HAC-style covariance summary; never n_eff or a decision threshold."""
    if not ordered:
        raise PRSCContractError("PRSC_HAC_REQUIRES_LAWFUL_ORDERING")
    if max_lag < 0:
        raise PRSCContractError("PRSC_HAC_LAG_INVALID")
    vals = tuple(float(v) for v in values)
    if len(vals) < 2:
        raise PRSCContractError("PRSC_HAC_VALUES_INSUFFICIENT")
    mean = fsum(vals) / len(vals)
    centered = tuple(v - mean for v in vals)
    gamma0 = fsum(v * v for v in centered) / len(vals)
    terms: list[dict] = []
    hac = gamma0
    limit = min(max_lag, len(vals) - 1)
    for lag in range(1, limit + 1):
        covariance = fsum(centered[i] * centered[i - lag] for i in range(lag, len(vals))) / len(vals)
        weight = 1.0 - lag / (limit + 1.0) if limit else 0.0
        hac += 2.0 * weight * covariance
        terms.append({"lag": lag, "bartlett_weight": weight, "covariance": covariance})
    return {"adapter": "HAC_EXPLICIT_ORDERED_SECONDARY", "n": len(vals), "max_lag": max_lag, "variance_summary": hac, "lag_terms": terms, "n_eff": None, "alpha": None, "decision_effect": "ANNOTATE_ONLY"}
