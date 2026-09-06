"""Inactive repository-native RRSCG R2 continuation-constraint kernel.

Conformance-only research-operations transport. This namespace grants no capability
activation, ACTIVE_DISCOVERY, ACTIVE_DEVELOPMENT, ACTIVE_VALIDATION, selector
replacement, semantic promotion, publication, probability/risk/exposure/E-H,
trading/execution, or agent-write authority.
"""
from .kernel import *
from .d10 import (
    D10_ALGORITHM_ID,
    D10_CAPABILITY_STATE,
    D10_CLAIM_CAP,
    D10_PACKAGE_SHA256,
    D10_REDUCER_PACK_ID,
    D10ReducerBindingError,
    D10ReducerRecord,
    reduce_d9_state,
)
