# DIASI DGS full-shadow cutover-readiness contract v0.1

WP5 qualifies the complete DGS CORE route in side-effect-free shadow and prepares—but does not cross—the reserved `DIASI-G-DGS-CUTOVER-DRAIN` boundary.

The selected class is the WP0-frozen `DSAI_VIT_RECEIPT_ONLY_V0_1`. Shadow equivalence covers admission, dispatch, qualification, receipt, successor, and currentness outcomes against the complete reference route. The closed adversarial universe is `DIAS-AV-01` through `DIAS-AV-16`.

The shadow firewall requires zero physical-main writes, detached-ledger writes, live status writes, live dispatches, intake freezes, writer transfers, CERS/PES mutations, and parent-RAC evidence writes. Any nonzero value invalidates the shadow evidence and blocks the gate.

Cutover-scope coverage requires all six incumbent CERS/PES functions to have an inactive, shadow-qualified owner-local replacement with complete trigger, reconciliation, currentness, and gate-time in-flight disposition. This closes only the selected cutover scope. It authorises neither a global intake freeze nor retirement/removal.

`DIASI-G5-DGS-CUTOVER-READY` is auto-ratifiable when full shadow, the complete reference route, protection/currentness, route and writer fencing, qualification-transfer rehearsal, rollback rehearsal, receipt reconstruction, fresh-process recovery, and frozen budgets all pass. G5 has no live effect.

Only an exact operator PASS at `DIASI-G-DGS-CUTOVER-DRAIN` may authorise WP6/WP7A to activate the selected route, advance fencing, atomically transfer the qualification-ledger writer, freeze/drain the exact old intake scope, and disable-retain the old route under the bounded rollback envelope. Deletion, retirement, proof substitution, ruleset mutation, and every scientific/protected consequence remain denied.
