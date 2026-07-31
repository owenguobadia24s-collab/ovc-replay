# PD-JUNE-FULL-MONTH-MDR Source and Review Contract v0.1

## Binding

This contract binds `PD-JUNE-FULL-MONTH-MDR` to one exact target month and one deterministic context interval.

- target: `[2026-06-01T00:00:00Z, 2026-07-01T00:00:00Z)`
- context source: `[2026-05-30T00:00:00Z, 2026-07-03T00:00:00Z)`
- instrument: `GBPUSD`
- sides: `BID`, `ASK`
- provider: `DUKASCOPY`
- transport clocks: native `M1`, native `H1`
- derived clocks: existing approved `15M`, `2H_A_L`

May and July records are context-only. A target-eligibility predicate must reject every timestamp before June 1 or on/after July 1.

## Context derivation

The context duration is the maximum of all declared computational and review horizons, not an arbitrary calendar extension.

- 15M C2 level history: 32 bars = 8 hours.
- 2H_A_L C2 level history: 24 bars = 48 hours.
- largest previous-state requirement: 2 hours.
- repeated-switching history: 6 × 15M = 90 minutes.
- bounded candidate completion horizon: 48 hours.

The resulting pre-target and post-target buffers are each 48 hours.

Any future implementation dependency that requires more than 48 hours must fail closed and return to an operator gate before source execution. It may not silently widen the source interval.

## Intake rules

Provider execution is operator-local only and prohibited in CI or GitHub Actions.

The source intake must request:

- 34 daily M1 partitions per side from May 30 through July 2 inclusive;
- three monthly H1 transports per side for May, June and July 2026;
- exact clipping to the source interval.

All source objects and replay outputs remain outside Git under `OVC_EXTERNAL_ARTIFACT_ROOT`.

The frozen source manifest must include:

- provider path, URL, transport hash and size;
- logical stream, accepted interval and row count;
- first and last accepted timestamps;
- source CSV hash and schema fingerprint;
- exact target and context classification;
- immutable source-slice identity;
- release status `NOT_A_RELEASE`;
- selector eligibility `NONE`;
- R2 publication `DENIED`.

## Source acceptance

Acceptance requires:

1. exact BID/ASK timestamp pairing for each logical clock;
2. zero duplicate and zero non-monotonic rows;
3. all non-weekend discontinuities explicitly listed;
4. boundary coverage sufficient for the exact source interval;
5. native H1 reconciliation against complete M1-derived H1 bars with zero OHLC mismatch;
6. no overwrite of an existing source destination;
7. quarantine on any failure;
8. no provider repair, interpolation or silent row insertion.

Weekend and documented market-closure gaps may be accepted only when symmetric across BID and ASK and explicitly recorded.

## Replay rules

Replay must use the existing approved OPT-A, C1, C2 and Pattern Discovery code and frozen parameters. This programme may add orchestration, filtering, manifests, review presentation and assurance checks, but it may not change market semantics.

The replay must preserve separate source and target classifications:

- `CONTEXT_PRE_TARGET`
- `TARGET_JUNE`
- `CONTEXT_POST_TARGET`

Only `TARGET_JUNE` may enter the scored population.

## Evidence-completeness rules

Every June target state and candidate receives one completeness classification:

- `COMPLETE`
- `SOURCE_BOUNDARY_INCOMPLETE`
- `PROVIDER_GAP_INCOMPLETE`
- `ALGORITHMIC_NOT_EVALUATED`
- `ALGORITHMIC_NOT_EVALUABLE`
- `PRESENTATION_INCOMPLETE`

`SOURCE_BOUNDARY_INCOMPLETE` must be zero before operator review.

The audit must not convert algorithmic non-evaluation into a pass. It must expose the exact axis, reason code, missing source dependency and whether the state could have been evaluated with the approved source interval.

## Review-card rules

A blinded card must expose enough information for an operator to independently assess the description without seeing candidate/control class or the answer key.

Required card evidence:

- exact UTC target and surrounding timestamps;
- 15M OHLC bars and five C2 axis payloads;
- actual active levels, values, types and relation identities;
- persistence counts and the sequence that produced them;
- source transitions and trigger calculation;
- 2H parent state and parent levels when the scope uses parent context;
- explicit quality, exclusions, gaps and completeness class;
- pre-trigger and post-trigger state sequence through natural closure or 48-hour maximum.

Required questions are separate:

1. trigger classification;
2. structural-description verdict;
3. evidence-completeness verdict;
4. pilot-object disposition;
5. confidence and reason.

## Population and controls

The review construction must cover all June weeks, both sides, both local and 2H-parent scopes, multiple UTC sessions and both trigger and non-trigger observations.

Controls must not overlap target candidate source-state identities or one another. Control selection, suppression and exclusions must be deterministic and recorded before unblinding.

## Authority boundary

This contract grants no formula, threshold, semantic, trigger-definition, candidate-definition, distance, clustering or model change; no promotion; no selector or release mutation; no canonical 2021–2023 Discovery processing; no R2 publication; no Validation consumption; and no probability, risk, exposure, trading, execution or agent-write authority.

## Rollback

Derived local source, replay and review objects may be deleted and deterministically rebuilt from the immutable provider transports and compact manifests. Repository corrections require new non-destructive commits. Prior CORR2 evidence and all decision history remain preserved.