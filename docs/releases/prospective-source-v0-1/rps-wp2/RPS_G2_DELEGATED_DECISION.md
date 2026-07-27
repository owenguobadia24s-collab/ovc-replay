# RPS-G2 — Delegated Source-Slice Acceptance Decision

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-WP2`
- Gate: `RPS-G2`
- Decision: `PASS`
- Authority: `DELEGATED_AUTO_EXECUTABLE_WITHIN_RPS_G1B`
- Baseline main: `18ba74378ece734647801576f373d68b4ba8687f`
- Tested evidence head: `be01c0d2d272bb89aad5aa4279189dc802b991e4`
- Canonical workflow: `30289144879`
- Canonical unit-test job: `90054311140`
- Slice: `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`
- Coverage: `GAPPED`
- QA: `PASS`

## Decision

Accept the compact evidence for the exact checksum-pinned local June source slice and complete RPS-WP2. The source is available only as an immutable local `GAPPED` prospective source, not as a release or active evidentiary input.

The decision relies on the previously granted operator authority in RPS-G1B. It introduces no new source-integrity rule and therefore remains within the approved auto-executable envelope.

## Evidence

- manifest logical SHA-256: `429b7b568b7a43d04893c1873773f0b1b567730f2d5d4122d6a1c06dd40e3e41`
- manifest file SHA-256: `8509b6cc66814663786e429e6ba1dc0c3497482fc6ac8ceb016cfc1867ec78eb`
- quarantine inventory logical SHA-256: `ce58bc91ea36e920fa2f855a96ee7084e5d867b976a0d06a9e94bf65b20084c2`
- four source-object identities and hashes recorded in `RPS_WP2_COMPACT_EVIDENCE_INDEX.json`
- gap, BID/ASK, native-H1 and downstream-coverage QA: PASS
- original source quarantine unchanged after copy: true
- provider network access during recovery: false
- canonical repository tests: PASS

## Accepted scope

- one immutable local source slice;
- M1 BID and ASK with 35 explicit absent minutes;
- native H1 BID and ASK as reconciliation controls;
- 271 complete 15M parents;
- 64 complete M1-derived H1 parents;
- 30 complete 2H parents;
- deterministic exclusion of every incomplete parent.

## Authority retained as denied

Provider retry, gap repair, forward fill, interpolation, synthesis, incomplete-parent consumption, selector or release mutation, R2 publication, Validation consumption, LIVE_PROSPECTIVE append, ACTIVE_RESEARCH_TRIAGE, semantic or theory promotion, probability, risk, exposure, trading, execution and agent write remain denied.

## Rollback

Revert this bounded acceptance state and preserve all local frozen and quarantined evidence. No deletion, relabelling, source mutation or history rewrite is authorised.

## Next packet

`RPS-WP3 — derived local prospective compute and exact source binding`.
