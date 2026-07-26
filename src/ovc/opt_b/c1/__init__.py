"""OPT-B.C1 v2 atomic-fact namespace.

WP2 has frozen the primitive contract, formula registry, null policy and record/release schemas.
WP3 may implement the reference engine against approved synthetic/golden fixtures only.
No market replay, release, selector, downstream, probability or execution authority exists.
"""

AUTHORITY_STATE = "WP2_CONTRACTS_FROZEN_WP3_SYNTHETIC_ENGINE_AUTHORISED"
FORMULA_REGISTRY_ID = "C1.FORMULAS.v0.1"
FORMULA_COUNT = 18

__all__ = ["AUTHORITY_STATE", "FORMULA_REGISTRY_ID", "FORMULA_COUNT"]
