# C2 vNext Real-Source Observation Materialisation Contract v0.1

**Packet:** `C2VNEXT-REAL-OBS-MATERIALISATION-20260809`  
**Programme:** `OVC-C2AR-JUNE-OBSERVATION-MATERIALISATION-CORRECTIVE-v0.1`  
**Operator authority:** `C2VNEXT-RM1.OPERATOR.APPROVE.20260809T115300+0100`

## Purpose
Materialise the already-accepted June GBP/USD C1 evidence into the physically missing C2 vNext observation-level surface required by the frozen revised-C2 -> C2E handoff. This is a bounded upstream corrective packet. It does not alter the active C2 selector or any frozen C2AR scientific definition.

## Exact source binding
- source slice: `RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1`
- source manifest SHA-256: `1578b555f3d5aa2822b603141261f86a047096030e5faacd4380ef2c6d4f52e3`
- C1 release: `RPS.C1SET.GBPUSD.PD-JUNE-FM.20260530_20260703.v1`
- C1 manifest: `RPS.C1MANIFEST.PD-JUNE-FM.9cad7d7274091b27fb153c99`
- revised-C2 package: `C2AR.INTEGRATED.SHADOW.PACKAGE.v1`
- revised-C2 package SHA-256: `150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3`
- local grain: GBPUSD / BID+ASK / 15M / `LATTICE.15M.UTC_0000.v1`
- parent grain: same side / `2H_A_L` / `LATTICE.2H.UTC_0000.v1`
- context: `[2026-05-30T00:00:00Z, 2026-07-03T00:00:00Z)`
- target: `[2026-06-01T00:00:00Z, 2026-07-01T00:00:00Z)` using accepted C1 `target_eligible` membership.

No provider request is permitted. The four named accepted C1 payloads are the only market inputs.

## Materialised surface
For each source-complete 15M observation, emit deterministic C2 observation identity and first-valid chronology; typed trailing-count horizon memberships for all three already-frozen candidate horizons 4, 8 and 16; trailing-range HIGH/LOW/MIDPOINT measurement levels for every computable candidate horizon; corresponding measurement containers; raw location relations and complete relation-set inventories over that declared measurement surface; four structural profile families `LOCATION`, `MOTION`, `ORGANISATION`, `INTERACTION`; an exact fixed-parent 2H context bundle or explicit `EXPECTED_PARENT_SLOT_MISSING`; and one compact observation bundle resolving every identity.

All three horizon candidates are emitted. No horizon is selected or promoted. Pivot/swing structural candidates are outside this smallest corrective materialisation packet and are not silently inferred or declared absent from C2 generally.

## Adapter invariants
1. Horizon evaluator `COMPUTABLE` maps to formula-profile membership `COMPLETE`; a non-computable horizon maps its exact frozen reason code into the formula-profile non-complete status. The horizon record itself is retained unchanged.
2. Parent-context `bundle_id` is the source identity exposed downstream as `context_bundle_id`; bundle payload is unchanged.
3. C1 numeric price strings are parsed to existing C2 vNext float geometry inputs; no new normalization is introduced.
4. The optimized trailing-count membership path must be byte-for-byte equal to `evaluate_horizon(..., consumer_class="C2_MEASUREMENT")` for the same frozen definition and observation ledger. CI tests this equivalence.

## Evidence and missingness
Not-computable output is lawful evidence. No gap is bridged. No missing 2H parent is replaced by an older parent. No global QUALITY gate is introduced. All target records retain source continuity segment and first-valid chronology.

`profile_output_id` remains content-addressed as defined by the frozen formula-profile implementation. Identical empty/not-computable content may therefore be referenced by more than one observation; the external profile store deduplicates only when complete canonical payloads are byte-identical.

## Authority
Allowed by operator approval: read exact accepted C1 artifacts; deterministically derive and freeze the inactive/shadow observation-level surface; write large derived outputs to external artifact storage; commit compact contracts, code, tests, hashes, QA and state; expose the result to later C2E replacement-run preparation read-only.

Denied: new provider intake; source repair/interpolation; active C2 selector or clock/lattice change; new threshold; semantic/event/family/theory/model promotion; outcome use; Development/Validation consumption; canonical/R2 publication; C2E activation; agent write; probability, risk, exposure or execution.

## Acceptance
PASS requires exact input hashes; 4,072 target 15M observations = 2,036 BID + 2,036 ASK; every target observation resolves one LOCATION, three MOTION, one ORGANISATION and one INTERACTION profile reference plus a parent-context bundle; all references resolve; two clean materialisations are byte-equivalent; no parent is first-valid after its local observation; no target row is sampled; external artifacts are hash-bound; repository tests pass; reserved authority remains unchanged.

## Rollback
The materialisation is inactive and additive. Rollback is to stop consuming its immutable identity and preserve its artifacts/receipts as historical evidence. Do not rewrite C1, C2AR, C2E or historical operator decisions.
