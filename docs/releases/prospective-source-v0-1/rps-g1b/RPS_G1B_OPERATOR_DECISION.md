# RPS-G1B — Operator Decision

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1`
- Plan version: `0.1`
- Packet: `RPS-WP2`
- Gate: `RPS-G1B`
- Decision: `PASS`
- Authority: `OPERATOR`
- Approval command: `OVC APPROVE RPS-G1B`
- Approved on: `2026-07-27`
- Baseline main: `6aaa898727be83ebf3e5c32ebca129d38e629adb`
- Gate-ready branch head: `3955593633b0680cc0cd79d9135154b9e5b97e52`
- Canonical workflow: `30286888160`
- Canonical unit-test job: `90046787818`
- QA recommendation: `PASS`

## Approved authority delta

Approve one no-network, checksum-pinned re-evaluation and immutable local freeze of only:

- slice `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`;
- quarantine `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1.20260727T160337Z.38a69acd`;
- interval `[2026-06-22T00:00:00Z, 2026-06-25T00:00:00Z)`;
- M1 BID, M1 ASK, native H1 BID and native H1 ASK;
- 25 MiB compressed and 100 MiB expanded limits;
- result `coverage_state: GAPPED` only when every frozen acceptance condition passes.

The approved command may calculate a local checksum inventory, copy and re-hash the exact quarantined transport files in a new staging workspace, materialise immutable QA receipts and freeze one local source slice. It may not contact Dukascopy or any other provider.

## Acceptance basis

- 4,285 M1 rows per side;
- identical BID/ASK timestamp sets;
- 35 absent M1 timestamps in 24 gap runs;
- complete interval boundaries;
- zero duplicate or non-monotonic timestamps;
- 72 native-H1 rows per side with exact BID/ASK pairing;
- 64 complete M1-derived H1 comparisons per side;
- zero missing native-H1 timestamps or OHLC mismatches;
- explicit exclusion of incomplete 15M, M1-derived H1 and 2H parents;
- no repair, interpolation, forward fill or synthesis.

## Retained prohibitions

Another provider request, another quarantine identity, quarantine mutation or relabelling, incomplete-parent consumption, gap repair, interpolation, forward fill, synthetic candles, ACTIVE_RESEARCH_TRIAGE, LIVE_PROSPECTIVE append, live Pattern Discovery processing, active novelty ranking, selector or release mutation, R2 publication, Validation consumption, semantic or theory promotion, probability, risk, exposure, trading, execution and agent write remain denied.

## Rollback

Before a frozen GAPPED source slice exists, revert the RPS-G1B squash merge and withdraw this re-evaluation authority. Preserve the July and June quarantines and any compact local inventory or failure evidence. After a frozen slice exists, quarantine that derived slice and preserve all source and checksum evidence; do not mutate the original quarantine.

## Continuation

1. Commit this decision and authority record.
2. Pin the final PR head and rerun canonical checks.
3. Squash-merge PR #103 into `main` when eligible.
4. Pull `main` locally.
5. Run `preflight`, `inventory` and `freeze` from the RPS-G1B Windows operator guide.
6. Supply the compact manifest and receipts, then resume RPS-WP2 for RPS-G2 evaluation.
