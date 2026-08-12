"""C2E v0.2 active-engine implementation package.

The current stack binds this implementation to the exact operator-selected
boundary pack and permits governed active-C2-vNext Discovery/Development inputs
inside the existing GBPUSD BID/ASK 15M/2H_A_L envelope. Exact June population,
run-token and date-window identities are no longer activation identities.
Importing this package cannot replace the boundary pack, change boundary
semantics or thresholds, fetch a newly governed provider source, consume
Validation, publish, promote family/semantic state, or create probability, risk,
exposure, trading, execution, or agent-write authority.
"""

from .handoff import C2EHandoffError, build_input_frame

AUTHORITY_STATE = "ACTIVE_ENGINE_CURRENT_OPERATOR_SELECTED_PACK_MARKET_ENVELOPE_BOUND"

__all__ = ["AUTHORITY_STATE", "C2EHandoffError", "build_input_frame"]
