# DIASI DGS selected-class live cutover contract v0.1

This contract applies only to `DSAI_VIT_RECEIPT_ONLY_V0_1` under the materially integrated `DIASI-G-DGS-CUTOVER-DRAIN` PASS.

1. The cutover is one atomic protected-main state change: freeze the exact incumbent intake, enumerate and disposition every exact-scope in-flight item, advance both route and qualification-writer fences to generation 2, open the successor intake, and leave the incumbent route disabled-retained.
2. `VIT_QUALIFICATION_OWNER_LOCAL` owns envelope write, exact-head publication, and idempotent replay for the selected class. PES generation 1 events for that class are stale and fail closed. Non-selected PES/CERS scopes are unchanged.
3. The physical controller remains `DSAI_VIT_PHYSICAL_CONTROLLER` through `DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY`. There is one physical writer and no parallel merge route.
4. Every selected-class candidate remains subject to the complete canonical reference assurance route. This cutover performs no proof substitution or assurance compression.
5. A selected-class publisher must prove every logical change is an ADD or MODIFY of a receipt JSON path admitted by the active RAC owner policy. A caller-supplied class label cannot widen the class.
6. Unknown in-flight state, stale fences, writer mismatch, GRT/protection drift, incomplete receipts, A3 mismatch, or reference divergence blocks or rolls back the exact class. No global freeze follows.
7. PES/CERS code, contracts, registries, credentials, triggers, detached evidence, and history remain retained until a separate `DIASI-G-DGS-RETIRE-REMOVE` PASS.
