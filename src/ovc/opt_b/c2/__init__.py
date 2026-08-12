"""Pre-redesign OPT-B.C2 v2 parallel-state namespace.

The historical v2 state/transition implementation and selector records are
preserved for exact lineage and explicitly marked historical replay only. They
are denied as parents/selectors for new evidence under the current active stack.
The legacy ``AUTHORITY_STATE`` token is retained for historical compatibility;
current orchestration must use ``CURRENT_AUTHORITY_STATE`` or the central
active-stack pointer.
"""

AUTHORITY_STATE = "DESIGN_AND_FIXTURES_ONLY"
CURRENT_AUTHORITY_STATE = "LEGACY_INACTIVE_NEW_EVIDENCE_DENIED"
__all__ = ["AUTHORITY_STATE", "CURRENT_AUTHORITY_STATE"]
