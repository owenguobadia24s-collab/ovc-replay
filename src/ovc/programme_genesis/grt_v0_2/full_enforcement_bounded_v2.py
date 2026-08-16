"""Compatibility facade for the final direct-typed full-G3 replay correction."""
from __future__ import annotations

from . import full_enforcement_bounded_v3 as _impl

# Forward declared-path references may form longer source chains. This bound
# permits deterministic fixed-point convergence while the 256-path capacity
# circuit breaker remains the controlling fail-closed limit.
_impl._MAX_FORWARD_ROUNDS = 16

FullG3ReplayError = _impl.FullG3ReplayError
REQUIRED_FULL_G3_RULE_FAMILIES = _impl.REQUIRED_FULL_G3_RULE_FAMILIES
replay_full_g3_candidate = _impl.replay_full_g3_candidate

__all__ = [
    "FullG3ReplayError",
    "REQUIRED_FULL_G3_RULE_FAMILIES",
    "replay_full_g3_candidate",
]
