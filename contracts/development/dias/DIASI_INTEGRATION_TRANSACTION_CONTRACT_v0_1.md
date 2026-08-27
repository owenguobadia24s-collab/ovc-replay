# DIASI IntegrationTransaction contract v0.1

An `IntegrationTransaction` is a durable derivative state machine bound to one immutable PIP, exact owner facts, trigger coverage, writer-generation fence, event cursor, idempotence key, and bounded recovery budget. It creates no authority and requires no chat, cache, PES, or CERS runtime state.

Every nonterminal state has at least one durable trigger, a reconciliation route, a positive maximum age, and a dead-letter disposition. Duplicate event identities are no-ops. Unknown or stale writers are quarantined. Invalid transitions consume bounded recovery capacity and dead-letter when exhausted. `WRITE_UNKNOWN` is reconstructed from durable facts before continuation.
