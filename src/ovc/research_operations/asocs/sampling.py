"""ASOCS WP6 deterministic sampling prebuild.

No review population is frozen by this module. It implements the G2-frozen ranking
algorithm, stratum exhaustion, de-duplication, opaque blind IDs, and the pre-census
operational hidden-repeat/session choices.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any, Iterable, Mapping, Sequence


class ASOCSSamplingError(ValueError):
    pass


def selection_score(population_hash: str, nonce_hex: str, stratum_id: str, object_id: str) -> str:
    payload = (population_hash + nonce_hex + stratum_id + object_id).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def select_frame(
    objects: Iterable[Mapping[str, Any]],
    *,
    population_hash: str,
    nonce_hex: str,
    stratum_id: str,
    target_size: int,
) -> dict[str, Any]:
    if target_size < 0:
        raise ASOCSSamplingError("NEGATIVE_TARGET_SIZE")
    rows = [dict(x) for x in objects]
    ids = [str(x["object_id"]) for x in rows]
    if len(ids) != len(set(ids)):
        raise ASOCSSamplingError("DUPLICATE_OBJECT_ID")
    ranked = sorted(
        rows,
        key=lambda row: (
            selection_score(population_hash, nonce_hex, stratum_id, str(row["object_id"])),
            str(row["object_id"]),
        ),
    )
    exhausted = len(ranked) < target_size
    chosen = ranked if exhausted else ranked[:target_size]
    return {
        "stratum_id": stratum_id,
        "target_size": target_size,
        "eligible_count": len(ranked),
        "selection_count": len(chosen),
        "exhaustion": "STRATUM_EXHAUSTED_FULL_CENSUS" if exhausted else "TARGET_FILLED",
        "object_ids": [str(x["object_id"]) for x in chosen],
        "scores": {
            str(x["object_id"]): selection_score(population_hash, nonce_hex, stratum_id, str(x["object_id"]))
            for x in chosen
        },
    }


def deduplicate_frames(frames: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    membership: dict[str, list[str]] = {}
    for frame in frames:
        sid = str(frame["stratum_id"])
        for object_id in frame["object_ids"]:
            membership.setdefault(str(object_id), []).append(sid)
    return [
        {"review_unit_id": object_id, "stratum_memberships": sorted(set(strata))}
        for object_id, strata in sorted(membership.items())
    ]


def blind_case_id(population_hash: str, nonce_hex: str, review_unit_id: str) -> str:
    digest = hashlib.sha256(
        (population_hash + nonce_hex + "BLIND_CASE" + review_unit_id).encode("utf-8")
    ).hexdigest()
    return "ASOCS.BLIND." + digest[:24]


def freeze_case_order(
    units: Sequence[Mapping[str, Any]], population_hash: str, nonce_hex: str
) -> list[dict[str, Any]]:
    rows = [dict(x) for x in units]
    rows.sort(
        key=lambda row: selection_score(
            population_hash, nonce_hex, "REVIEW_CASE_ORDER", str(row["review_unit_id"])
        )
    )
    return [
        {
            **row,
            "blind_case_id": blind_case_id(population_hash, nonce_hex, str(row["review_unit_id"])),
            "case_ordinal": i,
        }
        for i, row in enumerate(rows, start=1)
    ]


def select_hidden_repeats(
    ordered_units: Sequence[Mapping[str, Any]],
    population_hash: str,
    nonce_hex: str,
    *,
    fraction: float = 0.05,
) -> list[str]:
    if not 0.05 <= fraction <= 0.10:
        raise ASOCSSamplingError("HIDDEN_REPEAT_FRACTION_OUTSIDE_PLAN")
    if not ordered_units:
        return []
    count = max(1, math.ceil(len(ordered_units) * fraction))
    ranked = sorted(
        ordered_units,
        key=lambda row: selection_score(
            population_hash, nonce_hex, "HIDDEN_REPEAT", str(row["review_unit_id"])
        ),
    )
    return [str(row["blind_case_id"]) for row in ranked[:count]]
