# RRSCG C2-owner and IROF transport contract v0.1

**Contract ID:** `RRSCG.C2.OWNER.IROF.TRANSPORT.v0.1`  
**Status:** inactive conformance transport  
**Authority effect:** none

The RRSCG owner adapter consumes only
`C2.VNEXT.OWNER.STRUCTURAL.SNAPSHOT.READ.HANDOFF.v0.1` from owner generation
`C2VNEXT.OWNER.GENERATION.ASR00.C2AR-PACKAGE-v1.READ-v0.1`.

It verifies the snapshot content identity, source binding, instrument, side,
local and parent clocks, effective time, first-valid time, missingness and
read-only authority envelope. It preserves the complete owner snapshot as a
nested owner object. It may not flatten, infer, repair, select, impute or mutate
owner records.

The IROF pack reuses existing `StageSpec`, `PipelineProfile`, `PopulationSpec`,
`AuthorityBinding`, semantic cache and checkpoint/restart contracts. The pack
adds no runner, scheduler, cache plane, checkpoint plane or orchestration
framework. Stage registration grants no execution authority.

The current pack is executable only for synthetic conformance populations in
the existing GBPUSD, BID/ASK, 15M with 2H_A_L parent envelope. A real-source
run requires a separately effective population/source authority and a later
versioned admission. Validation remains locked-unconsumed.

D10 is a reducer-only child of the D9 observer stage. D9 state, geometry,
motion and trajectory remain the reference faculty.

Rollback is forward-only supersession of this adapter or stage pack while
preserving owner and IROF identities, generated evidence and Git history.
