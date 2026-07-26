"""OPT-B.C1 v2 atomic-fact namespace.

WP4 has completed the B1-G0-bounded Discovery and Development replay with deterministic QA.
The resulting artifact is a local candidate only: selectors, R2 publication, Validation,
downstream, probability, exposure, trading and execution authority remain absent.
"""

from .adapter import InputRejected, adapt
from .builder import build
from .serialization import dumps, to_dict
from .validation import validate

AUTHORITY_STATE = "WP4_REPLAY_QA_PASS_LOCAL_CANDIDATE"
FORMULA_REGISTRY_ID = "C1.FORMULAS.v0.1"
FORMULA_COUNT = 18

__all__ = [
    "AUTHORITY_STATE", "FORMULA_REGISTRY_ID", "FORMULA_COUNT",
    "InputRejected", "adapt", "build", "dumps", "to_dict", "validate",
]
