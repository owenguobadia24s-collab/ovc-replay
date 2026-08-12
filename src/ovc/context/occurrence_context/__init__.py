"""Active-foundation, non-structural standalone OccurrenceContext package.

The accepted v0.1 contract may produce deterministic contextual enrichment and
append-only successors around governed structural occurrences. It cannot mutate
C2/C2E identity or history. Representation input remains denied by default;
Validation, C2P activation, selector replacement, publication, probability,
risk, exposure, trading, execution and agent-write authority remain unavailable.
"""

from .builder import OccurrenceContextError, build_context, build_occurrence_key
from .models import BuildRequest, ContextDependencyRef, OccurrenceAnchorRef
from .replay import replay_contexts
from .supersession import create_supersession

AUTHORITY_STATE = "ACTIVE_FOUNDATION_NONSTRUCTURAL_ENRICHMENT"

__all__ = [
    "AUTHORITY_STATE",
    "BuildRequest",
    "ContextDependencyRef",
    "OccurrenceAnchorRef",
    "OccurrenceContextError",
    "build_context",
    "build_occurrence_key",
    "create_supersession",
    "replay_contexts",
]
