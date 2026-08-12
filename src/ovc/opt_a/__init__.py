"""OPT-A v2 sealed-observation namespace.

Current stack authority permits existing governed GBPUSD Discovery and
Development source consumption. Validation remains LOCKED_UNCONSUMED. The
legacy ``AUTHORITY_STATE`` token is retained for historical test/replay
compatibility; current orchestration must resolve ``CURRENT_AUTHORITY_STATE``
or the central active-stack pointer. Importing this package does not authorize
provider intake, publication, probability, risk, exposure, trading, execution,
or agent writes.
"""

AUTHORITY_STATE = "DESIGN_AND_FIXTURES_ONLY"
CURRENT_AUTHORITY_STATE = "ACTIVE_SEALED_OBSERVATION_INPUT_DISCOVERY_DEVELOPMENT_VALIDATION_LOCKED"
__all__ = ["AUTHORITY_STATE", "CURRENT_AUTHORITY_STATE"]
