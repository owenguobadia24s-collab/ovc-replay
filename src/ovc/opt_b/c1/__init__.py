"""OPT-B.C1 v2 atomic-fact namespace.

B1-G1 has accepted the exact WP4 Discovery and Development candidate inventory and
has authorised a controlled durable local freeze of that candidate only. The release
is not yet frozen, published or selected; Validation, downstream, probability,
exposure, trading and execution authority remain absent.
"""

from .adapter import InputRejected, adapt
from .builder import build
from .serialization import dumps, to_dict
from .validation import validate

AUTHORITY_STATE = "B1_G1_CANDIDATE_INVENTORY_ACCEPTED_FREEZE_AUTHORISED"
FORMULA_REGISTRY_ID = "C1.FORMULAS.v0.1"
FORMULA_COUNT = 18

__all__ = [
    "AUTHORITY_STATE", "FORMULA_REGISTRY_ID", "FORMULA_COUNT",
    "InputRejected", "adapt", "build", "dumps", "to_dict", "validate",
]
