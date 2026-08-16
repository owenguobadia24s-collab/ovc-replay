"""Final bounded full-G3 replay facade for correction qualification.

The first bounded adapter proved the performance target but an ordinary pilot
candidate required more than six typed relationship-closure rounds. The
constitutional bound is the impact-path capacity, not an arbitrary six-hop
semantic cutoff. This generation therefore permits deterministic convergence
up to 32 rounds while retaining the 512-path fail-closed capacity limit.
"""
from __future__ import annotations

from . import full_enforcement_bounded as _impl

_impl._MAX_CLOSURE_ROUNDS = 32

REQUIRED_FULL_G3_RULE_FAMILIES = _impl.REQUIRED_FULL_G3_RULE_FAMILIES
FullG3ReplayError = _impl.FullG3ReplayError
replay_full_g3_candidate = _impl.replay_full_g3_candidate
