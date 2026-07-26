"""OPT-B.C1 v2 atomic-fact namespace.

WP3 implements the deterministic reference engine against approved synthetic/golden fixtures only.
No market replay, release, selector, downstream, probability or execution authority exists.
"""

from .adapter import InputRejected, adapt
from .builder import build
from .serialization import dumps, to_dict
from .validation import validate

AUTHORITY_STATE = "WP3_REFERENCE_ENGINE_FIXTURE_TRUST_PASS"
FORMULA_REGISTRY_ID = "C1.FORMULAS.v0.1"
FORMULA_COUNT = 18

__all__ = [
    "AUTHORITY_STATE", "FORMULA_REGISTRY_ID", "FORMULA_COUNT",
    "InputRejected", "adapt", "build", "dumps", "to_dict", "validate",
]
