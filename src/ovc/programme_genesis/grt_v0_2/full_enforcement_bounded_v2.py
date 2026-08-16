"""Compatibility facade for the final direct-typed full-G3 replay correction."""
from __future__ import annotations

from .full_enforcement_bounded_v3 import (
    FullG3ReplayError,
    REQUIRED_FULL_G3_RULE_FAMILIES,
    replay_full_g3_candidate,
)

__all__ = [
    "FullG3ReplayError",
    "REQUIRED_FULL_G3_RULE_FAMILIES",
    "replay_full_g3_candidate",
]
