# OVC DSAI v0.3 VIT Ledger, Train, Conflict & Invalidation Contract v0.1

Authority: prospective/shadow implementation only. No physical repository write authority is introduced.

## Ledger
`VirtualIntegrationLedger` is append-only. One admitted `PacketIntegrationPayload` on one exact predecessor creates at most one logical placement record for that exact `(payload_id, predecessor_tree, apply_profile)` tuple. Exact resubmission is idempotent. Reordering or repair creates a new placement/generation; historical generations are never edited.

## Train
`IntegrationTrainGeneration` is immutable and starts from one exact `PhysicalMainAnchor`. It records one ordered prospective path, its scheduling reason, supersession lineage and exactly one active materialisation-path flag. Train ordinals are placement state, never packet identity.

## Conflicts
Path-level prospective mutation overlap is classified conservatively. Exact same payload is idempotent; disjoint mutations are `COMMUTATIVE` absent a declared dependency; shared-path divergent mutation is `ORDER_SENSITIVE` or `MUTUALLY_EXCLUSIVE`; undeclared/insufficient evidence is `UNKNOWN` and fails closed. `SAFE_BYPASS` is allowed only when there is no dependency edge and no order-sensitive/serial/mutually-exclusive/unknown conflict.

## Selective invalidation
A placement-only predecessor change emits `PLACEMENT_RECOMPUTE_ONLY`. Base-sensitive proof invalidation emits `ASSURANCE_RENEWAL_REQUIRED`. A dependency/source change that alters payload meaning emits `PAYLOAD_REBUILD_REQUIRED`. Authority-frontier change emits `AUTHORITY_REVIEW_REQUIRED`. Global invalidation is forbidden when the exact dependency frontier proves a narrower impact.

## Scheduling
Build scheduling and integration ordering are distinct. The reference scheduler is deterministic, fair by admission sequence within equal dependency readiness, and work-conserving: it does not idle an eligible safe-bypass packet merely because an unrelated earlier packet is blocked.

## Non-authority
VIT ordering, queue age, safe bypass, conflict classification, technical PASS and prospective depth cannot create authority. Physical main remains the court record and parallel physical merge remains false.
