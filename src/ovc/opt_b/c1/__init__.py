"""OPT-B.C1 v2 atomic-fact namespace.

The exact remote-verified Discovery and Development v2 releases are active
under the current selector record and may feed the active C2 vNext core inside
the current stack envelope. The legacy ``AUTHORITY_STATE`` token is retained
for historical B1-G5 replay/test compatibility; current orchestration must use
``CURRENT_AUTHORITY_STATE`` or the central active-stack pointer. Validation
remains LOCKED_UNCONSUMED and no publication, probability, risk, exposure,
trading, execution, or agent-write authority is implied by import.
"""

from .adapter import InputRejected, adapt
from .builder import build
from .serialization import dumps, to_dict
from .validation import validate

AUTHORITY_STATE = "B1_G5_SHADOW_SELECTED_C2_DENIED"
CURRENT_AUTHORITY_STATE = "ACTIVE_DISCOVERY_AND_DEVELOPMENT"
FORMULA_REGISTRY_ID = "C1.FORMULAS.v0.1"
FORMULA_COUNT = 18

__all__ = [
    "AUTHORITY_STATE", "CURRENT_AUTHORITY_STATE", "FORMULA_REGISTRY_ID", "FORMULA_COUNT",
    "InputRejected", "adapt", "build", "dumps", "to_dict", "validate",
]
