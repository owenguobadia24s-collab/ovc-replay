"""OPT-B.C1 v2 atomic-fact namespace.

B1-G2 has accepted the exact WP4F-frozen Discovery and Development release
inventories and authorised their bounded immutable R2 publication through WP5.
No C1 selector, C2 handoff, Validation consumption, probability, exposure,
trading or execution authority is active.
"""

from .adapter import InputRejected, adapt
from .builder import build
from .serialization import dumps, to_dict
from .validation import validate

AUTHORITY_STATE = "B1_G2_PUBLICATION_READY_WP5_AUTHORISED"
FORMULA_REGISTRY_ID = "C1.FORMULAS.v0.1"
FORMULA_COUNT = 18

__all__ = [
    "AUTHORITY_STATE", "FORMULA_REGISTRY_ID", "FORMULA_COUNT",
    "InputRejected", "adapt", "build", "dumps", "to_dict", "validate",
]
