"""Standalone, non-structural OccurrenceContext engineering package."""

from .builder import OccurrenceContextError, build_context, build_occurrence_key
from .models import BuildRequest, ContextDependencyRef, OccurrenceAnchorRef
from .replay import replay_contexts
from .supersession import create_supersession

__all__ = [
    "BuildRequest",
    "ContextDependencyRef",
    "OccurrenceAnchorRef",
    "OccurrenceContextError",
    "build_context",
    "build_occurrence_key",
    "create_supersession",
    "replay_contexts",
]
