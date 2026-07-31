# PD-JUNE-FULL-MONTH-MDR Source and Review Contract Amendment A1

## Binding and precedence

This amendment is bound to `PD-JUNE-FM-A1-JULY-NATIVE-H1-WAIVER` and supersedes only the base contract clauses that require a July 2026 native-H1 monthly transport. Every other clause of `PD_JUNE_FULL_MONTH_MDR_SOURCE_AND_REVIEW_CONTRACT_v0_1.md` remains in force.

## Unchanged boundary

- target: `[2026-06-01T00:00:00Z, 2026-07-01T00:00:00Z)`;
- context source: `[2026-05-30T00:00:00Z, 2026-07-03T00:00:00Z)`;
- May and July eligibility: `CONTEXT_ONLY`;
- source slice: `RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1`.

July 1–2 M1 context remains mandatory. Removing that context is not authorised.

## Amended provider transports

The provider request plan must contain exactly:

- 68 daily M1 transports: 34 per side, May 30 through July 2 inclusive;
- 4 monthly native-H1 transports: May and June only, per side;
- 72 provider objects in total;
- zero July native-H1 requests.

The July native-H1 status must be recorded as `WAIVED_BY_OPERATOR_A1_PROVIDER_OBJECT_UNAVAILABLE`.

## Combined H1 logical stream

Each side's accepted H1 source object is one deterministic logical stream:

- May 30 through June 30: clipped native H1;
- July 1 through July 2: M1-derived H1 from complete 60-minute membership.

Its provenance must be `NATIVE_MAY_JUNE_PLUS_M1_DERIVED_JULY_CONTEXT`.

M1-derived H1 is permitted only for post-target context. It may not replace native May or June H1, alter the target interval, repair a gap, or introduce a source timestamp that is not supported by 60 complete M1 members.

## QA

Acceptance requires:

- zero duplicate or non-monotonic M1/H1 rows;
- all non-weekend M1 gaps absent;
- exact M1 and combined-H1 BID/ASK timestamp pairing;
- exactly 48 derived July context H1 hours per side;
- zero missing or unexpected derived July hours;
- native May/June H1 reconciliation against complete M1-derived H1 with zero OHLC mismatch;
- explicit recording of native-covered and M1-derived intervals;
- no provider repair, interpolation, forward fill or synthetic price insertion.

A missing July M1 minute that prevents a complete context hour blocks and quarantines the run. The programme may not classify such an hour as complete.

## Evidence

The manifest, provider receipt, inventory, coverage QA, H1 reconciliation and freeze receipt must all record:

- amendment `PD-JUNE-FM-A1-JULY-NATIVE-H1-WAIVER`;
- native July H1 waiver;
- post-target M1-derived H1 authority;
- non-release, selector-ineligible, R2-denied and Validation-denied state.

## Authority boundary

This amendment grants no formula, threshold, semantic, trigger-definition, candidate-definition, distance, clustering or model change; no promotion; no selector or release mutation; no canonical 2021–2023 Discovery processing or append; no R2 publication; no Validation consumption; and no probability, risk, exposure, trading, execution or agent-write authority.

## Rollback

Preserve the provider incident and quarantine. Correct A1 only through new non-destructive commits. Never reuse or relabel incomplete quarantine material as an accepted source slice.