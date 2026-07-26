"""OPT-B.C1 v2 atomic-fact namespace.

B1-G5 has selected the exact remote-verified Discovery and Development C1
releases as SHADOW derived-fact authorities. Shadow selection permits bounded
inspection and comparison only. C2 consumption remains denied pending a
separate handoff review; Validation, probability, exposure, trading and
execution authority remain unavailable.
"""

from .adapter import InputRejected, adapt
from .builder import build
from .serialization import dumps, to_dict
from .validation import validate

AUTHORITY_STATE = "B1_G5_SHADOW_SELECTED_C2_DENIED"
FORMULA_REGISTRY_ID = "C1.FORMULAS.v0.1"
FORMULA_COUNT = 18

__all__ = [
    "AUTHORITY_STATE", "FORMULA_REGISTRY_ID", "FORMULA_COUNT",
    "InputRejected", "adapt", "build", "dumps", "to_dict", "validate",
]
