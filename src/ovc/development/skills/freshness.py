from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ovc.development.identity import canonical_sha256


@dataclass(frozen=True)
class BaseFreshnessPolicy:
    max_readonly_commit_distance: int = 5
    max_readonly_elapsed_minutes: int = 30

    def __post_init__(self) -> None:
        if not 0 <= self.max_readonly_commit_distance <= 5:
            raise ValueError("packet freshness policy may tighten but not loosen 5-commit default")
        if not 0 < self.max_readonly_elapsed_minutes <= 30:
            raise ValueError("packet freshness policy may tighten but not loosen 30-minute default")

    def assess(
        self,
        *,
        baseline_main_sha: str,
        current_main_sha: str,
        commit_distance: int,
        elapsed_minutes: int,
        dependency_or_write_overlap: bool,
        mutating: bool,
        merge_candidate: bool,
    ) -> dict[str, Any]:
        if commit_distance < 0 or elapsed_minutes < 0:
            raise ValueError("freshness distances must be non-negative")
        moved = baseline_main_sha != current_main_sha
        reasons: list[str] = []
        if dependency_or_write_overlap:
            reasons.append("DEPENDENCY_OR_WRITE_SET_OVERLAP")
        if moved and (mutating or merge_candidate):
            reasons.append("MAIN_MOVED_WRITE_SIDE_EFFECT_REPREFLIGHT")
        if moved and not (mutating or merge_candidate):
            if commit_distance > self.max_readonly_commit_distance:
                reasons.append("READONLY_COMMIT_WINDOW_EXPIRED")
            if elapsed_minutes >= self.max_readonly_elapsed_minutes:
                reasons.append("READONLY_TIME_WINDOW_EXPIRED")
        status = "RE_PREFLIGHT_REQUIRED" if reasons else "FRESH"
        logical = {
            "baseline_main_sha": baseline_main_sha,
            "current_main_sha": current_main_sha,
            "main_moved": moved,
            "commit_distance": commit_distance,
            "elapsed_minutes": elapsed_minutes,
            "dependency_or_write_overlap": dependency_or_write_overlap,
            "mutating": mutating,
            "merge_candidate": merge_candidate,
            "status": status,
            "reason_codes": sorted(set(reasons)),
        }
        return {
            "schema": "ovc-dsai-base-freshness-receipt/v1",
            **logical,
            "authority_effect": "NONE",
            "receipt_id": canonical_sha256(logical, role="DSAI_BASE_FRESHNESS"),
        }
