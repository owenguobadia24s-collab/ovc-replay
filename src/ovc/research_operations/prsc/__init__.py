"""EC1 Post-Recurrence Scientific Challenge (PRSC) Research Operations namespace.

Research-only, non-authoritative challenge machinery. This package grants no market
or selector authority, no candidate-freeze or activation authority, no Validation or
publication authority, and no probability/risk/exposure/execution authority or
agent-write authority. Real-source PRSC challenge remains separately gated; missing
authority fails closed.
"""
from .contracts import (
    CHALLENGE_DIMENSIONS,
    PRSCContractError,
    adapt_ec1_record,
    build_protocol_generation,
    semantic_id,
)
__all__ = ["CHALLENGE_DIMENSIONS","PRSCContractError","adapt_ec1_record","build_protocol_generation","semantic_id"]
